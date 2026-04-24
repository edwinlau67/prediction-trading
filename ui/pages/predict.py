"""Predict page — single-ticker prediction with optional AI and 4H confluence."""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from ui.components import candlestick_chart, prediction_card
from ui.state import PREDICT_CHART_PATH, PREDICT_OHLCV, PREDICT_RESULT, PREDICT_TICKER

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
        from src.data_fetcher import DataFetcher
        from src.indicators import TechnicalIndicators
        from src.prediction import SignalScorer
        from src.reporting.prediction_chart import PredictionChart
        from src.system import PredictionTradingSystem

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
        from src.prediction.predictor import UnifiedPredictor as UP
        system.predictor = UP(
            scorer=system.scorer,
            ai=system.ai_predictor,
            ai_enabled=enable_ai and system.ai_predictor is not None,
            ai_weight=system.cfg.signals.get("ai_weight", 0.5),
            min_confidence=system.cfg.signals.get("min_confidence", 0.40),
            timeframe=timeframe,
        )

        market = system.fetch()

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
        )

        st.session_state[PREDICT_RESULT] = prediction
        st.session_state[PREDICT_OHLCV] = market.ohlcv
        st.session_state[PREDICT_CHART_PATH] = rendered
        st.session_state[PREDICT_TICKER] = ticker

        if save_report:
            system._market = market
            out_dir = system.save_report(prediction=prediction)
            st.success(f"Report saved: `{out_dir}`")

    except Exception as exc:
        st.error(f"Prediction failed: {exc}")
