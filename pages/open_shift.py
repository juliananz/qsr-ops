"""
Page 1 – Abrir Turno (simplified)
Only date field; opener is the logged-in user.
"""
import sqlite3
import streamlit as st
from datetime import date, datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import OPENING_CASH
from core.models import open_shift, get_open_shift_today, get_available_shift_name
from core.ui import inject_css, hr

inject_css()
st.title("🟢 Abrir Turno")

display = st.session_state.get("current_display", "")

today = date.today()

# ── Block if a shift is already open today ────────────────────────────────────
existing = get_open_shift_today()
if existing:
    opened_at = existing["opened_at"] or ""
    st.warning(
        f"⚠️ Ya hay un turno abierto hoy por **{existing['cashier_name']}** "
        f"desde las `{opened_at}`.\n\n"
        f"No se puede abrir un segundo turno mientras haya uno activo."
    )
    st.stop()

hr()

with st.form("open_shift_form"):
    shift_date = st.date_input("Fecha del turno", value=today, max_value=today)
    st.info(f"Abrirá el turno como: **{display}**")
    submitted = st.form_submit_button("✅ Abrir Turno", type="primary")

if submitted:
    slot = get_available_shift_name(shift_date)
    if slot is None:
        st.error("🚫 Ya existen turnos AM y PM para esta fecha.")
    else:
        try:
            shift_id = open_shift(
                shift_date=shift_date,
                shift_name=slot,
                cashier_name=display,
                delivery_controller=display,
                opening_cash=OPENING_CASH,
            )
            st.session_state["ops_shift_id"] = shift_id
            st.success(
                f"✅ Turno **{slot}** del **{shift_date}** abierto "
                f"por **{display}**."
            )
            st.balloons()
        except sqlite3.IntegrityError:
            st.error("🚫 Ya existe un turno para esa fecha y tipo.")
        except Exception as exc:
            st.error(f"Error al abrir el turno: {exc}")
