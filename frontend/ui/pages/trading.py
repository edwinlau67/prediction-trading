"""Trading page — start/stop AutoTrader with live portfolio monitoring."""
from __future__ import annotations

import queue
import threading
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from ui.components import equity_chart, metric_card
from ui.state import (
    TRADER_ERRORS,
    TRADER_INSTANCE,
    TRADER_QUEUE,
    TRADER_REPORTS,
    TRADER_RUNNING,
    TRADER_THREAD,
)


def render() -> None:
    st.markdown("## ⚡ Trading — AutoTrader")

    running = st.session_state.get(TRADER_RUNNING, False)

    if not running:
        _show_start_form()
    else:
        _show_running_dashboard()


def _show_start_form() -> None:
    st.markdown(
        '<div class="pt-card" style="border-left:3px solid #8b949e">'
        '<div class="pt-card-label">Status</div>'
        '<div style="color:#8b949e;font-weight:600">⏹ Stopped</div>'
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("trader_config"):
        col1, col2 = st.columns(2)
        with col1:
            raw = st.text_area("Tickers (one per line)", "AAPL\nMSFT\nNVDA", height=120)
            tickers = [t.strip().upper() for t in raw.splitlines() if t.strip()]
        with col2:
            interval = st.number_input("Cycle Interval (seconds)", 60, 3600, 300, step=60)
            dry_run = st.checkbox("Dry Run (signals only, no orders)", value=True)
            market_hours = st.checkbox("Enforce Market Hours", value=False)
            state_path = st.text_input("State File Path", "results/live/portfolio_state.json")

        st.caption(f"{len(tickers)} tickers selected")
        submitted = st.form_submit_button("▶ Start AutoTrader", type="primary")

    if submitted and tickers:
        _start_trader(tickers, interval, dry_run, market_hours, state_path)
        st.rerun()


def _show_running_dashboard() -> None:
    # Drain the queue
    q: queue.Queue = st.session_state.get(TRADER_QUEUE, queue.Queue())
    reports: list = st.session_state.get(TRADER_REPORTS) or []
    errors: list = st.session_state.get(TRADER_ERRORS) or []
    new_items = 0

    while not q.empty():
        try:
            item = q.get_nowait()
            new_items += 1
            if isinstance(item, Exception):
                errors.append(str(item))
            else:
                reports.append(item)
        except queue.Empty:
            break

    st.session_state[TRADER_REPORTS] = reports
    st.session_state[TRADER_ERRORS] = errors

    # Status + stop button
    col_status, col_stop = st.columns([4, 1])
    with col_status:
        st.markdown(
            '<div class="pt-card" style="border-left:3px solid #00d25b">'
            '<div class="pt-card-label">Status</div>'
            f'<div style="color:#00d25b;font-weight:600">🟢 Running — {len(reports)} cycles completed</div>'
            "</div>",
            unsafe_allow_html=True,
        )
    with col_stop:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⏹ Stop", type="secondary", use_container_width=True):
            st.session_state[TRADER_RUNNING] = False
            st.rerun()

    # Portfolio snapshot
    trader = st.session_state.get(TRADER_INSTANCE)
    if trader:
        portfolio = getattr(trader, "portfolio", None)
        broker = getattr(trader, "broker", None)

        if portfolio:
            prices = {}
            if broker:
                for t in getattr(portfolio, "positions", {}).keys():
                    try:
                        prices[t] = broker.get_quote(t)
                    except Exception:
                        pass

            equity = portfolio.equity(prices)
            initial = getattr(portfolio, "initial_capital", 0.0)
            ret_pct = (equity - initial) / initial * 100 if initial else 0.0
            sign = "+" if ret_pct >= 0 else ""

            c1, c2, c3 = st.columns(3)
            with c1:
                metric_card("Portfolio Value", f"${equity:,.2f}", f"{sign}{ret_pct:.2f}%")
            with c2:
                metric_card("Cash", f"${getattr(portfolio, 'cash', 0):,.2f}")
            with c3:
                metric_card("Open Positions", str(len(getattr(portfolio, "positions", {}))))

            curve = getattr(portfolio, "equity_curve", [])
            if curve:
                equity_chart(curve, initial, title="Live Equity Curve")

            positions = getattr(portfolio, "positions", {})
            if positions:
                st.markdown("#### Open Positions")
                rows = [{
                    "Ticker": t,
                    "Side": getattr(p, "side", "").upper(),
                    "Qty": getattr(p, "quantity", 0),
                    "Entry": f"${getattr(p, 'entry_price', 0):.2f}",
                    "Current": f"${prices.get(t, getattr(p, 'entry_price', 0)):.2f}",
                    "Unrealised": f"${p.unrealised(prices.get(t, getattr(p, 'entry_price', 0))):+.2f}"
                        if hasattr(p, "unrealised") else "—",
                    "Stop": f"${getattr(p, 'stop_loss', 0):.2f}",
                    "Target": f"${getattr(p, 'take_profit', 0):.2f}",
                } for t, p in positions.items()]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Last cycle summary
    if reports:
        last = reports[-1]
        finished = getattr(last, "finished_at", None)
        actions = getattr(last, "actions", [])
        errs = getattr(last, "errors", [])

        ts_str = finished.strftime("%H:%M:%S") if finished else "—"
        st.markdown(f"#### Last Cycle ({ts_str})")
        if actions:
            rows = [{
                "Ticker": getattr(a, "ticker", ""),
                "Action": getattr(a, "action", "").upper(),
                "Direction": getattr(a, "direction", ""),
                "Confidence": f"{getattr(a, 'confidence', 0) or 0:.1%}",
                "Price": f"${getattr(a, 'price', 0) or 0:.2f}",
                "Reason": getattr(a, "reason", ""),
            } for a in actions]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No actions taken this cycle.")

        if errs:
            with st.expander(f"Cycle errors ({len(errs)})"):
                for e in errs:
                    st.text(e)

    if errors:
        with st.expander(f"Error Log ({len(errors)} errors)", expanded=False):
            for e in errors[-20:]:
                st.text(e)

    # Auto-refresh: only rerun when trader is still running, avoid hard sleep
    if st.session_state.get(TRADER_RUNNING, False):
        st.markdown(
            '<meta http-equiv="refresh" content="10">',
            unsafe_allow_html=True,
        )


def _start_trader(
    tickers: list[str],
    interval: int,
    dry_run: bool,
    market_hours: bool,
    state_path: str,
) -> None:
    try:
        from prediction_trading.system import PredictionTradingSystem

        system = PredictionTradingSystem(ticker=tickers[0])
        Path(state_path).parent.mkdir(parents=True, exist_ok=True)
        trader = system.build_auto_trader(
            tickers=tickers,
            state_path=state_path,
            trade_log_path=str(Path(state_path).parent / "trades.csv"),
            dry_run=dry_run,
            enforce_market_hours=market_hours,
        )

        q: queue.Queue = queue.Queue()
        st.session_state[TRADER_INSTANCE] = trader
        st.session_state[TRADER_QUEUE] = q
        st.session_state[TRADER_REPORTS] = []
        st.session_state[TRADER_ERRORS] = []
        st.session_state[TRADER_RUNNING] = True

        thread = threading.Thread(
            target=_trader_loop,
            args=(trader, interval, q),
            daemon=True,
        )
        st.session_state[TRADER_THREAD] = thread
        thread.start()

    except Exception as exc:
        st.error(f"Could not start AutoTrader: {exc}")


def _trader_loop(trader, interval: int, q: queue.Queue) -> None:
    """Daemon thread: run one cycle, put result in queue, sleep, repeat."""
    while st.session_state.get(TRADER_RUNNING, False):
        try:
            report = trader.run_once()
            q.put(report)
        except Exception as exc:
            q.put(exc)
        time.sleep(interval)
