"""
feedback.py
===========
PHASE 2 — Feedback capture: clicks, ratings, thumbs up/down -> storage for
retraining. Writes to Postgres (POSTGRES_URL) when reachable, matching the
docker-compose stack; falls back to a local SQLite file (backend/feedback.db)
otherwise so the API still works without Docker running, the same
graceful-degradation pattern used for Qdrant in notebooks 05/06.
"""

import os
import sqlite3
import time

_SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback.db")

_backend = None   # "postgres" | "sqlite"
_pg_conn = None

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY {autoincrement},
    user_id INTEGER NOT NULL,
    movie_id INTEGER NOT NULL,
    rating REAL,
    clicked INTEGER,
    created_at {timestamp_type} NOT NULL
)
"""


def _init():
    global _backend, _pg_conn

    postgres_url = os.environ.get("POSTGRES_URL")
    if postgres_url:
        try:
            import psycopg2
            _pg_conn = psycopg2.connect(postgres_url, connect_timeout=3)
            with _pg_conn.cursor() as cur:
                cur.execute(_CREATE_TABLE_SQL.format(
                    autoincrement="GENERATED ALWAYS AS IDENTITY", timestamp_type="TIMESTAMPTZ"
                ))
            _pg_conn.commit()
            _backend = "postgres"
            return
        except Exception:
            _pg_conn = None

    conn = sqlite3.connect(_SQLITE_PATH)
    conn.execute(_CREATE_TABLE_SQL.format(autoincrement="AUTOINCREMENT", timestamp_type="REAL"))
    conn.commit()
    conn.close()
    _backend = "sqlite"


def log_feedback(user_id: int, movie_id: int, rating: float = None, clicked: bool = None):
    """Record one feedback event. Either `rating` or `clicked` (or both) may
    be given -- both are optional so a single click can be logged without a
    rating, and vice versa."""
    if _backend is None:
        _init()

    if _backend == "postgres":
        with _pg_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (user_id, movie_id, rating, clicked, created_at) "
                "VALUES (%s, %s, %s, %s, NOW())",
                (user_id, movie_id, rating, clicked),
            )
        _pg_conn.commit()
    else:
        conn = sqlite3.connect(_SQLITE_PATH)
        conn.execute(
            "INSERT INTO feedback (user_id, movie_id, rating, clicked, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, movie_id, rating, int(clicked) if clicked is not None else None, time.time()),
        )
        conn.commit()
        conn.close()

    return {"status": "ok", "backend": _backend}


def backend_in_use() -> str:
    if _backend is None:
        _init()
    return _backend
