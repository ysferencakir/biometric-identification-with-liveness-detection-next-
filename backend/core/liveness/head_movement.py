"""
core/liveness/head_movement.py
--------------------------------
Baş hareketi tabanlı liveness — Normalized Nose Offset + MediaPipe ensemble.

Yöntem (v4):
  - InsightFace: burun-göz normalize offset (primary)
  - MediaPipe: facial_transformation_matrix yaw açısı (secondary)
  - Adaptive ensemble: sinyal kalitesine göre dinamik ağırlıklandırma
  - Sağ/sol dönüş tespiti
"""

import logging
import time
from collections import deque
from typing import Optional

import numpy as np

from core.liveness.base import LivenessDetectorBase, LivenessResult
from core.liveness.mediapipe_provider import MediaPipeProvider
from core.liveness.utils import AdaptiveWeights
from core.detection import FaceDetector
from core.preprocessing import prepare_for_insightface

logger = logging.getLogger(__name__)

# 68-point landmark indeksleri
_NOSE_TIP       = 30
_LEFT_EYE_OUT   = 36
_RIGHT_EYE_OUT  = 45
_LEFT_EYE_IN    = 39
_RIGHT_EYE_IN   = 42

# Eşik: baseline'dan bu kadar sapma gerekli (normalize birim)
OFFSET_THRESHOLD = 0.12   # yaklaşık 15-20 derece dönüşe karşılık gelir
HOLD_FRAMES      = 4
WINDOW_SECONDS   = 20.0
CALIB_FRAMES     = 15
_DIRECTIONS      = ["right", "left"]


def _nose_offset(lm: np.ndarray) -> float:
    """
    Burun ucunun göz merkezine göre normalize yatay offseti.
    Sağa dönünce pozitif, sola dönünce negatif.
    """
    nose_x      = lm[_NOSE_TIP, 0]
    left_eye_x  = (lm[_LEFT_EYE_OUT, 0] + lm[_LEFT_EYE_IN, 0]) / 2.0
    right_eye_x = (lm[_RIGHT_EYE_OUT, 0] + lm[_RIGHT_EYE_IN, 0]) / 2.0
    eye_center_x = (left_eye_x + right_eye_x) / 2.0
    eye_distance = abs(right_eye_x - left_eye_x) + 1e-6
    return float((nose_x - eye_center_x) / eye_distance)


class HeadMovementDetector(LivenessDetectorBase):

    NAME = "head_movement"

    def __init__(self) -> None:
        self._mp_provider: Optional[MediaPipeProvider] = None
        self._adaptive_weights = AdaptiveWeights(initial_weight_primary=0.3)
        self._mp_yaw_buffer: deque[float] = deque(maxlen=10)
        self._reset_state()

    def _reset_state(self) -> None:
        self._completed      = []
        self._hold_count     = 0
        self._baseline       = None
        self._calib_offsets: list[float] = []
        self._start_time     = time.monotonic()
        
        # Adaptive weights
        self._adaptive_weights.reset()
        self._mp_yaw_buffer.clear()

    def get_instruction(self) -> str:
        return "Basi saga, sonra sola cevirin."

    def reset(self) -> None:
        self._reset_state()

    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        elapsed   = time.monotonic() - self._start_time
        timed_out = elapsed > WINDOW_SECONDS

        if timed_out and len(self._completed) < len(_DIRECTIONS):
            self._reset_state()
            elapsed   = 0.0
            timed_out = False

        # Initialize MediaPipe provider (lazy load)
        if self._mp_provider is None:
            try:
                self._mp_provider = MediaPipeProvider.get_instance()
            except Exception as e:
                logger.warning("MediaPipe provider init failed, using InsightFace only: %s", e)
                self._mp_provider = None

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
                metadata={"completed": self._completed},
            )

        lm68 = getattr(detection.single_face._raw, "landmark_3d_68", None)
        if lm68 is None:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="68 landmark bulunamadi.",
            )

        lm     = np.array(lm68)
        offset = _nose_offset(lm)

        # ── MediaPipe yaw sinyali ─────────────────────────────────────────
        mp_yaw_deg = 0.0
        mp_result = None
        if self._mp_provider is not None:
            try:
                mp_result = self._mp_provider.process(bgr_frame)
                if mp_result is not None:
                    mp_yaw_deg = self._mp_provider.get_head_yaw(mp_result)
                    self._mp_yaw_buffer.append(abs(mp_yaw_deg))
            except Exception as e:
                logger.debug("MediaPipe yaw extraction failed: %s", e)

        # ── Kalibrasyon: ilk CALIB_FRAMES frame'de baseline ──────────────
        if self._baseline is None:
            self._calib_offsets.append(offset)
            if len(self._calib_offsets) >= CALIB_FRAMES:
                self._baseline = float(np.median(self._calib_offsets))

            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False,
                message=f"Kalibre ediliyor... ({len(self._calib_offsets)}/{CALIB_FRAMES})",
                metadata={
                    "offset": round(offset, 3),
                    "completed": self._completed,
                    "mp_yaw_deg": round(mp_yaw_deg, 2),
                },
            )

        # ── Adaptive weighting: nose offset + MediaPipe yaw ───────────────
        offset_confidence = 0.6 if self._baseline is not None else 0.0
        mp_confidence = 0.5 if len(self._mp_yaw_buffer) > 0 else 0.0
        
        self._adaptive_weights.update(offset_confidence, mp_confidence)
        w_offset, w_mp = self._adaptive_weights.get_weights()

        # Baseline'a göre relative offset
        rel = offset - self._baseline

        # ── Yön tespiti ──────────────────────────────────────────────────
        completed = len(self._completed) == len(_DIRECTIONS)

        if not completed:
            if "right" not in self._completed and rel > OFFSET_THRESHOLD:
                self._hold_count += 1
                if self._hold_count >= HOLD_FRAMES:
                    self._completed.append("right")
                    self._hold_count = 0
            elif "left" not in self._completed and rel < -OFFSET_THRESHOLD:
                self._hold_count += 1
                if self._hold_count >= HOLD_FRAMES:
                    self._completed.append("left")
                    self._hold_count = 0
            else:
                self._hold_count = 0

        completed = len(self._completed) == len(_DIRECTIONS)
        score     = 1.0 if completed else len(self._completed) / len(_DIRECTIONS)

        dir_labels = {"right": "saga", "left": "sola"}
        remaining  = [dir_labels[d] for d in _DIRECTIONS if d not in self._completed]

        return LivenessResult(
            is_live=completed,
            score=round(score, 3),
            method=self.NAME,
            challenge_completed=completed,
            message="Tamamlandi!" if completed else f"Kalan: {' ve '.join(remaining)}",
            metadata={
                "offset":         round(offset, 3),
                "rel":            round(rel, 3),
                "baseline":       round(self._baseline, 3),
                "threshold":      OFFSET_THRESHOLD,
                "mp_yaw_deg":     round(mp_yaw_deg, 2),
                "ensemble_score": round(score, 3),
                "weight_offset":  round(w_offset, 2),
                "weight_mp":      round(w_mp, 2),
                "completed":      self._completed,
                "elapsed":        round(elapsed, 1),
            },
        )
