"""
core/liveness/mediapipe_provider.py
-----------------------------------
MediaPipe Face Landmarker provider — singleton model management.

Provides 478-landmark detection + blendshape extraction for liveness signals.
Parallel to InsightFace; InsightFace remains for recognition.

Model: face_landmarker.task (~30MB)
  - Download: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
  - Place at: backend/models/face_landmarker.task
"""

import logging
import os
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.warning("MediaPipe not found. Install: pip install mediapipe")

# Blendshape indeksleri (MediaPipe Face Landmarker 0.10.x)
BLENDSHAPE_INDEX_EYE_BLINK_LEFT = 9
BLENDSHAPE_INDEX_EYE_BLINK_RIGHT = 10
BLENDSHAPE_INDEX_JAW_OPEN = 12


class MediaPipeProvider:
    """
    Singleton provider for MediaPipe Face Landmarker.
    
    Loads model once on first use. Provides convenience methods for
    extracting liveness signals (blink, jaw, head pose).
    """

    _instance: Optional["MediaPipeProvider"] = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._landmarker = None
        self._initialized = False

        self._load_model()
        self._initialized = True

    def _load_model(self) -> None:
        """Load MediaPipe Face Landmarker model."""
        if not MEDIAPIPE_AVAILABLE:
            logger.error("MediaPipe is not installed")
            return

        model_path = self._get_model_path()

        if not os.path.exists(model_path):
            logger.error(
                "MediaPipe model not found: %s\n"
                "Download it: python backend/scripts/download_mediapipe_model.py",
                model_path
            )
            return

        try:
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_faces=1,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
            )
            self._landmarker = vision.FaceLandmarker.create_from_options(options)
            logger.info("MediaPipe Face Landmarker loaded from %s", model_path)
        except Exception as e:
            logger.error("Failed to load MediaPipe model: %s", e)
            self._landmarker = None

    @staticmethod
    def _get_model_path() -> str:
        """Get path to face_landmarker.task model."""
        backend_dir = Path(__file__).parent.parent.parent  # backend/
        # models/mediapipe/ veya models/ klasörüne bak
        for path in [
            backend_dir / "models" / "mediapipe" / "face_landmarker.task",
            backend_dir / "models" / "face_landmarker.task",
        ]:
            if path.exists():
                return str(path)
        return str(backend_dir / "models" / "mediapipe" / "face_landmarker.task")

    @staticmethod
    def get_instance() -> "MediaPipeProvider":
        """Get or create singleton instance."""
        return MediaPipeProvider()

    def process(self, bgr_frame: np.ndarray) -> Optional[vision.FaceLandmarkerResult]:
        """
        Process BGR frame with MediaPipe Face Landmarker.

        Parameters
        ----------
        bgr_frame : np.ndarray
            OpenCV BGR frame

        Returns
        -------
        Optional[vision.FaceLandmarkerResult]
            MediaPipe result or None on failure
        """
        if self._landmarker is None:
            logger.warning("MediaPipe landmarker not initialized")
            return None

        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)

            # MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # Detect
            result = self._landmarker.detect(mp_image)

            return result if result and result.face_landmarks else None
        except Exception as e:
            logger.error("MediaPipe detection failed: %s", e)
            return None

    def get_blink_scores(
        self, result: vision.FaceLandmarkerResult
    ) -> tuple[float, float]:
        """
        Extract eye blink scores from MediaPipe result.

        Blendshape values: 0.0 = eyes open, 1.0 = eyes closed

        Parameters
        ----------
        result : vision.FaceLandmarkerResult
            MediaPipe detection result

        Returns
        -------
        tuple[float, float]
            (left_blink_score, right_blink_score) — each in [0, 1]
        """
        if not result or not result.face_blendshapes:
            return 0.0, 0.0

        blendshapes = result.face_blendshapes[0]  # First face

        left_blink = 0.0
        right_blink = 0.0

        for blendshape in blendshapes:
            if blendshape.index == BLENDSHAPE_INDEX_EYE_BLINK_LEFT:
                left_blink = float(blendshape.score)
            elif blendshape.index == BLENDSHAPE_INDEX_EYE_BLINK_RIGHT:
                right_blink = float(blendshape.score)

        return left_blink, right_blink

    def get_jaw_open_score(self, result: vision.FaceLandmarkerResult) -> float:
        """
        Extract jaw open (mouth opening) score from MediaPipe result.

        Blendshape value: 0.0 = mouth closed, 1.0 = mouth open

        Parameters
        ----------
        result : vision.FaceLandmarkerResult
            MediaPipe detection result

        Returns
        -------
        float
            Jaw open score in [0, 1]
        """
        if not result or not result.face_blendshapes:
            return 0.0

        blendshapes = result.face_blendshapes[0]  # First face

        for blendshape in blendshapes:
            if blendshape.index == BLENDSHAPE_INDEX_JAW_OPEN:
                return float(blendshape.score)

        return 0.0

    def get_head_yaw(self, result: vision.FaceLandmarkerResult) -> float:
        """
        Extract head yaw angle from facial transformation matrix.

        Yaw angle: positive = head turned right, negative = head turned left

        Parameters
        ----------
        result : vision.FaceLandmarkerResult
            MediaPipe detection result

        Returns
        -------
        float
            Yaw angle in degrees, approximately [-90, 90]
        """
        if not result or not result.facial_transformation_matrixes:
            return 0.0

        matrix = result.facial_transformation_matrixes[0]  # First face (4x4)

        # Extract yaw from transformation matrix
        # Approximate: yaw ≈ arctan2(matrix[0, 2], matrix[0, 0]) in radians
        yaw_rad = np.arctan2(matrix[0, 2], matrix[0, 0])
        yaw_deg = float(np.degrees(yaw_rad))

        return yaw_deg

    def has_valid_face(self, result: Optional[vision.FaceLandmarkerResult]) -> bool:
        """Check if result contains valid face detection."""
        return result is not None and len(result.face_landmarks) > 0
