"""
Page 3 – Recepciones de proveedores
- Unit costs loaded from data/catalog_productos.json (fixed, not prompted each time).
- Toggle "¿Cambios en costos?" lets user update ONE product cost at a time before submitting.
- Shows today's full receiving log below the form.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import SUPPLIERS
from core.models import (
    save_receiving_log,
    get_receiving_log_today,
    load_catalog,
    get_catalog_cost,
    get_catalog_unit,
    update_catalog_cost,
)
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("🚚 Recepciones")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

user = st.session_state.get("current_display", "")

# Load catalog once
catalog = load_catalog()
cat_names = [item["nombre"] for item in catalog]

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

    producto = st.selectbox("Producto", cat_names, key="recv_producto")

with col2:
    # Auto-fill unit from catalog when product changes
    prev = st.session_state.get("_recv_prev_producto")
    if prev != producto:
        cat_unit = get_catalog_unit(producto) or "piezas"
        st.session_state["recv_unidad"] = cat_unit
        st.session_state["_recv_prev_producto"] = producto

    unidad   = st.text_input("Unidad", key="recv_unidad")
    cantidad = st.number_input(
        "Cantidad", min_value=0.0, step=1.0, format="%.0f", key="recv_cantidad"
    )

hr()

# ── Cost-change toggle ────────────────────────────────────────────────────────
cambios_costos = st.toggle("¿Cambios en costos?", key="recv_toggle_costos")

if cambios_costos:
    st.markdown("**Actualizar costo de un producto:**")
    cc1, cc2 = st.columns([2, 1])

    with cc1:
        cost_prod = st.selectbox(
            "Producto con nuevo costo",
            [""] + cat_names,
            format_func=lambda x: "— seleccionar —" if x == "" else x,
            key="recv_cost_prod",
        )

    if cost_prod:
        curr_cost = get_catalog_cost(cost_prod) or 0.0
        with cc2:
            new_cost = st.number_input(
                f"Nuevo costo (actual ${curr_cost:,.2f})",
                min_value=0.01,
                value=float(curr_cost),
                step=1.0,
                format="%.2f",
                key="recv_new_cost",
            )

        if st.button("✓ Confirmar cambio de costo", key="btn_confirm_cost"):
            update_catalog_cost(cost_prod, new_cost)
            st.success(f"✅ Costo de **{cost_prod}** actualizado a **${new_cost:,.2f}**")
            # Clear selector so user can pick another product if needed
            st.session_state.pop("recv_cost_prod", None)
            st.session_state.pop("recv_new_cost", None)
            st.rerun()

hr()

# ── Save button ───────────────────────────────────────────────────────────────
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
        costo = get_catalog_cost(producto) or 0.0
        save_receiving_log(
            shift_id, user, proveedor, producto, unidad, float(cantidad), costo
        )
        st.success(
            f"✅ {cantidad:.0f} {unidad} de **{producto}** de {proveedor} "
            f"registrado (costo: ${costo:,.2f}/u)."
        )
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
            "Costo/u":   f"${r['costo_unitario']:,.2f}" if r["costo_unitario"] else "—",
            "Usuario":   r["user"],
        }
        for r in records
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
