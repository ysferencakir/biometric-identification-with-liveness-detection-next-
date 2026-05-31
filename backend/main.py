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
import traceback
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.routes import router
from api.speech_liveness_routes import router as speech_router
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

# Body size limiti — 10 MB (base64 frame ~200KB, kayıt ~500KB)
MAX_BODY = 10 * 1024 * 1024  # 10 MB

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY:
            return JSONResponse(status_code=413, content={"detail": "Request body too large (max 10MB)"})
        return await call_next(request)

app.add_middleware(BodySizeLimitMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler — stacktrace sadece loga yazılır, kullanıcıya ifşa edilmez
@app.exception_handler(Exception)
async def _global_exc(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s: %s\n%s",
                 request.url.path, exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},  # detay ifşa edilmiyor
    )

app.include_router(router, prefix="/api/v1")
app.include_router(speech_router, prefix="/api/v1")


# ── Direct run ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
