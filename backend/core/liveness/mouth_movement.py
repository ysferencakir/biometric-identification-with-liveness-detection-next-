"""
core/liveness/mouth_movement.py
---------------------------------
Ağız hareketi tabanlı liveness.

Birincil sinyal: MediaPipe jawOpen blendshape [0.0-1.0]
  - 0.0  → ağız tamamen kapalı
  - 0.7+ → ağız belirgin şekilde açık

Yedek sinyal (MediaPipe yoksa): InsightFace landmark_3d_68 → MAR

State machine: jawOpen > OPEN_T için CONSEC_OPEN ardışık frame → "açık"
               jawOpen < CLOSE_T için CONSEC_CLOSE ardışık frame + açık durumdaysa → sayaç++
"""

import logging
import time
from collections import deque
from typing import Optional

import numpy as np

from core.liveness.base import LivenessDetectorBase, LivenessResult
from core.liveness.mediapipe_provider import MediaPipeProvider
from core.detection import FaceDetector
from core.preprocessing import prepare_for_insightface

logger = logging.getLogger(__name__)

# ── Eşikler ──────────────────────────────────────────────────────────────────
# MediaPipe jawOpen için (0-1 arası blendshape değeri)
MP_OPEN_THRESHOLD  = 0.45   # jawOpen > 0.45 → açık
MP_CLOSE_THRESHOLD = 0.30   # jawOpen < 0.30 → kapalı

# InsightFace MAR fallback için (normalize edilmiş, ref=0.55)
MAR_OPEN_THRESHOLD  = 0.70  # mar_norm > 0.70 (MAR ≈ 0.38) → açık
MAR_CLOSE_THRESHOLD = 0.20  # mar_norm < 0.20 (MAR ≈ 0.11) → kapalı
_MAR_OPEN_REF = 0.55

# Kaç ardışık frame açık/kapalı görünmeli (150ms polling → ×6 ≈ 0.9s)
CONSEC_OPEN  = 2   # açık sayılmak için gereken art arda frame (~450ms)
CONSEC_CLOSE = 2   # kapalı sayılmak için gereken art arda frame (~450ms)

MIN_OPEN_CLOSE = 2   # kaç kez aç-kapat
WINDOW_SECONDS = 20.0

# MediaPipe jawOpen smoothing buffer boyutu (küçük = hızlı tepki)
_MP_BUFFER = 3

# Outer lip landmark indeksleri (standart 68-point iBUG şeması)
_UPPER_CENTER = 51
_LOWER_CENTER = 57
_UPPER_RIGHT  = 52
_LOWER_LEFT   = 58
_LEFT_CORNER  = 48
_RIGHT_CORNER = 54


def _mar(lm68: np.ndarray) -> float:
    p = lm68[:, :2]
    A = np.linalg.norm(p[_UPPER_CENTER] - p[_LOWER_CENTER])
    B = np.linalg.norm(p[_UPPER_RIGHT]  - p[_LOWER_LEFT])
    C = np.linalg.norm(p[_LEFT_CORNER]  - p[_RIGHT_CORNER])
    return float((A + B) / (2.0 * C + 1e-6))


class MouthMovementDetector(LivenessDetectorBase):
    NAME = "mouth_movement"

    def __init__(self) -> None:
        self._mp_provider: Optional[MediaPipeProvider] = None
        self._jaw_buf: deque[float] = deque(maxlen=_MP_BUFFER)
        self._reset_state()

    def _reset_state(self) -> None:
        self._count        = 0
        self._mouth_open   = False
        self._consec_open  = 0
        self._consec_close = 0
        self._start_time   = time.monotonic()
        self._jaw_buf.clear()

    def get_instruction(self) -> str:
        return "Lutfen agzinizi iki kez acip kapatin."

    def reset(self) -> None:
        self._reset_state()

    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        elapsed = time.monotonic() - self._start_time
        if elapsed > WINDOW_SECONDS and self._count < MIN_OPEN_CLOSE:
            self._reset_state()

        # ── MediaPipe provider ─────────────────────────────────────────────
        if self._mp_provider is None:
            try:
                self._mp_provider = MediaPipeProvider.get_instance()
            except Exception as e:
                logger.warning("MediaPipe init failed: %s", e)

        # ── InsightFace yüz tespiti ────────────────────────────────────────
        try:
            detector  = FaceDetector.get_instance()
            rgb       = prepare_for_insightface(bgr_frame)
            detection = detector.detect(rgb)
        except Exception as exc:
            return self._err(f"Tespit hatasi: {exc}")

        if not detection.has_face or detection.count != 1:
            return self._err("Yuz bulunamadi — kameraya bakın.")

        # ── Sinyal seçimi: MediaPipe jawOpen öncelikli ─────────────────────
        jaw_raw = None
        if self._mp_provider is not None:
            try:
                mp_res = self._mp_provider.process(bgr_frame)
                if mp_res is not None:
                    jaw_raw = self._mp_provider.get_jaw_open_score(mp_res)
                    self._jaw_buf.append(jaw_raw)
            except Exception as e:
                logger.debug("MediaPipe hatasi: %s", e)

        use_mediapipe = len(self._jaw_buf) >= 1

        if use_mediapipe:
            # 3-frame buffer ortalaması: gürültüye dayanıklı, gecikme minimal
            signal  = float(np.mean(self._jaw_buf))
            open_t  = MP_OPEN_THRESHOLD
            close_t = MP_CLOSE_THRESHOLD
            src     = "MP"
        else:
            # InsightFace MAR fallback
            lm68 = getattr(detection.single_face._raw, "landmark_3d_68", None)
            if lm68 is None:
                return self._err("Landmark algilanamadi. Yuzunuzu kameraya dondurun.")
            mar    = _mar(np.array(lm68))
            signal = min(1.0, mar / _MAR_OPEN_REF)
            open_t  = MAR_OPEN_THRESHOLD
            close_t = MAR_CLOSE_THRESHOLD
            src     = "MAR"

        # ── Hysteresis state machine ───────────────────────────────────────
        if signal > open_t:
            self._consec_open  += 1
            self._consec_close  = 0
            if self._consec_open >= CONSEC_OPEN and not self._mouth_open:
                self._mouth_open = True
                logger.debug("Agiz ACILDI (signal=%.2f)", signal)
        elif signal < close_t:
            self._consec_close += 1
            self._consec_open   = 0
            if self._consec_close >= CONSEC_CLOSE and self._mouth_open:
                self._count      += 1
                self._mouth_open  = False
                logger.debug("Agiz KAPANDI — count=%d", self._count)
        else:
            # Hysteresis bölgesi — counter sıfırlanmaz
            pass

        completed = self._count >= MIN_OPEN_CLOSE
        score     = 1.0 if completed else min(0.99, self._count / MIN_OPEN_CLOSE)
        state_str = "ACIK" if self._mouth_open else "KAPALI"

        return LivenessResult(
            is_live=completed,
            score=round(score, 3),
            method=self.NAME,
            challenge_completed=completed,
            message=(
                "Tamamlandi!" if completed
                else f"[{state_str}|{src}] {self._count}/{MIN_OPEN_CLOSE}  sinyal:{signal:.2f}  jaw:{(jaw_raw if jaw_raw is not None else 0.0):.2f}"
            ),
            metadata={
                "signal":      round(signal, 3),
                "open_t":      open_t,
                "close_t":     close_t,
                "source":      src,
                "mouth_open":  self._mouth_open,
                "count":       self._count,
                "elapsed":     round(time.monotonic() - self._start_time, 1),
            },
        )

    def _err(self, msg: str) -> LivenessResult:
        return LivenessResult(
            is_live=False, score=0.0, method=self.NAME,
            challenge_completed=False, message=msg,
            metadata={"count": self._count},
        )
