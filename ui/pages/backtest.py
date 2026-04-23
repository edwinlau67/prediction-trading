"""Backtest page — historical simulation with equity curve and trade log."""
from __future__ import annotations

from datetime import date

import streamlit as st

from ui.components import equity_chart, metric_card, trade_log_table
from ui.state import BT_OHLCV, BT_RESULT, BT_TICKER


def render() -> None:
    st.title("Backtest")
    st.caption("Simulate the trading strategy on historical OHLCV data.")

    # ── Inputs ────────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        ticker = st.text_input("Ticker", "AAPL").upper().strip()
    with col2:
        start = st.date_input("Start Date", value=date(2023, 1, 1))
    with col3:
        end = st.date_input("End Date", value=date(2024, 1, 1))

    col4, col5 = st.columns(2)
    with col4:
        capital = st.number_input(
            "Initial Capital ($)", 1_000.0, 10_000_000.0, 10_000.0, step=1_000.0,
        )
    with col5:
        commission = st.number_input(
            "Commission per Trade ($)", 0.0, 100.0, 1.0,
        )

    if st.button("Run Backtest", type="primary", disabled=not ticker):
        if end <= start:
            st.error("End date must be after start date.")
        else:
            with st.spinner(f"Backtesting {ticker} from {start} to {end}..."):
                _run_backtest(ticker, str(start), str(end), capital, commission)

    # ── Results ───────────────────────────────────────────────────────────────
    result = st.session_state.get(BT_RESULT)
    cached_ticker = st.session_state.get(BT_TICKER, "")

    if result is not None:
        if cached_ticker != ticker:
            st.info(f"Showing cached results for **{cached_ticker}**.")
        _show_results(result, capital)


def _run_backtest(
    ticker: str,
    start: str,
    end: str,
    capital: float,
    commission: float,
) -> None:
    try:
        from src.system import PredictionTradingSystem

        system = PredictionTradingSystem(ticker=ticker, initial_capital=capital)
        system.cfg.portfolio["commission_per_trade"] = commission
        result = system.backtest(start, end)

        st.session_state[BT_RESULT] = result
        st.session_state[BT_TICKER] = ticker
        st.session_state[BT_OHLCV] = system._market.ohlcv if system._market else None

    except Exception as exc:
        st.error(f"Backtest failed: {exc}")
        raise


def _show_results(result, initial_capital: float = 10_000.0) -> None:
    st.divider()
    st.subheader("Backtest Results")

    stats = result.summary() if hasattr(result, "summary") else getattr(result, "stats", {})
    portfolio = getattr(result, "portfolio", None)

    # KPI row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ret = stats.get("return_pct", 0.0)
        metric_card("Total Return", f"{ret:+.2f}%")
    with col2:
        dd = stats.get("max_drawdown_pct", 0.0)
        metric_card("Max Drawdown", f"{dd:.2f}%")
    with col3:
        wr = stats.get("win_rate_pct", 0.0)
        metric_card("Win Rate", f"{wr:.1f}%")
    with col4:
        pf = stats.get("profit_factor", None)
        metric_card("Profit Factor", f"{pf:.2f}" if pf else "N/A")

    # Additional stats row
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        metric_card("Total Trades", str(stats.get("total_trades", 0)))
    with col6:
        metric_card("Winning Trades", str(stats.get("winning_trades", 0)))
    with col7:
        metric_card("Losing Trades", str(stats.get("losing_trades", 0)))
    with col8:
        if portfolio:
            final_equity = portfolio.equity({})
            metric_card("Final Equity", f"${final_equity:,.2f}")

    # Equity curve
    if portfolio and portfolio.equity_curve:
        equity_chart(portfolio.equity_curve, initial_capital, title="Portfolio Equity Curve")

    # Trade log
    st.subheader("Trade Log")
    if portfolio:
        trade_log_table(portfolio.closed_trades)

    # Save report
    ticker = st.session_state.get(BT_TICKER, "")
    if ticker and st.button("Save Full Report"):
        try:
            from src.data_fetcher import MarketData
            from src.system import PredictionTradingSystem

            ohlcv = st.session_state.get(BT_OHLCV)
            system = PredictionTradingSystem(ticker=ticker, initial_capital=initial_capital)
            if ohlcv is not None:
                system._market = MarketData(
                    ticker=ticker, ohlcv=ohlcv,
                    current_price=float(ohlcv["Close"].iloc[-1]),
                )
            out_dir = system.save_report(result=result)
            st.success(f"Report saved: `{out_dir}`")
        except Exception as exc:
            st.error(f"Could not save report: {exc}")
