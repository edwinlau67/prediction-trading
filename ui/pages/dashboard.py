"""Dashboard page — portfolio overview, equity curve, positions, recent trades."""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st

from ui.components import equity_chart, metric_card, trade_log_table
from ui.state import TRADER_INSTANCE, TRADER_RUNNING


def render() -> None:
    st.title("Dashboard")

    portfolio = _get_portfolio()

    if portfolio is None:
        st.info(
            "No portfolio loaded. Start the **AutoTrader** on the Trading page or run a "
            "**Backtest** to see portfolio data here."
        )
        _show_state_file_loader()
        return

    prices = _get_prices(portfolio)
    equity = portfolio.equity(prices)
    initial = getattr(portfolio, "initial_capital", 0.0)
    ret_pct = (equity - initial) / initial * 100 if initial else 0.0
    cash = getattr(portfolio, "cash", 0.0)
    trades = getattr(portfolio, "closed_trades", [])

    # Daily P&L: difference between equity today and yesterday's mark
    equity_curve = getattr(portfolio, "equity_curve", [])
    daily_pnl = 0.0
    if len(equity_curve) >= 2:
        daily_pnl = equity_curve[-1][1] - equity_curve[-2][1]

    # ── KPI row ───────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Portfolio Equity", f"${equity:,.2f}")
    with col2:
        metric_card("Cash", f"${cash:,.2f}")
    with col3:
        metric_card("Total Return", f"{ret_pct:+.2f}%")
    with col4:
        metric_card("Daily P&L", f"${daily_pnl:+.2f}")

    # ── Equity curve ──────────────────────────────────────────────────────────
    if equity_curve:
        equity_chart(equity_curve, initial)
    else:
        st.info("No equity curve data yet.")

    # ── Open positions ────────────────────────────────────────────────────────
    st.subheader("Open Positions")
    positions = getattr(portfolio, "positions", {})
    if positions:
        rows = []
        for ticker, pos in positions.items():
            current = prices.get(ticker, getattr(pos, "entry_price", 0.0))
            unrealised = pos.unrealised(current) if hasattr(pos, "unrealised") else 0.0
            rows.append({
                "Ticker": ticker,
                "Side": getattr(pos, "side", ""),
                "Qty": getattr(pos, "quantity", 0),
                "Entry": f"${getattr(pos, 'entry_price', 0):.2f}",
                "Current": f"${current:.2f}",
                "Unrealised P&L": f"${unrealised:+.2f}",
                "Stop": f"${getattr(pos, 'stop_loss', 0):.2f}",
                "Target": f"${getattr(pos, 'take_profit', 0):.2f}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No open positions.")

    # ── Recent trades ─────────────────────────────────────────────────────────
    st.subheader("Recent Trades (last 20)")
    trade_log_table(trades[-20:] if trades else [])

    # ── Auto-refresh ──────────────────────────────────────────────────────────
    running = st.session_state.get(TRADER_RUNNING, False)
    if running:
        st.caption("Auto-refreshing every 15 seconds while trader is running.")
        time.sleep(15)
        st.rerun()


def _get_portfolio():
    # Prefer live trader portfolio
    trader = st.session_state.get(TRADER_INSTANCE)
    if trader is not None:
        return getattr(trader, "portfolio", None)

    # Fall back to state file
    state_path = Path("results/live/portfolio_state.json")
    if state_path.exists():
        try:
            from src.trading.state import StateStore
            store = StateStore(state_path)
            return store.load_or_create(initial_capital=10_000.0, commission_per_trade=1.0)
        except Exception:
            pass

    return None


def _get_prices(portfolio) -> dict[str, float]:
    trader = st.session_state.get(TRADER_INSTANCE)
    if trader is None:
        return {}
    broker = getattr(trader, "broker", None)
    if broker is None:
        return {}
    prices = {}
    for ticker in getattr(portfolio, "positions", {}).keys():
        try:
            prices[ticker] = broker.get_quote(ticker)
        except Exception:
            pass
    return prices


def _show_state_file_loader() -> None:
    st.caption("Or load an existing portfolio state file:")
    uploaded = st.file_uploader("Upload portfolio_state.json", type=["json"])
    if uploaded:
        import json
        try:
            data = json.load(uploaded)
            st.json(data)
        except Exception as exc:
            st.error(f"Could not read file: {exc}")
