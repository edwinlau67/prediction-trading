"""Streamlit web UI for the Prediction Trading System.

Launch with:
    streamlit run app.py
"""
import streamlit as st

from ui.pages import backtest, dashboard, predict, scanner, settings, trading
from ui.state import init_session_state

st.set_page_config(
    page_title="Prediction Trading System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

PAGES = {
    "Dashboard": dashboard,
    "Predict": predict,
    "Scanner": scanner,
    "Backtest": backtest,
    "Trading": trading,
    "Settings": settings,
}

with st.sidebar:
    st.title("📈 Prediction Trading")
    st.caption("AI-powered stock analysis & automated trading")
    st.divider()
    selection = st.radio(
        "Navigate",
        list(PAGES.keys()),
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("v1.0 · [GitHub](https://github.com/edwinlau67) · [Docs](docs/ARCHITECTURE.md)")

PAGES[selection].render()
