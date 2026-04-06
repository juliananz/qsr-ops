"""
core/product_mapping.py
Maps POS product descriptions → product codes → inventory ingredient consumption.
"""

# ---------------------------------------------------------------------------
# POS product names used in App Sales and Consumption forms
# ---------------------------------------------------------------------------
POS_PRODUCTS: list[str] = [
    "HAMBURGUESA CON QUESO",
    "HAMBURGUESA SENCILLA",
    "HAMBURGUESA CON 2 CARNES",
    "ASTROBURGUER",
    "HAMBURGUESA DE POLLO",
    "ASTROPOLLO",
    "HOT DOG",
    "TORTA DE PIERNA",
    "TORTA TERNERA",
    "TORNILLOS",
    "PALOMAS TERNERA",
    "PALOMAS PIERNA",
    "ASTROPAPA",
    "PAPAS FRANCESAS",
    "1/2 ORDEN PAPAS",
    "BROWNIE",
    "EXTRA CARNE",
    "EXTRA POLLO",
    "EXTRA AGUACATE",
    "EXTRA QUESO",
    "EXTRA PEPINILLOS",
    "REFRESCO",
]

# ---------------------------------------------------------------------------
# A. POS description → product_code / bundle_code
#    Keys: uppercase, stripped (match df["descripcion"].str.upper().str.strip())
# ---------------------------------------------------------------------------
PRODUCT_NAME_MAPPING: dict[str, str] = {
    "HAMBURGUESA CON QUESO":                 "burger_cheese",
    "PAPAS FRANCESAS":                       "fries_full",
    "ASTROBURGUER":                          "burger_double_cheese",
    "REFRESCO":                              "soda",
    "TORTA DE PIERNA":                       "torta_pork",
    "ASTROPAPA":                             "astropapa",
    "HOT DOG":                              "hotdog",
    "HAMBURGUESA SENCILLA":                  "burger_plain",
    "1/2 ORDEN PAPAS":                       "fries_half",
    "TORNILLOS":                             "tornillos",
    "HAMBURGUESA DE POLLO":                  "burger_chicken",
    "TORTA TERNERA":                         "torta_beef",
    "BROWNIE":                               "brownie",
    "HAMBURGUESA CON 2 CARNES":              "burger_plain_double",
    "PALOMAS TERNERA":                       "palomas_beef",
    "EXTRA AGUACATE":                        "extra_avocado",
    "PALOMAS PIERNA":                        "palomas_pork",
    "EXTRA CARNE":                           "extra_meat",
    "AGUA NATURAL":                          "soda",
    "EXTRA QUESO":                           "extra_cheese",
    "EXTRA REBANADA DE QUESO":               "extra_cheese_slice",
    "FUZE TEA":                              "soda",
    "COCA LIGHT":                            "soda",
    "DELAWARE PUNCH":                        "soda",
    "EXTRA PEPINILLOS":                      "extra_pickles",
    "ASTROPOLLO":                            "burger_chicken_double",
    "EXTRA QUESO ASTROPAPA":                 "extra_cheese",
    "COCA REGULAR":                          "soda",
    "EXTRA POLLO":                           "extra_chicken",
    "FRESCA":                                "soda",
    "FANTA":                                 "soda",
    "SPRITE":                                "soda",
    "SIDRAL MUNDET":                         "soda",
    "PAQUETE 1 (HAMBURGUESA CON QUESO)":     "bundle_1",
    "PAQUETE 2: ASTROBURGUER":               "bundle_2",
    "PAQUETE 3: 2 HAMBURGUESAS CON QUESO":   "bundle_3",
    "PAQUETE 5: 2 ASTROBURGUER":             "bundle_5",
    "PAQUETE 6: 1 TORTA PIERNA":             "bundle_6_pork",
    "PAQUETE 8: HOT DOG":                    "bundle_8",
    "PAQUETE 6: 1 TORTA TERNERA":            "bundle_6_beef",
    "PAQUETE 7: TORNILLOS":                  "bundle_7",
    "PAQUETE 9: ASTROPAPA":                  "bundle_9",
    "PAQUETE 10: HAMBURGUESA POLLO":         "bundle_10",
    "PAQUETE 4: 2 TORTAS PIERNA":            "bundle_4_pork_pork",
    "PAQUETE FAMILIAR":                      "bundle_11",
    "PAQUETE 4: 2 TORTAS TERNERA":           "bundle_4_beef_beef",
    "PAQUETE 12: ASTROBURGER + SENCILLA QUESO": "bundle_12",
    "PAQUETE4:2 TORTAS MIXTA":               "bundle_4_pork_beef",
    "PAQUETE 12: ASTROPOLLO":                "bundle_12",
    "PAQUETE 13: 2 HAMBURGUESAS POLLO QUESO":"bundle_13",
    "PAQUETE 15: 2 ASTROPOLLOS":             "bundle_15",
    "PAQUETE 16: ASTROPOLLO":                "bundle_16",
    "PAQ. DE PALOMAS DE TERNERA":            "bundle_palomas_beef",
    "PAQ. DE PALOMAS DE PIERNA":             "bundle_palomas_pork",
}

# ---------------------------------------------------------------------------
# B. product_code → ingredient consumption (units from inventory)
# ---------------------------------------------------------------------------
INVENTORY_INGREDIENT_MAP: dict[str, dict[str, float]] = {
    "burger_cheese":         {"res": 1, "pan_hamburguesa": 1},
    "burger_double_cheese":  {"res": 2, "pan_hamburguesa": 1},
    "burger_plain":          {"res": 1, "pan_hamburguesa": 1},
    "burger_plain_double":   {"res": 2, "pan_hamburguesa": 1},
    "burger_chicken":        {"pollo": 1, "pan_hamburguesa": 1},
    "burger_chicken_double": {"pollo": 2, "pan_hamburguesa": 1},
    "hotdog":                {"salchicha": 1, "pan_hotdog": 1},
    "torta_pork":            {"pierna": 1, "pan_torta": 1},
    "torta_beef":            {"ternera": 1, "pan_torta": 1},
    "palomas_beef":          {"ternera": 1, "pan_torta": 1},
    "palomas_pork":          {"pierna": 1, "pan_torta": 1},
    "tornillos":             {"ternera": 1, "pan_torta": 1},
    "astropapa":             {"res": 1, "pan_hamburguesa": 1},
    "extra_meat":            {"res": 1},
    "extra_chicken":         {"pollo": 1},
    "bundle_1":              {"res": 1, "pan_hamburguesa": 1},
    "bundle_2":              {"res": 2, "pan_hamburguesa": 1},
    "bundle_3":              {"res": 2, "pan_hamburguesa": 2},
    "bundle_4_pork_pork":    {"pierna": 2, "pan_torta": 2},
    "bundle_4_beef_beef":    {"ternera": 2, "pan_torta": 2},
    "bundle_4_pork_beef":    {"pierna": 1, "ternera": 1, "pan_torta": 2},
    "bundle_5":              {"res": 4, "pan_hamburguesa": 2},
    "bundle_6_pork":         {"pierna": 1, "pan_torta": 1},
    "bundle_6_beef":         {"ternera": 1, "pan_torta": 1},
    "bundle_7":              {"ternera": 1, "pan_torta": 1},
    "bundle_8":              {"salchicha": 1, "pan_hotdog": 1},
    "bundle_9":              {"res": 1, "pan_hamburguesa": 1},
    "bundle_10":             {"pollo": 1, "pan_hamburguesa": 1},
    "bundle_11":             {"res": 4, "pan_hamburguesa": 4},
    "bundle_12":             {"res": 3, "pan_hamburguesa": 2},
    "bundle_13":             {"pollo": 2, "pan_hamburguesa": 2},
    "bundle_15":             {"pollo": 4, "pan_hamburguesa": 2},
    "bundle_16":             {"pollo": 2, "pan_hamburguesa": 1},
    "bundle_palomas_beef":   {"ternera": 2, "pan_torta": 2},
    "bundle_palomas_pork":   {"pierna": 2, "pan_torta": 2},
}

# ---------------------------------------------------------------------------
# Helpers: inventory product name ↔ ingredient key
# ---------------------------------------------------------------------------
INVENTORY_NAME_TO_KEY: dict[str, str] = {
    "Res":            "res",
    "Pollo":          "pollo",
    "Pierna":         "pierna",
    "Ternera":        "ternera",
    "Salchicha":      "salchicha",
    "Pan Hamburguesa":"pan_hamburguesa",
    "Pan Hot Dog":    "pan_hotdog",
    "Pan Torta":      "pan_torta",
}

KEY_TO_DISPLAY: dict[str, str] = {v: k for k, v in INVENTORY_NAME_TO_KEY.items()}

# Ordered list for table display (skip papa, aderezos, lácteos, etc.)
TRACKED_INGREDIENTS = [
    "res", "pollo", "pierna", "ternera", "salchicha",
    "pan_hamburguesa", "pan_hotdog", "pan_torta",
]


# ---------------------------------------------------------------------------
# C. calculate_theoretical_consumption
# ---------------------------------------------------------------------------
def calculate_theoretical_consumption(shift_id: int, db_conn) -> dict[str, float]:
    """
    Returns {ingredient_key: total_units_consumed} for the given shift.

    Sources:
      - pos_sales   (descripcion → PRODUCT_NAME_MAPPING → INVENTORY_INGREDIENT_MAP)
      - app_sales_items (product → same mapping, then INVENTORY_NAME_TO_KEY fallback)
      - consumption_log (product → INVENTORY_NAME_TO_KEY)
    """
    total: dict[str, float] = {}

    # ── POS sales ────────────────────────────────────────────────────────────
    rows = db_conn.execute(
        "SELECT descripcion, cantidad FROM pos_sales WHERE shift_id = ?",
        (shift_id,),
    ).fetchall()
    for row in rows:
        desc = str(row["descripcion"]).upper().strip()
        code = PRODUCT_NAME_MAPPING.get(desc)
        if not code:
            continue
        try:
            cantidad = float(row["cantidad"])
        except (TypeError, ValueError):
            cantidad = 0.0
        for ing, units in INVENTORY_INGREDIENT_MAP.get(code, {}).items():
            total[ing] = total.get(ing, 0.0) + units * cantidad

    # ── App sales items ───────────────────────────────────────────────────────
    items = db_conn.execute(
        """
        SELECT asi.product, asi.quantity
        FROM app_sales_items asi
        JOIN app_sales_log asl ON asl.id = asi.sale_id
        WHERE asl.shift_id = ?
        """,
        (shift_id,),
    ).fetchall()
    for item in items:
        product = str(item["product"])
        qty = float(item["quantity"])
        # Try menu-item mapping first
        code = PRODUCT_NAME_MAPPING.get(product.upper().strip())
        if code:
            for ing, units in INVENTORY_INGREDIENT_MAP.get(code, {}).items():
                total[ing] = total.get(ing, 0.0) + units * qty
        else:
            # Fall back to direct ingredient key
            key = INVENTORY_NAME_TO_KEY.get(product)
            if key:
                total[key] = total.get(key, 0.0) + qty

    # ── Consumption log ───────────────────────────────────────────────────────
    cons_rows = db_conn.execute(
        "SELECT product, cantidad FROM consumption_log WHERE shift_id = ?",
        (shift_id,),
    ).fetchall()
    for row in cons_rows:
        product = str(row["product"])
        qty = float(row["cantidad"])
        # Try POS product name mapping first
        code = PRODUCT_NAME_MAPPING.get(product.upper().strip())
        if code:
            for ing, units in INVENTORY_INGREDIENT_MAP.get(code, {}).items():
                total[ing] = total.get(ing, 0.0) + units * qty
        else:
            # Fall back to direct ingredient key (backward compat)
            key = INVENTORY_NAME_TO_KEY.get(product)
            if key:
                total[key] = total.get(key, 0.0) + qty

    return total
