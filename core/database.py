"""
ops_app/core/database.py
SQLite connection factory + schema initialisation.
All writes stay in ops_app/db/ops.sqlite — nothing touches /data/*.
"""
import sqlite3
from pathlib import Path

from .config import DB_PATH, UPLOADS_DIR


def get_conn() -> sqlite3.Connection:
    """Return a connection with FK enforcement and row_factory."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables from schema.sql if they don't exist yet."""
    schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    with get_conn() as conn:
        conn.executescript(sql)
    # Ensure uploads directory exists
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
