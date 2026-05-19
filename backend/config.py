"""
config.py
---------
Central application configuration.
All tuneable values live here; override via .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────
    APP_NAME: str = "Biometric ID – Face Recognition API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────
    DB_PATH: str = "data/biometric.db"

    # ── InsightFace ───────────────────────────────────────────────────────
    # Model name used by insightface model zoo (buffalo_l = best accuracy)
    INSIGHTFACE_MODEL: str = "buffalo_l"
    # 0 = GPU (CUDA), -1 = CPU
    INSIGHTFACE_CTX_ID: int = 0

    # ── Recognition ───────────────────────────────────────────────────────
    RECOGNITION_THRESHOLD: float = 0.45   # cosine similarity; defined in constants.py too
    # Minimum face size (pixels) to accept
    MIN_FACE_SIZE: int = 60

    # ── Embedding storage ─────────────────────────────────────────────────
    EMBEDDINGS_DIR: str = "data/embeddings"

    # ── Registration ─────────────────────────────────────────────────────
    # How many frames to collect during registration
    REGISTER_FRAMES_REQUIRED: int = 5

    # ── Session & Liveness ────────────────────────────────────────────────
    SESSION_TTL_SECONDS: int = 300
    LIVENESS_DETECTORS: list[str] = ["blink", "head_movement", "texture"]
    LIVENESS_CHALLENGES_COUNT: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()

# Ensure required directories exist at import time
Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
Path(settings.EMBEDDINGS_DIR).mkdir(parents=True, exist_ok=True)
