"""
core/detection.py
-----------------
Face detection wrapper around InsightFace.

Key design decisions
--------------------
* Singleton pattern: the model is loaded once at application startup and reused.
* GPU-first with automatic CPU fallback.
* Returns a typed FaceDetectionResult dataclass so callers never touch raw
  InsightFace objects directly. This makes future model swaps transparent.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from config import settings
from utils.constants import MIN_FACE_SIZE_PX

logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    """One detected face from a frame."""
    bbox: Tuple[int, int, int, int]   # (x1, y1, x2, y2) pixel coords
    score: float                       # detection confidence
    # InsightFace face object stored for embedding extraction (opaque to callers)
    _raw: object = field(default=None, repr=False)

    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> int:
        return self.width * self.height

    def as_xywh(self) -> Tuple[int, int, int, int]:
        """Return bbox as (x, y, w, h) — useful for drawing."""
        x1, y1, x2, y2 = self.bbox
        return x1, y1, x2 - x1, y2 - y1


@dataclass
class DetectionResult:
    faces: List[DetectedFace] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def count(self) -> int:
        return len(self.faces)

    @property
    def has_face(self) -> bool:
        return self.count > 0

    @property
    def single_face(self) -> Optional[DetectedFace]:
        return self.faces[0] if self.count == 1 else None


class FaceDetector:
    """
    Singleton wrapper around InsightFace FaceAnalysis.

    Usage
    -----
        detector = FaceDetector.get_instance()
        result = detector.detect(rgb_frame)
    """

    _instance: Optional["FaceDetector"] = None

    def __init__(self) -> None:
        self._app = self._load_model()

    @classmethod
    def get_instance(cls) -> "FaceDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Private ───────────────────────────────────────────────────────────

    def _load_model(self):
        """Load InsightFace; try GPU first, fall back to CPU."""
        from insightface.app import FaceAnalysis

        ctx_id = settings.INSIGHTFACE_CTX_ID  # 0 = GPU, -1 = CPU
        app = None

        # --- GPU attempt ---
        if ctx_id >= 0:
            try:
                app = FaceAnalysis(
                    name=settings.INSIGHTFACE_MODEL,
                    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                )
                app.prepare(ctx_id=ctx_id, det_size=(640, 640))
                logger.info("InsightFace loaded on GPU (ctx_id=%d)", ctx_id)
            except Exception as gpu_err:
                logger.warning("GPU init failed (%s); falling back to CPU", gpu_err)
                app = None

        # --- CPU fallback ---
        if app is None:
            try:
                app = FaceAnalysis(
                    name=settings.INSIGHTFACE_MODEL,
                    providers=["CPUExecutionProvider"],
                )
                app.prepare(ctx_id=-1, det_size=(640, 640))
                logger.info("InsightFace loaded on CPU (fallback)")
            except Exception as cpu_err:
                logger.error("InsightFace CPU init failed: %s", cpu_err)
                raise RuntimeError(f"Cannot initialise InsightFace: {cpu_err}") from cpu_err

        return app

    # ── Public ────────────────────────────────────────────────────────────

    def detect(self, rgb_frame: np.ndarray) -> DetectionResult:
        """
        Run detection on an RGB frame.

        Returns DetectionResult with all faces above MIN_FACE_SIZE_PX.
        Faces are sorted by area descending (largest first).
        """
        try:
            raw_faces = self._app.get(rgb_frame)
        except Exception as exc:
            logger.error("Detection inference failed: %s", exc)
            return DetectionResult(error=str(exc))

        detected: List[DetectedFace] = []
        for face in raw_faces:
            x1, y1, x2, y2 = [int(v) for v in face.bbox]
            w = x2 - x1
            h = y2 - y1
            if w < MIN_FACE_SIZE_PX or h < MIN_FACE_SIZE_PX:
                logger.debug("Skipping small face (%dx%d)", w, h)
                continue
            det = DetectedFace(
                bbox=(x1, y1, x2, y2),
                score=float(face.det_score) if hasattr(face, "det_score") else 1.0,
                _raw=face,
            )
            detected.append(det)

        # Sort by area descending
        detected.sort(key=lambda f: f.area, reverse=True)
        return DetectionResult(faces=detected)
