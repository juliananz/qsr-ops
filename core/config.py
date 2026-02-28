"""
ops_app/core/config.py
Static reference data — edit this file to update inventory items or categories.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OPS_ROOT    = Path(__file__).parent.parent          # ops_app/
DB_PATH     = OPS_ROOT / "db" / "ops.sqlite"
UPLOADS_DIR = OPS_ROOT / "uploads"
EXPORTS_DIR = OPS_ROOT / "exports"

# ---------------------------------------------------------------------------
# Shift constants
# ---------------------------------------------------------------------------
OPENING_CASH = 2000.0
SHIFT_NAMES  = ["AM", "PM"]

# ---------------------------------------------------------------------------
# Inventory items — mirrors the physical notebook exactly.
#
# input_type rules:
#   "quantity"  → numeric integer input (pieces, bags, boxes, jars, cans, meshes…)
#   "checklist" → checkbox OK / Not OK  (minor consumables, seasonings, cleaning)
#
# Do NOT change section names — they match the existing notebook categories.
# ---------------------------------------------------------------------------
INVENTORY_ITEMS = [
    # ── Proteínas ──────────────────────────────────────────────────────────
    # Counted in pieces (pzas). Never kg.
    {"name": "Carne res",    "unit": "pzas", "section": "Proteínas", "input_type": "quantity"},
    {"name": "Pollo",        "unit": "pzas", "section": "Proteínas", "input_type": "quantity"},
    {"name": "Pierna",       "unit": "pzas", "section": "Proteínas", "input_type": "quantity"},
    {"name": "Ternera",      "unit": "pzas", "section": "Proteínas", "input_type": "quantity"},
    {"name": "Tornillos",    "unit": "pzas", "section": "Proteínas", "input_type": "quantity"},
    {"name": "Salchichas",   "unit": "pzas", "section": "Proteínas", "input_type": "quantity"},
    # ── Pan ────────────────────────────────────────────────────────────────
    # Hamburguesa and hot dog: we count bags (6 buns each), NOT individual buns.
    # Torta: counted per piece.
    {"name": "Pan hamburguesa", "unit": "bolsas", "section": "Pan", "input_type": "quantity"},
    {"name": "Pan hot dog",     "unit": "bolsas", "section": "Pan", "input_type": "quantity"},
    {"name": "Pan torta",       "unit": "pzas",   "section": "Pan", "input_type": "quantity"},
    # ── Verduras ───────────────────────────────────────────────────────────
    {"name": "Tomate",   "unit": "cajas",  "section": "Verduras", "input_type": "quantity"},
    {"name": "Lechuga",  "unit": "cajas",  "section": "Verduras", "input_type": "quantity"},
    {"name": "Aguacate", "unit": "mallas", "section": "Verduras", "input_type": "quantity"},
    # ── Lácteos ────────────────────────────────────────────────────────────
    {"name": "Queso hamburguesa", "unit": "cajas", "section": "Lácteos", "input_type": "quantity"},
    {"name": "Queso AP",          "unit": "pzas",  "section": "Lácteos", "input_type": "quantity"},
    {"name": "Crema",             "unit": "botes", "section": "Lácteos", "input_type": "quantity"},
    {"name": "Mantequilla",       "unit": "botes", "section": "Lácteos", "input_type": "quantity"},
    # ── Salsas ─────────────────────────────────────────────────────────────
    # Primary unit: botes. Pickles and peppers also counted per bote.
    {"name": "Catsup",     "unit": "botes", "section": "Salsas", "input_type": "quantity"},
    {"name": "Mayonesa",   "unit": "botes", "section": "Salsas", "input_type": "quantity"},
    {"name": "Mostaza",    "unit": "botes", "section": "Salsas", "input_type": "quantity"},
    {"name": "Pepinillos", "unit": "botes", "section": "Salsas", "input_type": "quantity"},
    {"name": "Chiles",     "unit": "botes", "section": "Salsas", "input_type": "quantity"},
    # ── Guarniciones ───────────────────────────────────────────────────────
    # Papas: physically counted in bags.
    # Aceite, Sal, Lemon pepper: minor consumables → checklist only.
    {"name": "Papas congeladas", "unit": "bolsas", "section": "Guarniciones", "input_type": "quantity"},
    {"name": "Aceite de cocina", "unit": "",        "section": "Guarniciones", "input_type": "checklist"},
    {"name": "Sal",              "unit": "",        "section": "Guarniciones", "input_type": "checklist"},
    {"name": "Lemon pepper",     "unit": "",        "section": "Guarniciones", "input_type": "checklist"},
    # ── Bebidas ────────────────────────────────────────────────────────────
    {"name": "Coca 2L",    "unit": "pzas", "section": "Bebidas", "input_type": "quantity"},
    {"name": "Coca 600ml", "unit": "pzas", "section": "Bebidas", "input_type": "quantity"},
    # ── Empaque ────────────────────────────────────────────────────────────
    # Packaging is physically counted.
    {"name": "Bolsas grandes", "unit": "pzas",     "section": "Empaque", "input_type": "quantity"},
    {"name": "Bolsas chicas",  "unit": "pzas",     "section": "Empaque", "input_type": "quantity"},
    {"name": "Charolas",       "unit": "pzas",     "section": "Empaque", "input_type": "quantity"},
    {"name": "Servilletas",    "unit": "paquetes", "section": "Empaque", "input_type": "quantity"},
    {"name": "Vasos",          "unit": "pzas",     "section": "Empaque", "input_type": "quantity"},
    # ── Limpieza ───────────────────────────────────────────────────────────
    # All cleaning supplies are minor consumables → checklist only.
    {"name": "Fabuloso",      "unit": "", "section": "Limpieza", "input_type": "checklist"},
    {"name": "Desengrasante", "unit": "", "section": "Limpieza", "input_type": "checklist"},
    {"name": "Jabón",         "unit": "", "section": "Limpieza", "input_type": "checklist"},
    {"name": "Papel secante", "unit": "", "section": "Limpieza", "input_type": "checklist"},
    {"name": "Cloro",         "unit": "", "section": "Limpieza", "input_type": "checklist"},
]

# Fast lookup: item_name → item dict (for display in verifier / reports)
INVENTORY_ITEM_MAP: dict = {item["name"]: item for item in INVENTORY_ITEMS}

# ---------------------------------------------------------------------------
# Expense categories — unchanged
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

# ---------------------------------------------------------------------------
# Units for receiving
# ---------------------------------------------------------------------------
RECEIVING_UNITS = ["kg", "L", "pzas", "cajas", "bolsas", "paquetes"]
