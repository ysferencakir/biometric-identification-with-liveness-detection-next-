"""
db/store.py
-----------
SQLite persistence layer using the built-in sqlite3 module.
Stores user records and their mean face embeddings.

Schema
------
users
  id          TEXT  PRIMARY KEY   (UUID4)
  name        TEXT  NOT NULL
  embedding   BLOB  NOT NULL      (numpy float32 array serialised with numpy.save)
  created_at  TEXT  NOT NULL      (ISO-8601)
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import numpy as np

from config import settings

logger = logging.getLogger(__name__)

# ── Module-level connection (thread-local would be safer in prod; fine for grad project) ──
_DB_PATH = Path(settings.DB_PATH)


def _get_conn() -> sqlite3.Connection:
    """Return a connection with row_factory set."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Call once at startup."""
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                embedding   BLOB NOT NULL,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()
    logger.info("Database initialised at %s", _DB_PATH)


# ── Helpers for numpy ↔ BLOB ──────────────────────────────────────────────────

def _embedding_to_blob(embedding: np.ndarray) -> bytes:
    buf = embedding.astype(np.float32).tobytes()
    return buf


def _blob_to_embedding(blob: bytes, dim: int = 512) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def create_user(name: str, embedding: np.ndarray) -> str:
    """
    Persist a new user with their mean face embedding.
    Returns the generated user_id (UUID4 string).
    """
    user_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    blob = _embedding_to_blob(embedding)

    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, name, embedding, created_at) VALUES (?, ?, ?, ?)",
            (user_id, name, blob, created_at),
        )
        conn.commit()

    logger.info("User created: id=%s name=%s", user_id, name)
    return user_id


def get_all_users() -> List[dict]:
    """
    Return all users with their embeddings as numpy arrays.

    Each dict: {id, name, embedding (np.ndarray), created_at}
    """
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, embedding, created_at FROM users"
        ).fetchall()

    users = []
    for row in rows:
        users.append(
            {
                "id": row["id"],
                "name": row["name"],
                "embedding": _blob_to_embedding(row["embedding"]),
                "created_at": row["created_at"],
            }
        )
    return users


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Return a single user dict or None."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, name, embedding, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    if row is None:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "embedding": _blob_to_embedding(row["embedding"]),
        "created_at": row["created_at"],
    }


def delete_user(user_id: str) -> bool:
    """Delete a user by id. Returns True if a row was deleted."""
    with _get_conn() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    deleted = cursor.rowcount > 0
    if deleted:
        logger.info("User deleted: id=%s", user_id)
    return deleted


def list_users_summary() -> List[dict]:
    """
    Lightweight listing (no embedding blob) for admin/debug endpoints.
    Returns [{id, name, created_at}, ...]
    """
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]
