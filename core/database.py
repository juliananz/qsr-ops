"""
ops_app/core/database.py
SQLite connection factory + schema initialisation + migrations.
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
    """Create tables from schema.sql and apply any pending migrations."""
    schema_path = Path(__file__).parent.parent / "db" / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")

    conn = get_conn()
    try:
        conn.executescript(sql)
        _migrate(conn)
    finally:
        conn.close()

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _migrate(conn: sqlite3.Connection) -> None:
    """One-time schema migrations for breaking changes between versions."""

    # ── Migration 1: rebuild inventory_counts if it has the old schema ────────
    # Old schema used (count_type, item_name); new schema uses (mode, product, category, checked).
    old_cols = {row[1] for row in conn.execute("PRAGMA table_info(inventory_counts)")}
    if old_cols and "count_type" in old_cols:
        conn.executescript("""
            DROP TABLE IF EXISTS inventory_counts;
            CREATE TABLE inventory_counts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id    INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
                user        TEXT    NOT NULL,
                mode        TEXT    NOT NULL CHECK (mode IN ('apertura','cierre')),
                product     TEXT    NOT NULL,
                category    TEXT    NOT NULL,
                quantity    REAL,
                unit        TEXT,
                checked     INTEGER,
                recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS ix_inventory_shift ON inventory_counts (shift_id, mode);
        """)

    # ── Migration 2: drop old receiving table (replaced by receiving_log) ─────
    tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='receiving'"
        )
    }
    if tables:
        conn.execute("DROP TABLE IF EXISTS receiving")
        conn.commit()

    # ── Migration 3: rebuild shift_close if it has the old cash-reconciliation schema ──
    sc_cols = {row[1] for row in conn.execute("PRAGMA table_info(shift_close)")}
    if sc_cols and "total_sales" in sc_cols:
        conn.executescript("""
            DROP TABLE IF EXISTS shift_close;
            CREATE TABLE shift_close (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                shift_id          INTEGER NOT NULL UNIQUE REFERENCES shifts(id) ON DELETE CASCADE,
                ventas_pos        REAL    NOT NULL DEFAULT 0,
                ventas_app        REAL    NOT NULL DEFAULT 0,
                gastos_efectivo   REAL    NOT NULL DEFAULT 0,
                ventas_totales    REAL    NOT NULL DEFAULT 0,
                efectivo_contado  REAL    NOT NULL DEFAULT 0,
                ventas_tarjeta    REAL    NOT NULL DEFAULT 0,
                fondo_inicial     REAL    NOT NULL DEFAULT 2000,
                efectivo_neto     REAL    NOT NULL DEFAULT 0,
                comprobacion      REAL    NOT NULL DEFAULT 0,
                diferencia        REAL    NOT NULL DEFAULT 0,
                notas             TEXT,
                closed_at         DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
