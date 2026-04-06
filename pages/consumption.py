"""
Page 6 – Consumos
Register non-sale product consumption (merma, employee meals, etc.)
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import PRODUCT_NAMES, PRODUCT_UNITS
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

col1, col2 = st.columns(2)
with col1:
    tipo    = st.selectbox("Tipo", TIPOS, key="cons_tipo")
    product = st.selectbox("Producto", PRODUCT_NAMES, key="cons_product")

with col2:
    # Auto-fill unit when product changes
    prev = st.session_state.get("_cons_prev_product")
    if prev != product:
        st.session_state["cons_unidad"] = PRODUCT_UNITS.get(product, "piezas")
        st.session_state["_cons_prev_product"] = product

    unidad  = st.text_input("Unidad", key="cons_unidad")
    cantidad = st.number_input(
        "Cantidad", min_value=0.0, step=1.0, format="%.0f", key="cons_cantidad"
    )

notas = st.text_area("Notas (opcional)", key="cons_notas", height=80)

if st.button("💾 Guardar consumo", type="primary"):
    errors = []
    if cantidad <= 0:
        errors.append("La cantidad debe ser mayor a cero.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        save_consumption(
            shift_id=shift_id,
            user=user,
            tipo=tipo,
            product=product,
            cantidad=float(cantidad),
            unidad=unidad,
            notas=notas.strip() or None,
        )
        st.success(
            f"✅ {tipo}: {cantidad:.0f} {unidad} de **{product}** registrado."
        )
        for k in ["cons_cantidad", "cons_notas"]:
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
            "Unidad":   r["unidad"],
            "Notas":    r["notas"] or "",
            "Usuario":  r["user"],
        }
        for r in records
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
