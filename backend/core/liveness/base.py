"""
core/liveness/base.py
---------------------
Abstract base class for all liveness detection implementations.

Implementing a new liveness method:
    1. Subclass LivenessDetectorBase
    2. Set the NAME class attribute (unique, snake_case)
    3. Implement check(), get_instruction(), reset()
    4. Register in core/liveness/__init__.py

This file keeps liveness completely decoupled from recognition.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class LivenessResult:
    is_live: bool
    score: float                  # model confidence 0.0 – 1.0
    method: str                   # detector NAME that produced the result
    challenge_completed: bool     # user completed the requested action
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class LivenessDetectorBase(ABC):
    """
    All liveness detectors must implement this interface.

    check()           – analyse one BGR frame, return LivenessResult
    get_instruction() – short user-facing text ("Please blink twice")
    reset()           – clear per-session state (call before each new challenge)
    """

    # Subclasses MUST override with a unique snake_case identifier.
    # manager.py uses NAME as the registry key.
    NAME: str = "base"

    @abstractmethod
    def check(
        self,
        bgr_frame: np.ndarray,
        bbox: tuple,              # (x1, y1, x2, y2) pixel coords
    ) -> LivenessResult:
        """
        Decide whether the face in bbox is live.

        Parameters
        ----------
        bgr_frame : full BGR frame from the camera
        bbox      : (x1, y1, x2, y2) pixel coordinates of the detected face

        Returns
        -------
        LivenessResult
        """
        ...

    @abstractmethod
    def get_instruction(self) -> str:
        """
        Return a short, human-readable instruction shown to the user.

        Examples
        --------
        "Lütfen iki kez göz kırpın."
        "Başınızı yavaşça sağa çevirin."
        "Kameraya düz bakın."
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """
        Clear any per-session / per-challenge internal state.
        Called by the session manager before each new challenge round.
        """
        ...
