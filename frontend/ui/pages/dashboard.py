"""Dashboard page — portfolio overview, equity curve, positions, recent trades."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from ui.components import equity_chart, metric_card, trade_log_table
from ui.state import TRADER_INSTANCE, TRADER_RUNNING


def render() -> None:
    portfolio = _get_portfolio()

    if portfolio is None:
        st.markdown("## Dashboard")
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
    equity_curve = getattr(portfolio, "equity_curve", [])
    positions = getattr(portfolio, "positions", {})

    daily_pnl = 0.0
    if len(equity_curve) >= 2:
        daily_pnl = equity_curve[-1][1] - equity_curve[-2][1]

    # ── Overview / Risk tabs ──────────────────────────────────────────────────
    tab_overview, tab_risk = st.tabs(["Overview", "Risk"])

    with tab_overview:
        # KPI row
        c1, c2, c3, c4 = st.columns(4)
        sign = "+" if ret_pct >= 0 else ""
        with c1:
            metric_card("Portfolio Value", f"${equity:,.2f}",
                        f"{sign}{ret_pct:.2f}%")
        with c2:
            metric_card("Cash Available", f"${cash:,.2f}")
        with c3:
            dpnl_sign = "+" if daily_pnl >= 0 else ""
            metric_card("Day P&L", f"${daily_pnl:+,.2f}",
                        f"{dpnl_sign}{daily_pnl / initial * 100:.2f}%" if initial else None)
        with c4:
            metric_card("Open Positions", f"{len(positions)} / {5}")

        # Equity curve
        if equity_curve:
            equity_chart(equity_curve, initial)
        else:
            st.info("No equity curve data yet. Run the AutoTrader or a Backtest.")

        # Open positions table
        st.markdown("#### Open Positions")
        if positions:
            rows = []
            for ticker, pos in positions.items():
                current = prices.get(ticker, getattr(pos, "entry_price", 0.0))
                unrealised = pos.unrealised(current) if hasattr(pos, "unrealised") else 0.0
                entry_p = getattr(pos, "entry_price", 0.0)
                ret_pos = (current - entry_p) / entry_p * 100 if entry_p else 0.0
                rows.append({
                    "Ticker": ticker,
                    "Side": getattr(pos, "side", "").upper(),
                    "Qty": getattr(pos, "quantity", 0),
                    "Entry": f"${entry_p:.2f}",
                    "Current": f"${current:.2f}",
                    "Unrealised P&L": f"${unrealised:+,.2f}",
                    "Return %": f"{ret_pos:+.2f}%",
                    "Stop": f"${getattr(pos, 'stop_loss', 0):.2f}",
                    "Target": f"${getattr(pos, 'take_profit', 0):.2f}",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No open positions.")

        # Recent trades
        st.markdown("#### Recent Trades")
        trade_log_table(trades[-20:] if trades else [])

    with tab_risk:
        _render_risk_tab(portfolio, prices, equity, initial)

    # Auto-refresh without blocking sleep
    running = st.session_state.get(TRADER_RUNNING, False)
    if running:
        st.caption("🟢 AutoTrader running — page refreshes automatically.")
        # Use fragment-safe refresh: schedule via meta tag
        st.markdown(
            '<meta http-equiv="refresh" content="15">',
            unsafe_allow_html=True,
        )


def _render_risk_tab(portfolio, prices: dict, equity: float, initial: float) -> None:
    trades = getattr(portfolio, "closed_trades", [])
    equity_curve = getattr(portfolio, "equity_curve", [])
    positions = getattr(portfolio, "positions", {})
    max_dd = getattr(portfolio, "max_drawdown", 0.0)
    win_rate = getattr(portfolio, "win_rate", 0.0)

    wins = [t for t in trades if getattr(t, "is_win", False)]
    losses = [t for t in trades if not getattr(t, "is_win", True)]
    gross_profit = sum(getattr(t, "pnl", 0) for t in wins)
    gross_loss = abs(sum(getattr(t, "pnl", 0) for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

    # Day P&L vs cap
    daily_pnl = 0.0
    if len(equity_curve) >= 2:
        daily_pnl = equity_curve[-1][1] - equity_curve[-2][1]
    daily_loss_cap_pct = 0.02
    daily_loss_pct = abs(min(0.0, daily_pnl)) / initial * 100 if initial else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Max Drawdown", f"{max_dd:.2f}%")
    with c2:
        metric_card("Win Rate", f"{win_rate:.1f}%")
    with c3:
        metric_card("Profit Factor", f"{profit_factor:.2f}" if profit_factor else "N/A")
    with c4:
        metric_card("Total Trades", str(len(trades)))

    # Daily loss progress bar
    st.markdown("#### Daily Loss vs Cap (2%)")
    cap_pct = min(1.0, daily_loss_pct / (daily_loss_cap_pct * 100))
    bar_color = "#ff4b4b" if cap_pct >= 0.5 else "#f0b429" if cap_pct >= 0.25 else "#00d25b"
    st.markdown(
        f'<div style="background:#21262d;border-radius:4px;height:10px;margin-bottom:6px">'
        f'<div style="background:{bar_color};width:{cap_pct*100:.1f}%;height:10px;border-radius:4px"></div>'
        f"</div>"
        f'<div style="color:#8b949e;font-size:0.8rem">{daily_loss_pct:.2f}% of {daily_loss_cap_pct*100:.0f}% daily limit used</div>',
        unsafe_allow_html=True,
    )

    # Position concentration
    if positions:
        st.markdown("#### Position Concentration")
        import plotly.graph_objects as go
        tickers = list(positions.keys())
        vals = []
        for t in tickers:
            pos = positions[t]
            px = prices.get(t, getattr(pos, "entry_price", 0))
            vals.append(pos.unrealised(px) + getattr(pos, "entry_price", 0) * getattr(pos, "quantity", 0))
        total = sum(vals) or 1
        pcts = [v / total * 100 for v in vals]
        fig = go.Figure(go.Bar(
            x=tickers, y=pcts,
            marker_color="#58a6ff",
            text=[f"{p:.1f}%" for p in pcts],
            textposition="outside",
        ))
        fig.update_layout(
            template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
            height=220, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(title="% of Portfolio", gridcolor="#21262d"),
            font=dict(color="#c9d1d9"),
        )
        st.plotly_chart(fig, use_container_width=True)


def _get_portfolio():
    trader = st.session_state.get(TRADER_INSTANCE)
    if trader is not None:
        return getattr(trader, "portfolio", None)

    state_path = Path("results/live/portfolio_state.json")
    if state_path.exists():
        try:
            from prediction_trading.trading.state import StateStore
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
