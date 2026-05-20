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
import random
import time
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from api.schemas import (
    DeleteUserResponse,
    DetectorInfo,
    HealthResponse,
    LivenessAvailableResponse,
    LivenessResultSummary,
    LivenessSubmitRequest,
    LivenessSubmitResponse,
    RecognitionResponse,
    RecognizeFrameRequest,
    RegisterRequest,
    RegisterResponse,
    SessionCreateResponse,
    SessionStatusResponse,
    UserSummary,
    UsersListResponse,
    VerifyRequest,
    VerifyResponse,
)
from config import settings
from core.decision_engine import decide
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

# Session başına detector instance'ları — {session_id: {challenge_name: detector}}
_session_detectors: dict[str, dict] = {}
_session_locks: dict[str, "threading.Lock"] = {}
import threading


def _get_session_lock(session_id: str) -> "threading.Lock":
    if session_id not in _session_locks:
        _session_locks[session_id] = threading.Lock()
    return _session_locks[session_id]


def _get_detector(session_id: str, challenge_name: str):
    """Session'a ait detector instance'ını döner, yoksa oluşturur."""
    from core.liveness import liveness_manager
    if session_id not in _session_detectors:
        _session_detectors[session_id] = {}
    if challenge_name not in _session_detectors[session_id]:
        # Manager'dan yeni bir instance al (her session için ayrı state)
        available = liveness_manager._registry
        if challenge_name in available:
            import copy
            det = copy.deepcopy(available[challenge_name])
            det.reset()
            _session_detectors[session_id][challenge_name] = det
        else:
            _session_detectors[session_id][challenge_name] = None
    return _session_detectors[session_id].get(challenge_name)


def _cleanup_session_detectors(session_id: str) -> None:
    _session_detectors.pop(session_id, None)
    _session_locks.pop(session_id, None)

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


# ── Liveness ──────────────────────────────────────────────────────────────────

@router.get("/liveness/available", response_model=LivenessAvailableResponse, tags=["Liveness"])
def get_available_detectors() -> LivenessAvailableResponse:
    """List all registered liveness detector modules."""
    from core.liveness import liveness_manager

    detectors = []
    for name in liveness_manager.available_methods:
        detector = liveness_manager._registry.get(name)
        if detector:
            instruction = detector.get_instruction()
            detectors.append(DetectorInfo(name=name, instruction=instruction))
    return LivenessAvailableResponse(detectors=detectors)


@router.post("/session/create", response_model=SessionCreateResponse, tags=["Session"])
def create_session() -> SessionCreateResponse:
    """
    Start a new verification session.
    Randomly picks LIVENESS_CHALLENGES_COUNT detectors from the available pool.
    """
    available = settings.LIVENESS_DETECTORS
    count = min(settings.LIVENESS_CHALLENGES_COUNT, len(available))
    challenges = random.sample(available, k=count)

    session = db.create_session(challenges, ttl_seconds=settings.SESSION_TTL_SECONDS)
    db.add_audit_log(session["session_id"], "session_created", {"challenges": challenges})

    return SessionCreateResponse(
        session_id=session["session_id"],
        challenges=session["challenges"],
        expires_at=session["expires_at"],
    )


@router.get("/session/{session_id}", response_model=SessionStatusResponse, tags=["Session"])
def get_session(session_id: str) -> SessionStatusResponse:
    """Get the current status of a verification session."""
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionStatusResponse(
        session_id=session["id"],
        status=session["status"],
        challenges=session["challenges"],
        completed_challenges=session["completed_challenges"],
        expires_at=session["expires_at"],
    )


@router.post("/liveness/submit", response_model=LivenessSubmitResponse, tags=["Liveness"])
def submit_liveness(body: LivenessSubmitRequest) -> LivenessSubmitResponse:
    import traceback as _tb
    try:
        return _submit_liveness_inner(body)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("UNHANDLED in submit_liveness:\n%s", _tb.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{type(exc).__name__}: {exc}",
        )


def _submit_liveness_inner(body: LivenessSubmitRequest) -> LivenessSubmitResponse:
    t0 = time.monotonic()

    session = db.get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session["status"] == "expired":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session expired")

    # Challenge veya session zaten tamamlandıysa — sessizce 200 dön
    if body.challenge_name not in session["challenges"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Challenge '{body.challenge_name}' not in this session")

    all_done = session["status"] in ("completed", "denied")
    if body.challenge_name in session["completed_challenges"] or all_done:
        return LivenessSubmitResponse(
            challenge_name=body.challenge_name,
            passed=True,
            confidence=1.0,
            instruction="Tamamlandi!",
            all_challenges_passed=session["status"] == "completed",
        )

    img = decode_base64_image(body.frame)
    if img is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot decode frame")

    # Gerçek liveness detector'ı çalıştır (thread-safe)
    det            = _get_detector(body.session_id, body.challenge_name)
    liveness_msg   = ""

    if det is not None:
        with _get_session_lock(body.session_id):
            liveness_result = det.check(img, (0, 0, 0, 0))
        passed          = liveness_result.challenge_completed
        confidence      = liveness_result.score
        liveness_msg    = liveness_result.message   # "Göz kırpma: 1/2"
    else:
        from core.preprocessing import prepare_for_insightface
        face_det = FaceDetector.get_instance()
        rgb      = prepare_for_insightface(img)
        detected = face_det.detect(rgb)
        passed     = detected.has_face and detected.count == 1
        confidence = float(detected.single_face.score) if passed else 0.0

    # Sadece passed=True olduğunda DB'ye yaz (her frame'i kaydetme)
    latency_ms = int((time.monotonic() - t0) * 1000)
    if passed:
        updated = db.complete_challenge(
            body.session_id, body.challenge_name, passed, confidence, latency_ms
        )
        db.add_audit_log(body.session_id, "challenge_passed", {
            "challenge": body.challenge_name, "confidence": confidence,
        })
        all_passed = updated["status"] == "completed"
        if all_passed:
            _cleanup_session_detectors(body.session_id)
    else:
        updated    = db.get_session(body.session_id) or {}
        all_passed = False

    return LivenessSubmitResponse(
        challenge_name=body.challenge_name,
        passed=passed,
        confidence=round(confidence, 4),
        instruction=liveness_msg or (det.get_instruction() if det else ""),
        all_challenges_passed=all_passed,
    )


# ── Verify ────────────────────────────────────────────────────────────────────

@router.post("/verify", response_model=VerifyResponse, tags=["Verify"])
def verify(body: VerifyRequest) -> VerifyResponse:
    """
    Run biometric recognition after all liveness challenges are passed.
    Returns access decision with matched user and liveness summary.
    """
    session = db.get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session["status"] == "expired":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session expired")
    if session["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Liveness challenges not completed (status: {session['status']})",
        )

    img = decode_base64_image(body.frame)
    if img is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot decode frame")

    # Her challenge için sadece en iyi (passed=1 olan) sonucu al
    from db.store import _get_conn
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT challenge_name,
                   MAX(passed)                                          AS passed,
                   MAX(CASE WHEN passed=1 THEN confidence ELSE 0 END)  AS confidence
            FROM liveness_challenges
            WHERE session_id = ?
            GROUP BY challenge_name
            """,
            (body.session_id,),
        ).fetchall()
    liveness_rows = [dict(r) for r in rows]

    # Recognition + liveness → karar
    recognition = recognize_frame(img, threshold=settings.RECOGNITION_THRESHOLD)
    decision    = decide(recognition, liveness_results=liveness_rows)

    db.update_session_status(body.session_id, "denied" if not decision.access_granted else "completed")
    db.add_audit_log(body.session_id,
        "access_granted" if decision.access_granted else "access_denied",
        {
            "user_id": recognition.user_id,
            "score":   recognition.recognition_score,
            "reason":  decision.reason,
            "liveness_avg_conf": decision.liveness.avg_confidence if decision.liveness else None,
        },
    )

    liveness_results = [
        LivenessResultSummary(
            challenge=r["challenge_name"],
            passed=bool(r["passed"]),
            confidence=r["confidence"],
        )
        for r in liveness_rows
    ]

    return VerifyResponse(
        access_granted=decision.access_granted,
        matched_user=decision.user_id,
        name=decision.name,
        recognition_score=round(decision.recognition_score, 4),
        liveness_results=liveness_results,
        decision_reason=decision.reason,
    )
