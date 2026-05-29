"""
ops_app/core/models.py
Thin data-access layer — all SQL in one place.
"""
import csv
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List

from .config import EXPORTS_DIR, UPLOADS_DIR
from .database import get_conn

# ============================================================
# Product catalog (JSON file — fixed costs, updatable)
# ============================================================

CATALOG_PATH = Path(__file__).parent.parent / "data" / "catalog_productos.json"


def load_catalog() -> list[dict]:
    if not CATALOG_PATH.exists():
        return []
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_catalog_cost(producto: str) -> Optional[float]:
    for item in load_catalog():
        if item["nombre"] == producto:
            return float(item["costo_unitario"])
    return None


def get_catalog_unit(producto: str) -> Optional[str]:
    for item in load_catalog():
        if item["nombre"] == producto:
            return item["unidad_compra"]
    return None


def update_catalog_cost(producto: str, nuevo_costo: float) -> None:
    cat = load_catalog()
    for item in cat:
        if item["nombre"] == producto:
            item["costo_unitario"] = round(nuevo_costo, 2)
            break
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)


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


def get_open_shift_today() -> Optional[sqlite3.Row]:
    """Return the open shift for today, or None."""
    today = date.today().isoformat()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM shifts WHERE shift_date=? AND status='open' LIMIT 1",
            (today,),
        ).fetchone()


def get_available_shift_name(shift_date: date) -> Optional[str]:
    """Return first available slot ('AM' or 'PM') for the date, or None if both taken."""
    with get_conn() as conn:
        taken = {
            row[0] for row in conn.execute(
                "SELECT shift_name FROM shifts WHERE shift_date=?",
                (shift_date.isoformat(),),
            )
        }
    for name in ("AM", "PM"):
        if name not in taken:
            return name
    return None


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


def get_shift_by_date_name(shift_date: str, shift_name: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM shifts WHERE shift_date=? AND shift_name=?",
            (shift_date, shift_name),
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

def save_inventory_counts(
    shift_id: int,
    user: str,
    mode: str,
    counts: list[dict],
) -> None:
    """
    counts: [{"product": str, "category": str,
              "quantity": float|None, "unit": str|None, "checked": int|None}]
    Records are immutable once saved — do not call if counts already exist.
    """
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO inventory_counts
                (shift_id, user, mode, product, category, quantity, unit, checked)
            VALUES (:shift_id, :user, :mode, :product, :category, :quantity, :unit, :checked)
            """,
            [{"shift_id": shift_id, "user": user, "mode": mode, **c} for c in counts],
        )


def has_inventory_counts(shift_id: int, mode: str) -> bool:
    """True if at least one inventory_counts row exists for this shift + mode."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM inventory_counts WHERE shift_id=? AND mode=?",
            (shift_id, mode),
        ).fetchone()
        return row[0] > 0


def has_inventory_today_any_shift(shift_date: str, mode: str) -> bool:
    """True if ANY shift on this date already has an inventory count for mode."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM inventory_counts ic
            JOIN shifts s ON ic.shift_id = s.id
            WHERE s.shift_date = ? AND ic.mode = ?
            """,
            (shift_date, mode),
        ).fetchone()
        return row[0] > 0


def get_inventory_counts(shift_id: int, mode: str) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM inventory_counts WHERE shift_id=? AND mode=? ORDER BY id",
            (shift_id, mode),
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
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE shift_id=?",
            (shift_id,),
        ).fetchone()
        return float(row[0])


def get_pos_sales_total(shift_id: int) -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(importe),0) FROM pos_sales WHERE shift_id=?",
            (shift_id,),
        ).fetchone()
        return float(row[0])


def get_app_sales_total(shift_id: int) -> float:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(business_amount),0) FROM app_sales_log WHERE shift_id=?",
            (shift_id,),
        ).fetchone()
        return float(row[0])


# ============================================================
# Receiving log
# ============================================================

def save_receiving_log(
    shift_id: int,
    user: str,
    proveedor: str,
    producto: str,
    unidad: str,
    cantidad: float,
    costo_unitario: float = 0.0,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO receiving_log
                (shift_id, user, proveedor, producto, unidad, cantidad, costo_unitario)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (shift_id, user, proveedor, producto, unidad, cantidad, costo_unitario),
        )
        return cur.lastrowid


def get_receiving_log(shift_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM receiving_log WHERE shift_id=? ORDER BY recorded_at",
            (shift_id,),
        ).fetchall()


def get_receiving_log_today() -> list:
    today = date.today().isoformat()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM receiving_log WHERE DATE(recorded_at)=? ORDER BY recorded_at",
            (today,),
        ).fetchall()


# ============================================================
# Close shift
# ============================================================

def close_shift(
    shift_id: int,
    ventas_pos: float,
    ventas_app: float,
    gastos_efectivo: float,
    efectivo_contado: float,
    ventas_tarjeta: float,
    fondo_inicial: float,
    notas: Optional[str],
) -> dict:
    ventas_totales = ventas_pos + ventas_app
    efectivo_neto  = efectivo_contado - fondo_inicial
    comprobacion   = efectivo_neto + ventas_tarjeta + ventas_app + gastos_efectivo
    diferencia     = ventas_totales - comprobacion

    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO shift_close
                (shift_id, ventas_pos, ventas_app, gastos_efectivo, ventas_totales,
                 efectivo_contado, ventas_tarjeta, fondo_inicial,
                 efectivo_neto, comprobacion, diferencia, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (shift_id, ventas_pos, ventas_app, gastos_efectivo, ventas_totales,
             efectivo_contado, ventas_tarjeta, fondo_inicial,
             efectivo_neto, comprobacion, diferencia, notas),
        )
        conn.execute(
            "UPDATE shifts SET status='closed' WHERE id=?", (shift_id,)
        )

    shift = get_shift(shift_id)
    _export_shift_csv(shift, {
        "ventas_pos":       ventas_pos,
        "ventas_app":       ventas_app,
        "gastos_efectivo":  gastos_efectivo,
        "ventas_totales":   ventas_totales,
        "efectivo_contado": efectivo_contado,
        "ventas_tarjeta":   ventas_tarjeta,
        "fondo_inicial":    fondo_inicial,
        "efectivo_neto":    efectivo_neto,
        "comprobacion":     comprobacion,
        "diferencia":       diferencia,
    })
    return {
        "ventas_totales": ventas_totales,
        "efectivo_neto":  efectivo_neto,
        "comprobacion":   comprobacion,
        "diferencia":     diferencia,
    }


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
        # Fix A: map Spanish status values to DB-level shift statuses
        shift_status = "approved" if status == "aprobado" else "flagged"
        conn.execute(
            "UPDATE shifts SET status=? WHERE id=?", (shift_status, shift_id)
        )


def get_verifier_review(shift_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM verifier_review WHERE shift_id=?", (shift_id,)
        ).fetchone()


# ============================================================
# App sales
# ============================================================

def save_app_sale(
    shift_id: int,
    user: str,
    app: str,
    payment_type: str,
    app_amount: float,
    business_amount: float,
    notes: Optional[str],
    items: list[dict],
) -> int:
    """items: [{"product": str, "quantity": float}, ...]"""
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO app_sales_log
                (shift_id, user, app, payment_type, app_amount, business_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (shift_id, user, app, payment_type, app_amount, business_amount, notes),
        )
        sale_id = cur.lastrowid
        for item in items:
            conn.execute(
                "INSERT INTO app_sales_items (sale_id, product, quantity) VALUES (?, ?, ?)",
                (sale_id, item["product"], item["quantity"]),
            )
        return sale_id


def get_app_sales_today() -> list:
    today = date.today().isoformat()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM app_sales_log WHERE DATE(recorded_at)=? ORDER BY recorded_at",
            (today,),
        ).fetchall()


def get_app_sale_items(sale_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM app_sales_items WHERE sale_id=?", (sale_id,)
        ).fetchall()


# ============================================================
# Consumption log
# ============================================================

def save_consumption(
    shift_id: int,
    user: str,
    tipo: str,
    product: str,
    cantidad: float,
    unidad: str,
    notas: Optional[str],
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO consumption_log
                (shift_id, user, tipo, product, cantidad, unidad, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (shift_id, user, tipo, product, cantidad, unidad, notas),
        )
        return cur.lastrowid


def get_consumption_today() -> list:
    today = date.today().isoformat()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM consumption_log WHERE DATE(recorded_at)=? ORDER BY recorded_at",
            (today,),
        ).fetchall()


def get_consumption_log(shift_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM consumption_log WHERE shift_id=? ORDER BY recorded_at",
            (shift_id,),
        ).fetchall()


# ============================================================
# POS sales
# ============================================================

def save_pos_sales(shift_id: int, records: list[dict]) -> None:
    """Bulk-insert POS rows.  Each dict must have the pos_sales columns."""
    from datetime import datetime as _dt
    uploaded_at = _dt.now().isoformat()
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO pos_sales
                (shift_id, foliocomanda, foliocuenta, orden,
                 fechaapertura, fechacierre, mesero, claveproducto,
                 descripcion, cantidad, descuento, importe, uploaded_at)
            VALUES
                (:shift_id, :foliocomanda, :foliocuenta, :orden,
                 :fechaapertura, :fechacierre, :mesero, :claveproducto,
                 :descripcion, :cantidad, :descuento, :importe, :uploaded_at)
            """,
            [{"shift_id": shift_id, "uploaded_at": uploaded_at, **r} for r in records],
        )


def has_pos_sales(shift_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM pos_sales WHERE shift_id=?", (shift_id,)
        ).fetchone()
        return row[0] > 0


def get_pos_sales(shift_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM pos_sales WHERE shift_id=? ORDER BY id",
            (shift_id,),
        ).fetchall()


# ============================================================
# Internal helpers
# ============================================================

def _save_photo(shift_id: int, category: str, filename: str, data: bytes) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = Path(filename).name
    folder = UPLOADS_DIR / str(shift_id) / category
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{ts}_{safe_name}"
    dest.write_bytes(data)
    return str(dest.relative_to(UPLOADS_DIR.parent))


def _export_shift_csv(shift: sqlite3.Row, sc: dict) -> str:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = str(shift["shift_date"]).replace("-", "")
    filename = f"{date_str}_{shift['shift_name']}_summary.csv"
    filepath = EXPORTS_DIR / filename

    rows = [
        ["Campo", "Valor"],
        ["Fecha",             shift["shift_date"]],
        ["Turno",             shift["shift_name"]],
        ["Abrió",             shift["cashier_name"]],
        ["Ventas POS",        sc["ventas_pos"]],
        ["Ventas App",        sc["ventas_app"]],
        ["Ventas totales",    sc["ventas_totales"]],
        ["Gastos efectivo",   sc["gastos_efectivo"]],
        ["Fondo inicial",     sc["fondo_inicial"]],
        ["Efectivo contado",  sc["efectivo_contado"]],
        ["Efectivo neto",     sc["efectivo_neto"]],
        ["Ventas tarjeta",    sc["ventas_tarjeta"]],
        ["Comprobación",      sc["comprobacion"]],
        ["Diferencia",        sc["diferencia"]],
        ["Generado el",       datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)

    return str(filepath)
