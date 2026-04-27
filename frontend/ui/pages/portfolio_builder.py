"""Portfolio Builder page — ETF metadata, correlation analysis, and combination recommendations."""
from __future__ import annotations

import sys
import os

import streamlit as st
import pandas as pd

# Ensure backend package is importable from the frontend working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../backend/src"))


_DEFAULT_TICKERS = "SPY\nQQQ\nXLK\nBND\nGLD"


def render() -> None:
    st.markdown("## 🧱 Portfolio Builder")
    st.caption(
        "Analyze a mix of stocks and ETFs: correlation heatmap, sector exposure, "
        "and diversification recommendations.  ·  Data: **yfinance**  ·  Reference: **ETF catalogue (built-in)**"
    )

    col_input, col_btn = st.columns([3, 1])
    with col_input:
        raw = st.text_area(
            "Tickers (one per line)",
            value=st.session_state.get("pb_tickers", _DEFAULT_TICKERS),
            height=130,
            key="pb_ticker_input",
        )
    with col_btn:
        st.write("")  # spacing
        st.write("")
        analyze = st.button("Analyze", type="primary", use_container_width=True)
        lookback = st.number_input(
            "Lookback (days)", min_value=30, max_value=1260, value=252, step=21,
        )

    tickers = [t.strip().upper() for t in raw.splitlines() if t.strip()]

    if not tickers:
        st.info("Enter at least one ticker above and click Analyze.")
        return

    if analyze or st.session_state.get("pb_last_tickers") == tickers:
        st.session_state["pb_tickers"] = raw
        st.session_state["pb_last_tickers"] = tickers
        _run_analysis(tickers, lookback_days=lookback)


def _run_analysis(tickers: list[str], lookback_days: int) -> None:
    try:
        from prediction_trading.etf import ETFAnalyzer
    except ImportError as exc:
        st.error(f"Could not import ETFAnalyzer: {exc}")
        return

    analyzer = ETFAnalyzer()

    with st.spinner("Fetching data and computing analysis…"):
        try:
            analysis = analyzer.analyze_portfolio(tickers, lookback_days=lookback_days)
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
            return

    # ── ETF info cards ─────────────────────────────────────────────────────────
    st.subheader("Holdings")
    cols = st.columns(min(len(analysis.etf_infos), 4))
    for i, info in enumerate(analysis.etf_infos):
        with cols[i % len(cols)]:
            badge = "🏷️ ETF" if info.is_etf else "📈 Stock"
            er = f"{info.expense_ratio:.2f}% ER" if info.expense_ratio is not None else ""
            st.metric(label=f"{info.ticker}  {badge}", value=info.name[:28] or info.ticker)
            st.caption(f"{info.category}\n{er}")

    st.divider()

    # ── Diversification score ──────────────────────────────────────────────────
    score = analysis.diversification_score
    color = "green" if score >= 0.5 else ("orange" if score >= 0.25 else "red")
    st.subheader("Diversification Score")
    st.markdown(
        f"<span style='font-size:2rem; font-weight:bold; color:{color}'>"
        f"{score:.2f} / 1.00</span>",
        unsafe_allow_html=True,
    )
    st.caption("Higher = lower average pairwise correlation = better diversification.")

    st.divider()

    # ── Correlation heatmap ────────────────────────────────────────────────────
    if not analysis.correlation_matrix.empty:
        st.subheader("Correlation Matrix")

        def _color_corr(val):
            if pd.isna(val):
                return ""
            if val >= 0.85:
                return "background-color: #ff4d4d; color: white"
            if val >= 0.60:
                return "background-color: #ffb347"
            if val >= 0.30:
                return "background-color: #fffacd"
            if val < 0.0:
                return "background-color: #add8e6"
            return "background-color: #d4edda"

        html_table = (
            analysis.correlation_matrix
            .round(2)
            .style
            .map(_color_corr)
            .format("{:.2f}")
            .to_html()
        )
        st.markdown(html_table, unsafe_allow_html=True)

    st.divider()

    # ── Sector exposure ────────────────────────────────────────────────────────
    if analysis.sector_exposure:
        st.subheader("Sector Exposure (Equal-Weighted)")
        exposure_df = (
            pd.Series(analysis.sector_exposure, name="Weight")
            .sort_values(ascending=False)
            .rename_axis("Sector")
            .reset_index()
        )
        exposure_df["Weight %"] = (exposure_df["Weight"] * 100).round(1)
        st.bar_chart(exposure_df.set_index("Sector")["Weight %"])

    st.divider()

    # ── Recommendations ────────────────────────────────────────────────────────
    st.subheader("Recommendations")
    for rec in analysis.recommendations:
        if "Low diversification" in rec or "highly correlated" in rec.lower():
            st.warning(rec)
        elif "high expense" in rec.lower() or "High correlation" in rec:
            st.warning(rec)
        else:
            st.info(rec)
