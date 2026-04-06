"""
Page 3 – Recepciones de proveedores
No cost, no photo. Auto-fills unit from product selection.
Shows today's full receiving log below the form.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import SUPPLIERS, PRODUCT_NAMES, PRODUCT_UNITS
from core.models import save_receiving_log, get_receiving_log_today
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("🚚 Recepciones")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

user = st.session_state.get("current_display", "")

# ── New receiving form ────────────────────────────────────────────────────────
st.subheader("Registrar recepción")

col1, col2 = st.columns(2)

with col1:
    proveedor_opt = st.selectbox("Proveedor", SUPPLIERS, key="recv_proveedor")
    if proveedor_opt == "Otro":
        proveedor_text = st.text_input(
            "Nombre del proveedor",
            key="recv_proveedor_text",
            placeholder="Escribe el nombre",
        )
    else:
        proveedor_text = ""

    producto = st.selectbox("Producto", PRODUCT_NAMES, key="recv_producto")

with col2:
    # Auto-fill unit when product changes
    prev = st.session_state.get("_recv_prev_producto")
    if prev != producto:
        st.session_state["recv_unidad"] = PRODUCT_UNITS.get(producto, "piezas")
        st.session_state["_recv_prev_producto"] = producto

    unidad   = st.text_input("Unidad", key="recv_unidad")
    cantidad = st.number_input(
        "Cantidad", min_value=0.0, step=1.0, format="%.0f", key="recv_cantidad"
    )

if st.button("💾 Guardar recepción", type="primary"):
    proveedor = proveedor_text.strip() if proveedor_opt == "Otro" else proveedor_opt
    errors = []
    if not proveedor:
        errors.append("El proveedor es obligatorio.")
    if cantidad <= 0:
        errors.append("La cantidad debe ser mayor a cero.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        save_receiving_log(shift_id, user, proveedor, producto, unidad, float(cantidad))
        st.success(f"✅ {cantidad:.0f} {unidad} de **{producto}** de {proveedor} registrado.")
        # Clear quantity; keep supplier/product for quick consecutive entries
        for k in ["recv_cantidad", "recv_proveedor_text"]:
            st.session_state.pop(k, None)
        st.rerun()

hr()

# ── Today's receiving log ─────────────────────────────────────────────────────
st.subheader("Recepciones de hoy")
records = get_receiving_log_today()

if not records:
    st.info("Sin recepciones registradas hoy.")
else:
    import pandas as pd
    rows = [
        {
            "Hora":      r["recorded_at"][11:16] if r["recorded_at"] else "",
            "Proveedor": r["proveedor"],
            "Producto":  r["producto"],
            "Cantidad":  int(r["cantidad"]),
            "Unidad":    r["unidad"],
            "Usuario":   r["user"],
        }
        for r in records
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
