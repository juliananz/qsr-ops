"""
Page 3 – Gastos
Photo required for purchase categories.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import EXPENSE_CATEGORIES, PHOTO_REQUIRED_CATEGORIES
from core.models import save_expense, get_expenses
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("💸 Gastos")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

# ── Current expenses summary ─────────────────────────────────────────────────
expenses = get_expenses(shift_id)
if expenses:
    total = sum(e["amount"] for e in expenses)
    st.metric("Total gastos del turno", f"${total:,.2f}")
    with st.expander(f"Ver {len(expenses)} gasto(s) registrado(s)"):
        for e in expenses:
            icon = "📷" if e["photo_path"] else "  "
            st.markdown(
                f"{icon} **{e['category']}** — {e['description']} — "
                f"**${e['amount']:,.2f}** "
                f"<span style='color:#888;font-size:.85em'>{e['recorded_at']}</span>",
                unsafe_allow_html=True,
            )
    hr()

# ── New expense form ──────────────────────────────────────────────────────────
st.subheader("Registrar gasto")

with st.form("expense_form", clear_on_submit=True):
    col1, col2 = st.columns([2, 1])

    with col1:
        category = st.selectbox("Categoría", EXPENSE_CATEGORIES)
        description = st.text_input("Descripción", placeholder="Detalle del gasto")

    with col2:
        amount = st.number_input("Monto ($)", min_value=0.01, step=10.0, format="%.2f")

    photo_required = category in PHOTO_REQUIRED_CATEGORIES
    photo_label = (
        f"📷 Comprobante (obligatorio para **{category}**)"
        if photo_required
        else "📷 Comprobante (opcional)"
    )
    photo_file = st.file_uploader(
        photo_label,
        type=["jpg", "jpeg", "png", "pdf", "heic"],
        key="expense_photo",
    )

    if photo_required:
        st.caption("⚠️ Esta categoría requiere foto del comprobante.")

    submitted = st.form_submit_button("💾 Guardar gasto", type="primary")

if submitted:
    errors = []
    if not description.strip():
        errors.append("La descripción es obligatoria.")
    if amount <= 0:
        errors.append("El monto debe ser mayor a cero.")
    if photo_required and not photo_file:
        errors.append(f"Debes adjuntar una foto para la categoría '{category}'.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        photo_bytes = photo_file.read() if photo_file else None
        photo_name  = photo_file.name   if photo_file else None
        save_expense(
            shift_id=shift_id,
            category=category,
            description=description.strip(),
            amount=amount,
            photo_bytes=photo_bytes,
            photo_filename=photo_name,
        )
        st.success(f"✅ Gasto de **${amount:,.2f}** en **{category}** guardado.")
        st.rerun()
