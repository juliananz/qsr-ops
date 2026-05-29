"""
Page 2 – Inventario
Sections A–F. Apertura / Cierre modes.
- Only one apertura and one cierre per calendar day (enforced).
- Once submitted a count is immutable (read-only view shown instead of form).
- Checklist section includes a free-text comentarios field.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collections import defaultdict

from core.config import INVENTORY_SECTIONS
from core.models import (
    save_inventory_counts,
    has_inventory_counts,
    has_inventory_today_any_shift,
    get_inventory_counts,
    get_shift,
)
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("📦 Inventario")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

shift = get_shift(shift_id)
shift_date = str(shift["shift_date"])
user = st.session_state.get("current_display", "")

mode = st.radio(
    "Tipo de conteo",
    ["apertura", "cierre"],
    format_func=lambda x: "🌅 Apertura" if x == "apertura" else "🌇 Cierre",
    horizontal=True,
)

hr()

# ── Already submitted for THIS shift → read-only ──────────────────────────────
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
            normal_rows = [r for r in rows if r["product"] != "_comentarios_"]
            comentarios_row = next(
                (r for r in rows if r["product"] == "_comentarios_"), None
            )
            cols = st.columns(4)
            for i, row in enumerate(normal_rows):
                icon = "✅" if row["checked"] else "❌"
                cols[i % 4].markdown(f"{icon} {row['product']}")
            if comentarios_row and comentarios_row["unit"]:
                st.info(f"💬 **Comentarios:** {comentarios_row['unit']}")
        else:
            pairs = [rows[i : i + 2] for i in range(0, len(rows), 2)]
            for pair in pairs:
                c = st.columns(2)
                for col, row in zip(c, pair):
                    col.metric(row["product"], f"{int(row['quantity'])} {row['unit'] or ''}")
        hr()
    st.stop()

# ── Enforce: only one apertura/cierre per calendar day ────────────────────────
if has_inventory_today_any_shift(shift_date, mode):
    st.warning(
        f"⚠️ El conteo de **{mode}** ya fue registrado hoy en otro turno. "
        f"Solo se permite un conteo de {mode} por día."
    )
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
            # Free-text comentarios for the checklist
            comentarios_text = st.text_area(
                "Comentarios",
                key=f"inv_{mode}_comentarios",
                height=80,
                placeholder="Observaciones adicionales del turno...",
            )
            counts.append({
                "product":  "_comentarios_",
                "category": section_name,
                "quantity": None,
                "unit":     comentarios_text.strip() if comentarios_text else "",
                "checked":  None,
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
    qty_items = [c for c in counts if c["checked"] is None and c["product"] != "_comentarios_"]
    chk_items = [c for c in counts if c["checked"] is not None]
    chk_ok    = sum(1 for c in chk_items if c["checked"])
    st.success(
        f"✅ Conteo de **{mode}** guardado — "
        f"{len(qty_items)} artículos, "
        f"{chk_ok}/{len(chk_items)} checklist OK."
    )
    st.rerun()
