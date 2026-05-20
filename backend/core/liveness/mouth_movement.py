"""
core/liveness/mouth_movement.py
---------------------------------
Ağız hareketi tabanlı liveness tespiti.

Yöntem:
  - InsightFace landmark_3d_68 kullanılır (zaten yüklü).
  - MAR (Mouth Aspect Ratio) hesaplanır.
  - Kullanıcıdan ağzını 2 kez açıp kapatması istenir.
  - Fotoğraf/ekran: MAR sabit kalır → FAIL
  - Gerçek yüz: MAR dalgalanır → PASS

MAR formülü:
  A = ||p51 - p59||  (üst-alt dikey)
  B = ||p53 - p57||  (üst-alt dikey orta)
  C = ||p48 - p54||  (yatay genişlik)
  MAR = (A + B) / (2 * C)

  Ağız kapalı ≈ 0.3-0.5
  Ağız açık   > 0.6
"""

import time

import numpy as np

from core.liveness.base import LivenessDetectorBase, LivenessResult
from core.detection import FaceDetector
from core.preprocessing import prepare_for_insightface

# 68-point ağız landmark indeksleri
_OUTER_TOP    = 51   # üst dış orta
_OUTER_BOTTOM = 59   # alt dış orta
_INNER_TOP    = 53   # üst dış sağ
_INNER_BOTTOM = 57   # alt dış sağ
_LEFT_CORNER  = 48   # sol köşe
_RIGHT_CORNER = 54   # sağ köşe

_OPEN_THRESHOLD  = 0.55   # MAR bu değerin üstü = ağız açık
_CLOSE_THRESHOLD = 0.40   # MAR bu değerin altı = ağız kapalı
_CONSEC_FRAMES   = 2      # kaç ardışık frame aynı durumda olmalı
_MIN_OPEN_CLOSE  = 2      # kaç kez açıp kapama
_WINDOW_SECONDS  = 15.0


def _mar(landmarks: np.ndarray) -> float:
    """Mouth Aspect Ratio hesapla."""
    p = landmarks[:, :2]   # sadece x,y
    A = np.linalg.norm(p[_OUTER_TOP] - p[_OUTER_BOTTOM])
    B = np.linalg.norm(p[_INNER_TOP] - p[_INNER_BOTTOM])
    C = np.linalg.norm(p[_LEFT_CORNER] - p[_RIGHT_CORNER])
    return float((A + B) / (2.0 * C + 1e-6))


class MouthMovementDetector(LivenessDetectorBase):
    """
    Aktif liveness: kullanıcıdan ağzını açıp kapatması istenir.
    Fotoğraf veya ekranda MAR değişmez → FAIL.
    """

    NAME = "mouth_movement"

    def __init__(self) -> None:
        self._reset_state()

    def _reset_state(self) -> None:
        self._open_close_count = 0    # tamamlanan açma-kapama sayısı
        self._consec_open      = 0    # ardışık açık frame
        self._consec_closed    = 0    # ardışık kapalı frame
        self._mouth_open       = False
        self._start_time       = time.monotonic()

    def get_instruction(self) -> str:
        return "Lutfen agzinizi iki kez acip kapatin."

    def reset(self) -> None:
        self._reset_state()

    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        elapsed   = time.monotonic() - self._start_time
        timed_out = elapsed > _WINDOW_SECONDS

        if timed_out and not (self._open_close_count >= _MIN_OPEN_CLOSE):
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
        mar = _mar(lm)

        # Açma-kapama state machine
        if mar > _OPEN_THRESHOLD:
            self._consec_open   += 1
            self._consec_closed  = 0
            if self._consec_open >= _CONSEC_FRAMES:
                self._mouth_open = True
        elif mar < _CLOSE_THRESHOLD:
            self._consec_closed += 1
            self._consec_open    = 0
            if self._consec_closed >= _CONSEC_FRAMES and self._mouth_open:
                self._open_close_count += 1
                self._mouth_open = False
        else:
            self._consec_open   = 0
            self._consec_closed = 0

        completed = self._open_close_count >= _MIN_OPEN_CLOSE
        score     = 1.0 if completed else min(0.99, self._open_close_count / _MIN_OPEN_CLOSE)

        return LivenessResult(
            is_live=completed,
            score=round(score, 3),
            method=self.NAME,
            challenge_completed=completed,
            message=(
                "Tamamlandi!" if completed
                else f"Agiz ac/kapat: {self._open_close_count}/{_MIN_OPEN_CLOSE}"
            ),
            metadata={
                "mar":        round(mar, 3),
                "open_close": self._open_close_count,
                "elapsed":    round(elapsed, 1),
            },
        )
