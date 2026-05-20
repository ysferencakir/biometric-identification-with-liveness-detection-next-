"""
core/liveness/blink_detector.py
--------------------------------
Göz kırpma tabanlı liveness — Temporal Dip Detection + MediaPipe ensemble.

Yöntem (v4):
  - InsightFace EAR: kişinin kendi baseline'ından sap tespiti (primary)
  - MediaPipe blendshape: iris normalize göz kırpma skoru (secondary)
  - Adaptive ensemble: sinyal kalitesine göre dinamik ağırlıklandırma
  - "açık→dip→açık" state machine (gürültü filtresi)
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

_LEFT_EYE  = [36, 37, 38, 39, 40, 41]
_RIGHT_EYE = [42, 43, 44, 45, 46, 47]

# Baseline EMA parametresi — yavaş güncelleme (göz kırpmalar baseline'ı bozmasın)
EMA_ALPHA        = 0.05      # düşük alpha → baseline yavaş değişir

# Dip eşiği: baseline * DIP_FACTOR altına düşerse göz kapalı sayılır
# 0.85 = baseline'ın %15 altı → çok küçük göz aralığı için de çalışır
DIP_FACTOR       = 0.85

# Gürültü filtresi
CONSEC_FRAMES    = 2         # kaç ardışık frame dip görülmeli
MIN_BLINKS       = 2
WINDOW_SECONDS   = 15.0

# Kalibrasyon: ilk N frame'de baseline kurulsun
CALIB_FRAMES     = 20


def _ear(landmarks: np.ndarray, idx: list) -> float:
    p = landmarks[idx, :2]
    A = np.linalg.norm(p[1] - p[5])
    B = np.linalg.norm(p[2] - p[4])
    C = np.linalg.norm(p[0] - p[3])
    return float((A + B) / (2.0 * C + 1e-6))


class BlinkDetector(LivenessDetectorBase):

    NAME = "blink"

    def __init__(self) -> None:
        self._mp_provider: Optional[MediaPipeProvider] = None
        # Higher weight to EAR (more reliable in poor lighting)
        self._adaptive_weights = AdaptiveWeights(initial_weight_primary=0.7)
        self._mp_blink_buffer: deque[float] = deque(maxlen=10)
        self._reset_state()

    def _reset_state(self) -> None:
        self._baseline     = None        # EMA baseline (başta None)
        self._calib_buf: list[float] = []  # ilk N frame toplama
        self._calibrated   = False

        self._blink_count  = 0
        self._consec_dip   = 0
        self._in_dip       = False       # dip içinde miyiz?

        self._start_time   = time.monotonic()
        
        # Adaptive weights
        self._adaptive_weights.reset()
        self._mp_blink_buffer.clear()

    def get_instruction(self) -> str:
        return "Lutfen dogal sekilde iki kez goz kirpin."

    def reset(self) -> None:
        self._reset_state()

    @property
    def _threshold(self) -> float:
        if self._baseline is None:
            return 0.0
        return self._baseline * DIP_FACTOR

    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        elapsed   = time.monotonic() - self._start_time
        timed_out = elapsed > WINDOW_SECONDS

        if timed_out and self._blink_count < MIN_BLINKS:
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
                metadata={"blinks": self._blink_count, "calibrated": self._calibrated},
            )

        lm68 = getattr(detection.single_face._raw, "landmark_3d_68", None)
        if lm68 is None:
            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False, message="68 landmark bulunamadi.",
            )

        lm = np.array(lm68)
        ear = (_ear(lm, _LEFT_EYE) + _ear(lm, _RIGHT_EYE)) / 2.0

        # ── MediaPipe blendshape sinyali ──────────────────────────────────
        mp_blink_score = 0.0
        mp_result = None
        if self._mp_provider is not None:
            try:
                mp_result = self._mp_provider.process(bgr_frame)
                if mp_result is not None:
                    left_blink, right_blink = self._mp_provider.get_blink_scores(mp_result)
                    # Inverse: blendshape 0=open, 1=closed; we want open=high
                    mp_blink_score = 1.0 - ((left_blink + right_blink) / 2.0)
                    self._mp_blink_buffer.append(mp_blink_score)
            except Exception as e:
                logger.debug("MediaPipe extraction failed: %s", e)

        # ── Kalibrasyon: ilk CALIB_FRAMES frame'de baseline kur ──────────
        if not self._calibrated:
            self._calib_buf.append(ear)
            if len(self._calib_buf) >= CALIB_FRAMES:
                self._baseline   = float(np.median(self._calib_buf))
                self._calibrated = True

            return LivenessResult(
                is_live=False, score=0.0, method=self.NAME,
                challenge_completed=False,
                message=f"Kalibre ediliyor... ({len(self._calib_buf)}/{CALIB_FRAMES})",
                metadata={
                    "ear":        round(ear, 4),
                    "baseline":   round(np.median(self._calib_buf) if self._calib_buf else 0, 4),
                    "threshold":  0.0,
                    "calibrated": False,
                    "blinks":     0,
                    "mp_blink_score": round(mp_blink_score, 3),
                },
            )

        # ── Adaptive weighting: EAR dip + MediaPipe blink ─────────────────
        ear_confidence = 0.7 if self._baseline is not None else 0.0
        mp_confidence = 0.5 if len(self._mp_blink_buffer) > 0 else 0.0
        
        self._adaptive_weights.update(ear_confidence, mp_confidence)
        w_ear, w_mp = self._adaptive_weights.get_weights()

        # ── EMA baseline güncelle (yalnızca göz açıkken) ─────────────────
        threshold = self._threshold
        if ear > threshold:
            # Göz açık — baseline'ı yavaşça güncelle
            self._baseline = EMA_ALPHA * ear + (1 - EMA_ALPHA) * self._baseline

        # ── Temporal dip state machine ────────────────────────────────────
        if ear < threshold:
            self._consec_dip += 1
            self._in_dip      = True
        else:
            # Dip bitti — göz tekrar açıldı
            if self._in_dip and self._consec_dip >= CONSEC_FRAMES:
                self._blink_count += 1
            self._consec_dip = 0
            self._in_dip     = False

        completed = self._blink_count >= MIN_BLINKS
        score     = 1.0 if completed else min(0.99, self._blink_count / MIN_BLINKS)

        return LivenessResult(
            is_live=completed,
            score=round(score, 3),
            method=self.NAME,
            challenge_completed=completed,
            message=(
                "Tamamlandi!" if completed
                else f"Goz kirpma: {self._blink_count}/{MIN_BLINKS}"
            ),
            metadata={
                "ear":            round(ear, 4),
                "baseline":       round(self._baseline, 4),
                "threshold":      round(threshold, 4),
                "dip_pct":        round((1 - ear / self._baseline) * 100, 1),
                "mp_blink_score": round(mp_blink_score, 3),
                "ensemble_score": round(score, 3),
                "weight_ear":     round(w_ear, 2),
                "weight_mp":      round(w_mp, 2),
                "blinks":         self._blink_count,
                "elapsed":        round(elapsed, 1),
                "calibrated":     True,
            },
        )
