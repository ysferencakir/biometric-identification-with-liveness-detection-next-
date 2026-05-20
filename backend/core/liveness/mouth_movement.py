"""
core/liveness/mouth_movement.py
---------------------------------
Ağız hareketi tabanlı liveness — Inner-lip aperture + hysteresis.

Yöntem (v2 — Araştırma raporu adaptasyonu):
  - Outer-lip yerine INNER-lip (60-67) aperture kullanılır
  - Yatay normalizasyon: ağız köşeleri arası mesafe (48-54)
  - İki eşikli hysteresis: aç eşiği > kapat eşiği (gürültü filtresi)
  - CONSEC_FRAMES ardışık frame tutmalı
  - 15 saniyede MIN_OPEN_CLOSE kez açıp kapama → passed=True

68-point inner lip indeksleri (iBUG/300-W):
  60: sol iç köşe, 61: üst sol, 62: üst orta, 63: üst sağ
  64: sağ iç köşe, 65: alt sağ, 66: alt orta, 67: alt sol
"""

import time

import numpy as np

from core.liveness.base import LivenessDetectorBase, LivenessResult
from core.detection import FaceDetector
from core.preprocessing import prepare_for_insightface

# Inner lip landmark indeksleri (68-point şeması)
_INNER_TOP    = 62   # üst iç orta
_INNER_BOTTOM = 66   # alt iç orta

# Outer lip köşeleri (yatay normalizasyon için)
_OUTER_LEFT  = 48
_OUTER_RIGHT = 54

# Hysteresis eşikleri
OPEN_THRESHOLD  = 0.30   # MAR bu değerin üstü → ağız açılıyor
CLOSE_THRESHOLD = 0.15   # MAR bu değerin altı → ağız kapandı
CONSEC_FRAMES   = 2
MIN_OPEN_CLOSE  = 2
WINDOW_SECONDS  = 15.0


def _mar_inner(landmarks: np.ndarray) -> float:
    """
    Inner-lip Mouth Aspect Ratio.
    Dikey: üst-alt iç orta noktaları arası mesafe.
    Yatay: outer lip köşeleri arası (daha stabil referans).
    """
    p = landmarks[:, :2]
    vertical  = np.linalg.norm(p[_INNER_TOP] - p[_INNER_BOTTOM])
    horizontal = np.linalg.norm(p[_OUTER_LEFT] - p[_OUTER_RIGHT])
    return float(vertical / (horizontal + 1e-6))


class MouthMovementDetector(LivenessDetectorBase):
    """
    Aktif liveness: ağzı açıp kapatma.
    Inner-lip aperture + hysteresis ile daha stabil tespit.
    """

    NAME = "mouth_movement"

    def __init__(self) -> None:
        self._reset_state()

    def _reset_state(self) -> None:
        self._open_close_count = 0
        self._consec_open      = 0
        self._consec_closed    = 0
        self._mouth_open       = False
        self._start_time       = time.monotonic()

    def get_instruction(self) -> str:
        return "Lutfen agzinizi iki kez acip kapatin."

    def reset(self) -> None:
        self._reset_state()

    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        elapsed   = time.monotonic() - self._start_time
        timed_out = elapsed > WINDOW_SECONDS

        if timed_out and self._open_close_count < MIN_OPEN_CLOSE:
            self._reset_state()
            elapsed   = 0.0
            timed_out = False

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
                metadata={"open_close": self._open_close_count},
            )

        lm68 = getattr(detection.single_face._raw, "landmark_3d_68", None)
        if lm68 is None:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="68 landmark bulunamadi.",
            )

        lm  = np.array(lm68)
        mar = _mar_inner(lm)

        # ── Hysteresis state machine ──────────────────────────────────────
        if mar > OPEN_THRESHOLD:
            self._consec_open   += 1
            self._consec_closed  = 0
            if self._consec_open >= CONSEC_FRAMES:
                self._mouth_open = True
        elif mar < CLOSE_THRESHOLD:
            self._consec_closed += 1
            self._consec_open    = 0
            if self._consec_closed >= CONSEC_FRAMES and self._mouth_open:
                self._open_close_count += 1
                self._mouth_open = False
        else:
            # Hysteresis zone — durum korunur
            self._consec_open   = 0
            self._consec_closed = 0

        completed = self._open_close_count >= MIN_OPEN_CLOSE
        score     = 1.0 if completed else min(0.99, self._open_close_count / MIN_OPEN_CLOSE)

        return LivenessResult(
            is_live=completed,
            score=round(score, 3),
            method=self.NAME,
            challenge_completed=completed,
            message=(
                "Tamamlandi!" if completed
                else f"Agiz ac/kapat: {self._open_close_count}/{MIN_OPEN_CLOSE}"
            ),
            metadata={
                "mar":        round(mar, 3),
                "open_close": self._open_close_count,
                "mouth_open": self._mouth_open,
                "elapsed":    round(elapsed, 1),
            },
        )
