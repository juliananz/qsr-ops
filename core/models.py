"""
ops_app/core/models.py
Thin data-access layer — all SQL in one place, no ORM needed at this scale.
"""
import csv
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .config import EXPORTS_DIR, UPLOADS_DIR
from .database import get_conn


# ============================================================
# Shifts
# ============================================================

def open_shift(
    shift_date: date,
    shift_name: str,
    cashier_name: str,
    delivery_controller: str,
    opening_cash: float = 2000.0,
) -> int:
    """Insert a new shift. Returns new shift id.
    Raises sqlite3.IntegrityError if (shift_date, shift_name) already exists.
    """
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO shifts
                (shift_date, shift_name, opening_cash, cashier_name, delivery_controller)
            VALUES (?, ?, ?, ?, ?)
            """,
            (shift_date.isoformat(), shift_name, opening_cash, cashier_name, delivery_controller),
        )
        return cur.lastrowid


def any_shift_open() -> bool:
    """True if any shift currently has status='open'."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM shifts WHERE status='open'"
        ).fetchone()
        return row[0] > 0


def get_shift(shift_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM shifts WHERE id = ?", (shift_id,)
        ).fetchone()


def get_open_shifts() -> list:
    """Return all shifts with status='open', newest first."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM shifts WHERE status='open' ORDER BY shift_date DESC, shift_name"
        ).fetchall()


def get_all_shifts(limit: int = 60) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM shifts ORDER BY shift_date DESC, shift_name LIMIT ?", (limit,)
        ).fetchall()


def get_shifts_pending_review() -> list:
    """Closed shifts that have no verifier_review yet."""
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT s.* FROM shifts s
            LEFT JOIN verifier_review vr ON vr.shift_id = s.id
            WHERE s.status = 'closed' AND vr.id IS NULL
            ORDER BY s.shift_date DESC, s.shift_name
            """
        ).fetchall()


# ============================================================
# Inventory counts
# ============================================================

def save_inventory_counts(shift_id: int, count_type: str, counts: list[dict]) -> None:
    """
    counts: [{"item_name": str, "quantity": float, "unit": str}, ...]
    For checklist items: quantity=1.0 means OK, 0.0 means Not OK.
    Replaces existing counts of the same type for this shift.
    """
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM inventory_counts WHERE shift_id=? AND count_type=?",
            (shift_id, count_type),
        )
        conn.executemany(
            """
            INSERT INTO inventory_counts (shift_id, count_type, item_name, quantity, unit)
            VALUES (:shift_id, :count_type, :item_name, :quantity, :unit)
            """,
            [{"shift_id": shift_id, "count_type": count_type, **c} for c in counts],
        )


def has_inventory_counts(shift_id: int, count_type: str) -> bool:
    """True if at least one inventory_counts row exists for this shift + count_type."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM inventory_counts WHERE shift_id=? AND count_type=?",
            (shift_id, count_type),
        ).fetchone()
        return row[0] > 0


def get_inventory_counts(shift_id: int, count_type: str) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM inventory_counts WHERE shift_id=? AND count_type=? ORDER BY id",
            (shift_id, count_type),
        ).fetchall()


# ============================================================
# Expenses
# ============================================================

def save_expense(
    shift_id: int,
    category: str,
    description: str,
    amount: float,
    photo_bytes: Optional[bytes],
    photo_filename: Optional[str],
) -> int:
    photo_path = None
    if photo_bytes and photo_filename:
        photo_path = _save_photo(shift_id, "gastos", photo_filename, photo_bytes)

    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO expenses (shift_id, category, description, amount, photo_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (shift_id, category, description, amount, photo_path),
        )
        return cur.lastrowid


def get_expenses(shift_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM expenses WHERE shift_id=? ORDER BY recorded_at",
            (shift_id,),
        ).fetchall()


def get_total_cash_expenses(shift_id: int) -> float:
    """Sum of expenses — used as default for cash_expenses in close shift."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE shift_id=?",
            (shift_id,),
        ).fetchone()
        return float(row[0])


# ============================================================
# Receiving
# ============================================================

def save_receiving(
    shift_id: int,
    supplier: str,
    item: str,
    quantity: float,
    unit: str,
    total_cost: float,
    photo_bytes: bytes,
    photo_filename: str,
) -> int:
    photo_path = _save_photo(shift_id, "recepciones", photo_filename, photo_bytes)
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO receiving (shift_id, supplier, item, quantity, unit, total_cost, photo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (shift_id, supplier, item, quantity, unit, total_cost, photo_path),
        )
        return cur.lastrowid


def get_receiving(shift_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM receiving WHERE shift_id=? ORDER BY recorded_at",
            (shift_id,),
        ).fetchall()


# ============================================================
# Close shift
# ============================================================

def close_shift(
    shift_id: int,
    total_sales: float,
    cash_sales: float,
    card_sales: float,
    cxc_sales: float,
    actual_cash_counted: float,
    cash_expenses: float,
    opening_cash: float,
) -> dict:
    expected_cash = opening_cash + cash_sales - cash_expenses
    discrepancy   = actual_cash_counted - expected_cash

    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO shift_close
                (shift_id, total_sales, cash_sales, card_sales, cxc_sales,
                 actual_cash_counted, cash_expenses, expected_cash, discrepancy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (shift_id, total_sales, cash_sales, card_sales, cxc_sales,
             actual_cash_counted, cash_expenses, expected_cash, discrepancy),
        )
        conn.execute(
            "UPDATE shifts SET status='closed' WHERE id=?", (shift_id,)
        )

    result = {
        "expected_cash": expected_cash,
        "discrepancy":   discrepancy,
    }

    # Auto-export CSV on every close
    shift = get_shift(shift_id)
    _export_shift_csv(shift, {
        "total_sales":         total_sales,
        "cash_sales":          cash_sales,
        "card_sales":          card_sales,
        "cxc_sales":           cxc_sales,
        "opening_cash":        opening_cash,
        "cash_expenses":       cash_expenses,
        "expected_cash":       expected_cash,
        "actual_cash_counted": actual_cash_counted,
        "discrepancy":         discrepancy,
    })

    return result


def get_shift_close(shift_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM shift_close WHERE shift_id=?", (shift_id,)
        ).fetchone()


# ============================================================
# Verifier review
# ============================================================

def save_verifier_review(
    shift_id: int,
    verifier_name: str,
    status: str,
    notes: Optional[str],
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO verifier_review (shift_id, verifier_name, status, notes)
            VALUES (?, ?, ?, ?)
            """,
            (shift_id, verifier_name, status, notes),
        )
        conn.execute(
            "UPDATE shifts SET status=? WHERE id=?", (status, shift_id)
        )


def get_verifier_review(shift_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM verifier_review WHERE shift_id=?", (shift_id,)
        ).fetchone()


# ============================================================
# Internal helpers
# ============================================================

def _save_photo(shift_id: int, category: str, filename: str, data: bytes) -> str:
    """
    Saves photo and returns the relative path string stored in DB.
    Structure: uploads/{shift_id}/{category}/{timestamp}_{filename}
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = Path(filename).name  # strip any directory traversal
    folder = UPLOADS_DIR / str(shift_id) / category
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{ts}_{safe_name}"
    dest.write_bytes(data)
    # Store relative path from ops_app root
    return str(dest.relative_to(UPLOADS_DIR.parent))


def _export_shift_csv(shift: sqlite3.Row, sc: dict) -> str:
    """
    Write a flat summary CSV to ops_app/exports/.
    Filename: YYYYMMDD_<AM|PM>_summary.csv
    Returns the full path of the written file.
    """
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = str(shift["shift_date"]).replace("-", "")
    filename = f"{date_str}_{shift['shift_name']}_summary.csv"
    filepath = EXPORTS_DIR / filename

    rows = [
        ["Campo", "Valor"],
        ["Fecha",                    shift["shift_date"]],
        ["Turno",                    shift["shift_name"]],
        ["Cajero",                   shift["cashier_name"]],
        ["Controlador de delivery",  shift["delivery_controller"]],
        ["Ventas totales",           sc["total_sales"]],
        ["Ventas efectivo",          sc["cash_sales"]],
        ["Ventas tarjeta",           sc["card_sales"]],
        ["Ventas CxC",               sc["cxc_sales"]],
        ["Fondo inicial",            sc["opening_cash"]],
        ["Gastos en efectivo",       sc["cash_expenses"]],
        ["Efectivo esperado",        sc["expected_cash"]],
        ["Efectivo contado",         sc["actual_cash_counted"]],
        ["Diferencia",               sc["discrepancy"]],
        ["Generado el",              datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return str(filepath)
