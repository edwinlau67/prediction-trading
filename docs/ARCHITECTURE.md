# Architecture

## Overview

The Prediction Trading System is a Python-based platform that combines rule-based technical analysis, optional Claude AI prediction, backtesting, and live paper trading. It exposes three surfaces: a Streamlit web UI (`uv run streamlit run frontend/app.py`), a FastAPI REST API (`uv run uvicorn prediction_trading.api.main:app`), and a set of CLI entrypoints.

---

## Layer Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                              │
│  frontend/app.py (Streamlit)   stock-predictor   automated-trader│
│  scan-watchlist                prediction_trading/api/ (FastAPI) │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│          prediction_trading/system.py — PredictionTradingSystem  │
│   (façade: fetch / predict / backtest / save_report /            │
│    build_auto_trader)                                            │
└──┬────────────────┬─────────────────────┬────────────────────────┘
   │                │                     │
┌──▼──────────┐  ┌──▼───────────────┐  ┌──▼────────────────────────┐
│ PREDICTION  │  │    TRADING       │  │       BACKTEST            │
│             │  │                  │  │                           │
│ SignalScorer│  │ Portfolio        │  │ Backtester                │
│ AIPredictor │  │ RiskManager      │  │ (bar-by-bar, 200-bar      │
│ UnifiedPred.│  │ AutoTrader       │  │  warmup, stops/targets)   │
└──┬──────────┘  │ PaperBroker      │  └───────────────────────────┘
   │             │ StateStore       │
┌──▼──────────┐  └──────────────────┘
│  INDICATORS │
│             │
│ TechnicalIn.│◄── prediction_trading/data_fetcher.py (yfinance OHLCV + fundamentals)
│ SupportRes. │
└─────────────┘
        │
┌───────▼──────────────────────────────────────────────────────────┐
│                     REPORTING                                    │
│  PredictionChart   PredictionReportWriter   ChartBuilder         │
│  results/predict_*/  results/backtest_*/  results/live_*/        │
└──────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Prediction pipeline

```
DataFetcher.fetch(ticker)
  → MarketData {ohlcv, current_price, fundamentals}
  → TechnicalIndicators.compute_all(ohlcv)         # adds SMA, EMA, MACD, RSI, …
  → SignalScorer.score(df, weekly=, hourly_4h=)     # emits Factors, ScoredSignal
  → AIPredictor.predict(ticker)     [optional]      # Claude tool-use loop
  → UnifiedPredictor.predict(…)                     # weighted fusion
  → Prediction {direction, confidence, price_target, factors, …}
  → PredictionChart.render(…) + PredictionReportWriter.write(…)
```

### Backtesting pipeline

```
DataFetcher.fetch_history(ticker, start, end)
  → Backtester.run(ticker, ohlcv)
       for each bar (after 200-bar warmup):
         TechnicalIndicators.compute_all(ohlcv[:i])
         SignalScorer.score(df)
         RiskManager.evaluate(signal, portfolio, atr)
         PaperBroker.place_order / close_position
  → BacktestResult {stats, portfolio.equity_curve, closed_trades}
  → ChartBuilder.save_all + ReportWriter.write
```

### AutoTrader loop

```
AutoTrader.run(interval_seconds=300)
  for each cycle:
    for each ticker:
      DataFetcher.fetch(ticker)
      TechnicalIndicators.compute_all
      Portfolio.check exits (stop-loss / take-profit)
      SignalScorer.score
      RiskManager.evaluate → TradeProposal | None
      PaperBroker.place_order (unless dry_run)
      StateStore.save(portfolio)
```

---

## Component Descriptions

### `prediction_trading/system.py — PredictionTradingSystem`
The top-level façade. Reads `config/default.yaml`, instantiates all sub-components, and exposes a high-level API. Every CLI and UI page goes through this class.

### `prediction_trading/prediction/signal_scorer.py — SignalScorer`
Point-based rule engine. Nine indicator categories emit `Factor` objects (±1 to ±2 points each). Net points → direction + confidence (`min(1.0, |net| / confidence_scale)`). Multi-timeframe bonuses applied for weekly and 4H agreement. The `news`, `macro`, and `sector` categories are activated when the corresponding context objects (`NewsContext`, `MacroContext`, `SectorContext`) are passed to `score()`.

### `prediction_trading/prediction/ai_predictor.py — AIPredictor`
Claude tool-use loop. The model calls `stock_prediction` tool → local execution runs `DataFetcher.fetch(include_enriched=True)` and `SignalScorer` (with news/macro/sector contexts) → tool result includes optional `news`, `macro`, `sector` dicts → second API call returns a narrative (≤500 words). System prompt uses `cache_control: ephemeral` for prompt caching (~90% cost reduction on cache hits).

### `prediction_trading/prediction/predictor.py — UnifiedPredictor`
Fuses rule and AI signals: `blended = (1 - ai_weight) × rule_signed + ai_weight × ai_signed`. Falls back to rule-only when AI is disabled or unavailable.

### `prediction_trading/trading/risk_manager.py — RiskManager`
Sequential gate: min_confidence → max_positions → max_position_size → available_cash → daily_loss_cap → R:R ratio. Returns a `TradeProposal` or `None`.

### `prediction_trading/trading/broker.py — PaperBroker`
Simulated fills against `Portfolio`. Applies optional slippage in basis points. `RecordingBroker` is a thin test double.

### `prediction_trading/trading/portfolio.py — Portfolio`
Tracks open `Position` objects, closed `Trade` history, equity curve snapshots, and cash balance. `Portfolio.equity(prices)` marks all open positions to market.

### `prediction_trading/trading/state.py — StateStore`
JSON-backed persistence. `load_or_create()` restores the portfolio across restarts; `save()` serialises it after each cycle.

### `prediction_trading/backtest/backtester.py — Backtester`
Bar-by-bar simulation with 200-bar indicator warmup. Checks exits (stop/target) before scoring each bar to prevent look-ahead bias.

### `prediction_trading/data_fetcher.py — DataFetcher`
Thin wrapper around `yfinance`. Normalises MultiIndex columns, removes NaN rows, and returns `MarketData`. When `include_enriched=True`, also populates `MarketData.news_context` (`NewsContext`), `macro_context` (`MacroContext`), and `sector_context` (`SectorContext`) via three additional yfinance calls. Enriched fetching is only used by `AIPredictor`; the rule-based path uses the default `include_enriched=False`.

### `prediction_trading/scanner.py — WatchlistScanner`
`ThreadPoolExecutor`-based parallel screening. Reuses `SignalScorer` without charts or reporting for low-latency bulk scanning.

### Reporting (`prediction_trading/reporting/`)
- `PredictionChart`: Multi-panel matplotlib PNG — Price+Target, Confidence arc, Signal Factors, and optional category panels (MACD, RSI, Stochastic, Volume, Support, ATR, Fundamentals).
- `ChartBuilder`: Four backtest PNG charts (indicators, signals, performance, risk).
- `ReportWriter`: Orchestrates both flows, places output in `results/<prefix>_<timestamp>/`.

---

## Configuration Hierarchy

```
config/default.yaml          — system-wide defaults (read by _Config.load())
config/risk_profiles.yaml    — conservative / moderate / aggressive presets
config/indicators_config.yaml — per-indicator period/threshold reference
.env                          — ANTHROPIC_API_KEY (not committed)
```

Values in `default.yaml` can be overridden at `PredictionTradingSystem` instantiation via kwargs (`initial_capital=`, `enable_ai=`, etc.).

---

## Design Decisions

### Point-based scoring over weighted averages
Each rule emits an integer point value, making the score auditable — you can read exactly which factors drove the direction. The old weighted-component model is preserved as a `components` dict for backwards compatibility with the backtester.

### Factor as lingua franca
`Factor(category, name, direction, points, detail)` is the unit of information flowing between scoring, charts, and reports. Charts render factor bars; reports render factor lists; the AI prompt lists the top factors. The `news`, `macro`, and `sector` categories follow the same `Factor` pattern and appear in the same factor lists and bar charts as the technical categories.

### Enriched context only on the AI path
`DataFetcher.fetch(include_enriched=True)` makes three extra yfinance calls (news headlines, macro index symbols, sector ETF prices). This is called exclusively by `AIPredictor.predict()` so the rule-based scanner and backtester remain fast and offline-compatible.

### Prompt caching
`AIPredictor` pins the system prompt with `cache_control: ephemeral`. A typical run sends ~1 500 cached tokens + ~200 uncached, reducing cost by ~90% on repeated calls.

### Broker abstraction
`AutoTrader` only speaks to `BaseBroker`. Swapping to a live broker requires implementing three methods: `get_quote`, `place_order`, `close_position`.

### Streamlit threading model
`AutoTrader.run()` is blocking. The Trading page runs it in a daemon `threading.Thread`, communicating with the UI via a `queue.Queue` stored in `st.session_state`. Each render call drains the queue and then calls `st.rerun()` after a short sleep for live updates.

### No look-ahead in backtesting
`Backtester` computes indicators only on bars `0..i` at each step, then checks exits before scoring — mimicking real-world execution where you can only act on information available at the time.
