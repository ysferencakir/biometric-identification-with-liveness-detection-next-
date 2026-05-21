"""
core/liveness/texture_analyzer.py
-----------------------------------
Çok sinyalli pasif PAD (Presentation Attack Detection).

4 bileşenli ensemble:
  1. Quality gate      — blur / yüz boyutu / pozlama kontrol
  2. FFT replay        — moiré pattern + frekans anomalisi
  3. Speküler glare    — ekran / baskı parlaması
  4. LBP mikrotekstür  — düşük çeşitlilik = sahte
  + MiniFASNet (opsiyonel, yüklüyse ağırlıklı sinyal olarak eklenir)
"""

from __future__ import annotations

import importlib.util
import logging
import time
from pathlib import Path

import cv2
import numpy as np

from core.liveness.base import LivenessDetectorBase, LivenessResult
from core.detection import FaceDetector
from core.preprocessing import prepare_for_insightface

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
_MODEL_DIR   = Path(__file__).parent.parent.parent / "models" / "anti_spoofing"
_MODEL_V2    = _MODEL_DIR / "2.7_80x80_MiniFASNetV2.pth"
_MODEL_V1SE  = _MODEL_DIR / "4_0_0_80x80_MiniFASNetV1SE.pth"
_MFAS_PY     = _MODEL_DIR / "MiniFASNet.py"

_FRAMES_REQ      = 8          # karar için gereken minimum frame
_WINDOW_SECS     = 20.0
_LIVE_THRESHOLD  = 0.55       # ensemble skoru eşiği
_FACE_MARGIN     = 0.25

# Quality gate eşikleri
_MIN_FACE_PX     = 60         # bbox kısa kenar minimum piksel
_MAX_BLUR_VAR    = 15.0       # Laplacian varyans: altı = bulanık
_MIN_BRIGHTNESS  = 30         # ortalama parlaklık
_MAX_BRIGHTNESS  = 230

# FFT eşikleri
_FFT_BAND_LOW    = 0.15       # normalize frekans alt sınır
_FFT_BAND_HIGH   = 0.45       # normalize frekans üst sınır
_FFT_RATIO_THR   = 0.30       # orta bant / toplam enerji oranı eşiği

# Glare eşiği
_GLARE_PCT_THR   = 0.04       # parlak piksel yüzdesi (>%4 şüpheli)

# LBP eşiği
_LBP_ENTROPY_THR = 3.5        # bit cinsinden Shannon entropi alt sınırı

# MiniFASNet ensemble ağırlığı (mevcutsa)
_MFAS_WEIGHT     = 0.35

# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar — Quality Gate
# ---------------------------------------------------------------------------

def _quality_gate(face_bgr: np.ndarray) -> tuple[bool, str]:
    """
    Kalite kontrolü. Geçemezse PAD kararı üretilmez.
    Returns (ok, reason).
    """
    h, w = face_bgr.shape[:2]
    short_side = min(h, w)
    if short_side < _MIN_FACE_PX:
        return False, f"yuz cok kucuk ({short_side}px)"

    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)

    blur_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_var < _MAX_BLUR_VAR:
        return False, f"bulanik kare (var={blur_var:.1f})"

    brightness = float(gray.mean())
    if brightness < _MIN_BRIGHTNESS:
        return False, f"cok karanlik ({brightness:.0f})"
    if brightness > _MAX_BRIGHTNESS:
        return False, f"asiri pozlama ({brightness:.0f})"

    return True, "ok"


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar — FFT Replay
# ---------------------------------------------------------------------------

def _fft_replay_score(face_bgr: np.ndarray) -> float:
    """
    Orta frekans bandındaki enerji oranını döndürür (0–1).
    Ekran/baskı saldırılarında bu bant anormalleşir.
    Düşük oran = gerçek yüz, Yüksek oran = replay şüphesi.
    Döndürülen değer: spoof riski (0=gerçek, 1=sahte).
    """
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    f    = np.fft.fft2(gray)
    fsh  = np.fft.fftshift(f)
    mag  = np.abs(fsh) + 1e-8

    rows, cols = gray.shape
    cy, cx = rows // 2, cols // 2
    max_r = min(cy, cx)

    total = 0.0
    band  = 0.0
    for r in range(1, max_r):
        norm_r = r / max_r
        ring_mask = _ring_mask(rows, cols, cy, cx, r)
        energy = float(mag[ring_mask].sum())
        total += energy
        if _FFT_BAND_LOW <= norm_r <= _FFT_BAND_HIGH:
            band += energy

    ratio = band / (total + 1e-8)
    # Oranı [0,1] spoof riskine dönüştür
    spoof_risk = min(1.0, ratio / _FFT_RATIO_THR)
    return float(spoof_risk)


def _ring_mask(rows: int, cols: int, cy: int, cx: int, r: int) -> np.ndarray:
    y, x = np.ogrid[:rows, :cols]
    dist = np.sqrt((y - cy) ** 2 + (x - cx) ** 2)
    return (dist >= r - 0.5) & (dist < r + 0.5)


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar — Speküler Glare
# ---------------------------------------------------------------------------

def _glare_score(face_bgr: np.ndarray) -> float:
    """
    Aşırı parlak piksel yüzdesi → spoof riski (0=gerçek, 1=sahte).
    Ekran/kağıt baskısı tipik olarak çok parlak noktalar bırakır.
    """
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    bright_pct = float((gray > 240).sum()) / gray.size
    spoof_risk = min(1.0, bright_pct / _GLARE_PCT_THR)
    return spoof_risk


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar — LBP Mikrotekstür
# ---------------------------------------------------------------------------

def _lbp_entropy_score(face_bgr: np.ndarray) -> float:
    """
    LBP histogramının Shannon entropisi → spoof riski (0=gerçek, 1=sahte).
    Gerçek deri: yüksek entropi. Baskı/ekran: düşük entropi.
    """
    gray   = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (64, 64))
    lbp    = _compute_lbp(resized)
    hist, _ = np.histogram(lbp, bins=256, range=(0, 256), density=True)
    hist    = hist[hist > 0]
    entropy = float(-np.sum(hist * np.log2(hist + 1e-10)))
    # Düşük entropi = yüksek spoof riski
    spoof_risk = max(0.0, 1.0 - entropy / _LBP_ENTROPY_THR)
    return min(1.0, spoof_risk)


def _compute_lbp(gray: np.ndarray) -> np.ndarray:
    """Basit 3×3 uniform LBP hesaplar."""
    h, w = gray.shape
    lbp  = np.zeros((h - 2, w - 2), dtype=np.uint8)
    center = gray[1:-1, 1:-1]
    neighbors = [
        gray[0:-2, 0:-2], gray[0:-2, 1:-1], gray[0:-2, 2:],
        gray[1:-1, 2:],
        gray[2:,   2:],   gray[2:,   1:-1], gray[2:,   0:-2],
        gray[1:-1, 0:-2],
    ]
    for i, nb in enumerate(neighbors):
        lbp |= ((nb >= center).astype(np.uint8) << i)
    return lbp


# ---------------------------------------------------------------------------
# MiniFASNet — opsiyonel yardımcı sinyal
# ---------------------------------------------------------------------------

class _MiniFASNetHelper:
    _loaded   = False
    _model_v2   = None
    _model_v1se = None

    @classmethod
    def load(cls) -> bool:
        if cls._loaded:
            return True
        if not (_MFAS_PY.exists() and _MODEL_V2.exists() and _MODEL_V1SE.exists()):
            return False
        try:
            import torch
            import torch.nn.functional as F  # noqa: F401

            spec = importlib.util.spec_from_file_location("MiniFASNet", str(_MFAS_PY))
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            def _lm(cls_, path):
                m = cls_(conv6_kernel=(5, 5))
                st = torch.load(str(path), map_location="cpu", weights_only=False)
                if isinstance(st, dict):
                    st = {k.replace("module.", ""): v for k, v in st.items()}
                m.load_state_dict(st, strict=False)
                m.eval()
                return m

            cls._model_v2   = _lm(mod.MiniFASNetV2,   _MODEL_V2)
            cls._model_v1se = _lm(mod.MiniFASNetV1SE, _MODEL_V1SE)
            cls._loaded = True
            log.info("MiniFASNet modelleri yuklendi (aux sinyal)")
            return True
        except Exception as exc:
            log.warning("MiniFASNet yuklenemedi (devam edilecek): %s", exc)
            return False

    @classmethod
    def infer(cls, face_bgr: np.ndarray) -> float | None:
        """Gerçek yüz skoru (0–1). Yüklenemezse None döner."""
        if not cls._loaded:
            return None
        try:
            import torch
            import torch.nn.functional as F
            img = cv2.resize(face_bgr, (80, 80))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            t   = torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0).float()
            with torch.no_grad():
                p2   = F.softmax(cls._model_v2(t),   dim=1)[0, 1].item()
                p1se = F.softmax(cls._model_v1se(t), dim=1)[0, 1].item()
            # index 1 = spoof → gerçek skoru = 1 - spoof
            return float(1.0 - (p2 + p1se) / 2.0)
        except Exception as exc:
            log.debug("MiniFASNet infer hatasi: %s", exc)
            return None


# ---------------------------------------------------------------------------
# Yüz kırpma
# ---------------------------------------------------------------------------

def _crop_face(frame: np.ndarray, bbox: tuple, margin: float = _FACE_MARGIN) -> np.ndarray:
    x1, y1, x2, y2 = (int(v) for v in bbox)
    h, w = frame.shape[:2]
    mw = int((x2 - x1) * margin)
    mh = int((y2 - y1) * margin)
    return frame[max(0, y1 - mh):min(h, y2 + mh), max(0, x1 - mw):min(w, x2 + mw)]


# ---------------------------------------------------------------------------
# TextureAnalyzer
# ---------------------------------------------------------------------------

class TextureAnalyzer(LivenessDetectorBase):
    NAME = "texture"

    def __init__(self) -> None:
        _MiniFASNetHelper.load()
        self._reset_state()

    # ------------------------------------------------------------------
    def _reset_state(self) -> None:
        self._scores: list[float] = []
        self._start_time = time.monotonic()
        self._quality_skips = 0

    def get_instruction(self) -> str:
        return "Kameraya duz bakin, hareketsiz kalin."

    def reset(self) -> None:
        self._reset_state()

    # ------------------------------------------------------------------
    def _ensemble_score(self, face_bgr: np.ndarray) -> tuple[float, dict]:
        """
        4 bileşenli ensemble → tek spoof riski skoru (0=gerçek, 1=sahte).
        """
        fft_risk   = _fft_replay_score(face_bgr)
        glare_risk = _glare_score(face_bgr)
        lbp_risk   = _lbp_entropy_score(face_bgr)

        meta = {
            "fft_risk":   round(fft_risk,   3),
            "glare_risk": round(glare_risk, 3),
            "lbp_risk":   round(lbp_risk,   3),
        }

        mfas_score = _MiniFASNetHelper.infer(face_bgr)
        if mfas_score is not None:
            # mfas_score = gerçek yüz olasılığı → spoof riski = 1 - mfas
            mfas_risk = 1.0 - mfas_score
            meta["mfas_risk"] = round(mfas_risk, 3)
            # Ağırlıklı ensemble: MiniFASNet dahil
            spoof_risk = (
                0.25 * fft_risk
                + 0.20 * glare_risk
                + 0.20 * lbp_risk
                + _MFAS_WEIGHT * mfas_risk
            )
        else:
            # MiniFASNet yok: 3 bileşen eşit ağırlık
            spoof_risk = (fft_risk + glare_risk + lbp_risk) / 3.0

        real_score = 1.0 - float(np.clip(spoof_risk, 0.0, 1.0))
        return real_score, meta

    # ------------------------------------------------------------------
    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        elapsed   = time.monotonic() - self._start_time
        timed_out = elapsed > _WINDOW_SECS

        # Yüzü tespit et
        try:
            detector  = FaceDetector.get_instance()
            rgb       = prepare_for_insightface(bgr_frame)
            detection = detector.detect(rgb)
        except Exception as exc:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message=f"Tespit hatasi: {exc}",
            )

        if not detection.has_face or detection.count != 1:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="Tek yuz bulunamadi.",
                metadata={"frames": len(self._scores)},
            )

        face_crop = _crop_face(bgr_frame, detection.single_face.bbox)
        if face_crop.size == 0:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="Yuz kirpma hatasi.",
            )

        # Kalite kapısı
        ok, reason = _quality_gate(face_crop)
        if not ok:
            self._quality_skips += 1
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False,
                message=f"Kalite yetersiz: {reason}",
                metadata={"quality_skips": self._quality_skips},
            )

        real_score, meta = self._ensemble_score(face_crop)
        self._scores.append(real_score)

        frames_so_far = len(self._scores)

        if frames_so_far >= _FRAMES_REQ or timed_out:
            avg  = float(np.mean(self._scores))
            live = avg >= _LIVE_THRESHOLD
            done = live
            msg  = "Tamamlandi!" if done else f"Sahte goruntu tespit edildi. (skor={avg:.2f})"
        else:
            avg  = real_score
            live = False
            done = False
            msg  = f"Analiz: {frames_so_far}/{_FRAMES_REQ} kare ({avg:.2f})"

        meta["frames"]          = frames_so_far
        meta["quality_skips"]   = self._quality_skips
        meta["mfas_available"]  = _MiniFASNetHelper._loaded

        return LivenessResult(
            is_live=live,
            score=round(avg, 3),
            method=self.NAME,
            challenge_completed=done,
            message=msg,
            metadata=meta,
        )
