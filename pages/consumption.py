"""
Page 6 – Consumos
Register non-sale product consumption (merma, employee meals, etc.)
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.product_mapping import POS_PRODUCTS
from core.models import save_consumption, get_consumption_today
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("🍽️ Consumos")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

user = st.session_state.get("current_display", "")

TIPOS = ["Consumo empleado", "Consumo dueño", "Merma", "Otro"]

# ── Registration form ─────────────────────────────────────────────────────────
st.subheader("Registrar consumo")

tipo = st.selectbox("Tipo", TIPOS, key="cons_tipo")

selected_products = st.multiselect(
    "Productos", POS_PRODUCTS, key="cons_products"
)

product_quantities: dict[str, int] = {}
if selected_products:
    st.markdown("Cantidades:")
    groups = [selected_products[i : i + 3] for i in range(0, len(selected_products), 3)]
    for group in groups:
        cols = st.columns(3)
        for col, prod in zip(cols, group):
            with col:
                product_quantities[prod] = st.number_input(
                    prod, min_value=1, value=1, step=1, key=f"cons_qty_{prod}"
                )

notas = st.text_area("Notas (opcional)", key="cons_notas", height=80)

if st.button("💾 Guardar consumo", type="primary"):
    errors = []
    if not selected_products:
        errors.append("Selecciona al menos un producto.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        for prod in selected_products:
            qty = product_quantities.get(prod, 1)
            save_consumption(
                shift_id=shift_id,
                user=user,
                tipo=tipo,
                product=prod,
                cantidad=float(qty),
                unidad="piezas",
                notas=notas.strip() or None,
            )
        names = ", ".join(
            f"{product_quantities.get(p, 1)} × {p}" for p in selected_products
        )
        st.success(f"✅ {tipo}: {names} registrado.")
        for k in ["cons_products", "cons_notas"] + [f"cons_qty_{p}" for p in selected_products]:
            st.session_state.pop(k, None)
        st.rerun()

hr()

# ── Today's consumption log ───────────────────────────────────────────────────
st.subheader("Consumos de hoy")
records = get_consumption_today()

if not records:
    st.info("Sin consumos registrados hoy.")
else:
    import pandas as pd
    rows = [
        {
            "Hora":     r["recorded_at"][11:16] if r["recorded_at"] else "",
            "Tipo":     r["tipo"],
            "Producto": r["product"],
            "Cantidad": int(r["cantidad"]),
            "Notas":    r["notas"] or "",
            "Usuario":  r["user"],
        }
        for r in records
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
