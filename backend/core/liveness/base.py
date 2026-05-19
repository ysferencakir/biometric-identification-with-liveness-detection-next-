"""
core/liveness/base.py
---------------------
Abstract base class for all liveness detection implementations.

Implementing a new liveness method:
    1. Subclass LivenessDetectorBase
    2. Implement the `check` method
    3. Register it in manager.py

This file keeps liveness completely decoupled from recognition.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class LivenessResult:
    is_live: bool
    score: float          # model confidence 0.0 – 1.0
    method: str           # name of the algorithm that produced the result
    message: str = ""


class LivenessDetectorBase(ABC):
    """
    All liveness detectors must implement this interface.

    Parameters accepted by `check` are intentionally broad (raw BGR frame +
    face bbox) so that both passive (texture/depth) and active (challenge-
    response) methods can conform to the same interface.
    """

    @abstractmethod
    def check(
        self,
        bgr_frame: np.ndarray,
        bbox: tuple,          # (x1, y1, x2, y2)
    ) -> LivenessResult:
        """
        Decide whether the face in the given bbox is live.

        Parameters
        ----------
        bgr_frame : full BGR frame from the camera
        bbox      : (x1, y1, x2, y2) pixel coordinates of the detected face

        Returns
        -------
        LivenessResult
        """
        ...
