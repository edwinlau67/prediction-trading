"""Alerts Manager page — price/confidence/P&L trigger management."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from ui.state import ALERTS_LIST, ALERTS_TRIGGERED

_ALERTS_FILE = Path("alerts.json")
_TRIGGER_TYPES = [
    "Price above",
    "Price below",
    "Confidence ≥",
    "Daily P&L ≥",
    "Daily P&L ≤",
]


def _load_alerts() -> tuple[list[dict], list[dict]]:
    if _ALERTS_FILE.exists():
        try:
            data = json.loads(_ALERTS_FILE.read_text())
            return data.get("active", []), data.get("triggered", [])
        except Exception:
            pass
    return (
        list(st.session_state.get(ALERTS_LIST, [])),
        list(st.session_state.get(ALERTS_TRIGGERED, [])),
    )


def _save_alerts(active: list[dict], triggered: list[dict]) -> None:
    try:
        _ALERTS_FILE.write_text(json.dumps({"active": active, "triggered": triggered}))
    except Exception:
        pass


def render() -> None:
    st.markdown("## 🔔 Alerts Manager")

    active, triggered = _load_alerts()

    tab_active, tab_create, tab_log = st.tabs(["Active Alerts", "Create Alert", "Triggered Log"])

    with tab_active:
        if not active:
            st.info("No active alerts. Create one in the **Create Alert** tab.")
        else:
            st.markdown(f"**{len(active)} active alert(s)**")
            for idx, alert in enumerate(active):
                col_info, col_del = st.columns([5, 1])
                with col_info:
                    ticker = alert.get("ticker", "")
                    ttype = alert.get("type", "")
                    value = alert.get("value", "")
                    created = alert.get("created", "")
                    color = "#00d25b" if "above" in ttype or "≥" in ttype else "#ff4b4b"
                    st.markdown(
                        f'<div class="pt-card" style="border-left:3px solid {color}">'
                        f'<div style="display:flex;justify-content:space-between">'
                        f'<span style="font-weight:700;color:#e6edf3">{ticker}</span>'
                        f'<span style="color:#8b949e;font-size:0.8rem">{created}</span>'
                        f"</div>"
                        f'<div style="color:{color};font-size:0.9rem">{ttype} <strong>{value}</strong></div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_del:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("✕", key=f"del_alert_{idx}", use_container_width=True):
                        active.pop(idx)
                        _save_alerts(active, triggered)
                        st.session_state[ALERTS_LIST] = active
                        st.rerun()

        # Check alerts against current prices
        if active and st.button("🔄 Check Alerts Now", type="secondary"):
            _check_alerts(active, triggered)
            st.session_state[ALERTS_LIST] = active
            st.session_state[ALERTS_TRIGGERED] = triggered
            _save_alerts(active, triggered)
            st.rerun()

    with tab_create:
        st.markdown("#### New Alert")
        col1, col2, col3 = st.columns(3)
        with col1:
            new_ticker = st.text_input("Ticker", "AAPL", key="alert_ticker").upper().strip()
        with col2:
            new_type = st.selectbox("Trigger Type", _TRIGGER_TYPES, key="alert_type")
        with col3:
            new_value = st.number_input(
                "Value", value=150.0, key="alert_value",
                help="Price in $ for price triggers; 0–100 for confidence/P&L %",
            )

        if st.button("➕ Create Alert", type="primary", disabled=not new_ticker):
            alert = {
                "ticker": new_ticker,
                "type": new_type,
                "value": new_value,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "active": True,
            }
            active.append(alert)
            _save_alerts(active, triggered)
            st.session_state[ALERTS_LIST] = active
            st.success(f"Alert created: **{new_ticker}** — {new_type} {new_value}")
            st.rerun()

    with tab_log:
        if not triggered:
            st.info("No alerts have been triggered yet.")
        else:
            st.markdown(f"**{len(triggered)} triggered alert(s)**")
            for entry in reversed(triggered[-50:]):
                color = "#00d25b" if "above" in entry.get("type", "") else "#ff4b4b"
                st.markdown(
                    f'<div class="pt-card">'
                    f'<div style="display:flex;justify-content:space-between">'
                    f'<span style="font-weight:700;color:#e6edf3">{entry.get("ticker","")}</span>'
                    f'<span style="color:#8b949e;font-size:0.8rem">{entry.get("fired_at","")}</span>'
                    f"</div>"
                    f'<div style="color:{color};font-size:0.9rem">'
                    f'{entry.get("type","")} {entry.get("value","")} — '
                    f'actual: <strong>{entry.get("actual","")}</strong>'
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

            if st.button("🗑 Clear Log"):
                triggered.clear()
                _save_alerts(active, triggered)
                st.session_state[ALERTS_TRIGGERED] = []
                st.rerun()


def _check_alerts(active: list[dict], triggered: list[dict]) -> None:
    """Check each active alert against the latest price via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        st.warning("yfinance not available.")
        return

    fired_any = False
    for alert in list(active):
        ticker = alert.get("ticker", "")
        ttype = alert.get("type", "")
        threshold = float(alert.get("value", 0))

        try:
            info = yf.Ticker(ticker).fast_info
            price = float(info.last_price or 0)
        except Exception:
            continue

        fired = False
        if ttype == "Price above" and price > threshold:
            fired = True
        elif ttype == "Price below" and price < threshold:
            fired = True

        if fired:
            entry = {
                **alert,
                "fired_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "actual": f"${price:.2f}",
            }
            triggered.append(entry)
            active.remove(alert)
            fired_any = True
            st.toast(f"🔔 Alert fired: {ticker} — {ttype} {threshold} (actual ${price:.2f})")

    if not fired_any:
        st.info("No alerts triggered.")
