"""
Page 2 – Inventario
- quantity items → integer number_input
- checklist items → checkbox (OK / Not OK)
Supports apertura and cierre counts.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import INVENTORY_ITEMS
from core.models import save_inventory_counts, get_inventory_counts
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("📦 Inventario")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

# ── Count type selector ──────────────────────────────────────────────────────
count_type = st.radio(
    "Tipo de conteo",
    ["apertura", "cierre"],
    format_func=lambda x: "🌅 Apertura" if x == "apertura" else "🌇 Cierre",
    horizontal=True,
)

# ── Pre-fill existing counts if they exist ───────────────────────────────────
existing = get_inventory_counts(shift_id, count_type)
existing_map = {r["item_name"]: r["quantity"] for r in existing}

if existing:
    st.info(
        f"Ya existe un conteo de **{count_type}** para este turno. "
        f"Puedes corregirlo y guardar de nuevo."
    )

hr()

# ── Group items by section ────────────────────────────────────────────────────
sections: dict[str, list] = {}
for item in INVENTORY_ITEMS:
    sections.setdefault(item["section"], []).append(item)

counts: list[dict] = []

with st.form("inventory_form"):
    for section, items in sections.items():
        st.subheader(section)

        # Separate quantity and checklist items within each section
        qty_items  = [i for i in items if i["input_type"] == "quantity"]
        chk_items  = [i for i in items if i["input_type"] == "checklist"]

        # ── Quantity items: 2 per row ───────────────────────────────────────
        if qty_items:
            pairs = [qty_items[i : i + 2] for i in range(0, len(qty_items), 2)]
            for pair in pairs:
                cols = st.columns(2)
                for col, item in zip(cols, pair):
                    with col:
                        default_val = int(existing_map.get(item["name"], 0))
                        qty = st.number_input(
                            f"{item['name']}  ({item['unit']})",
                            min_value=0,
                            value=default_val,
                            step=1,
                            key=f"inv_{count_type}_{item['name']}",
                        )
                        counts.append(
                            {
                                "item_name": item["name"],
                                "quantity": float(qty),
                                "unit": item["unit"],
                            }
                        )

        # ── Checklist items: 3 per row ──────────────────────────────────────
        if chk_items:
            if qty_items:
                st.markdown("**Consumibles**")
            triples = [chk_items[i : i + 3] for i in range(0, len(chk_items), 3)]
            for triple in triples:
                cols = st.columns(3)
                for col, item in zip(cols, triple):
                    with col:
                        default_checked = existing_map.get(item["name"], 0.0) >= 1.0
                        checked = st.checkbox(
                            item["name"],
                            value=default_checked,
                            key=f"inv_{count_type}_{item['name']}",
                        )
                        counts.append(
                            {
                                "item_name": item["name"],
                                "quantity": 1.0 if checked else 0.0,
                                "unit": "",
                            }
                        )

        hr()

    submitted = st.form_submit_button(
        f"💾 Guardar conteo de {count_type}", type="primary"
    )

if submitted:
    save_inventory_counts(shift_id, count_type, counts)
    qty_saved = sum(1 for c in counts if c["unit"] != "" and c["quantity"] > 0)
    chk_ok    = sum(1 for c in counts if c["unit"] == "" and c["quantity"] >= 1)
    chk_total = sum(1 for c in counts if c["unit"] == "")
    st.success(
        f"✅ Conteo de **{count_type}** guardado — "
        f"{qty_saved} artículos contados, "
        f"{chk_ok}/{chk_total} consumibles OK."
    )
