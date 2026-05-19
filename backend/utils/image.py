"""
utils/image.py
--------------
Utility helpers for image I/O between FastAPI / OpenCV / InsightFace.
"""

import base64
import io
import logging
from typing import Optional

import cv2
import numpy as np
from fastapi import UploadFile

logger = logging.getLogger(__name__)


def decode_base64_image(b64_string: str) -> Optional[np.ndarray]:
    """
    Decode a base64-encoded image string into an OpenCV BGR ndarray.

    Accepts both plain base64 and data-URI strings
    (e.g. 'data:image/jpeg;base64,/9j/4AAQ...').

    Returns None on failure.
    """
    try:
        # Strip data-URI prefix if present
        if "," in b64_string:
            b64_string = b64_string.split(",", 1)[1]

        image_bytes = base64.b64decode(b64_string)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as exc:
        logger.error("base64 decode failed: %s", exc)
        return None


async def decode_upload_image(file: UploadFile) -> Optional[np.ndarray]:
    """
    Read an UploadFile (multipart/form-data) and convert to BGR ndarray.

    Returns None on failure.
    """
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as exc:
        logger.error("upload image decode failed: %s", exc)
        return None


def encode_image_to_base64(img: np.ndarray, ext: str = ".jpg") -> str:
    """
    Encode an OpenCV BGR ndarray to a base64 string (no data-URI prefix).
    """
    success, buffer = cv2.imencode(ext, img)
    if not success:
        raise ValueError("cv2.imencode failed")
    return base64.b64encode(buffer).decode("utf-8")


def resize_keep_aspect(img: np.ndarray, max_side: int = 640) -> np.ndarray:
    """
    Resize image so the longest side is ≤ max_side, preserving aspect ratio.
    """
    h, w = img.shape[:2]
    scale = min(max_side / max(h, w), 1.0)  # never upscale
    if scale < 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return img
