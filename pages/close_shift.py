"""
Page 5 – Cerrar Turno
POS reconciliation + cash count. Computes expected cash & discrepancy.
Blocked unless both apertura AND cierre inventory counts exist.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import (
    get_shift,
    get_shift_close,
    get_total_cash_expenses,
    has_inventory_counts,
    close_shift,
)
from core.ui import inject_css, hr, require_active_shift, shift_header

inject_css()
st.title("🔴 Cerrar Turno")

shift_id = require_active_shift()
shift_header(shift_id)
hr()

shift = get_shift(shift_id)

# ── Already closed: show summary only ────────────────────────────────────────
if shift["status"] == "closed":
    sc = get_shift_close(shift_id)
    st.success("✅ Este turno ya fue cerrado.")
    if sc:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Ventas totales",    f"${sc['total_sales']:,.2f}")
        col2.metric("Efectivo esperado", f"${sc['expected_cash']:,.2f}")
        col3.metric("Efectivo contado",  f"${sc['actual_cash_counted']:,.2f}")
        disc = sc["discrepancy"]
        delta_color = "normal" if abs(disc) < 1 else ("inverse" if disc < 0 else "off")
        col4.metric("Diferencia",        f"${disc:,.2f}", delta_color=delta_color)
    st.stop()

# ── Inventory gate: both apertura AND cierre must exist ───────────────────────
has_apertura = has_inventory_counts(shift_id, "apertura")
has_cierre   = has_inventory_counts(shift_id, "cierre")

if not has_apertura or not has_cierre:
    missing = []
    if not has_apertura:
        missing.append("**inventario de apertura**")
    if not has_cierre:
        missing.append("**inventario de cierre**")
    st.error(
        f"🚫 No se puede cerrar el turno. "
        f"Faltan: {' y '.join(missing)}.\n\n"
        f"Ve a la página de **Inventario** y registra los conteos antes de cerrar."
    )
    st.stop()

# ── Pre-fill cash expenses from recorded expenses ─────────────────────────────
auto_expenses = get_total_cash_expenses(shift_id)
opening_cash  = float(shift["opening_cash"])

st.info(
    f"Fondo inicial: **${opening_cash:,.2f}** · "
    f"Gastos registrados en app: **${auto_expenses:,.2f}**"
)

# ── POS totals form ───────────────────────────────────────────────────────────
with st.form("close_shift_form"):
    st.subheader("Totales del POS")
    c1, c2, c3, c4 = st.columns(4)
    total_sales = c1.number_input("Ventas totales ($)",      min_value=0.0, step=100.0, format="%.2f")
    cash_sales  = c2.number_input("Ventas en efectivo ($)",  min_value=0.0, step=100.0, format="%.2f")
    card_sales  = c3.number_input("Ventas con tarjeta ($)",  min_value=0.0, step=100.0, format="%.2f")
    cxc_sales   = c4.number_input("Ventas CxC ($)",          min_value=0.0, step=100.0, format="%.2f")

    hr()
    st.subheader("Arqueo de caja")
    c5, c6 = st.columns(2)
    actual_cash = c5.number_input(
        "Efectivo físico contado ($)", min_value=0.0, step=100.0, format="%.2f"
    )
    cash_expenses = c6.number_input(
        "Gastos en efectivo ($)",
        min_value=0.0,
        value=auto_expenses,
        step=10.0,
        format="%.2f",
        help="Pre-llenado con los gastos registrados en la app. Ajusta si hubo gastos no registrados.",
    )

    hr()
    submitted = st.form_submit_button("🔴 Cerrar turno y calcular diferencia", type="primary")

if submitted:
    # Soft warning if POS totals don't add up
    if total_sales > 0 and abs((cash_sales + card_sales + cxc_sales) - total_sales) > 1:
        st.warning(
            f"⚠️ La suma Efectivo + Tarjeta + CxC "
            f"(${cash_sales + card_sales + cxc_sales:,.2f}) no cuadra con "
            f"Ventas totales (${total_sales:,.2f}). Verifica los montos."
        )

    result = close_shift(
        shift_id=shift_id,
        total_sales=total_sales,
        cash_sales=cash_sales,
        card_sales=card_sales,
        cxc_sales=cxc_sales,
        actual_cash_counted=actual_cash,
        cash_expenses=cash_expenses,
        opening_cash=opening_cash,
    )
    expected = result["expected_cash"]
    disc     = result["discrepancy"]

    st.success("✅ Turno cerrado. Resumen exportado a CSV.")
    hr()
    col1, col2, col3 = st.columns(3)
    col1.metric("Efectivo esperado", f"${expected:,.2f}",
                help="Fondo inicial + ventas en efectivo – gastos en efectivo")
    col2.metric("Efectivo contado",  f"${actual_cash:,.2f}")

    if abs(disc) < 1:
        disc_html = f'<div class="alert-ok">✅ Sin diferencia (${disc:,.2f})</div>'
    elif disc < 0:
        disc_html = f'<div class="alert-err">🔴 Faltante: ${disc:,.2f}</div>'
    else:
        disc_html = f'<div class="alert-warn">🟡 Sobrante: +${disc:,.2f}</div>'

    col3.markdown(disc_html, unsafe_allow_html=True)

    st.session_state.pop("ops_shift_id", None)
    st.info("Ve a **Revisión Verificador** para aprobar o marcar el turno.")
