"""
ops_app/core/config.py
Static reference data.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OPS_ROOT    = Path(__file__).parent.parent
DB_PATH     = OPS_ROOT / "db" / "ops.sqlite"
UPLOADS_DIR = OPS_ROOT / "uploads"
EXPORTS_DIR = OPS_ROOT / "exports"

# ---------------------------------------------------------------------------
# Shift constants
# ---------------------------------------------------------------------------
OPENING_CASH = 2000.0

# ---------------------------------------------------------------------------
# Hardcoded users
# ---------------------------------------------------------------------------
USERS = {
    "paulina":     {"pin": "0000", "display": "Paulina"},
    "miguel":      {"pin": "0000", "display": "Miguel"},
    "josejulian":  {"pin": "0000", "display": "José Julián"},
    "jorgejulian": {"pin": "0000", "display": "Jorge Julián"},
}

# ---------------------------------------------------------------------------
# Inventory sections A–H
# input_type: "quantity" | "checklist"
# cierre_only: True → field only appears in Cierre mode
# ---------------------------------------------------------------------------
INVENTORY_SECTIONS: dict[str, list[dict]] = {
    "Carnes": [
        {"name": "Res",       "unit": "piezas", "input_type": "quantity"},
        {"name": "Pollo",     "unit": "piezas", "input_type": "quantity"},
        {"name": "Pierna",    "unit": "piezas", "input_type": "quantity"},
        {"name": "Ternera",   "unit": "piezas", "input_type": "quantity"},
        {"name": "Salchicha", "unit": "piezas", "input_type": "quantity"},
    ],
    "Papas": [
        {"name": "Papa", "unit": "bultos", "input_type": "quantity"},
    ],
    "Pan": [
        {"name": "Pan Hamburguesa", "unit": "charolas", "input_type": "quantity"},
        {"name": "Pan Hot Dog",     "unit": "paquetes", "input_type": "quantity"},
    ],
    "Aderezos": [
        {"name": "Catsup",     "unit": "piezas", "input_type": "quantity"},
        {"name": "Mayonesa",   "unit": "piezas", "input_type": "quantity"},
        {"name": "Mostaza",    "unit": "piezas", "input_type": "quantity"},
        {"name": "Pepinillos", "unit": "piezas", "input_type": "quantity"},
        {"name": "Chiles",     "unit": "piezas", "input_type": "quantity"},
    ],
    "Verduras": [
        {"name": "Tomate",   "unit": "cajas",  "input_type": "quantity"},
        {"name": "Lechuga",  "unit": "cajas",  "input_type": "quantity"},
        {"name": "Aguacate", "unit": "mallas", "input_type": "quantity"},
    ],
    "Checklist": [
        {"name": "Sal",            "input_type": "checklist"},
        {"name": "Pimienta",       "input_type": "checklist"},
        {"name": "Valentina",      "input_type": "checklist"},
        {"name": "Lemon pepper",   "input_type": "checklist"},
        {"name": "Papel 1/2",      "input_type": "checklist"},
        {"name": "Papel cebolla",  "input_type": "checklist"},
        {"name": "Papel encerado", "input_type": "checklist"},
        {"name": "Aluminio",       "input_type": "checklist"},
        {"name": "Bolsa 4/6",      "input_type": "checklist"},
        {"name": "Bolsa embolsar", "input_type": "checklist"},
        {"name": "Bolsa camiseta", "input_type": "checklist"},
        {"name": "Fabuloso",       "input_type": "checklist"},
        {"name": "Desengrasante",  "input_type": "checklist"},
        {"name": "Jabón",          "input_type": "checklist"},
        {"name": "Papel secante",  "input_type": "checklist"},
        {"name": "Servilletas",    "input_type": "checklist"},
        {"name": "Charolas",       "input_type": "checklist"},
    ],
}

# ---------------------------------------------------------------------------
# Flat product list for receiving / app_sales / consumption (sections A–G)
# ---------------------------------------------------------------------------
PRODUCTS: list[tuple[str, str]] = [
    # Carnes
    ("Res",       "piezas"),
    ("Pollo",     "piezas"),
    ("Pierna",    "piezas"),
    ("Ternera",   "piezas"),
    ("Salchicha", "piezas"),
    # Papas
    ("Papa", "bultos"),
    # Pan
    ("Pan Hamburguesa", "charolas"),
    ("Pan Hot Dog",     "paquetes"),
    # Aderezos
    ("Catsup",     "piezas"),
    ("Mayonesa",   "piezas"),
    ("Mostaza",    "piezas"),
    ("Pepinillos", "piezas"),
    ("Chiles",     "piezas"),
    # Verduras
    ("Tomate",   "cajas"),
    ("Lechuga",  "cajas"),
    ("Aguacate", "mallas"),
]

PRODUCT_UNITS: dict[str, str] = {name: unit for name, unit in PRODUCTS}
PRODUCT_NAMES: list[str]       = [name for name, _ in PRODUCTS]

# ---------------------------------------------------------------------------
# Suppliers for receiving
# ---------------------------------------------------------------------------
SUPPLIERS = [
    "Astroburger Coss",
    "Sam's",
    "Frutas Luis",
    "Tienda",
    "Chica Brownie",
    "Tortugas",
    "Otro",
]

# ---------------------------------------------------------------------------
# Expense categories
# ---------------------------------------------------------------------------
EXPENSE_CATEGORIES = [
    "Compra de insumos",
    "Compra de bebidas",
    "Gas LP",
    "Limpieza y desinfección",
    "Mantenimiento / Reparación",
    "Transporte / Envíos",
    "Nómina eventual",
    "Otros",
]

PHOTO_REQUIRED_CATEGORIES = {
    "Compra de insumos",
    "Compra de bebidas",
    "Mantenimiento / Reparación",
}
