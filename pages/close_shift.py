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
    get_pos_sales_total,
    get_app_sales_total,
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
        col1.metric("Ventas totales",  f"${sc['ventas_totales']:,.2f}")
        col2.metric("Efectivo contado", f"${sc['efectivo_contado']:,.2f}")
        col3.metric("Comprobación",    f"${sc['comprobacion']:,.2f}")
        disc = sc["diferencia"]
        col4.metric("Diferencia",      f"${disc:,.2f}")
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
# SECTION 3 — Arqueo de caja (requires both inventory counts)
# =============================================================================
st.subheader("💰 Arqueo de Caja")

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

# ── STEP A: Auto-calculated from existing data ────────────────────────────────
ventas_pos      = get_pos_sales_total(shift_id)
ventas_app      = get_app_sales_total(shift_id)
gastos_efectivo = get_total_cash_expenses(shift_id)
ventas_totales  = ventas_pos + ventas_app

st.markdown("**Ventas registradas (automático)**")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Ventas POS",       f"${ventas_pos:,.2f}")
c2.metric("Ventas App",       f"${ventas_app:,.2f}")
c3.metric("Gastos efectivo",  f"${gastos_efectivo:,.2f}")
c4.metric("Ventas totales",   f"${ventas_totales:,.2f}")

hr()

# ── STEP B: Manual inputs ─────────────────────────────────────────────────────
st.markdown("**Conteo de denominaciones**")

BILLS  = [1000, 500, 200, 100, 50, 20]
COINS  = [10, 5, 2, 1, 0.50]

bill_cols = st.columns(len(BILLS))
coin_cols = st.columns(len(COINS))

bill_counts: dict[float, int] = {}
coin_counts: dict[float, int] = {}

for col, denom in zip(bill_cols, BILLS):
    with col:
        st.markdown(f"**${denom:,.0f}**")
        bill_counts[denom] = st.number_input(
            "piezas", min_value=0, step=1, key=f"denom_{denom}", label_visibility="collapsed"
        )

for col, denom in zip(coin_cols, COINS):
    with col:
        label = f"**${denom:,.2f}**" if denom < 1 else f"**${denom:,.0f}**"
        st.markdown(label)
        coin_counts[denom] = st.number_input(
            "piezas", min_value=0, step=1, key=f"denom_{denom}", label_visibility="collapsed"
        )

efectivo_contado = sum(d * q for d, q in bill_counts.items()) + sum(d * q for d, q in coin_counts.items())

st.markdown(f"**Total contado: ${efectivo_contado:,.2f}**")

hr()

st.markdown("**Otros datos del arqueo (manual)**")
c1, c2, c3 = st.columns(3)
with c1:
    ventas_tarjeta = st.number_input(
        "Ventas tarjeta (según terminal)",
        min_value=0.0, step=100.0, format="%.2f",
        key="cs_ventas_tarjeta",
    )
with c2:
    fondo_inicial = st.number_input(
        "Fondo inicial",
        min_value=0.0, value=float(shift["opening_cash"]),
        step=100.0, format="%.2f",
        key="cs_fondo_inicial",
    )
with c3:
    st.metric("Efectivo en caja", f"${efectivo_contado:,.2f}")

# ── STEP C: Auto-calculated arqueo ────────────────────────────────────────────
efectivo_neto = efectivo_contado - fondo_inicial
comprobacion  = efectivo_neto + ventas_tarjeta + ventas_app + gastos_efectivo
diferencia    = ventas_totales - comprobacion

hr()
st.markdown("**Resultado del arqueo**")
c1, c2, c3 = st.columns(3)
c1.metric("Efectivo neto", f"${efectivo_neto:,.2f}",
          help="Efectivo contado menos fondo inicial")
c2.metric("Comprobación",  f"${comprobacion:,.2f}",
          help="Efectivo neto + tarjeta + app + gastos")

if diferencia == 0:
    c3.markdown(
        '<div class="alert-ok">✅ Cuadrado perfecto</div>',
        unsafe_allow_html=True,
    )
elif diferencia > 0:
    c3.markdown(
        f'<div class="alert-warn">🟡 Sobran ${diferencia:,.2f}</div>',
        unsafe_allow_html=True,
    )
else:
    c3.markdown(
        f'<div class="alert-err">🔴 Faltan ${abs(diferencia):,.2f}</div>',
        unsafe_allow_html=True,
    )

# ── STEP D: Notes + submit ────────────────────────────────────────────────────
hr()
notas = st.text_area("Notas del turno (opcional)", key="cs_notas", height=80)

if st.button("🔴 Cerrar Turno", type="primary"):
    close_shift(
        shift_id=shift_id,
        ventas_pos=ventas_pos,
        ventas_app=ventas_app,
        gastos_efectivo=gastos_efectivo,
        efectivo_contado=efectivo_contado,
        ventas_tarjeta=ventas_tarjeta,
        fondo_inicial=fondo_inicial,
        notas=notas.strip() or None,
    )
    st.success("✅ Turno cerrado. Resumen exportado a CSV.")
    st.session_state.pop("ops_shift_id", None)
    st.info("Ve a **Revisión Verificador** para aprobar o marcar el turno.")
    st.rerun()
