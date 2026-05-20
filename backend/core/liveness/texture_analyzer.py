"""
core/liveness/texture_analyzer.py
-----------------------------------
LBP (Local Binary Pattern) tabanlı pasif liveness tespiti.

Yöntem:
  - Yüz bölgesi kırpılır ve gri tonlamaya dönüştürülür.
  - LBP histogram hesaplanır (uniform LBP, 8 komşu, r=1).
  - Gerçek yüzler geniş, düzgün dağılımlı LBP histogramına sahiptir.
  - Baskılı fotoğraflar / ekranlar: histogram belirli değerlere yığılır.
  - Ek özellikler:
      * Laplacian varyansı (frekans zenginliği)
      * Lokal kontrast (yüz bölgelerinin kendi içinde değişimi)

Referans:
  Maatta et al. "Face Spoofing Detection From Single Images Using
  Micro-Texture Analysis", IJCB 2011.
"""

import time

import numpy as np

from core.liveness.base import LivenessDetectorBase, LivenessResult
from core.detection import FaceDetector
from core.preprocessing import prepare_for_insightface

# ── Eşik değerleri ────────────────────────────────────────────────────────────
_LAP_VAR_THRESHOLD   = 40.0    # Laplacian varyansı — webcam için düşürüldü
_HIST_ENTROPY_MIN    = 3.5     # LBP histogram entropisi
_LOCAL_CONTRAST_MIN  = 8.0     # Lokal kontrast
_FRAMES_REQUIRED     = 5       # Kaç frame ortalansın
_WINDOW_SECONDS      = 12.0
_FACE_MARGIN         = 0.20    # Yüz bbox'ını % kadar genişlet


def _lbp_histogram(gray: np.ndarray) -> np.ndarray:
    """Uniform LBP histogramı hesapla (8 komşu, r=1)."""
    h, w = gray.shape
    lbp = np.zeros((h - 2, w - 2), dtype=np.uint8)

    center = gray[1:-1, 1:-1].astype(np.int16)
    neighbors = [
        gray[0:-2, 0:-2], gray[0:-2, 1:-1], gray[0:-2, 2:],
        gray[1:-1, 2:],   gray[2:,   2:],   gray[2:,   1:-1],
        gray[2:,   0:-2], gray[1:-1, 0:-2],
    ]
    for i, nb in enumerate(neighbors):
        lbp += ((nb.astype(np.int16) >= center).astype(np.uint8) << i)

    hist, _ = np.histogram(lbp, bins=256, range=(0, 255))
    hist = hist.astype(np.float32)
    hist /= (hist.sum() + 1e-6)
    return hist


def _entropy(hist: np.ndarray) -> float:
    """Shannon entropisi."""
    p = hist[hist > 0]
    return float(-np.sum(p * np.log2(p)))


def _laplacian_variance(gray: np.ndarray) -> float:
    """Görüntünün frekans zenginliğini ölçer (odak + doku)."""
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    from scipy.ndimage import convolve
    lap = convolve(gray.astype(np.float32), kernel)
    return float(np.var(lap))


def _local_contrast(gray: np.ndarray, block: int = 16) -> float:
    """Blok blok standart sapma ortalaması — lokal doku zenginliği."""
    h, w = gray.shape
    stds = []
    for r in range(0, h - block, block):
        for c in range(0, w - block, block):
            stds.append(np.std(gray[r:r+block, c:c+block]))
    return float(np.mean(stds)) if stds else 0.0


def _crop_face(bgr_frame: np.ndarray, bbox: tuple, margin: float = _FACE_MARGIN) -> np.ndarray:
    """Yüz bölgesini bbox'tan kırp, margin ekle."""
    x1, y1, x2, y2 = [int(v) for v in bbox]
    h, w = bgr_frame.shape[:2]
    mw = int((x2 - x1) * margin)
    mh = int((y2 - y1) * margin)
    x1 = max(0, x1 - mw); y1 = max(0, y1 - mh)
    x2 = min(w, x2 + mw); y2 = min(h, y2 + mh)
    return bgr_frame[y1:y2, x1:x2]


class TextureAnalyzer(LivenessDetectorBase):
    """
    Pasif liveness: kullanıcıdan ekstra hareket istenmez.
    Yüz dokusu analiz edilerek gerçek mi sahte mi karar verilir.
    """

    NAME = "texture"

    def __init__(self) -> None:
        self._reset_state()

    def _reset_state(self) -> None:
        self._scores: list[float] = []
        self._start_time = time.monotonic()

    def get_instruction(self) -> str:
        return "Kameraya duz bakin, hareketsiz kalin."

    def reset(self) -> None:
        self._reset_state()

    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        elapsed   = time.monotonic() - self._start_time
        timed_out = elapsed > _WINDOW_SECONDS

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

        face_bbox = detection.single_face.bbox
        face_crop = _crop_face(bgr_frame, face_bbox)

        if face_crop.size == 0:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="Yuz kirpma hatasi.",
            )

        import cv2
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)

        # ── Özellik hesaplamaları ──────────────────────────────────────────
        try:
            from scipy.ndimage import convolve as _conv
            lap_var = _laplacian_variance(gray)
        except ImportError:
            # scipy yoksa Laplacian varyansını OpenCV ile hesapla
            lap = cv2.Laplacian(gray, cv2.CV_64F)
            lap_var = float(np.var(lap))

        hist        = _lbp_histogram(gray)
        entropy     = _entropy(hist)
        loc_contrast = _local_contrast(gray)

        # ── Normalleştirilmiş skor (0-1) ──────────────────────────────────
        lap_score  = min(1.0, lap_var / (_LAP_VAR_THRESHOLD * 3))
        ent_score  = min(1.0, max(0.0, (entropy - _HIST_ENTROPY_MIN) / 3.0))
        cont_score = min(1.0, loc_contrast / (_LOCAL_CONTRAST_MIN * 2))

        frame_score = (lap_score * 0.4 + ent_score * 0.35 + cont_score * 0.25)
        self._scores.append(frame_score)

        # ── Yeterli frame toplandıysa karar ver ───────────────────────────
        if len(self._scores) >= _FRAMES_REQUIRED or timed_out:
            avg_score = float(np.mean(self._scores))
            is_live   = (
                avg_score >= 0.40 and
                lap_var   >= _LAP_VAR_THRESHOLD and
                entropy   >= _HIST_ENTROPY_MIN and
                loc_contrast >= _LOCAL_CONTRAST_MIN
            )
            # challenge_completed sadece is_live=True ise True
            completed = is_live
            if not is_live and not timed_out:
                # Sahte tespit: score'ları temizle, tekrar dene
                self._scores.clear()
        else:
            avg_score = frame_score
            is_live   = False
            completed = False

        return LivenessResult(
            is_live=is_live,
            score=round(avg_score if completed else frame_score, 3),
            method=self.NAME,
            challenge_completed=completed,
            message=(
                "Tamamlandi!" if (completed and is_live)
                else "Sahte goruntu tespit edildi." if (completed and not is_live)
                else f"Analiz ediliyor... ({len(self._scores)}/{_FRAMES_REQUIRED})"
            ),
            metadata={
                "lap_var":      round(lap_var, 1),
                "entropy":      round(entropy, 3),
                "loc_contrast": round(loc_contrast, 1),
                "frames":       len(self._scores),
            },
        )
