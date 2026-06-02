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

from streamlit_cookies_controller import CookieController   # noqa: E402

from core.database import init_db                           # noqa: E402
from core.ui import inject_css, shift_selector_sidebar      # noqa: E402
from core.config import USERS, SESSION_TIMEOUT_MIN          # noqa: E402
from core.auth import (                                     # noqa: E402
    COOKIE_NAME,
    verify_pin,
    make_cookie,
    parse_cookie,
    should_refresh_cookie,
    mark_cookie_refreshed,
)

# ── Bootstrap ─────────────────────────────────────────────────────────────────
init_db()
inject_css()

# ── Cookie controller — must be instantiated before any st.stop() ─────────────
_cookies = CookieController(key="qsr_cookies")


# ── Session helpers ───────────────────────────────────────────────────────────

def _restore_from_cookie() -> bool:
    """Try to restore an authenticated session from the browser cookie.
    Returns True if a valid, non-expired cookie was found.
    """
    raw = _cookies.get(COOKIE_NAME)
    if not raw:
        return False
    parsed = parse_cookie(raw)
    if not parsed:
        _cookies.remove(COOKIE_NAME)
        return False
    st.session_state["current_user"]    = parsed["username"]
    st.session_state["current_display"] = parsed["display"]
    # Mark as refreshed so the sliding-window logic doesn't immediately fire
    mark_cookie_refreshed()
    return True


def _logout() -> None:
    """Clear session state and delete the browser cookie, then rerun."""
    for k in ["current_user", "current_display", "ops_shift_id"]:
        st.session_state.pop(k, None)
    _cookies.remove(COOKIE_NAME)
    st.rerun()


# ── Login form ────────────────────────────────────────────────────────────────

def _show_login() -> None:
    """Render login screen and halt execution until user authenticates."""
    st.title("🍔 Astro Burger · Ops")
    st.subheader("Iniciar sesión")

    try:
        # Probe secrets to give a clear error if [auth] is not configured
        _ = st.secrets["auth"]["salt"]
    except Exception:
        st.error(
            "⚠️ Sección `[auth]` no encontrada en `.streamlit/secrets.toml`. "
            "Consulta `secrets.toml.example` para configurarla."
        )
        st.stop()

    with st.form("login_form"):
        username = st.selectbox(
            "Usuario",
            list(USERS.keys()),
            format_func=lambda k: USERS[k],
        )
        pin = st.text_input("PIN", type="password", max_chars=4, placeholder="····")
        submitted = st.form_submit_button("Entrar", type="primary")

    if submitted:
        if verify_pin(username, pin):
            display = USERS[username]
            st.session_state["current_user"]    = username
            st.session_state["current_display"] = display
            mark_cookie_refreshed()
            _cookies.set(
                COOKIE_NAME,
                make_cookie(username, display),
                max_age=SESSION_TIMEOUT_MIN * 60,
            )
            st.rerun()
        else:
            st.error("PIN incorrecto.")

    st.stop()


# ── Auth gate ─────────────────────────────────────────────────────────────────

if "current_user" not in st.session_state:
    # Page refresh or new browser tab: try cookie before showing login form.
    # Note: on the very first render the cookie controller may not have
    # received browser data yet (returns None). If so, _restore_from_cookie()
    # returns False and the login form shows briefly until the controller
    # initialises (one extra Streamlit rerun, ~100 ms).
    if not _restore_from_cookie():
        _show_login()

else:
    # Already authenticated via session state.
    # Slide the inactivity window: rewrite the cookie (max once per 5 min)
    # so that the stored last_activity stays current.
    if should_refresh_cookie():
        raw = _cookies.get(COOKIE_NAME)
        if raw:
            parsed = parse_cookie(raw)
            if parsed:
                mark_cookie_refreshed()  # update guard BEFORE set() fires
                _cookies.set(
                    COOKIE_NAME,
                    make_cookie(parsed["username"], parsed["display"]),
                    max_age=SESSION_TIMEOUT_MIN * 60,
                )
            else:
                # Cookie expired while session state was still alive → logout
                _logout()


# ── Sidebar: user info + logout ───────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"👤 **{st.session_state['current_display']}**")
    if st.button("Cerrar sesión", key="logout_btn"):
        _logout()
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

_SHIFT_FREE = {"Abrir Turno", "Verificador"}
try:
    _needs_shift = pg.title not in _SHIFT_FREE
except AttributeError:
    _needs_shift = False

if _needs_shift:
    shift_selector_sidebar()

pg.run()
