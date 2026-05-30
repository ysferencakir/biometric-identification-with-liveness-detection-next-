"""
core/liveness/hands_provider.py
--------------------------------
MediaPipe Hand Landmarker singleton — real-time hand landmark detection.

Uses the Tasks API (mediapipe.tasks) — same approach as mediapipe_provider.py.
mp.solutions.hands was removed in MediaPipe 0.10.x.

Model: hand_landmarker.task (~25MB)
  - Download: python backend/scripts/download_hand_model.py
  - Place at: backend/models/hand_landmarker.task
"""

import logging
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

# ── Landmark indices ──────────────────────────────────────────────────────────
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP       = 1,  2,  3,  4
INDEX_MCP,  INDEX_PIP,  INDEX_DIP,  INDEX_TIP    = 5,  6,  7,  8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP   = 9,  10, 11, 12
RING_MCP,   RING_PIP,   RING_DID,   RING_TIP     = 13, 14, 15, 16
PINKY_MCP,  PINKY_PIP,  PINKY_DIP,  PINKY_TIP    = 17, 18, 19, 20

# Minimum projection along hand's "up" axis to count a finger as extended
_EXTEND_THRESH = 0.025


class HandsProvider:
    """
    Singleton provider for MediaPipe Hand Landmarker (Tasks API).

    Loads the model once on first use. Call process() per frame to get
    the number of extended fingers (0–5), or None if no hand is visible.
    """

    _instance: Optional["HandsProvider"] = None

    def __new__(cls) -> "HandsProvider":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._landmarker = None
        self._load_model()
        self._initialized = True

    @staticmethod
    def get_instance() -> "HandsProvider":
        return HandsProvider()

    # ── Model loading ─────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        if not MEDIAPIPE_AVAILABLE:
            logger.error("MediaPipe not installed — HandsProvider unavailable")
            return

        model_path = self._find_model()
        if not model_path:
            logger.error(
                "hand_landmarker.task not found. "
                "Download it: python backend/scripts/download_hand_model.py"
            )
            return

        try:
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_hands=1,
                min_hand_detection_confidence=0.75,
                min_hand_presence_confidence=0.6,
                min_tracking_confidence=0.6,
            )
            self._landmarker = vision.HandLandmarker.create_from_options(options)
            logger.info("MediaPipe HandLandmarker loaded from %s", model_path)
        except Exception as exc:
            logger.error("Failed to load HandLandmarker: %s", exc)
            self._landmarker = None

    @staticmethod
    def _find_model() -> Optional[str]:
        backend_dir = Path(__file__).parent.parent.parent
        candidates = [
            backend_dir / "models" / "hand_landmarker.task",
            backend_dir / "models" / "mediapipe" / "hand_landmarker.task",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    # ── Public API ────────────────────────────────────────────────────────────

    def process(self, bgr_frame: np.ndarray) -> Optional[int]:
        """
        Process one BGR camera frame.

        Returns
        -------
        int
            Number of extended fingers (0–5).
        None
            No hand detected or model unavailable.
        """
        if self._landmarker is None:
            return None

        try:
            rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._landmarker.detect(mp_image)

            if not result.hand_landmarks or not result.handedness:
                return None

            lm = result.hand_landmarks[0]
            # Tasks API handedness: "Left"/"Right" from the model's perspective
            handedness: str = result.handedness[0][0].category_name

            return self._count_fingers(lm, handedness)

        except Exception as exc:
            logger.debug("HandsProvider.process error: %s", exc)
            return None

    # ── Finger counting ───────────────────────────────────────────────────────

    @staticmethod
    def _count_fingers(landmarks, handedness: str) -> int:
        """
        Count extended fingers using hand-orientation-aware projection.

        The wrist→middle-finger-MCP vector defines the hand's "up" axis.
        Each non-thumb finger is considered extended when its tip projects
        further along that axis than its PIP joint.  The thumb uses the
        perpendicular lateral axis since it extends sideways.

        Works correctly for hands tilted up to ~60° without angle math.
        """
        lm = landmarks

        # ── Hand "up" direction: wrist → middle-MCP ──────────────────────
        wrist   = np.array([lm[WRIST].x,      lm[WRIST].y])
        mid_mcp = np.array([lm[MIDDLE_MCP].x, lm[MIDDLE_MCP].y])
        up = mid_mcp - wrist
        up_norm = np.linalg.norm(up)
        if up_norm < 1e-6:
            return 0
        up = up / up_norm

        # Lateral axis: perpendicular to "up", pointing screen-right
        lateral = np.array([-up[1], up[0]])

        count = 0

        # ── Thumb (extends laterally, not upward) ─────────────────────────
        thumb_tip = np.array([lm[THUMB_TIP].x, lm[THUMB_TIP].y])
        thumb_ip  = np.array([lm[THUMB_IP].x,  lm[THUMB_IP].y])
        lateral_proj = float(np.dot(thumb_tip - thumb_ip, lateral))
        # Tasks API: "Right" = user's right hand → thumb points screen-left
        if handedness == "Right":
            if lateral_proj < -_EXTEND_THRESH:
                count += 1
        else:
            if lateral_proj > _EXTEND_THRESH:
                count += 1

        # ── Four fingers: tip vs PIP projected onto "up" ─────────────────
        finger_pairs = [
            (INDEX_TIP,  INDEX_PIP),
            (MIDDLE_TIP, MIDDLE_PIP),
            (RING_TIP,   RING_PIP),
            (PINKY_TIP,  PINKY_PIP),
        ]
        for tip_id, pip_id in finger_pairs:
            tip = np.array([lm[tip_id].x, lm[tip_id].y])
            pip = np.array([lm[pip_id].x, lm[pip_id].y])
            if float(np.dot(tip - pip, up)) > _EXTEND_THRESH:
                count += 1

        return count
