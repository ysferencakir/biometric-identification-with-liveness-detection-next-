#!/usr/bin/env python3
"""
backend/scripts/download_hand_model.py
---------------------------------------
Download MediaPipe Hand Landmarker model (~25MB).

Usage:
    python backend/scripts/download_hand_model.py

Model will be saved to: backend/models/hand_landmarker.task
"""

import logging
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
CHUNK_SIZE = 8192


def download_model() -> None:
    backend_dir = Path(__file__).parent.parent
    model_dir = backend_dir / "models"
    model_dir.mkdir(exist_ok=True)
    model_path = model_dir / "hand_landmarker.task"

    if model_path.exists():
        logger.info("Model already exists: %s", model_path)
        return

    logger.info("Downloading MediaPipe Hand Landmarker model...")
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

        logger.info("Model saved to: %s", model_path)

    except requests.RequestException as exc:
        logger.error("Download failed: %s", exc)
        if model_path.exists():
            model_path.unlink()
        raise


if __name__ == "__main__":
    download_model()
