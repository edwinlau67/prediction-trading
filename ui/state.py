"""Session state key constants and initialiser for the Streamlit UI."""
from __future__ import annotations

import queue

import streamlit as st

# Predict page
PREDICT_RESULT = "predict_result"
PREDICT_OHLCV = "predict_ohlcv"
PREDICT_CHART_PATH = "predict_chart_path"
PREDICT_TICKER = "predict_ticker"

# Backtest page
BT_RESULT = "bt_result"
BT_TICKER = "bt_ticker"
BT_OHLCV = "bt_ohlcv"

# Scanner page
SCAN_RESULTS = "scan_results"

# Trading page
TRADER_RUNNING = "trader_running"
TRADER_INSTANCE = "trader_instance"
TRADER_THREAD = "trader_thread"
TRADER_QUEUE = "trader_queue"
TRADER_REPORTS = "trader_reports"
TRADER_ERRORS = "trader_errors"

# Settings / shared
ACTIVE_PROFILE = "active_profile"
SETTINGS_DIRTY = "settings_dirty"

_DEFAULTS: dict = {
    PREDICT_RESULT: None,
    PREDICT_OHLCV: None,
    PREDICT_CHART_PATH: None,
    PREDICT_TICKER: "",
    BT_RESULT: None,
    BT_TICKER: "",
    BT_OHLCV: None,
    SCAN_RESULTS: None,
    TRADER_RUNNING: False,
    TRADER_INSTANCE: None,
    TRADER_THREAD: None,
    TRADER_REPORTS: None,  # will be set to list on start
    TRADER_ERRORS: None,   # will be set to list on start
    ACTIVE_PROFILE: "moderate",
    SETTINGS_DIRTY: False,
}


def init_session_state() -> None:
    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
    # TRADER_QUEUE must be a real Queue object
    if TRADER_QUEUE not in st.session_state:
        st.session_state[TRADER_QUEUE] = queue.Queue()
