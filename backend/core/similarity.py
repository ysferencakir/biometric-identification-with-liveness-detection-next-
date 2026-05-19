"""
core/similarity.py
------------------
Cosine similarity computation between embeddings.

Because all embeddings are L2-normalised in embedding.py,
cosine_similarity(a, b) == np.dot(a, b).

Keeping this in its own module makes it trivial to swap to a different
distance metric (e.g. Euclidean, Mahalanobis) without touching recognition.py.
"""

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from utils.constants import RECOGNITION_THRESHOLD


@dataclass
class SimilarityMatch:
    user_id: str
    name: str
    score: float          # cosine similarity 0.0 – 1.0
    is_match: bool        # score >= RECOGNITION_THRESHOLD


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two L2-normalised embeddings.
    Result is in [-1, 1]; clipped to [0, 1] for cleaner output.
    """
    sim = float(np.dot(a, b))
    return float(np.clip(sim, 0.0, 1.0))


def find_best_match(
    query_embedding: np.ndarray,
    users: List[dict],
    threshold: float = RECOGNITION_THRESHOLD,
) -> Optional[SimilarityMatch]:
    """
    Compare query_embedding against all registered users.

    Parameters
    ----------
    query_embedding : L2-normalised (512,) float32 array
    users           : list of dicts with keys {id, name, embedding}
    threshold       : minimum cosine similarity to consider a match

    Returns the best SimilarityMatch if any score >= threshold, else None.
    The returned match contains the actual best score for logging even if
    it's below the threshold — callers should check .is_match.
    """
    if not users:
        return None

    best_score: float = -1.0
    best_user: Optional[dict] = None

    for user in users:
        stored: np.ndarray = user["embedding"]
        score = cosine_similarity(query_embedding, stored)
        if score > best_score:
            best_score = score
            best_user = user

    if best_user is None:
        return None

    return SimilarityMatch(
        user_id=best_user["id"],
        name=best_user["name"],
        score=best_score,
        is_match=best_score >= threshold,
    )
