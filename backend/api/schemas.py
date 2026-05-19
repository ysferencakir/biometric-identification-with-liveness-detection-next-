"""
api/schemas.py
--------------
Pydantic request / response models.

All API contracts are defined here; routes.py never builds raw dicts.
"""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


# ── Recognition ───────────────────────────────────────────────────────────────

class RecognizeFrameRequest(BaseModel):
    """
    Send a single camera frame for recognition.
    image_b64: base64-encoded image (JPEG / PNG).
               Accepts both plain base64 and data-URI format.
    threshold: optional per-request override for cosine similarity threshold.
    """
    image_b64: str = Field(..., description="Base64-encoded image frame")
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold override (default from config)",
    )


class RecognitionResponse(BaseModel):
    face_detected: bool
    face_count: int
    recognized: bool
    user_id: Optional[str]
    name: Optional[str]
    recognition_score: float
    bbox: Optional[List[int]]    # [x, y, w, h]
    message: str


# ── Registration ──────────────────────────────────────────────────────────────

class RegisterFrameItem(BaseModel):
    """Single base64-encoded frame for registration."""
    image_b64: str


class RegisterRequest(BaseModel):
    """
    Register a new user with multiple camera frames.
    name   : display name stored in the database
    frames : list of base64-encoded frames (min 3, max 10)
    """
    name: str = Field(..., min_length=1, max_length=128, description="User display name")
    frames: List[str] = Field(
        ...,
        min_length=1,
        description="List of base64-encoded image frames",
    )


class RegisterResponse(BaseModel):
    success: bool
    user_id: Optional[str]
    name: Optional[str]
    frames_used: int           # how many frames successfully contributed embeddings
    message: str


# ── User management ───────────────────────────────────────────────────────────

class UserSummary(BaseModel):
    id: str
    name: str
    created_at: str


class UsersListResponse(BaseModel):
    users: List[UserSummary]
    count: int


class DeleteUserResponse(BaseModel):
    success: bool
    message: str


# ── Session ───────────────────────────────────────────────────────────────────

class SessionCreateResponse(BaseModel):
    session_id: str
    challenges: List[str]
    expires_at: str


class SessionStatusResponse(BaseModel):
    session_id: str
    status: str                    # active | completed | expired | denied
    challenges: List[str]
    completed_challenges: List[str]
    expires_at: str


# ── Liveness ──────────────────────────────────────────────────────────────────

class DetectorInfo(BaseModel):
    name: str
    instruction: str


class LivenessAvailableResponse(BaseModel):
    detectors: List[DetectorInfo]


class LivenessSubmitRequest(BaseModel):
    session_id: str
    challenge_name: str
    frame: str = Field(..., description="Base64-encoded image frame")


class LivenessSubmitResponse(BaseModel):
    challenge_name: str
    passed: bool
    confidence: float
    instruction: str
    all_challenges_passed: bool


# ── Verify ────────────────────────────────────────────────────────────────────

class VerifyRequest(BaseModel):
    session_id: str
    frame: str = Field(..., description="Base64-encoded image frame")


class LivenessResultSummary(BaseModel):
    challenge: str
    passed: bool
    confidence: float


class VerifyResponse(BaseModel):
    access_granted: bool
    matched_user: Optional[str]
    name: Optional[str]
    recognition_score: float
    liveness_results: List[LivenessResultSummary]
    decision_reason: str


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    model: str
