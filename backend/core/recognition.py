"""
core/recognition.py
-------------------
High-level recognition orchestrator.

This module answers ONE question: "Whose face is in this frame?"

It intentionally has NO liveness logic.  The final access decision
(recognition + liveness) is made by decision_engine.py.

Flow
----
  raw BGR frame
      │
      ▼
  preprocessing.prepare_for_insightface()
      │
      ▼
  FaceDetector.detect()   ─── 0 faces → RecognitionResult(face_detected=False)
      │                   ─── >1 face → RecognitionResult(multiple_faces=True)
      ▼
  embedding.extract_embedding()
      │
      ▼
  similarity.find_best_match()
      │
      ▼
  RecognitionResult
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from core.detection import FaceDetector, DetectionResult
from core.embedding import extract_embedding
from core.preprocessing import prepare_for_insightface, validate_frame
from core.similarity import find_best_match, SimilarityMatch
from db import store as db
from utils.constants import (
    RECOGNITION_THRESHOLD,
    MSG_NO_FACE,
    MSG_MULTIPLE_FACES,
    MSG_RECOGNIZED,
    MSG_UNKNOWN,
)

logger = logging.getLogger(__name__)


@dataclass
class RecognitionResult:
    face_detected: bool = False
    face_count: int = 0
    recognized: bool = False
    user_id: Optional[str] = None
    name: Optional[str] = None
    recognition_score: float = 0.0
    bbox: Optional[Tuple[int, int, int, int]] = None   # (x, y, w, h)
    message: str = MSG_NO_FACE


def recognize_frame(
    bgr_frame: np.ndarray,
    threshold: float = RECOGNITION_THRESHOLD,
) -> RecognitionResult:
    """
    Run full recognition pipeline on a single BGR frame.

    Parameters
    ----------
    bgr_frame : OpenCV BGR ndarray (direct from cv2.VideoCapture or decoded upload)
    threshold : cosine similarity threshold; override for per-request tuning

    Returns
    -------
    RecognitionResult dataclass — callers can serialise this directly.
    """

    # 1. Validate frame
    if not validate_frame(bgr_frame):
        return RecognitionResult(message="Invalid or empty frame")

    # 2. Pre-process
    rgb_frame = prepare_for_insightface(bgr_frame)

    # 3. Detect faces
    detector = FaceDetector.get_instance()
    detection: DetectionResult = detector.detect(rgb_frame)

    if not detection.has_face:
        return RecognitionResult(face_detected=False, face_count=0, message=MSG_NO_FACE)

    if detection.count > 1:
        return RecognitionResult(
            face_detected=True,
            face_count=detection.count,
            message=MSG_MULTIPLE_FACES,
        )

    # 4. Single face – extract embedding
    face = detection.single_face
    embedding = extract_embedding(face)
    if embedding is None:
        return RecognitionResult(
            face_detected=True,
            face_count=1,
            bbox=face.as_xywh(),
            message="Embedding extraction failed",
        )

    # 5. Load all users and compare
    users = db.get_all_users()
    if not users:
        return RecognitionResult(
            face_detected=True,
            face_count=1,
            recognized=False,
            bbox=face.as_xywh(),
            recognition_score=0.0,
            message=MSG_UNKNOWN,
        )

    match: Optional[SimilarityMatch] = find_best_match(embedding, users, threshold)

    # 6. Build result
    x, y, w, h = face.as_xywh()
    if match and match.is_match:
        return RecognitionResult(
            face_detected=True,
            face_count=1,
            recognized=True,
            user_id=match.user_id,
            name=match.name,
            recognition_score=round(match.score, 4),
            bbox=(x, y, w, h),
            message=MSG_RECOGNIZED,
        )
    else:
        score = round(match.score, 4) if match else 0.0
        return RecognitionResult(
            face_detected=True,
            face_count=1,
            recognized=False,
            bbox=(x, y, w, h),
            recognition_score=score,
            message=MSG_UNKNOWN,
        )
