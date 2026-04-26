"""Streamlit web UI for the Prediction Trading System.

Launch with:
    streamlit run app.py
"""
import streamlit as st

from ui.pages import backtest, dashboard, portfolio_builder, predict, scanner, settings, trading
from ui.pages import alerts as alerts_page
from ui.state import CURRENT_PAGE, init_session_state
from ui.theme import inject_theme
from ui.watchlist import render_sidebar

st.set_page_config(
    page_title="Prediction Trading",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state()

# ── Theme selection (persists in session state, default light) ────────────────
if "theme_dark" not in st.session_state:
    st.session_state["theme_dark"] = False

inject_theme(dark=st.session_state["theme_dark"])
render_sidebar()

# ── Top navigation ────────────────────────────────────────────────────────────
NAV_ITEMS = [
    ("📊", "Dashboard"),
    ("🔮", "Predict"),
    ("🔍", "Scanner"),
    ("📅", "Backtest"),
    ("⚡", "Trading"),
    ("🧱", "Portfolio Builder"),
    ("🔔", "Alerts"),
    ("⚙️", "Settings"),
]

PAGE_MODULES = {
    "Dashboard": dashboard,
    "Predict": predict,
    "Scanner": scanner,
    "Backtest": backtest,
    "Trading": trading,
    "Portfolio Builder": portfolio_builder,
    "Alerts": alerts_page,
    "Settings": settings,
}

# Header with branding + theme toggle
hdr_logo, hdr_spacer, hdr_theme = st.columns([4, 6, 2])
with hdr_logo:
    st.markdown(
        '<div class="pt-header"><span class="pt-logo">📈 Prediction Trading</span></div>',
        unsafe_allow_html=True,
    )
with hdr_theme:
    theme_label = "🌙 Dark" if not st.session_state["theme_dark"] else "☀️ Light"
    if st.button(theme_label, key="theme_toggle", use_container_width=True):
        st.session_state["theme_dark"] = not st.session_state["theme_dark"]
        st.rerun()

cols = st.columns(len(NAV_ITEMS))
current = st.session_state.get(CURRENT_PAGE, "Dashboard")
for col, (icon, label) in zip(cols, NAV_ITEMS):
    with col:
        is_active = current == label
        btn_class = "nav-btn nav-btn-active" if is_active else "nav-btn"
        if st.button(
            f"{icon} {label}",
            key=f"nav_{label}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state[CURRENT_PAGE] = label
            st.rerun()

st.markdown('<div class="pt-nav-divider"></div>', unsafe_allow_html=True)

PAGE_MODULES[current].render()
