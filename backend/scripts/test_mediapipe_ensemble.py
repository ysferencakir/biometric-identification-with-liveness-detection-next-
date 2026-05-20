#!/usr/bin/env python3
"""
backend/scripts/test_mediapipe_ensemble.py
-------------------------------------------
E2E test for MediaPipe ensemble integration.

Tests all 3 detectors with MediaPipe ensemble:
  - BlinkDetector (EAR + MediaPipe blink)
  - HeadMovementDetector (nose offset + MediaPipe yaw)
  - MouthMovementDetector (MAR + MediaPipe jawOpen)

Measures latency and ensures target <500ms end-to-end.
"""

import logging
import time
from pathlib import Path

import cv2
import numpy as np

# Add backend to path
import sys
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.detection import FaceDetector
from core.liveness import liveness_manager
from core.preprocessing import prepare_for_insightface

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_detector_with_webcam(detector_name: str, num_frames: int = 100) -> dict:
    """
    Test a detector with webcam input.

    Parameters
    ----------
    detector_name : str
        Name of detector (blink, head_movement, mouth_movement)
    num_frames : int
        Number of frames to process

    Returns
    -------
    dict
        Metrics: latencies, passed, metadata samples
    """
    logger.info("Testing detector: %s", detector_name)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logger.error("Cannot open webcam")
        return {}

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    latencies = []
    passed_frames = 0
    failed_frames = 0
    metadata_samples = []

    try:
        for frame_idx in range(num_frames):
            ret, bgr_frame = cap.read()
            if not ret:
                break

            # Measure latency
            start = time.perf_counter()
            try:
                result = liveness_manager.check(bgr_frame, bbox=None, method=detector_name)
                elapsed_ms = (time.perf_counter() - start) * 1000

                if result is not None:
                    latencies.append(elapsed_ms)
                    if result.challenge_completed:
                        passed_frames += 1
                    else:
                        failed_frames += 1

                    # Sample metadata every 20 frames
                    if frame_idx % 20 == 0:
                        metadata_samples.append({
                            "frame": frame_idx,
                            "elapsed_ms": round(elapsed_ms, 2),
                            "score": result.score,
                            "message": result.message,
                            "metadata": result.metadata,
                        })

                # Display progress
                if frame_idx % 10 == 0:
                    logger.info(
                        "Frame %d: %.2f ms | Score: %.3f | %s",
                        frame_idx,
                        elapsed_ms,
                        result.score if result else 0.0,
                        result.message if result else "N/A",
                    )

            except Exception as e:
                logger.error("Processing failed: %s", e)
                failed_frames += 1

    finally:
        cap.release()

    # Compute statistics
    if latencies:
        stats = {
            "detector": detector_name,
            "total_frames": len(latencies),
            "passed_frames": passed_frames,
            "failed_frames": failed_frames,
            "avg_latency_ms": round(np.mean(latencies), 2),
            "min_latency_ms": round(np.min(latencies), 2),
            "max_latency_ms": round(np.max(latencies), 2),
            "std_latency_ms": round(np.std(latencies), 2),
            "target_met": np.mean(latencies) < 500,
            "metadata_samples": metadata_samples,
        }
    else:
        stats = {"error": "No valid frames processed"}

    return stats


def print_results(results: dict) -> None:
    """Pretty-print test results."""
    logger.info("\n" + "=" * 80)
    logger.info("E2E MEDIAPIPE ENSEMBLE TEST RESULTS")
    logger.info("=" * 80)

    for detector_name, metrics in results.items():
        logger.info("\n%s:", detector_name.upper())
        if "error" in metrics:
            logger.error("  Error: %s", metrics["error"])
            continue

        logger.info("  Total frames: %d", metrics["total_frames"])
        logger.info("  Passed: %d | Failed: %d", metrics["passed_frames"], metrics["failed_frames"])
        logger.info("  Latency (avg): %.2f ms", metrics["avg_latency_ms"])
        logger.info("  Latency (min): %.2f ms", metrics["min_latency_ms"])
        logger.info("  Latency (max): %.2f ms", metrics["max_latency_ms"])
        logger.info("  Latency (std): %.2f ms", metrics["std_latency_ms"])
        logger.info("  Target <500ms: %s", "✓ PASS" if metrics["target_met"] else "✗ FAIL")

        if metrics["metadata_samples"]:
            logger.info("\n  Sample metadata:")
            for sample in metrics["metadata_samples"][:3]:
                logger.info(
                    "    Frame %d: %.2f ms | Score: %.3f | %s",
                    sample["frame"],
                    sample["elapsed_ms"],
                    sample["score"],
                    sample["message"],
                )

    logger.info("\n" + "=" * 80)


def main():
    """Run E2E tests."""
    logger.info("MediaPipe Ensemble E2E Test")
    logger.info("Starting webcam tests... (press 'q' to skip to next)")

    results = {}

    # Test each detector
    for detector_name in ["blink", "head_movement", "mouth_movement"]:
        try:
            logger.info("\nTesting %s detector", detector_name)
            logger.info("Processing 100 frames from webcam...")
            stats = test_detector_with_webcam(detector_name, num_frames=100)
            results[detector_name] = stats
            logger.info("✓ Completed")
        except Exception as e:
            logger.error("✗ Failed: %s", e)
            results[detector_name] = {"error": str(e)}

    print_results(results)

    logger.info("\nVerification checklist:")
    logger.info("  [ ] All 3 detectors processed frames without error")
    logger.info("  [ ] Average latency < 500ms for each detector")
    logger.info("  [ ] Metadata includes 'mp_blink_score', 'mp_yaw_deg', 'mp_jaw_open'")
    logger.info("  [ ] Ensemble weights are present in metadata")
    logger.info("  [ ] Challenge completion messages are correct")


if __name__ == "__main__":
    main()
