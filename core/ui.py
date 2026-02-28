"""
ops_app/core/ui.py
Shared UI helpers: CSS injection, shift banner, session-state guards.
"""
import streamlit as st

from .models import get_shift, get_open_shifts


# ─── CSS ────────────────────────────────────────────────────────────────────

TABLET_CSS = """
<style>
/* ── Global ── */
html, body, [class*="css"] { font-size: 17px; }

/* ── Bigger buttons ── */
div.stButton > button {
    height: 3.2rem;
    font-size: 1.1rem;
    font-weight: 600;
    border-radius: 8px;
    width: 100%;
}

/* ── Primary buttons ── */
div.stButton > button[kind="primary"] {
    background-color: #e05c1b;
    border-color: #e05c1b;
    color: white;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #c44e14;
    border-color: #c44e14;
}

/* ── Form inputs ── */
input, textarea, select, [data-baseweb="select"] {
    font-size: 1.05rem !important;
    min-height: 2.6rem !important;
}

/* ── Number inputs ─ bigger touch target ── */
input[type="number"] { font-size: 1.15rem !important; }

/* ── Sidebar nav links ── */
[data-testid="stSidebarNavLink"] { font-size: 1.05rem; padding: 0.55rem 1rem; }

/* ── Section divider ── */
hr.section-hr { border-top: 2px solid #e05c1b; margin: 1.2rem 0; }

/* ── Metric tiles ── */
[data-testid="metric-container"] { background: #f9f9f9; border-radius:8px; padding:0.6rem; }

/* ── Alert boxes ── */
.alert-ok  { background:#d4edda; border-left:5px solid #28a745; padding:0.8rem; border-radius:4px; }
.alert-warn{ background:#fff3cd; border-left:5px solid #ffc107; padding:0.8rem; border-radius:4px; }
.alert-err { background:#f8d7da; border-left:5px solid #dc3545; padding:0.8rem; border-radius:4px; }
</style>
"""


def inject_css() -> None:
    st.markdown(TABLET_CSS, unsafe_allow_html=True)


def hr() -> None:
    st.markdown('<hr class="section-hr">', unsafe_allow_html=True)


# ─── Shift selector / guard ─────────────────────────────────────────────────

def shift_selector_sidebar() -> None:
    """
    Shows an active-shift selector in the sidebar.
    Stores the chosen shift_id in st.session_state['ops_shift_id'].
    """
    with st.sidebar:
        st.markdown("### Turno activo")
        open_shifts = get_open_shifts()

        if not open_shifts:
            st.warning("Sin turno abierto")
            if st.button("➕ Abrir turno"):
                st.switch_page("pages/open_shift.py")
            st.session_state.pop("ops_shift_id", None)
            return

        options = {
            f"{r['shift_date']} {r['shift_name']} – {r['cashier_name']}": r["id"]
            for r in open_shifts
        }
        # Keep previously selected if still valid
        current = st.session_state.get("ops_shift_id")
        ids = list(options.values())
        default_idx = ids.index(current) if current in ids else 0

        chosen_label = st.selectbox(
            "Turno",
            list(options.keys()),
            index=default_idx,
            label_visibility="collapsed",
        )
        st.session_state["ops_shift_id"] = options[chosen_label]


def require_active_shift() -> int:
    """
    Returns the active shift_id from session state, or stops the page with a warning.
    """
    shift_id = st.session_state.get("ops_shift_id")
    if not shift_id:
        st.warning("⚠️ Selecciona o abre un turno desde la barra lateral.")
        st.stop()
    return shift_id


def shift_header(shift_id: int) -> None:
    """Small banner showing current shift info at top of page."""
    shift = get_shift(shift_id)
    if shift:
        st.caption(
            f"Turno: **{shift['shift_date']} {shift['shift_name']}**  •  "
            f"Cajero: **{shift['cashier_name']}**  •  "
            f"Verificador: **{shift['delivery_controller']}**"
        )
