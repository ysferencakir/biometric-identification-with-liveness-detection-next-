"""
core/liveness/blink_detector.py
--------------------------------
Göz kırpma tabanlı liveness tespiti.

Yöntem:
  - InsightFace buffalo_l'nin 1k3d68 modeli kullanılır (zaten yüklü).
  - 68 standart landmark üzerinden EAR hesaplanır.
  - Sol göz: [36,37,38,39,40,41], Sağ göz: [42,43,44,45,46,47]
  - 8 saniye içinde 2 göz kırpma → passed=True

EAR formülü (Soukupova & Cech, 2016):
  EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
  Açık göz ≈ 0.25, kırpınca < threshold
"""

import time

import cv2
import numpy as np

from core.liveness.base import LivenessDetectorBase, LivenessResult

# 68-point standart göz indeksleri
_LEFT_EYE  = [36, 37, 38, 39, 40, 41]
_RIGHT_EYE = [42, 43, 44, 45, 46, 47]

_BLINK_THRESHOLD = 0.23   # normal kırpma algılanır, gürültü geçmez
_CONSEC_FRAMES   = 2      # 2 ardışık frame kapalı olmalı
_MIN_BLINKS      = 2
_WINDOW_SECONDS  = 15.0


def _ear(landmarks: np.ndarray, idx: list) -> float:
    p = landmarks[idx]          # (6, 2 veya 3)
    p = p[:, :2]                # sadece x,y
    A = np.linalg.norm(p[1] - p[5])
    B = np.linalg.norm(p[2] - p[4])
    C = np.linalg.norm(p[0] - p[3])
    return float((A + B) / (2.0 * C + 1e-6))


class BlinkDetector(LivenessDetectorBase):

    NAME = "blink"

    def __init__(self) -> None:
        self._reset_state()

    def _reset_state(self) -> None:
        self._blink_count  = 0
        self._consec_below = 0
        self._eye_closed   = False
        self._start_time   = time.monotonic()

    def get_instruction(self) -> str:
        return "Lutfen dogal sekilde iki kez goz kirpin. (15 saniye)"

    def reset(self) -> None:
        self._reset_state()

    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        elapsed   = time.monotonic() - self._start_time
        timed_out = elapsed > _WINDOW_SECONDS

        try:
            from core.detection import FaceDetector
            detector  = FaceDetector.get_instance()
            rgb       = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
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
                metadata={"blinks": self._blink_count},
            )

        raw_face = detection.single_face._raw

        # 3D 68-nokta landmark (buffalo_l her zaman yükler)
        lm68 = getattr(raw_face, "landmark_3d_68", None)
        if lm68 is None:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="68 landmark modeli bulunamadi.",
            )

        lm = np.array(lm68)   # (68, 3)

        left_ear  = _ear(lm, _LEFT_EYE)
        right_ear = _ear(lm, _RIGHT_EYE)
        avg_ear   = (left_ear + right_ear) / 2.0

        import logging as _log
        _log.getLogger("blink").debug(
            "EAR=%.3f (L=%.3f R=%.3f) blinks=%d consec=%d",
            avg_ear, left_ear, right_ear, self._blink_count, self._consec_below
        )

        # Göz kırpma state machine
        if avg_ear < _BLINK_THRESHOLD:
            self._consec_below += 1
            self._eye_closed    = True
        else:
            if self._eye_closed and self._consec_below >= _CONSEC_FRAMES:
                self._blink_count += 1
            self._consec_below = 0
            self._eye_closed   = False

        completed = self._blink_count >= _MIN_BLINKS
        # Tamamlandıysa her zaman 1.0, değilse kısmi ilerleme
        if completed:
            score = 1.0
        elif timed_out:
            score = 0.0
        else:
            score = min(0.99, self._blink_count / _MIN_BLINKS)

        return LivenessResult(
            is_live=completed,
            score=round(score, 3),
            method=self.NAME,
            challenge_completed=completed,
            message=(
                "Tamamlandi!" if completed
                else "Sure doldu." if timed_out
                else f"Goz kirpma: {self._blink_count}/{_MIN_BLINKS}"
            ),
            metadata={
                "blinks":  self._blink_count,
                "ear":     round(avg_ear, 3),
                "elapsed": round(elapsed, 1),
            },
        )
