"""
Page 3 – Recepciones de proveedores
- Batch table: all catalog products listed; user types Cantidad for what arrived.
- Inline Costo/u editing; cost changes persist to catalog on confirm.
- Multiple batches per day allowed; each confirm appends to today's log.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from core.config import SUPPLIERS
from core.models import (
    save_receiving_log,
    get_receiving_log_today,
    load_catalog,
    update_catalog_cost,
)
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("🚚 Recepciones")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

user = st.session_state.get("current_display", "")

catalog = load_catalog()

# ── Supplier selector ─────────────────────────────────────────────────────────
st.subheader("Registrar recepción")

proveedor_opt = st.selectbox("Proveedor", SUPPLIERS, key="recv_proveedor")
if proveedor_opt == "Otro":
    proveedor_text = st.text_input(
        "Nombre del proveedor",
        key="recv_proveedor_text",
        placeholder="Escribe el nombre",
    )
else:
    proveedor_text = ""

# ── Batch table ───────────────────────────────────────────────────────────────
_BATCH_KEY = "recv_batch_df"
_VER_KEY   = "recv_batch_ver"

if _VER_KEY not in st.session_state:
    st.session_state[_VER_KEY] = 0


def _build_batch_df(cat: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "Producto": item["nombre"],
            "Unidad":   item["unidad_compra"],
            "Cantidad": 0,
            "Costo/u":  float(item["costo_unitario"]),
        }
        for item in cat
    ])


if _BATCH_KEY not in st.session_state:
    st.session_state[_BATCH_KEY] = _build_batch_df(catalog)

ver = st.session_state[_VER_KEY]
editor_key = f"recv_editor_{ver}"

edited = st.data_editor(
    st.session_state[_BATCH_KEY],
    column_config={
        "Producto": st.column_config.TextColumn("Producto", disabled=True),
        "Unidad":   st.column_config.TextColumn("Unidad",   disabled=True),
        "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0, step=1, default=0),
        "Costo/u":  st.column_config.NumberColumn("Costo/u",  min_value=0.0, step=0.01, format="$%.2f"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key=editor_key,
)

hr()

if st.button("✅ Confirmar recepción", type="primary"):
    proveedor = proveedor_text.strip() if proveedor_opt == "Otro" else proveedor_opt
    if not proveedor:
        st.error("El proveedor es obligatorio.")
    else:
        mask = pd.to_numeric(edited["Cantidad"], errors="coerce").fillna(0) > 0
        to_save = edited[mask]
        if to_save.empty:
            st.warning("No hay productos con cantidad mayor a cero.")
        else:
            cat_costs = {item["nombre"]: float(item["costo_unitario"]) for item in catalog}
            saved = 0
            for _, row in to_save.iterrows():
                nombre   = str(row["Producto"])
                unidad   = str(row["Unidad"])
                cantidad = float(row["Cantidad"])
                costo    = float(row["Costo/u"])

                orig = cat_costs.get(nombre)
                if orig is not None and abs(costo - orig) > 0.001:
                    update_catalog_cost(nombre, costo)

                save_receiving_log(shift_id, user, proveedor, nombre, unidad, cantidad, costo)
                saved += 1

            st.success(f"✅ {saved} producto(s) registrado(s) de {proveedor}.")

            # Increment version → forces data_editor to remount as a new widget
            st.session_state[_VER_KEY] += 1
            st.session_state.pop(_BATCH_KEY, None)
            st.session_state.pop(editor_key, None)
            st.rerun()

hr()

# ── Today's receiving log ─────────────────────────────────────────────────────
st.subheader("Recepciones de hoy")
records = get_receiving_log_today()

if not records:
    st.info("Sin recepciones registradas hoy.")
else:
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
