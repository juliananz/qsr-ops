"""
Page 2 – Inventario
Sections A–H. Apertura / Cierre modes.
Once submitted a count is immutable (read-only view shown instead of form).
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collections import defaultdict

from core.config import INVENTORY_SECTIONS
from core.models import save_inventory_counts, has_inventory_counts, get_inventory_counts
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("📦 Inventario")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

user = st.session_state.get("current_display", "")

mode = st.radio(
    "Tipo de conteo",
    ["apertura", "cierre"],
    format_func=lambda x: "🌅 Apertura" if x == "apertura" else "🌇 Cierre",
    horizontal=True,
)

hr()

# ── Already submitted → read-only ────────────────────────────────────────────
if has_inventory_counts(shift_id, mode):
    st.success(f"✅ Conteo de **{mode}** ya registrado — solo lectura.")

    existing = get_inventory_counts(shift_id, mode)
    by_category: dict = defaultdict(list)
    for row in existing:
        by_category[row["category"]].append(row)

    for section_name in INVENTORY_SECTIONS:
        rows = by_category.get(section_name, [])
        if not rows:
            continue
        st.subheader(section_name)
        if section_name == "Checklist":
            cols = st.columns(4)
            for i, row in enumerate(rows):
                icon = "✅" if row["checked"] else "❌"
                cols[i % 4].markdown(f"{icon} {row['product']}")
        else:
            pairs = [rows[i : i + 2] for i in range(0, len(rows), 2)]
            for pair in pairs:
                c = st.columns(2)
                for col, row in zip(c, pair):
                    col.metric(row["product"], f"{int(row['quantity'])} {row['unit'] or ''}")
        hr()
    st.stop()

# ── Entry form ────────────────────────────────────────────────────────────────
counts: list[dict] = []

with st.form(f"inventory_form_{mode}"):
    for idx, (section_name, items) in enumerate(INVENTORY_SECTIONS.items()):
        letter = "ABCDEFGH"[idx]
        st.subheader(f"{letter}. {section_name}")

        if section_name == "Checklist":
            triples = [items[i : i + 3] for i in range(0, len(items), 3)]
            for triple in triples:
                cols = st.columns(3)
                for col, item in zip(cols, triple):
                    with col:
                        checked = st.checkbox(
                            item["name"],
                            key=f"inv_{mode}_{item['name']}",
                        )
                        counts.append({
                            "product":  item["name"],
                            "category": section_name,
                            "quantity": None,
                            "unit":     None,
                            "checked":  1 if checked else 0,
                        })
        else:
            visible = [
                i for i in items
                if not (i.get("cierre_only") and mode == "apertura")
            ]
            pairs = [visible[i : i + 2] for i in range(0, len(visible), 2)]
            for pair in pairs:
                cols = st.columns(2)
                for col, item in zip(cols, pair):
                    with col:
                        qty = st.number_input(
                            f"{item['name']}  ({item['unit']})",
                            min_value=0,
                            step=1,
                            key=f"inv_{mode}_{item['name']}",
                        )
                        counts.append({
                            "product":  item["name"],
                            "category": section_name,
                            "quantity": float(qty),
                            "unit":     item["unit"],
                            "checked":  None,
                        })

        hr()

    submitted = st.form_submit_button(
        f"💾 Guardar conteo de {mode}", type="primary"
    )

if submitted:
    save_inventory_counts(shift_id, user, mode, counts)
    qty_items = [c for c in counts if c["checked"] is None]
    chk_items = [c for c in counts if c["checked"] is not None]
    chk_ok    = sum(1 for c in chk_items if c["checked"])
    st.success(
        f"✅ Conteo de **{mode}** guardado — "
        f"{len(qty_items)} artículos, "
        f"{chk_ok}/{len(chk_items)} checklist OK."
    )
    st.rerun()
