#!/usr/bin/env python3
"""
backend/scripts/download_mediapipe_model.py
--------------------------------------------
Download MediaPipe Face Landmarker model (~30MB).

Usage:
    python backend/scripts/download_mediapipe_model.py

Model will be saved to: backend/models/face_landmarker.task
"""

import logging
import os
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

CHUNK_SIZE = 8192


def download_model() -> None:
    """Download MediaPipe Face Landmarker model."""
    # Determine model path
    backend_dir = Path(__file__).parent.parent
    model_dir = backend_dir / "models"
    model_dir.mkdir(exist_ok=True)
    model_path = model_dir / "face_landmarker.task"

    if model_path.exists():
        logger.info("Model already exists: %s", model_path)
        return

    logger.info("Downloading MediaPipe Face Landmarker model...")
    logger.info("URL: %s", MODEL_URL)

    try:
        response = requests.get(MODEL_URL, stream=True, timeout=60)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(model_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        logger.info(
                            "Downloaded: %.1f MB (%.1f%%)",
                            downloaded / (1024 * 1024),
                            pct,
                        )

        logger.info("✓ Model saved to: %s", model_path)

    except requests.RequestException as e:
        logger.error("Download failed: %s", e)
        if model_path.exists():
            model_path.unlink()
        raise


if __name__ == "__main__":
    download_model()
