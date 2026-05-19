"""
utils/constants.py
------------------
Single source of truth for all numeric / string constants.
Change these values to tune behaviour without touching business logic.
"""

# ── Recognition thresholds ────────────────────────────────────────────────────
# Cosine similarity range: 0.0 (completely different) → 1.0 (identical)
# ArcFace / buffalo_l recommended range: 0.40 – 0.55
RECOGNITION_THRESHOLD: float = 0.45   # above → recognized

# ── Face detection ────────────────────────────────────────────────────────────
MIN_FACE_SIZE_PX: int = 60            # faces smaller than this are ignored

# ── Registration ──────────────────────────────────────────────────────────────
REGISTER_MIN_FRAMES: int = 3          # at least N good frames required
REGISTER_MAX_FRAMES: int = 10         # capture at most N frames

# ── Embedding ─────────────────────────────────────────────────────────────────
EMBEDDING_DIM: int = 512              # InsightFace ArcFace embedding size

# ── Response messages ─────────────────────────────────────────────────────────
MSG_RECOGNIZED = "User recognized"
MSG_UNKNOWN = "Unknown face"
MSG_NO_FACE = "No face detected"
MSG_MULTIPLE_FACES = "Multiple faces detected"
MSG_REGISTERED = "User registered successfully"
MSG_SMALL_FACE = "Detected face is too small"
MSG_REGISTRATION_FAILED = "Registration failed: could not extract embeddings"

# ── BBox color codes (for client-side reference, not used by backend) ─────────
BBOX_COLOR_RECOGNIZED = (0, 255, 0)    # green  – BGR
BBOX_COLOR_UNKNOWN = (0, 0, 255)       # red    – BGR
