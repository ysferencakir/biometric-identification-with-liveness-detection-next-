"""
core/liveness/new_blink_detector.py
------------------------------------
MPEblink / InstBlink inspired Blink Detector.

Designed as a multi-person / untrimmed video state-machine blink detector.
Supports loading a custom deep learning model (e.g., ONNX model for MPEblink)
with a robust high-precision MediaPipe Face Mesh fallback for immediate testing.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Any
import numpy as np
import cv2

from core.liveness.base import LivenessDetectorBase, LivenessResult
from core.liveness.mediapipe_provider import MediaPipeProvider
from core.detection import FaceDetector

logger = logging.getLogger(__name__)

# State machine constants
STATE_OPEN = "OPEN"
STATE_CLOSING = "CLOSING"
STATE_CLOSED = "CLOSED"
STATE_OPENING = "OPENING"

class NewBlinkDetector(LivenessDetectorBase):
    NAME = "new_blink"

    def __init__(self) -> None:
        self.model_path = self._get_model_path()
        self.onnx_session = None
        self._mp_provider = None
        self._load_model()
        self.reset()

    def _get_model_path(self) -> Path:
        backend_dir = Path(__file__).parent.parent.parent
        return backend_dir / "models" / "new_blink.onnx"

    def _load_model(self) -> None:
        """Load pretrained MPEblink/InstBlink ONNX model if available."""
        if not self.model_path.exists():
            logger.info(
                "MPEblink/InstBlink model file not found at %s. "
                "Using high-precision MediaPipe Face Mesh fallback for testing.",
                self.model_path
            )
            return

        try:
            import onnxruntime as ort
            # Use CPU or GPU based on availability
            providers = ['CPUExecutionProvider']
            self.onnx_session = ort.InferenceSession(str(self.model_path), providers=providers)
            logger.info("MPEblink/InstBlink ONNX model loaded successfully from %s", self.model_path)
        except Exception as e:
            logger.error("Failed to load MPEblink/InstBlink ONNX model: %s", e)
            self.onnx_session = None

    def reset(self) -> None:
        """Reset the blink state machine and tracking buffers."""
        self._state = STATE_OPEN
        self._blink_count = 0
        self._blink_timestamps = []
        self._start_time = time.monotonic()
        self._frame_buffer = []  # For untrimmed video modeling / temporal context
        self._max_buffer_size = 15  # MPEblink benefits from temporal context
        self._calibrated = True

    def get_instruction(self) -> str:
        return "Lutfen yeni yontemle (New Blink) dogal sekilde iki kez goz kirpin."

    def update(self, bgr_frame: np.ndarray, face_rect: Optional[tuple] = None) -> dict[str, Any]:
        """
        Processes a single frame and updates the state machine.
        Returns a dict with blink_detected, eye_closeness_score, and current_state.
        """
        blink_detected = False
        eye_closeness = 0.0  # 1.0 = fully closed, 0.0 = fully open

        # ── 1. If ONNX model is available, use it ──────────────────────────
        if self.onnx_session is not None and face_rect is not None:
            try:
                # Preprocess face crop for MPEblink / InstBlink
                x1, y1, x2, y2 = face_rect
                h, w = bgr_frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                face_crop = bgr_frame[y1:y2, x1:x2]
                if face_crop.size > 0:
                    # Prepare input tensor (e.g. 112x112 resize, normalized)
                    resized = cv2.resize(face_crop, (112, 112))
                    input_data = resized.astype(np.float32) / 255.0
                    input_data = np.transpose(input_data, (2, 0, 1))  # HWC to CHW
                    input_data = np.expand_dims(input_data, axis=0)   # BCHW
                    
                    # Run inference
                    input_name = self.onnx_session.get_inputs()[0].name
                    outputs = self.onnx_session.run(None, {input_name: input_data})
                    
                    # Assume MPEblink returns a single closeness score or classification logit
                    closeness_score = float(outputs[0][0][0])
                    # Sigmoid if raw logits
                    eye_closeness = 1.0 / (1.0 + np.exp(-closeness_score)) if closeness_score < 10 else closeness_score
            except Exception as e:
                logger.error("ONNX inference failed, using landmark fallback: %s", e)

        # ── 2. Fallback / Complementary: High-precision MediaPipe blendshapes ──
        if self.onnx_session is None:
            if self._mp_provider is None:
                try:
                    self._mp_provider = MediaPipeProvider.get_instance()
                except Exception:
                    self._mp_provider = None

            if self._mp_provider is not None:
                mp_result = self._mp_provider.process(bgr_frame)
                if mp_result is not None:
                    left_blink, right_blink = self._mp_provider.get_blink_scores(mp_result)
                    # MediaPipe blink scores: 0.0 = open, 1.0 = closed
                    eye_closeness = (left_blink + right_blink) / 2.0

        # Maintain temporal buffer for model evaluation
        self._frame_buffer.append(eye_closeness)
        if len(self._frame_buffer) > self._max_buffer_size:
            self._frame_buffer.pop(0)

        # ── 3. State Machine (Temporal Dip / Event Detection) ──────────────
        CLOSE_THRESH = 0.50  # eyes considered closed
        OPEN_THRESH = 0.30   # eyes considered open

        prev_state = self._state
        timestamp = time.monotonic()

        if self._state == STATE_OPEN:
            if eye_closeness >= CLOSE_THRESH:
                self._state = STATE_CLOSED
        elif self._state == STATE_CLOSED:
            if eye_closeness < OPEN_THRESH:
                self._state = STATE_OPEN
                # Successfully registered a full blink event!
                blink_detected = True
                self._blink_count += 1
                self._blink_timestamps.append(timestamp)

        return {
            "blink_detected": blink_detected,
            "eye_closeness": eye_closeness,
            "current_state": self._state,
            "prev_state": prev_state,
        }

    def check(self, bgr_frame: np.ndarray, bbox: tuple) -> LivenessResult:
        elapsed = time.monotonic() - self._start_time
        WINDOW_SECONDS = 10.0
        MIN_BLINKS = 2

        if elapsed > WINDOW_SECONDS and self._blink_count < MIN_BLINKS:
            self.reset()
            elapsed = 0.0

        # Update state machine
        update_result = self.update(bgr_frame, bbox)
        
        eye_closeness = update_result["eye_closeness"]
        current_state = update_result["current_state"]
        
        completed = self._blink_count >= MIN_BLINKS
        score = 1.0 if completed else min(0.99, self._blink_count / MIN_BLINKS)

        mode = "ONNX Model" if self.onnx_session is not None else "MediaPipe Fallback"

        return LivenessResult(
            is_live=completed,
            score=round(score, 3),
            method=self.NAME,
            challenge_completed=completed,
            message=(
                "Tamamlandi!" if completed
                else f"Yeni Goz Kirpma (New Blink): {self._blink_count}/{MIN_BLINKS}"
            ),
            metadata={
                "eye_closeness": round(eye_closeness, 3),
                "state": current_state,
                "blinks": self._blink_count,
                "elapsed": round(elapsed, 1),
                "mode": mode,
                "model_loaded": self.onnx_session is not None,
                "completed": completed
            }
        )
