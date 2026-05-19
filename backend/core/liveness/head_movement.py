"""
core/liveness/head_movement.py
--------------------------------
Baş hareketi tabanlı liveness tespiti.

Yöntem:
  - InsightFace 3D 68 landmark üzerinden yaw (sağ-sol) açısı hesaplanır.
  - Kullanıcıdan başını sağa, sonra sola çevirmesi istenir.
  - Her yön için YAW_TARGET derece dönüş tespit edilince o yön tamamlanır.
  - İki yön de tamamlanınca passed=True.

Yaw hesabı:
  - Sol/sağ göz ve burun köprüsü landmark'ları kullanılır.
  - Göz merkezleri arasındaki X farkı ile burun genişliği oranlanır.
  - Bu oran yüz cepheden uzaklaştıkça değişir → yaw proxy değeri.
"""

import time

import cv2
import numpy as np

from core.liveness.base import LivenessDetectorBase, LivenessResult

# 68-point landmark indeksleri
_LEFT_EYE_OUTER  = 36   # sol göz dış köşe
_RIGHT_EYE_OUTER = 45   # sağ göz dış köşe
_NOSE_TIP        = 30   # burun ucu
_LEFT_EYE_IDX    = [36, 37, 38, 39, 40, 41]
_RIGHT_EYE_IDX   = [42, 43, 44, 45, 46, 47]

# Yaw proxy eşikleri (normalized değer)
# Düz bakışta ~0.5, sağa döndüğünde düşer, sola döndüğünde yükselir
_YAW_RIGHT_THRESHOLD = 0.38   # bu değerin altı = yeterince sağa döndü
_YAW_LEFT_THRESHOLD  = 0.62   # bu değerin üstü = yeterince sola döndü
_HOLD_FRAMES         = 4      # kaç frame tutmalı
_WINDOW_SECONDS      = 20.0   # 20 saniye

_DIRECTIONS = ["right", "left"]   # her ikisi tamamlanmalı (sıra önemli değil)


def _yaw_proxy(lm: np.ndarray) -> float:
    """
    Yüzün sağa-sola dönüşünü temsil eden 0-1 arası değer.
    0 = tamamen sağa, 0.5 = düz, 1 = tamamen sola.
    """
    left_x  = lm[_LEFT_EYE_OUTER,  0]
    right_x = lm[_RIGHT_EYE_OUTER, 0]
    nose_x  = lm[_NOSE_TIP,        0]
    eye_width = abs(right_x - left_x) + 1e-6
    return float((nose_x - left_x) / eye_width)


class HeadMovementDetector(LivenessDetectorBase):
    """
    Aktif liveness: kullanıcıdan başını sağa sonra sola çevirmesi istenir.
    """

    NAME = "head_movement"

    def __init__(self) -> None:
        self._reset_state()

    def _reset_state(self) -> None:
        self._completed    = []      # tamamlanan yönler
        self._hold_count   = 0       # mevcut yönde tutma sayacı
        self._start_time   = time.monotonic()

    def get_instruction(self) -> str:
        return "Basi saga, sonra sola cevirin."

    def reset(self) -> None:
        self._reset_state()

    def _next_direction(self) -> str | None:
        """Sıradaki tamamlanmamış yön."""
        for d in _DIRECTIONS:
            if d not in self._completed:
                return d
        return None

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
                metadata={"completed": self._completed},
            )

        lm68 = getattr(detection.single_face._raw, "landmark_3d_68", None)
        if lm68 is None:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="68 landmark bulunamadi.",
            )

        lm  = np.array(lm68)
        yaw = _yaw_proxy(lm)

        next_dir = self._next_direction()
        completed = len(self._completed) == len(_DIRECTIONS)

        # Timeout olursa otomatik reset — kullanıcı tekrar deneyebilir
        if timed_out and not completed:
            self._reset_state()
            elapsed   = 0.0
            timed_out = False

        if not completed:
            # Sıra önemli değil — hangi yönü yaparsa o sayılır
            if "right" not in self._completed and yaw < _YAW_RIGHT_THRESHOLD:
                self._hold_count += 1
                if self._hold_count >= _HOLD_FRAMES:
                    self._completed.append("right")
                    self._hold_count = 0
            elif "left" not in self._completed and yaw > _YAW_LEFT_THRESHOLD:
                self._hold_count += 1
                if self._hold_count >= _HOLD_FRAMES:
                    self._completed.append("left")
                    self._hold_count = 0
            else:
                self._hold_count = 0

        completed = len(self._completed) == len(_DIRECTIONS)
        score     = 1.0 if completed else len(self._completed) / len(_DIRECTIONS)

        dir_labels = {"right": "saga", "left": "sola"}
        remaining  = [dir_labels[d] for d in _DIRECTIONS if d not in self._completed]
        if completed:
            msg = "Tamamlandi!"
        elif remaining:
            msg = f"Kalan: {' ve '.join(remaining)}"
        else:
            msg = "Tamamlandi!"

        return LivenessResult(
            is_live=completed,
            score=round(score, 3),
            method=self.NAME,
            challenge_completed=completed,
            message=msg,
            metadata={
                "yaw":       round(yaw, 3),
                "completed": self._completed,
                "elapsed":   round(elapsed, 1),
            },
        )
