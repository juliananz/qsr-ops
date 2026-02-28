"""
Page 4 – Recepciones de proveedores
Photo of delivery note is always required.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import RECEIVING_UNITS
from core.models import save_receiving, get_receiving
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("🚚 Recepciones")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

# ── Current receiving list ────────────────────────────────────────────────────
records = get_receiving(shift_id)
if records:
    total_cost = sum(r["total_cost"] for r in records)
    st.metric("Total recepciones del turno", f"${total_cost:,.2f}")
    with st.expander(f"Ver {len(records)} recepción/es registrada(s)"):
        for r in records:
            st.markdown(
                f"📷 **{r['supplier']}** — {r['item']} — "
                f"{r['quantity']} {r['unit']} — "
                f"**${r['total_cost']:,.2f}** "
                f"<span style='color:#888;font-size:.85em'>{r['recorded_at']}</span>",
                unsafe_allow_html=True,
            )
    hr()

# ── New receiving form ────────────────────────────────────────────────────────
st.subheader("Registrar recepción")

with st.form("receiving_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        supplier = st.text_input("Proveedor", placeholder="Nombre del proveedor")
        item     = st.text_input("Artículo / Producto", placeholder="¿Qué se recibió?")

    with col2:
        qty  = st.number_input("Cantidad", min_value=0.0, step=1.0, format="%.2f")
        unit = st.selectbox("Unidad", RECEIVING_UNITS)
        total_cost = st.number_input("Costo total ($)", min_value=0.0, step=10.0, format="%.2f")

    photo_file = st.file_uploader(
        "📷 Foto del remisión / factura (obligatorio)",
        type=["jpg", "jpeg", "png", "pdf", "heic"],
        key="receiving_photo",
    )
    st.caption("⚠️ La foto del comprobante es siempre obligatoria.")

    submitted = st.form_submit_button("💾 Guardar recepción", type="primary")

if submitted:
    errors = []
    if not supplier.strip():
        errors.append("El nombre del proveedor es obligatorio.")
    if not item.strip():
        errors.append("El artículo es obligatorio.")
    if qty <= 0:
        errors.append("La cantidad debe ser mayor a cero.")
    if total_cost < 0:
        errors.append("El costo no puede ser negativo.")
    if not photo_file:
        errors.append("La foto del comprobante es obligatoria.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        save_receiving(
            shift_id=shift_id,
            supplier=supplier.strip(),
            item=item.strip(),
            quantity=qty,
            unit=unit,
            total_cost=total_cost,
            photo_bytes=photo_file.read(),
            photo_filename=photo_file.name,
        )
        st.success(
            f"✅ Recepción de **{supplier.strip()}** — "
            f"{qty} {unit} de **{item.strip()}** guardada."
        )
        st.rerun()
