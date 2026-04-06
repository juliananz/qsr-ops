"""
Page 5 – Ventas por Aplicación
Register Rappi/Didi orders processed outside the POS.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import PRODUCT_NAMES, PRODUCT_UNITS
from core.models import save_app_sale, get_app_sales_today, get_app_sale_items
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("📱 Ventas por Aplicación")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

user = st.session_state.get("current_display", "")

# ── Registration form ─────────────────────────────────────────────────────────
st.subheader("Registrar pedido de app")

col1, col2 = st.columns(2)
with col1:
    app          = st.selectbox("App", ["Rappi", "Didi"], key="as_app")
    payment_type = st.selectbox(
        "Pago", ["En línea", "Efectivo del repartidor"], key="as_payment"
    )
with col2:
    app_amount      = st.number_input(
        "Monto cobrado por la app (MXN)", min_value=0.0, step=10.0, format="%.2f", key="as_app_amt"
    )
    business_amount = st.number_input(
        "Ganancia estimada para el negocio (MXN)", min_value=0.0, step=10.0, format="%.2f", key="as_biz_amt"
    )

st.markdown("**Productos del pedido**")
selected_products = st.multiselect(
    "Selecciona productos", PRODUCT_NAMES, key="as_products"
)

product_quantities: dict[str, float] = {}
if selected_products:
    st.markdown("Cantidades:")
    groups = [selected_products[i : i + 3] for i in range(0, len(selected_products), 3)]
    for group in groups:
        cols = st.columns(3)
        for col, prod in zip(cols, group):
            with col:
                product_quantities[prod] = st.number_input(
                    prod, min_value=1, step=1, key=f"as_qty_{prod}"
                )

notes = st.text_area("Notas (opcional)", key="as_notes", height=80)

hr()

if st.button("💾 Guardar venta de app", type="primary"):
    errors = []
    if app_amount <= 0:
        errors.append("El monto cobrado por la app debe ser mayor a cero.")
    if not selected_products:
        errors.append("Selecciona al menos un producto del pedido.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        items = [
            {"product": p, "quantity": float(product_quantities[p])}
            for p in selected_products
        ]
        save_app_sale(
            shift_id=shift_id,
            user=user,
            app=app,
            payment_type=payment_type,
            app_amount=app_amount,
            business_amount=business_amount,
            notes=notes.strip() or None,
            items=items,
        )
        st.success(
            f"✅ Pedido de **{app}** — ${app_amount:.2f} — "
            f"{len(items)} producto(s) registrado."
        )
        # Clear form state
        for k in ["as_app", "as_payment", "as_app_amt", "as_biz_amt",
                  "as_products", "as_notes"] + [f"as_qty_{p}" for p in selected_products]:
            st.session_state.pop(k, None)
        st.rerun()

hr()

# ── Today's app sales log ─────────────────────────────────────────────────────
st.subheader("Ventas de app hoy")
sales = get_app_sales_today()

if not sales:
    st.info("Sin ventas de app registradas hoy.")
else:
    for sale in sales:
        items = get_app_sale_items(sale["id"])
        products_str = ", ".join(f"{i['product']} ×{int(i['quantity'])}" for i in items)
        hora = sale["recorded_at"][11:16] if sale["recorded_at"] else ""
        with st.expander(
            f"{hora}  **{sale['app']}** — ${sale['app_amount']:.2f} — {sale['user']}"
        ):
            st.markdown(f"**Pago:** {sale['payment_type']}")
            st.markdown(f"**Ganancia negocio:** ${sale['business_amount']:.2f}")
            st.markdown(f"**Productos:** {products_str or '—'}")
            if sale["notes"]:
                st.markdown(f"**Notas:** {sale['notes']}")
