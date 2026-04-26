"""Predict page — single-ticker prediction with optional AI and 4H confluence."""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from ui.components import candlestick_chart, prediction_card
from ui.state import (
    PREDICT_CHART_PATH, PREDICT_MACRO_CONTEXT, PREDICT_OHLCV,
    PREDICT_RESULT, PREDICT_TICKER,
)

_TIMEFRAMES = ["1d", "1w", "1m", "3m", "6m", "ytd", "1y", "2y", "5y"]
_ALL_CATEGORIES = ["trend", "momentum", "volatility", "volume", "support", "fundamental"]


def render() -> None:
    st.markdown("## 🔮 Predict")

    # ── Inputs ────────────────────────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        # Pre-fill from watchlist click
        prefill = st.session_state.get(PREDICT_TICKER, "AAPL")
        ticker = st.text_input(
            "Ticker Symbol", value=prefill,
            placeholder="e.g. AAPL, TSLA",
        ).upper().strip()
    with col2:
        timeframe = st.selectbox("Prediction Timeframe", _TIMEFRAMES, index=1)

    categories = st.multiselect(
        "Indicator Categories",
        _ALL_CATEGORIES,
        default=_ALL_CATEGORIES,
        help="Which rule categories to score. Affects factors, chart panels, and AI prompt.",
    )

    col3, col4, col5 = st.columns(3)
    with col3:
        enable_ai = st.toggle("Enable AI (Claude)", value=False)
    with col4:
        use_4h = st.toggle("4H Confluence", value=False,
                           help="Fetch 4-hour OHLCV and add confluence bonus.")
    with col5:
        save_report = st.checkbox("Save report to results/", value=False)

    run = st.button("▶ Run Prediction", type="primary", disabled=not ticker)

    if run and ticker:
        with st.spinner(f"Fetching data and running prediction for **{ticker}**..."):
            _run_prediction(ticker, timeframe, categories, enable_ai, use_4h, save_report)

    # ── Results ───────────────────────────────────────────────────────────────
    prediction = st.session_state.get(PREDICT_RESULT)
    cached_ticker = st.session_state.get(PREDICT_TICKER, "")
    ohlcv = st.session_state.get(PREDICT_OHLCV)

    if prediction is not None and cached_ticker == ticker:
        st.divider()

        tab_signal, tab_chart, tab_static = st.tabs(
            ["📊 Signal", "🕯️ Candlestick Chart", "📈 Analysis Chart"]
        )

        with tab_signal:
            prediction_card(prediction)
            _render_timing_card(getattr(prediction, "timing", None))
            _render_index_table(st.session_state.get(PREDICT_MACRO_CONTEXT))

        with tab_chart:
            if ohlcv is not None:
                entry = getattr(prediction, "current_price", None)
                # Get stop/target from the prediction's AI signal if available
                ai_sig = getattr(prediction, "ai_signal", None)
                stop_p = None
                target_p = getattr(prediction, "price_target", None)
                candlestick_chart(
                    ohlcv, title=f"{ticker} — Last 120 Bars",
                    entry_price=entry,
                    target_price=target_p,
                )
            else:
                st.info("OHLCV data not available for chart.")

        with tab_static:
            chart_path = st.session_state.get(PREDICT_CHART_PATH)
            if chart_path and Path(str(chart_path)).exists():
                st.image(str(chart_path), use_container_width=True)
            else:
                st.info("Run a prediction to generate the analysis chart.")

    elif prediction is not None and cached_ticker != ticker:
        st.info(f"Showing cached results for **{cached_ticker}**. Run prediction to refresh.")
        prediction_card(prediction)


def _run_prediction(
    ticker: str,
    timeframe: str,
    categories: list[str],
    enable_ai: bool,
    use_4h: bool,
    save_report: bool,
) -> None:
    try:
        from prediction_trading.data_fetcher import DataFetcher
        from prediction_trading.indicators import TechnicalIndicators
        from prediction_trading.prediction import SignalScorer
        from prediction_trading.reporting.prediction_chart import PredictionChart
        from prediction_trading.system import PredictionTradingSystem

        system = PredictionTradingSystem(
            ticker=ticker,
            enable_ai=enable_ai,
        )
        system.scorer = SignalScorer(
            categories=tuple(categories) if categories else None,
            multi_timeframe_bonus=int(system.cfg.signals.get("multi_timeframe_bonus", 2)),
            weights=system.cfg.signals.get("weights"),
        )
        if enable_ai and system.ai_predictor:
            system.ai_predictor.categories = tuple(categories) if categories else None
        from prediction_trading.prediction.predictor import UnifiedPredictor as UP
        system.predictor = UP(
            scorer=system.scorer,
            ai=system.ai_predictor,
            ai_enabled=enable_ai and system.ai_predictor is not None,
            ai_weight=system.cfg.signals.get("ai_weight", 0.5),
            min_confidence=system.cfg.signals.get("min_confidence", 0.40),
            timeframe=timeframe,
        )

        market = system.fetch()

        # Fetch macro context (index cross-reference + scoring enrichment)
        try:
            market.macro_context = system.data_fetcher.fetch_macro_context()
        except Exception:
            pass

        df_4h = None
        if use_4h:
            try:
                fetcher_4h = DataFetcher(interval="1h")
                ohlcv_4h = fetcher_4h.fetch_history(ticker, lookback_days=90)
                rules = {"Open": "first", "High": "max", "Low": "min",
                         "Close": "last", "Volume": "sum"}
                ohlcv_4h = ohlcv_4h.resample("4h").agg(rules).dropna()
                if not ohlcv_4h.empty:
                    df_4h = TechnicalIndicators.compute_all(ohlcv_4h)
            except Exception as exc:
                st.warning(f"Could not fetch 4H data: {exc}. Proceeding without it.")

        prediction = system.predict(market, hourly_4h=df_4h)

        tmp_dir = Path(tempfile.mkdtemp())
        chart_path = tmp_dir / f"{ticker}_{timeframe}.png"
        chart = PredictionChart()
        rendered = chart.render(
            prediction, market.ohlcv,
            categories=tuple(categories) if categories else None,
            timeframe=timeframe,
            out_path=chart_path,
            macro_context=market.macro_context,
        )

        st.session_state[PREDICT_RESULT] = prediction
        st.session_state[PREDICT_OHLCV] = market.ohlcv
        st.session_state[PREDICT_CHART_PATH] = rendered
        st.session_state[PREDICT_TICKER] = ticker
        st.session_state[PREDICT_MACRO_CONTEXT] = market.macro_context

        if save_report:
            system._market = market
            out_dir = system.save_report(prediction=prediction)
            st.success(f"Report saved: `{out_dir}`")

    except Exception as exc:
        st.error(f"Prediction failed: {exc}")


_TIMING_COLORS = {
    "BUY_NOW": "#00d25b",
    "BUY_ON_DIP": "#f0b429",
    "BUY_ON_BREAKOUT": "#58a6ff",
    "SELL_NOW": "#ff4b4b",
    "SELL_TRAILING": "#ff7f0e",
    "HOLD": "#8b949e",
    "WAIT": "#8b949e",
}
_TIMING_LABELS = {
    "BUY_NOW": "BUY NOW",
    "BUY_ON_DIP": "BUY ON DIP",
    "BUY_ON_BREAKOUT": "BREAKOUT ENTRY",
    "SELL_NOW": "SELL NOW",
    "SELL_TRAILING": "TRAILING STOP",
    "HOLD": "HOLD",
    "WAIT": "WAIT",
}


def _render_timing_card(timing) -> None:
    if timing is None:
        return
    action = getattr(timing, "action", "WAIT")
    reason = getattr(timing, "reason", "")
    color = _TIMING_COLORS.get(action, "#8b949e")
    label = _TIMING_LABELS.get(action, action)

    st.markdown(
        f'<div class="pt-timing-card" style="border-left:3px solid {color}">'
        f'<span class="pt-timing-label">Timing Recommendation</span><br/>'
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:3px;font-weight:700;font-size:0.85rem">{label}</span>'
        f'&nbsp;&nbsp;<span class="pt-timing-reason">{reason}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )

    entry = getattr(timing, "entry_price", None)
    stop = getattr(timing, "stop_loss", None)
    take_profit = getattr(timing, "take_profit", None)
    metrics = [(v, lbl) for v, lbl in [
        (entry, "Entry"), (stop, "Stop Loss"), (take_profit, "Take Profit")
    ] if v is not None]
    if metrics:
        cols = st.columns(len(metrics))
        for col, (val, lbl) in zip(cols, metrics):
            with col:
                st.metric(lbl, f"${val:,.2f}")


def _render_index_table(macro_ctx) -> None:
    if macro_ctx is None:
        return
    indexes = getattr(macro_ctx, "indexes", [])
    if not indexes:
        return

    dark = st.session_state.get("theme_dark", False)
    _TREND_COLOR = {
        "↑ Above SMA50": "#00d25b" if dark else "#1a7f37",
        "↓ Below SMA50": "#ff4b4b" if dark else "#cf222e",
    }
    _CHG_POS = "#00d25b" if dark else "#1a7f37"
    _CHG_NEG = "#ff4b4b" if dark else "#cf222e"
    _CHG_COLS = ["1D %", "5D %", "30D %"]

    rows = []
    for idx in indexes:
        price = idx.price
        trend = ("↑ Above SMA50" if idx.above_sma50 is True
                 else "↓ Below SMA50" if idx.above_sma50 is False else "—")
        rows.append({
            "Index": idx.name,
            "Price": f"${price:,.2f}" if price else "—",
            "1D %": f"{idx.change_1d_pct:+.2f}%" if idx.change_1d_pct is not None else "—",
            "5D %": f"{idx.change_5d_pct:+.2f}%" if idx.change_5d_pct is not None else "—",
            "30D %": f"{idx.change_30d_pct:+.2f}%" if idx.change_30d_pct is not None else "—",
            "Trend": trend,
        })

    headers = list(rows[0].keys()) if rows else []
    header_html = "".join(f"<th class='pt-idx-th'>{h}</th>" for h in headers)
    body_html = ""
    for row in rows:
        cells = ""
        for col, val in row.items():
            color = ""
            if col in _CHG_COLS and val not in ("—", ""):
                color = f"color:{_CHG_POS}" if val.startswith("+") else f"color:{_CHG_NEG}"
            elif col == "Trend":
                color = f"color:{_TREND_COLOR.get(val, '')}"
            cells += f"<td class='pt-idx-td' style='{color}'>{val}</td>"
        body_html += f"<tr>{cells}</tr>"

    st.markdown("#### Market Index Overview")
    st.markdown(
        f"<table style='width:100%;border-collapse:collapse;font-size:0.9rem'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{body_html}</tbody></table>",
        unsafe_allow_html=True,
    )
