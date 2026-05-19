"""
core/liveness/manager.py
------------------------
Registry and dispatcher for liveness detection algorithms.

Usage (future)
--------------
    manager = LivenessManager()
    manager.register("passive_texture", PassiveTextureLiveness())
    result = manager.check("passive_texture", frame, bbox)

TODO: Implement at least one liveness algorithm:
    - Option A: MN3 / MiniFASNet (fast, works with a single RGB frame)
    - Option B: Blink detection using facial landmarks (active, no extra model)
    - Option C: Depth map / IR sensor input if hardware supports it
"""

import logging
from typing import Dict, Optional

import numpy as np

from core.liveness.base import LivenessDetectorBase, LivenessResult

logger = logging.getLogger(__name__)


class LivenessManager:
    """
    Maintains a registry of liveness detectors identified by name.
    The active algorithm can be switched at runtime without restarting.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, LivenessDetectorBase] = {}
        self._active: Optional[str] = None

    def register(self, name: str, detector: LivenessDetectorBase) -> None:
        """Register a liveness detector under a given name."""
        self._registry[name] = detector
        logger.info("Liveness detector registered: %s", name)
        if self._active is None:
            self._active = name

    def set_active(self, name: str) -> None:
        """Switch the active liveness algorithm."""
        if name not in self._registry:
            raise KeyError(f"No liveness detector registered under '{name}'")
        self._active = name
        logger.info("Active liveness detector set to: %s", name)

    def check(
        self,
        bgr_frame: np.ndarray,
        bbox: tuple,
        method: Optional[str] = None,
    ) -> Optional[LivenessResult]:
        """
        Run liveness check with the specified (or active) detector.

        Returns None if no detector is registered yet.
        """
        name = method or self._active
        if name is None or name not in self._registry:
            # TODO: raise an error here once a detector is registered
            logger.warning("No liveness detector available; skipping check")
            return None

        return self._registry[name].check(bgr_frame, bbox)

    @property
    def available_methods(self):
        return list(self._registry.keys())


# Singleton instance – import and use this in decision_engine.py
liveness_manager = LivenessManager()
