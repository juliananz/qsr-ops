"""
Page 5 – Cerrar Turno
POS file upload → theoretical inventory → cash reconciliation.
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from core.models import (
    get_shift,
    get_shift_close,
    get_total_cash_expenses,
    has_inventory_counts,
    get_inventory_counts,
    get_receiving_log,
    close_shift,
    has_pos_sales,
    get_pos_sales,
    save_pos_sales,
)
from core.database import get_conn
from core.product_mapping import (
    calculate_theoretical_consumption,
    INVENTORY_NAME_TO_KEY,
    KEY_TO_DISPLAY,
    TRACKED_INGREDIENTS,
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

# ── Compute inventory gate flags early (needed for theoretical section too) ──
has_apertura = has_inventory_counts(shift_id, "apertura")
has_cierre   = has_inventory_counts(shift_id, "cierre")

# =============================================================================
# SECTION 1 — POS file upload
# =============================================================================
st.subheader("📂 Carga de archivo POS (comandas.xlsx)")

REQUIRED_COLS = [
    "foliocomanda", "foliocuenta", "orden", "fechaapertura", "fechacierre",
    "mesero", "claveproducto", "descripcion", "cantidad", "descuento", "importe",
]

if has_pos_sales(shift_id):
    pos_rows = get_pos_sales(shift_id)
    pos_df = pd.DataFrame([dict(r) for r in pos_rows])

    st.success(f"✅ Archivo POS cargado — {len(pos_df):,} registros.")

    fecha_min = pos_df["fechaapertura"].astype(str).str[:10].min()
    fecha_max = pos_df["fechaapertura"].astype(str).str[:10].max()
    total_importe = pos_df["importe"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total renglones", f"{len(pos_df):,}")
    c2.metric("Rango de fechas", f"{fecha_min} → {fecha_max}")
    c3.metric("Importe total", f"${total_importe:,.2f}")

    st.markdown("**Top 5 productos por cantidad:**")
    top5 = (
        pos_df.groupby("descripcion")["cantidad"]
        .sum()
        .nlargest(5)
        .reset_index()
    )
    top5.columns = ["Producto", "Cantidad"]
    st.dataframe(top5, use_container_width=True, hide_index=True)

else:
    uploaded = st.file_uploader(
        "Selecciona el archivo comandas.xlsx",
        type=["xlsx"],
        key="pos_uploader",
    )

    if uploaded is not None:
        try:
            raw = pd.read_excel(uploaded)
            # Normalize column names: lowercase, no spaces
            raw.columns = [c.strip().lower().replace(" ", "") for c in raw.columns]

            missing_cols = [c for c in REQUIRED_COLS if c not in raw.columns]
            if missing_cols:
                st.error(
                    f"Columnas faltantes en el archivo: {', '.join(missing_cols)}\n\n"
                    f"Columnas encontradas: {', '.join(raw.columns.tolist())}"
                )
            else:
                df = raw[REQUIRED_COLS].copy()

                # Type normalization
                for col in ["foliocomanda", "foliocuenta", "orden", "mesero",
                            "claveproducto", "descripcion"]:
                    df[col] = df[col].astype(str)
                for col in ["cantidad", "descuento", "importe"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                for col in ["fechaapertura", "fechacierre"]:
                    df[col] = pd.to_datetime(df[col], errors="coerce")

                # Drop rows with invalid fechaapertura
                before = len(df)
                df = df.dropna(subset=["fechaapertura"])
                dropped = before - len(df)

                if dropped:
                    st.warning(f"{dropped} filas descartadas por fechaapertura inválida.")

                st.info(f"**{len(df):,}** registros válidos listos para guardar.")

                if st.button("💾 Guardar datos POS", type="primary", key="btn_save_pos"):
                    # Convert datetimes to ISO strings for SQLite
                    records = []
                    for _, row in df.iterrows():
                        records.append({
                            "foliocomanda":  row["foliocomanda"],
                            "foliocuenta":   row["foliocuenta"],
                            "orden":         row["orden"],
                            "fechaapertura": row["fechaapertura"].isoformat(),
                            "fechacierre":   (
                                row["fechacierre"].isoformat()
                                if pd.notna(row["fechacierre"]) else None
                            ),
                            "mesero":        row["mesero"],
                            "claveproducto": row["claveproducto"],
                            "descripcion":   row["descripcion"],
                            "cantidad":      float(row["cantidad"]) if pd.notna(row["cantidad"]) else 0.0,
                            "descuento":     float(row["descuento"]) if pd.notna(row["descuento"]) else 0.0,
                            "importe":       float(row["importe"]) if pd.notna(row["importe"]) else 0.0,
                        })
                    save_pos_sales(shift_id, records)
                    st.success(f"✅ {len(records):,} registros guardados.")
                    st.rerun()

        except Exception as exc:
            st.error(f"Error al leer el archivo: {exc}")

hr()

# =============================================================================
# SECTION 2 — Inventario Teórico
# =============================================================================
st.subheader("📊 Inventario Teórico")

if not has_pos_sales(shift_id):
    st.info("⬆️ Carga el archivo POS para calcular el inventario teórico.")
elif not has_apertura:
    st.warning("Falta el inventario de **apertura** para calcular el inventario teórico.")
else:
    with get_conn() as conn:
        consumo = calculate_theoretical_consumption(shift_id, conn)

    # Only track ingredients that had non-zero theoretical consumption today
    relevant = [ing for ing in TRACKED_INGREDIENTS if consumo.get(ing, 0) > 0]

    if not relevant:
        st.info("Sin consumo teórico registrado para los ingredientes rastreados.")
    else:
        # Apertura inventory → {key: qty}
        apertura_map: dict[str, float] = {}
        for row in get_inventory_counts(shift_id, "apertura"):
            key = INVENTORY_NAME_TO_KEY.get(str(row["product"]))
            if key:
                apertura_map[key] = float(row["quantity"] or 0)

        # Recepciones for this shift → {key: total_qty}
        recepciones_map: dict[str, float] = {}
        for row in get_receiving_log(shift_id):
            key = INVENTORY_NAME_TO_KEY.get(str(row["producto"]))
            if key:
                recepciones_map[key] = recepciones_map.get(key, 0.0) + float(row["cantidad"])

        # Cierre inventory (if submitted) → {key: qty}
        cierre_map: dict[str, float] = {}
        if has_cierre:
            for row in get_inventory_counts(shift_id, "cierre"):
                key = INVENTORY_NAME_TO_KEY.get(str(row["product"]))
                if key:
                    cierre_map[key] = float(row["quantity"] or 0)

        if not has_cierre:
            st.info("⏳ Pendiente conteo de cierre — mostrando existencia teórica.")

        # Build display table
        table_rows = []
        for ing in relevant:
            inicial    = apertura_map.get(ing, 0.0)
            recv       = recepciones_map.get(ing, 0.0)
            cons       = consumo.get(ing, 0.0)
            teorico    = inicial + recv - cons

            row_data = {
                "Ingrediente":       KEY_TO_DISPLAY.get(ing, ing),
                "Inicial":           int(round(inicial)),
                "Recepciones":       int(round(recv)),
                "Consumo teórico":   round(cons, 1),
                "Exist. teórica":    round(teorico, 1),
            }

            if has_cierre:
                real = cierre_map.get(ing, 0.0)
                diff = real - teorico
                row_data["Conteo real"] = int(round(real))
                row_data["Diferencia"]  = round(diff, 1)

            table_rows.append(row_data)

        df_teorico = pd.DataFrame(table_rows)

        if has_cierre:
            def _diff_style(val):
                try:
                    v = float(val)
                except (TypeError, ValueError):
                    return ""
                if abs(v) < 0.5:
                    return "background-color: #d4edda"   # green
                elif abs(v) <= 1.5:
                    return "background-color: #fff3cd"   # yellow
                return "background-color: #f8d7da"        # red

            styled = df_teorico.style.map(_diff_style, subset=["Diferencia"])
            styled = styled.format({"Consumo teórico": "{:.1f}",
                                    "Exist. teórica":  "{:.1f}",
                                    "Diferencia":      "{:+.1f}"})
            st.dataframe(styled, use_container_width=True, hide_index=True)
        else:
            st.dataframe(
                df_teorico.style.format({"Consumo teórico": "{:.1f}",
                                         "Exist. teórica":  "{:.1f}"}),
                use_container_width=True,
                hide_index=True,
            )

hr()

# =============================================================================
# SECTION 3 — Cash reconciliation (requires both inventory counts)
# =============================================================================
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
