"""
Page 1 – Abrir Turno
"""
import sqlite3
import streamlit as st
from datetime import date

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import OPENING_CASH, SHIFT_NAMES
from core.models import open_shift, any_shift_open, get_open_shifts
from core.ui import inject_css, hr

inject_css()

st.title("🟢 Abrir Turno")

# ── Hard block: cannot open a new shift while one is already open ─────────────
if any_shift_open():
    open_shifts = get_open_shifts()
    labels = ", ".join(
        f"**{s['shift_name']}** ({s['shift_date']}) — {s['cashier_name']}"
        for s in open_shifts
    )
    st.error(
        f"🚫 No se puede abrir un nuevo turno. "
        f"Hay turno(s) activo(s): {labels}\n\n"
        f"Cierra el turno activo antes de abrir uno nuevo."
    )
    st.stop()

hr()

with st.form("open_shift_form", clear_on_submit=True):
    today = date.today()
    col1, col2 = st.columns(2)

    with col1:
        shift_date = st.date_input(
            "Fecha del turno",
            value=today,
            max_value=today,
        )
        shift_name = st.radio(
            "Turno",
            SHIFT_NAMES,
            horizontal=True,
        )

    with col2:
        cashier_name = st.text_input(
            "Nombre del cajero",
            placeholder="Escribe el nombre completo",
        )
        delivery_controller = st.text_input(
            "Nombre del controlador de delivery",
            placeholder="Escribe el nombre completo",
        )

    hr()
    st.metric("Efectivo de apertura", f"${OPENING_CASH:,.0f}", delta=None)

    submitted = st.form_submit_button("✅ Abrir Turno", type="primary")

if submitted:
    errors = []
    if not cashier_name.strip():
        errors.append("El nombre del cajero es obligatorio.")
    if not delivery_controller.strip():
        errors.append("El nombre del controlador de delivery es obligatorio.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        try:
            shift_id = open_shift(
                shift_date=shift_date,
                shift_name=shift_name,
                cashier_name=cashier_name.strip(),
                delivery_controller=delivery_controller.strip(),
                opening_cash=OPENING_CASH,
            )
            st.session_state["ops_shift_id"] = shift_id
            st.success(
                f"✅ Turno **{shift_name}** del **{shift_date}** abierto "
                f"para **{cashier_name.strip()}**."
            )
            st.balloons()
        except sqlite3.IntegrityError:
            st.error(
                f"🚫 Ya existe un turno **{shift_name}** para el **{shift_date}**. "
                f"No se pueden tener dos turnos del mismo tipo en el mismo día."
            )
        except Exception as exc:
            st.error(f"Error al abrir el turno: {exc}")
