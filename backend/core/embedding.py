"""
core/embedding.py
-----------------
Extract and normalise 512-D ArcFace embeddings from DetectedFace objects.

The embedding is L2-normalised so that cosine similarity == dot product,
which makes the similarity module simpler and faster.
"""

import logging
from typing import List, Optional

import numpy as np

from core.detection import DetectedFace

logger = logging.getLogger(__name__)


def extract_embedding(face: DetectedFace) -> Optional[np.ndarray]:
    """
    Extract and L2-normalise the embedding from a DetectedFace.

    The raw InsightFace face object must have been produced by a FaceAnalysis
    pipeline that includes the recognition model (buffalo_l does).

    Returns a (512,) float32 ndarray or None if extraction fails.
    """
    raw = face._raw
    if raw is None:
        logger.warning("DetectedFace has no raw InsightFace object")
        return None

    embedding = getattr(raw, "embedding", None)
    if embedding is None:
        logger.warning("InsightFace face object has no 'embedding' attribute")
        return None

    emb = np.array(embedding, dtype=np.float32)

    # L2 normalise
    norm = np.linalg.norm(emb)
    if norm < 1e-6:
        logger.warning("Near-zero embedding norm; skipping")
        return None

    return emb / norm


def compute_mean_embedding(embeddings: List[np.ndarray]) -> Optional[np.ndarray]:
    """
    Compute the mean of a list of L2-normalised embeddings and re-normalise.

    This is the canonical way to create a robust registration embedding from
    multiple frames.

    Returns a (512,) float32 ndarray or None if the list is empty.
    """
    if not embeddings:
        return None

    stack = np.stack(embeddings, axis=0)       # (N, 512)
    mean = stack.mean(axis=0)                  # (512,)

    norm = np.linalg.norm(mean)
    if norm < 1e-6:
        logger.warning("Mean embedding norm is near-zero")
        return None

    return (mean / norm).astype(np.float32)
