"""Persistent watchlist sidebar with live price badges."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from ui.state import CURRENT_PAGE, PREDICT_TICKER, WATCHLIST_TICKERS

_WATCHLIST_FILE = Path("watchlist.json")


def _load_watchlist() -> list[str]:
    if _WATCHLIST_FILE.exists():
        try:
            data = json.loads(_WATCHLIST_FILE.read_text())
            if isinstance(data, list):
                return [str(t).upper().strip() for t in data if t]
        except Exception:
            pass
    return list(st.session_state.get(WATCHLIST_TICKERS, []))


def _save_watchlist(tickers: list[str]) -> None:
    try:
        _WATCHLIST_FILE.write_text(json.dumps(tickers))
    except Exception:
        pass


def _get_price(ticker: str) -> float | None:
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).fast_info
        return float(info.last_price or 0) or None
    except Exception:
        return None


def render_sidebar() -> None:
    """Render the watchlist in the Streamlit sidebar."""
    tickers = _load_watchlist()

    with st.sidebar:
        st.markdown(
            '<div style="font-size:0.75rem;color:#8b949e;text-transform:uppercase;'
            'letter-spacing:0.6px;margin-bottom:0.5rem">Watchlist</div>',
            unsafe_allow_html=True,
        )

        # Add ticker input
        col_in, col_add = st.columns([3, 1])
        with col_in:
            new_ticker = st.text_input(
                "Add ticker", key="wl_add_input", label_visibility="collapsed",
                placeholder="e.g. AAPL",
            ).upper().strip()
        with col_add:
            if st.button("＋", key="wl_add_btn", use_container_width=True) and new_ticker:
                if new_ticker not in tickers:
                    tickers.append(new_ticker)
                    _save_watchlist(tickers)
                    st.session_state[WATCHLIST_TICKERS] = tickers
                    st.rerun()

        st.markdown("---")

        # Render each ticker with remove button
        for ticker in list(tickers):
            col_ticker, col_rm = st.columns([4, 1])
            with col_ticker:
                if st.button(ticker, key=f"wl_{ticker}", use_container_width=True,
                             type="secondary"):
                    # Navigate to Predict page with this ticker pre-filled
                    st.session_state[PREDICT_TICKER] = ticker
                    st.session_state[CURRENT_PAGE] = "Predict"
                    st.rerun()
            with col_rm:
                if st.button("✕", key=f"wl_rm_{ticker}", use_container_width=True):
                    tickers.remove(ticker)
                    _save_watchlist(tickers)
                    st.session_state[WATCHLIST_TICKERS] = tickers
                    st.rerun()

        if not tickers:
            st.caption("No tickers in watchlist.")

        st.session_state[WATCHLIST_TICKERS] = tickers
