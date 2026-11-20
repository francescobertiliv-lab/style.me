"""Accesso a SQLite con sqlite3 puro."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from . import config

HERE = Path(__file__).parent


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(path: Path | str | None = None) -> None:
    """Crea le tabelle e carica i dati iniziali, solo se il database è nuovo."""
    conn = connect(path)
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='settings'"
        ).fetchone()
        if not exists:
            conn.executescript((HERE / "schema.sql").read_text())
            conn.executescript((HERE / "seed.sql").read_text())
            conn.commit()
    finally:
        conn.close()


@contextmanager
def session(path: Path | str | None = None):
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db():
    """Dipendenza FastAPI."""
    with session() as conn:
        yield conn


def rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def row(cur) -> dict | None:
    r = cur.fetchone()
    return dict(r) if r else None


def get_setting(conn, key: str, default=None):
    r = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return json.loads(r["value"]) if r else default


def set_setting(conn, key: str, value) -> None:
    conn.execute(
        "INSERT INTO settings(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, json.dumps(value)),
    )
