"""
main.py
-------
FastAPI application entry point.

Startup sequence:
  1. Initialise SQLite schema
  2. Warm up InsightFace model (so first request isn't slow)
  3. Mount API router
"""

import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from config import settings
from db.store import init_db

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks, then yield, then run shutdown tasks."""
    logger.info("=== Biometric ID API starting up ===")

    # 1. Initialise DB
    init_db()

    # 2. Warm up InsightFace (loads model weights into VRAM/RAM)
    logger.info("Loading InsightFace model – please wait…")
    from core.detection import FaceDetector
    try:
        FaceDetector.get_instance()
        logger.info("InsightFace model ready OK")
    except Exception as exc:
        logger.error("Failed to load InsightFace: %s", exc)
        # Don't crash – let the health endpoint report the error gracefully
        # TODO: surface this in /health response

    logger.info("=== API ready at http://0.0.0.0:8000 ===")
    yield

    logger.info("=== Biometric ID API shutting down ===")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Face Detection & Recognition backend for the Biometric Identification "
        "with Liveness Detection graduation project."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS – allow all origins in development; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


# ── Direct run ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
