"""
ops_app/app.py  –  Astro Burger · Control Operacional
Entry point for the Streamlit multipage app.
Run: streamlit run ops_app/app.py
"""
import streamlit as st

# Must be the very first Streamlit call.
st.set_page_config(
    page_title="Astro Burger · Ops",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.database import init_db  # noqa: E402 (after set_page_config)
from core.ui import inject_css, shift_selector_sidebar  # noqa: E402

# ── Bootstrap ────────────────────────────────────────────────────────────────
init_db()
inject_css()

# ── Navigation ───────────────────────────────────────────────────────────────
pages = [
    st.Page("pages/open_shift.py",   title="Abrir Turno",         icon="🟢"),
    st.Page("pages/inventory.py",    title="Inventario",           icon="📦"),
    st.Page("pages/expenses.py",     title="Gastos",               icon="💸"),
    st.Page("pages/receiving.py",    title="Recepciones",          icon="🚚"),
    st.Page("pages/close_shift.py",  title="Cerrar Turno",         icon="🔴"),
    st.Page("pages/verifier.py",     title="Revisión Verificador", icon="✅"),
]

pg = st.navigation(pages)

# ── Sidebar: active-shift selector (shown on all pages except open_shift) ───
if pg.title != "Abrir Turno":
    shift_selector_sidebar()

pg.run()
