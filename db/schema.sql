-- =============================================================
-- ops_app database schema  –  Astro Burger anti-leakage system
-- =============================================================
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------
-- shifts  (one row per AM/PM shift)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS shifts (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_date               DATE    NOT NULL,
    shift_name               TEXT    NOT NULL CHECK (shift_name IN ('AM','PM')),
    opening_cash             REAL    NOT NULL DEFAULT 2000,
    cashier_name             TEXT    NOT NULL,
    delivery_controller      TEXT    NOT NULL,
    status                   TEXT    NOT NULL DEFAULT 'open'
                             CHECK (status IN ('open','closed','approved','flagged')),
    opened_at                DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_shifts_date_name
    ON shifts (shift_date, shift_name);

-- ----------------------------------------------------------
-- inventory_counts
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory_counts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id     INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    count_type   TEXT    NOT NULL CHECK (count_type IN ('apertura','cierre')),
    item_name    TEXT    NOT NULL,
    quantity     REAL    NOT NULL,
    unit         TEXT    NOT NULL,
    recorded_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_inventory_shift ON inventory_counts (shift_id, count_type);

-- ----------------------------------------------------------
-- expenses
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS expenses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id     INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    category     TEXT    NOT NULL,
    description  TEXT    NOT NULL,
    amount       REAL    NOT NULL CHECK (amount > 0),
    photo_path   TEXT,                            -- NULL only if category has no photo requirement
    recorded_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_expenses_shift ON expenses (shift_id);

-- ----------------------------------------------------------
-- receiving  (supplier deliveries)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS receiving (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id     INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
    supplier     TEXT    NOT NULL,
    item         TEXT    NOT NULL,
    quantity     REAL    NOT NULL CHECK (quantity > 0),
    unit         TEXT    NOT NULL,
    total_cost   REAL    NOT NULL CHECK (total_cost >= 0),
    photo_path   TEXT    NOT NULL,                -- always required
    recorded_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_receiving_shift ON receiving (shift_id);

-- ----------------------------------------------------------
-- shift_close  (POS reconciliation, one row per shift)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS shift_close (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    shift_id             INTEGER NOT NULL UNIQUE REFERENCES shifts(id) ON DELETE CASCADE,
    total_sales          REAL    NOT NULL,
    cash_sales           REAL    NOT NULL,
    card_sales           REAL    NOT NULL,
    cxc_sales            REAL    NOT NULL,
    actual_cash_counted  REAL    NOT NULL,
    cash_expenses        REAL    NOT NULL,
    expected_cash        REAL    NOT NULL,   -- opening_cash + cash_sales - cash_expenses
    discrepancy          REAL    NOT NULL,   -- actual_cash_counted - expected_cash
    closed_at            DATETIME DEFAULT CURRENT_TIMESTAMP
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
