-- =============================================================
-- ops_app database schema  –  Astro Burger control operacional
-- =============================================================
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------
-- shifts  (one row per AM/PM shift)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS shifts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_date          DATE    NOT NULL,
    shift_name          TEXT    NOT NULL CHECK (shift_name IN ('AM','PM')),
    opening_cash        REAL    NOT NULL DEFAULT 2000,
    cashier_name        TEXT    NOT NULL,
    delivery_controller TEXT    NOT NULL,
    status              TEXT    NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','closed','approved','flagged')),
    opened_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_shifts_date_name
    ON shifts (shift_date, shift_name);

-- ----------------------------------------------------------
-- inventory_counts  (new schema: user, mode, product, category)
-- NOTE: if upgrading from a pre-redesign DB, database.py
-- migration will drop the old table and recreate it.
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory_counts (
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

-- ----------------------------------------------------------
-- expenses
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS expenses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id     INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    category     TEXT    NOT NULL,
    description  TEXT    NOT NULL,
    amount       REAL    NOT NULL CHECK (amount > 0),
    photo_path   TEXT,
    recorded_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_expenses_shift ON expenses (shift_id);

-- ----------------------------------------------------------
-- receiving_log  (replaces old receiving; no cost/photo)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS receiving_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id    INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    user        TEXT    NOT NULL,
    proveedor   TEXT    NOT NULL,
    producto    TEXT    NOT NULL,
    unidad      TEXT    NOT NULL,
    cantidad    REAL    NOT NULL CHECK (cantidad > 0),
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_receiving_log_shift ON receiving_log (shift_id);

-- ----------------------------------------------------------
-- shift_close  (cash reconciliation, one row per shift)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS shift_close (
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

-- ----------------------------------------------------------
-- verifier_review  (one review per shift)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS verifier_review (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id       INTEGER NOT NULL UNIQUE REFERENCES shifts(id) ON DELETE CASCADE,
    verifier_name  TEXT    NOT NULL,
    status         TEXT    NOT NULL CHECK (status IN ('aprobado','marcado')),
    notes          TEXT,
    reviewed_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------
-- app_sales_log  (delivery app orders outside POS)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_sales_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id        INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    user            TEXT    NOT NULL,
    app             TEXT    NOT NULL CHECK (app IN ('Rappi','Didi')),
    payment_type    TEXT    NOT NULL,
    app_amount      REAL    NOT NULL,
    business_amount REAL    NOT NULL,
    notes           TEXT,
    recorded_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_app_sales_shift ON app_sales_log (shift_id);

-- ----------------------------------------------------------
-- app_sales_items  (line items for each app sale)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_sales_items (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id  INTEGER NOT NULL REFERENCES app_sales_log(id) ON DELETE CASCADE,
    product  TEXT    NOT NULL,
    quantity REAL    NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_app_sales_items ON app_sales_items (sale_id);

-- ----------------------------------------------------------
-- consumption_log  (non-sale product use: merma, employee, etc.)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS consumption_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id    INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    user        TEXT    NOT NULL,
    tipo        TEXT    NOT NULL,
    product     TEXT    NOT NULL,
    cantidad    REAL    NOT NULL,
    unidad      TEXT    NOT NULL,
    notas       TEXT,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_consumption_shift ON consumption_log (shift_id);

-- ----------------------------------------------------------
-- pos_sales  (daily POS export: comandas.xlsx)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS pos_sales (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id      INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    foliocomanda  TEXT    NOT NULL,
    foliocuenta   TEXT    NOT NULL,
    orden         TEXT    NOT NULL,
    fechaapertura DATETIME NOT NULL,
    fechacierre   DATETIME,
    mesero        TEXT    NOT NULL,
    claveproducto TEXT    NOT NULL,
    descripcion   TEXT    NOT NULL,
    cantidad      REAL    NOT NULL DEFAULT 0,
    descuento     REAL    NOT NULL DEFAULT 0,
    importe       REAL    NOT NULL DEFAULT 0,
    uploaded_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pos_sales_shift ON pos_sales (shift_id);
