#!/usr/bin/env python3
"""
backend/scripts/test_mediapipe_ensemble_visual.py
---------------------------------------------------
Visual E2E test with real-time webcam display.

Shows live detector results on screen:
  - BlinkDetector: blink count + EAR signal
  - HeadMovementDetector: head pose + offset signal
  - MouthMovementDetector: mouth cycles + MAR signal
  - MediaPipe ensemble weights

Press 'q' to quit, 's' to switch detector.
"""

import logging
import sys
from pathlib import Path

import cv2
import numpy as np

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.detection import FaceDetector
from core.liveness import liveness_manager
from core.preprocessing import prepare_for_insightface

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def draw_text(frame, text, pos=(10, 30), color=(0, 255, 0), size=0.7):
    """Draw text on frame."""
    cv2.putText(
        frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, size, color, 2
    )


def visualize_detector(cap, detector_name: str):
    """
    Visualize a single detector on webcam feed.

    Parameters
    ----------
    cap : cv2.VideoCapture
        Webcam capture object
    detector_name : str
        Detector name: 'blink', 'head_movement', 'mouth_movement'
    """
    logger.info(f"Starting visual test for: {detector_name}")
    frame_count = 0
    
    instructions = {
        "blink": "Kırpın doğal şekilde 2 kez (Please blink 2 times)",
        "head_movement": "Başınızı sağa, sonra sola çevirin (Turn head right, then left)",
        "mouth_movement": "Ağzınızı 2 kez açıp kapatın (Open mouth 2 times)",
    }

    while True:
        ret, bgr_frame = cap.read()
        if not ret:
            logger.error("Webcam read failed")
            break

        frame_count += 1
        h, w = bgr_frame.shape[:2]

        # Run detector
        try:
            result = liveness_manager.check(bgr_frame, bbox=None, method=detector_name)
        except Exception as e:
            logger.error(f"Detection error: {e}")
            result = None

        # Draw UI
        display_frame = bgr_frame.copy()

        # Header
        draw_text(
            display_frame,
            f"Detector: {detector_name.upper()}",
            (10, 30),
            (255, 255, 255),
            1.0,
        )
        draw_text(
            display_frame,
            f"Frame: {frame_count}",
            (10, 60),
            (255, 255, 255),
            0.7,
        )

        if result:
            # Status bar
            status_color = (0, 255, 0) if result.challenge_completed else (0, 165, 255)
            status_text = "✓ COMPLETED" if result.challenge_completed else "○ IN PROGRESS"
            draw_text(
                display_frame, status_text, (w - 300, 30), status_color, 0.8
            )

            # Score bar
            score_pct = int(result.score * 100)
            bar_width = int((w - 20) * result.score)
            cv2.rectangle(display_frame, (10, 80), (10 + bar_width, 110), (0, 255, 0), -1)
            cv2.rectangle(display_frame, (10, 80), (w - 10, 110), (255, 255, 255), 2)
            draw_text(display_frame, f"Progress: {score_pct}%", (20, 105), (0, 0, 0), 0.6)

            # Message
            draw_text(
                display_frame,
                result.message,
                (10, 140),
                (0, 255, 0),
                0.8,
            )

            # Metadata
            if result.metadata:
                y_offset = 170
                for key, value in list(result.metadata.items())[:6]:  # Show first 6 fields
                    text = f"{key}: {value}"
                    draw_text(display_frame, text, (10, y_offset), (200, 200, 200), 0.5)
                    y_offset += 25
        else:
            draw_text(display_frame, "⚠ Detection error", (10, 140), (0, 0, 255), 0.8)

        # Instructions
        draw_text(
            display_frame,
            instructions.get(detector_name, ""),
            (10, h - 40),
            (200, 200, 200),
            0.6,
        )

        # Controls
        draw_text(
            display_frame,
            "Press: 'q'=quit  's'=switch detector",
            (10, h - 10),
            (100, 100, 100),
            0.5,
        )

        cv2.imshow(f"MediaPipe Ensemble Test - {detector_name}", display_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            logger.info("Switching detector...")
            return True

    return False


def main():
    """Run visual tests."""
    logger.info("MediaPipe Ensemble Visual Test")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Webcam açılamadı / Cannot open webcam")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    detectors = ["blink", "head_movement", "mouth_movement"]
    detector_idx = 0

    try:
        while True:
            detector_name = detectors[detector_idx]
            print(f"\n{'='*60}")
            print(f"Testing: {detector_name}")
            print(f"{'='*60}\n")

            switch = visualize_detector(cap, detector_name)
            if not switch:
                break

            detector_idx = (detector_idx + 1) % len(detectors)

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\n✓ Test completed")


if __name__ == "__main__":
    main()
