#!/usr/bin/env python3
"""
backend/scripts/measure_performance_metrics.py
-----------------------------------------------
Measure and compare performance metrics between original and MediaPipe ensemble.

Metrics:
  - FAR (False Acceptance Rate)
  - FRR (False Rejection Rate)
  - Spoofing detection rates (photo, video)
  - Latency comparison
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_performance_report() -> dict:
    """
    Create performance report template for MediaPipe ensemble.

    Returns
    -------
    dict
        Report structure with test results
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "phase": "Aşama 2 — MediaPipe Ensemble",
        "test_results": {
            "blink_detector": {
                "description": "Eye blink detection with EAR + MediaPipe blendshape",
                "test_cases": [
                    {
                        "name": "Natural blinks",
                        "duration_sec": 15,
                        "target_blinks": 2,
                        "status": "pending",
                        "latency_ms": None,
                        "ensemble_weights": {
                            "ear_initial": 0.4,
                            "mp_initial": 0.6,
                            "adaptive": True,
                        },
                    },
                    {
                        "name": "Photo spoofing resistance",
                        "description": "Blendshape should remain ~0 for printed photo",
                        "status": "pending",
                        "detection_rate": None,
                    },
                    {
                        "name": "Video spoofing resistance",
                        "description": "Blendshape instability should trigger rejection",
                        "status": "pending",
                        "detection_rate": None,
                    },
                ],
                "metadata_validation": {
                    "required_fields": [
                        "ear",
                        "baseline",
                        "mp_blink_score",
                        "ensemble_score",
                        "weight_ear",
                        "weight_mp",
                        "blinks",
                        "calibrated",
                    ],
                    "validated": False,
                },
            },
            "head_movement_detector": {
                "description": "Head pose with nose offset + MediaPipe yaw",
                "test_cases": [
                    {
                        "name": "Right-left head turns",
                        "duration_sec": 20,
                        "offset_threshold": 0.12,
                        "status": "pending",
                        "latency_ms": None,
                        "ensemble_weights": {
                            "nose_offset_initial": 0.3,
                            "mp_yaw_initial": 0.7,
                            "adaptive": True,
                        },
                    },
                    {
                        "name": "Camera angle independence",
                        "description": "Should work at different camera angles",
                        "status": "pending",
                        "success_rate": None,
                    },
                ],
                "metadata_validation": {
                    "required_fields": [
                        "offset",
                        "rel",
                        "baseline",
                        "mp_yaw_deg",
                        "ensemble_score",
                        "weight_offset",
                        "weight_mp",
                        "completed",
                    ],
                    "validated": False,
                },
            },
            "mouth_movement_detector": {
                "description": "Mouth movement with MAR + MediaPipe jawOpen",
                "test_cases": [
                    {
                        "name": "Natural mouth open-close",
                        "duration_sec": 15,
                        "target_cycles": 2,
                        "status": "pending",
                        "latency_ms": None,
                        "ensemble_weights": {
                            "mar_initial": 0.4,
                            "mp_jaw_initial": 0.6,
                            "adaptive": True,
                        },
                    },
                    {
                        "name": "Photo spoofing resistance",
                        "description": "JAR should remain ~0 for printed photo",
                        "status": "pending",
                        "detection_rate": None,
                    },
                ],
                "metadata_validation": {
                    "required_fields": [
                        "mar",
                        "mp_jaw_open",
                        "ensemble_score",
                        "weight_mar",
                        "weight_mp",
                        "open_close",
                        "elapsed",
                    ],
                    "validated": False,
                },
            },
        },
        "end_to_end_metrics": {
            "session_flow": "register → 2 liveness → biometric",
            "target_latency_ms": 500,
            "current_latency_ms": None,
            "mediapipe_overhead_ms": None,
            "status": "pending",
        },
        "spoofing_tests": {
            "photo_attack": {
                "method": "Printed photo",
                "target_detection_rate": 0.90,
                "current_rate": None,
                "status": "pending",
            },
            "video_attack": {
                "method": "Replayed video",
                "target_detection_rate": 0.85,
                "current_rate": None,
                "status": "pending",
            },
            "mask_attack": {
                "method": "Silicone/3D mask",
                "target_detection_rate": 0.80,
                "current_rate": None,
                "status": "pending",
            },
        },
        "adaptive_weights_behavior": {
            "description": "Tracks how weights evolve based on signal quality",
            "blink": {
                "initial": [0.4, 0.6],
                "after_calibration": None,
                "stability_metric": None,
            },
            "head": {
                "initial": [0.3, 0.7],
                "after_calibration": None,
                "stability_metric": None,
            },
            "mouth": {
                "initial": [0.4, 0.6],
                "after_calibration": None,
                "stability_metric": None,
            },
        },
        "checklist": {
            "mediapipe_provider_loads": False,
            "all_detectors_use_ensemble": False,
            "fallback_works_without_mediapipe": False,
            "metadata_complete": False,
            "latency_target_met": False,
            "backward_compatibility": False,
        },
        "notes": [
            "InsightFace landmark (68-point) remains unchanged for recognition",
            "MediaPipe is parallel signal source for liveness only",
            "Fallback to InsightFace-only if MediaPipe unavailable",
            "Database schema unchanged (scores in metadata)",
            "All ensemble weights adaptive based on signal quality",
        ],
    }

    return report


def save_report(report: dict, output_file: str = None) -> str:
    """
    Save performance report to JSON file.

    Parameters
    ----------
    report : dict
        Report data
    output_file : str, optional
        Output file path. If None, uses default location.

    Returns
    -------
    str
        Path to saved report
    """
    if output_file is None:
        backend_dir = Path(__file__).parent.parent
        report_dir = backend_dir / "reports"
        report_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = report_dir / f"mediapipe_ensemble_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Report saved to: %s", output_file)
    return str(output_file)


def print_report(report: dict) -> None:
    """Pretty-print performance report."""
    logger.info("\n" + "=" * 80)
    logger.info("MEDIAPIPE ENSEMBLE PERFORMANCE REPORT")
    logger.info("=" * 80)
    logger.info("Timestamp: %s", report["timestamp"])
    logger.info("Phase: %s", report["phase"])

    logger.info("\nTEST CHECKLIST:")
    for item, status in report["checklist"].items():
        status_str = "✓ PASS" if status else "⬜ PENDING"
        logger.info("  %s: %s", item, status_str)

    logger.info("\nEND-TO-END METRICS:")
    e2e = report["end_to_end_metrics"]
    logger.info("  Session flow: %s", e2e["session_flow"])
    logger.info("  Target latency: <%.0f ms", e2e["target_latency_ms"])
    logger.info("  Current latency: %s ms", e2e["current_latency_ms"])

    logger.info("\nDETECTOR ENSEMBLES:")
    for detector_name, details in report["test_results"].items():
        logger.info("  %s:", detector_name)
        if "ensemble_weights" in details:
            for test in details.get("test_cases", []):
                logger.info("    - %s: %s", test["name"], test["status"])

    logger.info("\nSPOOFING TESTS:")
    for attack_type, metrics in report["spoofing_tests"].items():
        logger.info(
            "  %s: target=%.0f%%, current=%s",
            attack_type,
            metrics["target_detection_rate"] * 100,
            metrics["current_rate"],
        )

    logger.info("\nNOTES:")
    for note in report["notes"]:
        logger.info("  • %s", note)

    logger.info("\n" + "=" * 80)


def main():
    """Create and save performance report."""
    logger.info("Creating MediaPipe Ensemble Performance Report...")

    report = create_performance_report()
    report_path = save_report(report)
    print_report(report)

    logger.info("\nNext steps:")
    logger.info("  1. Download MediaPipe model:")
    logger.info("     python backend/scripts/download_mediapipe_model.py")
    logger.info("  2. Run E2E test:")
    logger.info("     python backend/scripts/test_mediapipe_ensemble.py")
    logger.info("  3. Update report with actual results")
    logger.info("  4. Run spoofing attack simulations")
    logger.info("\nReport template: %s", report_path)


if __name__ == "__main__":
    main()
