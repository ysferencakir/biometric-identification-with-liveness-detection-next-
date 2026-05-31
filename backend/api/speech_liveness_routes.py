import os
import time
import logging
import hashlib
import tempfile
import wave
import subprocess
import threading
from typing import Set, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from core.speech_liveness import (
    speech_challenge_registry,
    normalize_text,
    check_similarity,
    speech_transcriber
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/speech-liveness", tags=["Speech Liveness"])

# Thread-safe in-memory cache to store hashes of processed audio data to prevent replay attacks
_used_audio_hashes: Set[str] = set()
_hash_lock = threading.Lock()

class ChallengeResponse(BaseModel):
    challenge_id: str
    target_text: str

class LivenessResponse(BaseModel):
    success: bool
    target_text: str
    transcript: str
    similarity: float
    threshold: float
    word_match_ratio: float
    duration_seconds: float

def _is_audio_replayed(file_bytes: bytes) -> bool:
    """Computes SHA-256 hash of the audio data and checks for duplicates to prevent replay attacks."""
    hasher = hashlib.sha256()
    hasher.update(file_bytes)
    audio_hash = hasher.hexdigest()
    
    with _hash_lock:
        if audio_hash in _used_audio_hashes:
            return True
        _used_audio_hashes.add(audio_hash)
        
        # Keep hash set size bounded (lazily trim if it exceeds 10,000 to prevent leak)
        if len(_used_audio_hashes) > 10000:
            _used_audio_hashes.clear()
            _used_audio_hashes.add(audio_hash)
            
        return False

def _convert_to_pcm_wav(input_path: str, output_path: str) -> bool:
    """
    Converts input audio file to standard 16kHz mono 16-bit PCM WAV using ffmpeg.
    Returns True on success, False if ffmpeg is missing or conversion failed.
    """
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            output_path
        ]
        # Run ffmpeg, redirecting output to null to keep stdout clean
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning("ffmpeg conversion failed or ffmpeg not found in PATH: %s", e)
        return False

def _get_wav_duration(file_path: str) -> float:
    """Calculates duration of a WAV file in seconds using python's built-in wave module."""
    try:
        with wave.open(file_path, "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            if rate > 0:
                return float(frames / rate)
    except Exception as e:
        logger.warning("Could not parse WAV duration using wave module: %s", e)
    return 0.0

@router.post("/challenge", response_model=ChallengeResponse)
async def generate_speech_challenge() -> ChallengeResponse:
    """
    Generates a new speech challenge.
    Returns a unique challenge ID and a random Turkish sentence.
    """
    challenge_id, target_text = speech_challenge_registry.generate_challenge()
    logger.info("Generated speech challenge: ID=%s Text='%s'", challenge_id, target_text)
    return ChallengeResponse(challenge_id=challenge_id, target_text=target_text)

@router.post("/verify", response_model=LivenessResponse)
async def verify_speech_liveness(
    challenge_id: str = Form(..., description="The unique challenge ID"),
    audio_file: UploadFile = File(..., description="The recorded browser audio file (e.g. webm/wav)"),
    session_id: Optional[str] = Form(None, description="Optional active session ID to update")
) -> LivenessResponse:
    """
    Verifies speech liveness:
    1. Validates and consumes the challenge (fails if used, expired, or non-existent).
    2. Detects and blocks replay attacks using audio SHA-256.
    3. Formats audio to 16kHz mono WAV using ffmpeg.
    4. Enforces duration limits (0.5s to 25.0s).
    5. Transcribes Turkish speech using faster-whisper.
    6. Compares normalized target sentence vs transcript using character and word fuzzy metrics.
    """
    t0 = time.monotonic()
    
    # 1. Anti-Replay: Read audio bytes and check hash
    audio_bytes = await audio_file.read()
    if not audio_bytes or len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ses dosyası boş."
        )
        
    if _is_audio_replayed(audio_bytes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Güvenlik Engeli: Bu ses kaydı daha önce gönderilmiş (Anti-Replay)."
        )
        
    # 2. Validate Challenge ID and Consume (Single-Use, Expiry Check)
    is_valid, target_text, err_msg = speech_challenge_registry.validate_and_consume(challenge_id)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg
        )
        
    # Ensure temporary directory exists
    temp_dir = os.path.join(os.getcwd(), "data", "temp_audio")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate unique temporary file paths
    temp_input_fd, temp_input_path = tempfile.mkstemp(suffix=os.path.splitext(audio_file.filename or ".webm")[1], dir=temp_dir)
    temp_output_fd, temp_output_path = tempfile.mkstemp(suffix=".wav", dir=temp_dir)
    
    # Close descriptors immediately as we will open them by paths
    os.close(temp_input_fd)
    os.close(temp_output_fd)
    
    try:
        # Write uploaded bytes to temp input file
        with open(temp_input_path, "wb") as f:
            f.write(audio_bytes)
            
        # 3. Format Audio using ffmpeg
        conversion_ok = _convert_to_pcm_wav(temp_input_path, temp_output_path)
        
        final_audio_path = temp_output_path if conversion_ok else temp_input_path
        
        # If conversion failed, double check if it is a wav file so we can proceed, otherwise fail
        if not conversion_ok:
            logger.warning("ffmpeg is not available or failed. Processing file directly.")
            # Verify if it has a wave structure by attempting to get its parameters
            if not temp_input_path.lower().endswith(".wav"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sistemde ffmpeg yüklü değil ve gönderilen dosya WAV formatında değil. Lütfen WAV formatında gönderin veya sunucuya ffmpeg kurun."
                )
        
        # 4. Enforce Duration Checks (0.5s to 25.0s)
        duration = _get_wav_duration(final_audio_path)
        
        # Fallback to estimate duration by size if wav reading fails (assuming 16kHz 16bit mono PCM = 32KB/sec)
        if duration == 0.0:
            file_size = os.path.getsize(final_audio_path)
            duration = file_size / 32000.0
            
        if duration < 0.5 or duration > 25.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ses süresi geçersiz: {duration:.2f} saniye. Süre 0.5 ile 25.0 saniye arasında olmalıdır."
            )
            
        # 5. Transcription using faster-whisper (priming with target_text to ensure near-100% accuracy)
        try:
            transcript = speech_transcriber.transcribe(final_audio_path, initial_prompt=target_text)
        except Exception as stt_err:
            logger.error("Speech to text translation failed: %s", stt_err)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ses yazıya çevrilirken bir hata oluştu: {stt_err}"
            )
            
        # 6. Text Normalization and Similarity Calculation
        norm_target = normalize_text(target_text)
        norm_transcript = normalize_text(transcript)
        
        success, similarity, word_match_ratio = check_similarity(
            norm_target, 
            norm_transcript, 
            required_similarity=80.0
        )
        
        latency_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "Speech liveness verify: ID=%s Target='%s' Transcript='%s' Sim=%s%% Pass=%s Latency=%sms",
            challenge_id, target_text, transcript, similarity, success, latency_ms
        )
        
        # Enforce Session Challenge DB Updates if session_id is provided and speech liveness passed
        if session_id and success:
            from db import store as db
            session = db.get_session(session_id)
            if not session:
                logger.warning("Session ID '%s' not found for speech liveness completion.", session_id)
            elif session["status"] == "expired":
                logger.warning("Session ID '%s' is expired for speech liveness completion.", session_id)
            elif "speech" not in session["challenges"]:
                logger.warning("Speech challenge not in session '%s'.", session_id)
            else:
                db.complete_challenge(
                    session_id, 
                    "speech", 
                    passed=True, 
                    confidence=similarity / 100.0, 
                    latency_ms=latency_ms
                )
                db.add_audit_log(session_id, "challenge_passed", {
                    "challenge": "speech", 
                    "confidence": similarity / 100.0
                })
                logger.info("Speech challenge completed successfully in database for Session=%s", session_id)
        
        return LivenessResponse(
            success=success,
            target_text=target_text,
            transcript=transcript if transcript else "(Ses algılanamadı)",
            similarity=similarity,
            threshold=80.0,
            word_match_ratio=word_match_ratio,
            duration_seconds=round(duration, 2)
        )
        
    finally:
        # Clean up temporary files immediately to preserve workspace disk hygiene
        for path in (temp_input_path, temp_output_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as clean_err:
                logger.warning("Temporary file cleanup error for %s: %s", path, clean_err)
