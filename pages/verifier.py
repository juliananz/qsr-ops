"""
Page 8 – Revisión del Verificador
Full shift summary. Action form available only for status='closed'.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import (
    get_shifts_pending_review,
    get_all_shifts,
    get_shift,
    get_shift_close,
    get_inventory_counts,
    get_expenses,
    get_receiving_log,
    get_verifier_review,
    save_verifier_review,
)
from core.ui import inject_css, hr

inject_css()
st.title("✅ Revisión del Verificador")
hr()

# ── Shift picker ──────────────────────────────────────────────────────────────
tab_pending, tab_all = st.tabs(["⏳ Pendientes de revisión", "📋 Todos los turnos"])

with tab_pending:
    pending = get_shifts_pending_review()
    if not pending:
        st.success("Sin turnos pendientes de revisión.")
        selected_pending_id = None
    else:
        opts = {
            f"{s['shift_date']} {s['shift_name']} — {s['cashier_name']}": s["id"]
            for s in pending
        }
        chosen_label = st.selectbox("Selecciona turno a revisar", list(opts.keys()), key="pend_sel")
        selected_pending_id = opts[chosen_label]

with tab_all:
    all_shifts = get_all_shifts()
    if not all_shifts:
        st.info("No hay turnos registrados aún.")
        st.stop()
    opts_all = {
        f"{s['shift_date']} {s['shift_name']} — {s['cashier_name']} [{s['status']}]": s["id"]
        for s in all_shifts
    }
    chosen_all = st.selectbox("Selecciona turno", list(opts_all.keys()), key="all_sel")
    selected_all_id = opts_all[chosen_all]

review_id = selected_pending_id if pending else selected_all_id

if not review_id:
    st.stop()

hr()

# ── Full shift summary ────────────────────────────────────────────────────────
shift = get_shift(review_id)
sc    = get_shift_close(review_id)
rev   = get_verifier_review(review_id)

st.subheader(f"Turno {shift['shift_date']} {shift['shift_name']} — {shift['cashier_name']}")
st.caption(f"Abrió: **{shift['cashier_name']}** · Estado: **{shift['status']}**")

# ── Cash reconciliation ───────────────────────────────────────────────────────
if sc:
    st.markdown("#### 💵 Arqueo de caja")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ventas totales", f"${sc['total_sales']:,.2f}")
    c2.metric("Vtas efectivo",  f"${sc['cash_sales']:,.2f}")
    c3.metric("Vtas tarjeta",   f"${sc['card_sales']:,.2f}")
    c4.metric("Vtas CxC",       f"${sc['cxc_sales']:,.2f}")
    c5, c6, c7 = st.columns(3)
    c5.metric("Efectivo esperado", f"${sc['expected_cash']:,.2f}")
    c6.metric("Efectivo contado",  f"${sc['actual_cash_counted']:,.2f}")
    disc = sc["discrepancy"]
    if abs(disc) < 1:
        c7.markdown('<div class="alert-ok">✅ Sin diferencia</div>', unsafe_allow_html=True)
    elif disc < 0:
        c7.markdown(f'<div class="alert-err">🔴 Faltante ${disc:,.2f}</div>', unsafe_allow_html=True)
    else:
        c7.markdown(f'<div class="alert-warn">🟡 Sobrante +${disc:,.2f}</div>', unsafe_allow_html=True)
else:
    st.warning("⚠️ Este turno aún no tiene cierre registrado.")

hr()

# ── Expenses summary ──────────────────────────────────────────────────────────
expenses = get_expenses(review_id)
if expenses:
    st.markdown(f"#### 💸 Gastos ({len(expenses)})")
    for e in expenses:
        icon = "📷" if e["photo_path"] else "⬜"
        st.markdown(f"{icon} **{e['category']}** — {e['description']} — **${e['amount']:,.2f}**")

# ── Receiving summary ─────────────────────────────────────────────────────────
receiving = get_receiving_log(review_id)
if receiving:
    st.markdown(f"#### 🚚 Recepciones ({len(receiving)})")
    for r in receiving:
        st.markdown(
            f"**{r['proveedor']}** — {r['producto']} "
            f"{int(r['cantidad'])} {r['unidad']} — {r['user']}"
        )

# ── Inventory counts ──────────────────────────────────────────────────────────
inv_ap = get_inventory_counts(review_id, "apertura")
inv_ci = get_inventory_counts(review_id, "cierre")
if inv_ap or inv_ci:
    with st.expander(
        f"📦 Inventarios (apertura: {len(inv_ap)}, cierre: {len(inv_ci)} artículos)"
    ):
        col_a, col_c = st.columns(2)

        def _fmt_inv_row(row) -> str:
            if row["checked"] is not None:
                badge = "✅ OK" if row["checked"] else "❌ No OK"
                return f"{row['product']}: {badge}"
            elif row["quantity"] is not None and row["quantity"] > 0:
                return f"{row['product']}: {int(row['quantity'])} {row['unit'] or ''}"
            return ""

        with col_a:
            st.markdown("**Apertura**")
            for i in inv_ap:
                line = _fmt_inv_row(i)
                if line:
                    st.text(line)
        with col_c:
            st.markdown("**Cierre**")
            for i in inv_ci:
                line = _fmt_inv_row(i)
                if line:
                    st.text(line)

hr()

# ── Previous review result ────────────────────────────────────────────────────
if rev:
    if rev["status"] == "aprobado":
        st.markdown(
            f'<div class="alert-ok">✅ Aprobado por <b>{rev["verifier_name"]}</b>'
            f' — {rev["reviewed_at"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="alert-err">🚩 Marcado por <b>{rev["verifier_name"]}</b>'
            f' — {rev["reviewed_at"]}<br>Notas: {rev["notes"]}</div>',
            unsafe_allow_html=True,
        )
    hr()

# ── Verifier action — only available when shift is 'closed' ──────────────────
if shift["status"] == "closed":
    with st.form("verifier_form"):
        st.markdown("#### Decisión del verificador")
        verifier_name = st.text_input(
            "Nombre del verificador",
            placeholder="Tu nombre completo",
        )
        decision = st.radio(
            "Decisión",
            ["aprobado", "marcado"],
            format_func=lambda x: "✅ Aprobar turno" if x == "aprobado" else "🚩 Marcar / Rechazar",
            horizontal=True,
        )
        notes = st.text_area(
            "Notas",
            placeholder="Obligatorio si marcas el turno.",
            height=100,
        )
        submitted = st.form_submit_button("💾 Guardar revisión", type="primary")

    if submitted:
        errors = []
        if not verifier_name.strip():
            errors.append("El nombre del verificador es obligatorio.")
        if decision == "marcado" and not notes.strip():
            errors.append("Las notas son obligatorias cuando se marca un turno.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            save_verifier_review(
                shift_id=review_id,
                verifier_name=verifier_name.strip(),
                status=decision,
                notes=notes.strip() or None,
            )
            verb = "aprobado" if decision == "aprobado" else "marcado"
            st.success(f"✅ Turno {verb} por **{verifier_name.strip()}**.")
            st.rerun()

elif shift["status"] == "open":
    st.info("El turno debe estar cerrado antes de poder revisarlo.")
else:
    st.info(f"Este turno ya fue revisado (estado: **{shift['status']}**).")
