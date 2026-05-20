"""
core/liveness/utils.py
----------------------
Liveness detection utilities — adaptive weighting, signal quality metrics.
"""

from collections import deque
from typing import Tuple

import numpy as np


class AdaptiveWeights:
    """
    Dynamic weight adjustment based on signal quality.

    Maintains confidence scores for primary and secondary signals,
    adjusts blending weights accordingly. Stabilizes after observing
    10+ frames.

    Example:
        aw = AdaptiveWeights(initial_weight_primary=0.4)
        # Each frame:
        aw.update(ear_confidence=0.9, mp_blink_confidence=0.7)
        w_primary, w_secondary = aw.get_weights()
        score = w_primary * ear_score + w_secondary * mp_score
    """

    def __init__(self, initial_weight_primary: float = 0.4):
        """
        Parameters
        ----------
        initial_weight_primary : float
            Initial weight for primary signal (0.0 - 1.0).
            Secondary weight = 1.0 - primary.
        """
        self.weight_primary = initial_weight_primary
        self.weight_secondary = 1.0 - initial_weight_primary

        # Buffer of (primary_confidence, secondary_confidence) tuples
        # maxlen=10 → sliding window of last 10 frames
        self.confidence_buffer: deque[Tuple[float, float]] = deque(maxlen=10)

    def update(self, primary_confidence: float, secondary_confidence: float) -> None:
        """
        Record signal quality for this frame.

        Parameters
        ----------
        primary_confidence : float
            Confidence of primary signal (0.0 - 1.0)
        secondary_confidence : float
            Confidence of secondary signal (0.0 - 1.0)
        """
        self.confidence_buffer.append((primary_confidence, secondary_confidence))

    def get_weights(self) -> Tuple[float, float]:
        """
        Compute weights based on signal quality history.

        Returns
        -------
        Tuple[float, float]
            (weight_primary, weight_secondary) summing to 1.0
        """
        # Need at least 3 observations before adaptive weighting
        if len(self.confidence_buffer) < 3:
            return self.weight_primary, self.weight_secondary

        # Average confidence of each signal
        confidences = np.array(list(self.confidence_buffer))
        avg_primary = float(np.mean(confidences[:, 0]))
        avg_secondary = float(np.mean(confidences[:, 1]))

        total = avg_primary + avg_secondary
        if total < 1e-6:
            # Both signals are near-zero; return initial weights
            return self.weight_primary, self.weight_secondary

        # Normalize confidence to weights
        w_primary = avg_primary / total
        w_secondary = avg_secondary / total

        return w_primary, w_secondary

    def reset(self) -> None:
        """Clear confidence history."""
        self.confidence_buffer.clear()


def estimate_signal_stability(scores: deque) -> float:
    """
    Estimate stability of a signal over recent frames.

    Stability = 1 - (std_dev / mean).
    Higher stability (closer to 1.0) means consistent signal.

    Parameters
    ----------
    scores : deque[float]
        Buffer of recent signal scores

    Returns
    -------
    float
        Stability metric in [0, 1], where 1.0 = very stable
    """
    if len(scores) < 2:
        return 0.0

    scores_arr = np.array(list(scores))
    mean = np.mean(scores_arr)

    if mean < 1e-6:
        return 0.0

    std = np.std(scores_arr)
    stability = max(0.0, 1.0 - (std / (mean + 1e-6)))

    return float(stability)
