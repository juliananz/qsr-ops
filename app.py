"""
ops_app/app.py  –  Astro Burger · Control Operacional
Entry point for the Streamlit multipage app.
Run: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="Astro Burger · Ops",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="expanded",
)

from core.database import init_db          # noqa: E402
from core.ui import inject_css, shift_selector_sidebar  # noqa: E402
from core.config import USERS              # noqa: E402

# ── Bootstrap ────────────────────────────────────────────────────────────────
init_db()
inject_css()


# ── Authentication ────────────────────────────────────────────────────────────
def _show_login() -> None:
    """Render login screen and halt execution until user authenticates."""
    st.title("🍔 Astro Burger · Ops")
    st.subheader("Iniciar sesión")

    with st.form("login_form"):
        username = st.selectbox(
            "Usuario",
            list(USERS.keys()),
            format_func=lambda k: USERS[k]["display"],
        )
        pin = st.text_input("PIN", type="password", max_chars=4, placeholder="····")
        submitted = st.form_submit_button("Entrar", type="primary")

    if submitted:
        if USERS[username]["pin"] == pin:
            st.session_state["current_user"]    = username
            st.session_state["current_display"] = USERS[username]["display"]
            st.rerun()
        else:
            st.error("PIN incorrecto.")

    st.stop()


if "current_user" not in st.session_state:
    _show_login()

# ── Sidebar: user info + logout ───────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"👤 **{st.session_state['current_display']}**")
    if st.button("Cerrar sesión", key="logout_btn"):
        for k in ["current_user", "current_display", "ops_shift_id"]:
            st.session_state.pop(k, None)
        st.rerun()
    st.divider()

# ── Navigation ────────────────────────────────────────────────────────────────
pages = [
    st.Page("pages/open_shift.py",   title="Abrir Turno",    icon="🟢"),
    st.Page("pages/inventory.py",    title="Inventario",      icon="📦"),
    st.Page("pages/receiving.py",    title="Recepciones",     icon="🚚"),
    st.Page("pages/expenses.py",     title="Gastos",          icon="💸"),
    st.Page("pages/app_sales.py",    title="Ventas App",      icon="📱"),
    st.Page("pages/consumption.py",  title="Consumos",        icon="🍽️"),
    st.Page("pages/close_shift.py",  title="Cierre de Turno", icon="🔴"),
    st.Page("pages/verifier.py",     title="Verificador",     icon="✅"),
]

pg = st.navigation(pages)

# Shift selector for pages that require an active shift
_SHIFT_FREE = {"Abrir Turno", "Verificador"}
try:
    _needs_shift = pg.title not in _SHIFT_FREE
except AttributeError:
    _needs_shift = False

if _needs_shift:
    shift_selector_sidebar()

pg.run()
