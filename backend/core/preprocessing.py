"""
core/preprocessing.py
----------------------
Pre-processing steps applied to raw frames before detection / recognition.

Current pipeline:
  1. Validate image (not None, minimum dimensions)
  2. Optional resize to cap max resolution (speeds up inference)
  3. Convert to RGB (InsightFace expects RGB)

The module intentionally has NO InsightFace import so it can be unit-tested
cheaply with only OpenCV + NumPy.
"""

import logging
from typing import Optional, Tuple

import cv2
import numpy as np

from utils.constants import MIN_FACE_SIZE_PX

logger = logging.getLogger(__name__)

# Resize large frames for faster inference; set to None to disable
_MAX_INFERENCE_SIDE = 1280


def validate_frame(img: Optional[np.ndarray]) -> bool:
    """Return True if the image is a valid, non-trivial BGR ndarray."""
    if img is None:
        return False
    if img.ndim != 3 or img.shape[2] != 3:
        return False
    h, w = img.shape[:2]
    if h < MIN_FACE_SIZE_PX or w < MIN_FACE_SIZE_PX:
        logger.warning("Frame too small: %dx%d", w, h)
        return False
    return True


def prepare_for_insightface(img: np.ndarray) -> np.ndarray:
    """
    Convert a BGR OpenCV frame to an RGB ndarray suitable for InsightFace.
    Optionally downscales very large frames.
    """
    # Downscale if necessary
    if _MAX_INFERENCE_SIDE is not None:
        h, w = img.shape[:2]
        scale = min(_MAX_INFERENCE_SIDE / max(h, w), 1.0)
        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # BGR → RGB
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return rgb


def crop_face(img: np.ndarray, bbox: Tuple[int, int, int, int], padding: float = 0.15) -> np.ndarray:
    """
    Crop the face region from an image with optional padding.

    bbox: (x1, y1, x2, y2) in pixel coordinates.
    padding: fractional amount to expand each side (0.15 = 15%).
    """
    h, w = img.shape[:2]
    x1, y1, x2, y2 = bbox
    bw = x2 - x1
    bh = y2 - y1

    pad_x = int(bw * padding)
    pad_y = int(bh * padding)

    cx1 = max(0, x1 - pad_x)
    cy1 = max(0, y1 - pad_y)
    cx2 = min(w, x2 + pad_x)
    cy2 = min(h, y2 + pad_y)

    return img[cy1:cy2, cx1:cx2]
