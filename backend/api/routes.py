"""
api/routes.py
-------------
All FastAPI route handlers.

Keeps business logic OUT of this file — routes only:
  1. Parse & validate the request (schemas.py)
  2. Call into core/ or db/
  3. Return a typed response (schemas.py)
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from api.schemas import (
    DeleteUserResponse,
    HealthResponse,
    RecognitionResponse,
    RecognizeFrameRequest,
    RegisterRequest,
    RegisterResponse,
    UserSummary,
    UsersListResponse,
)
from config import settings
from core.detection import FaceDetector
from core.embedding import compute_mean_embedding, extract_embedding
from core.preprocessing import prepare_for_insightface, validate_frame
from core.recognition import recognize_frame, RecognitionResult
from db import store as db
from utils.constants import (
    MSG_REGISTRATION_FAILED,
    MSG_REGISTERED,
    REGISTER_MIN_FRAMES,
)
from utils.image import decode_base64_image, decode_upload_image

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
def health_check() -> HealthResponse:
    """Quick liveness probe for load balancers / CI."""
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        model=settings.INSIGHTFACE_MODEL,
    )


# ── Recognition ───────────────────────────────────────────────────────────────

@router.post("/recognize", response_model=RecognitionResponse, tags=["Recognition"])
def recognize(body: RecognizeFrameRequest) -> RecognitionResponse:
    """
    Recognize a face from a base64-encoded image frame.

    Accepts both plain base64 and data-URI strings.
    """
    img = decode_base64_image(body.image_b64)
    if img is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot decode image. Ensure it is a valid JPEG/PNG in base64.",
        )

    threshold = body.threshold if body.threshold is not None else settings.RECOGNITION_THRESHOLD
    result: RecognitionResult = recognize_frame(img, threshold=threshold)

    return RecognitionResponse(
        face_detected=result.face_detected,
        face_count=result.face_count,
        recognized=result.recognized,
        user_id=result.user_id,
        name=result.name,
        recognition_score=result.recognition_score,
        bbox=list(result.bbox) if result.bbox else None,
        message=result.message,
    )


@router.post(
    "/recognize/upload",
    response_model=RecognitionResponse,
    tags=["Recognition"],
)
async def recognize_upload(
    file: UploadFile = File(..., description="Image file (JPEG/PNG)"),
    threshold: Optional[float] = Form(default=None),
) -> RecognitionResponse:
    """
    Recognize a face from a multipart file upload.
    Useful for direct curl / form-based clients.
    """
    img = await decode_upload_image(file)
    if img is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot decode uploaded image.",
        )

    th = threshold if threshold is not None else settings.RECOGNITION_THRESHOLD
    result: RecognitionResult = recognize_frame(img, threshold=th)

    return RecognitionResponse(
        face_detected=result.face_detected,
        face_count=result.face_count,
        recognized=result.recognized,
        user_id=result.user_id,
        name=result.name,
        recognition_score=result.recognition_score,
        bbox=list(result.bbox) if result.bbox else None,
        message=result.message,
    )


# ── Registration ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, tags=["Registration"])
def register_user(body: RegisterRequest) -> RegisterResponse:
    """
    Register a new user from multiple camera frames.

    Pipeline:
      1. Decode each base64 frame
      2. Detect faces (must be exactly 1 per frame)
      3. Extract embedding per frame
      4. Average all valid embeddings → mean embedding
      5. Store in SQLite

    Requires at least REGISTER_MIN_FRAMES valid frames.
    """
    detector = FaceDetector.get_instance()
    embeddings = []

    for i, b64 in enumerate(body.frames):
        img = decode_base64_image(b64)
        if img is None:
            logger.warning("Frame %d: could not decode, skipping", i)
            continue

        if not validate_frame(img):
            logger.warning("Frame %d: invalid frame, skipping", i)
            continue

        rgb = prepare_for_insightface(img)
        detection = detector.detect(rgb)

        if not detection.has_face:
            logger.info("Frame %d: no face detected, skipping", i)
            continue

        if detection.count > 1:
            logger.info("Frame %d: multiple faces, skipping for security", i)
            continue

        face = detection.single_face
        emb = extract_embedding(face)
        if emb is not None:
            embeddings.append(emb)
        else:
            logger.warning("Frame %d: embedding extraction failed", i)

    if len(embeddings) < REGISTER_MIN_FRAMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Only {len(embeddings)} valid face frames out of {len(body.frames)} provided. "
                f"Need at least {REGISTER_MIN_FRAMES}. "
                "Ensure good lighting, single face, and minimum face size."
            ),
        )

    mean_emb = compute_mean_embedding(embeddings)
    if mean_emb is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MSG_REGISTRATION_FAILED,
        )

    user_id = db.create_user(name=body.name, embedding=mean_emb)

    return RegisterResponse(
        success=True,
        user_id=user_id,
        name=body.name,
        frames_used=len(embeddings),
        message=MSG_REGISTERED,
    )


# ── User management ───────────────────────────────────────────────────────────

@router.get("/users", response_model=UsersListResponse, tags=["Users"])
def list_users() -> UsersListResponse:
    """Return a summary list of all registered users (no embeddings)."""
    users = db.list_users_summary()
    return UsersListResponse(
        users=[UserSummary(**u) for u in users],
        count=len(users),
    )


@router.delete("/users/{user_id}", response_model=DeleteUserResponse, tags=["Users"])
def delete_user(user_id: str) -> DeleteUserResponse:
    """Delete a registered user by ID."""
    deleted = db.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found",
        )
    return DeleteUserResponse(success=True, message=f"User '{user_id}' deleted")
