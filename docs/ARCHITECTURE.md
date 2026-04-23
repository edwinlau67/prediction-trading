# Architecture

## Overview

The Prediction Trading System is a Python-based platform that combines rule-based technical analysis, optional Claude AI prediction, backtesting, and live paper trading. It exposes two surfaces: a Streamlit web UI (`streamlit run app.py`) and a set of CLI entrypoints.

---

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                             │
│  app.py (Streamlit)    stock_predictor.py    automated_trader.py│
│  scan_watchlist.py                                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                  src/system.py — PredictionTradingSystem         │
│   (façade: fetch / predict / backtest / save_report /            │
│    build_auto_trader)                                            │
└──┬────────────────┬──────────────────┬──────────────────────────┘
   │                │                  │
┌──▼──────────┐  ┌──▼──────────────┐  ┌▼──────────────────────────┐
│ PREDICTION  │  │    TRADING       │  │       BACKTEST             │
│             │  │                  │  │                            │
│ SignalScorer│  │ Portfolio         │  │ Backtester                 │
│ AIPredictor │  │ RiskManager      │  │ (bar-by-bar, 200-bar       │
│ UnifiedPred.│  │ AutoTrader       │  │  warmup, stops/targets)    │
└──┬──────────┘  │ PaperBroker      │  └────────────────────────────┘
   │             │ StateStore       │
┌──▼──────────┐  └──────────────────┘
│  INDICATORS │
│             │
│ TechnicalIn.│◄── src/data_fetcher.py (yfinance OHLCV + fundamentals)
│ SupportRes. │
└─────────────┘
        │
┌───────▼────────────────────────────────────────────────────────┐
│                     REPORTING                                   │
│  PredictionChart   PredictionReportWriter   ChartBuilder        │
│  results/predict_*/  results/backtest_*/  results/live_*/       │
└────────────────────────────────────────────────────────────────┘
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

### `src/system.py — PredictionTradingSystem`
The top-level façade. Reads `config/default.yaml`, instantiates all sub-components, and exposes a high-level API. Every CLI and UI page goes through this class.

### `src/prediction/signal_scorer.py — SignalScorer`
Point-based rule engine. Six indicator categories emit `Factor` objects (±1 to ±2 points each). Net points → direction + confidence (`min(1.0, |net| / confidence_scale)`). Multi-timeframe bonuses applied for weekly and 4H agreement.

### `src/prediction/ai_predictor.py — AIPredictor`
Claude tool-use loop. The model calls `stock_prediction` tool → local execution runs `SignalScorer` → second API call returns a narrative. System prompt uses `cache_control: ephemeral` for prompt caching (~10% cost on cache hits).

### `src/prediction/predictor.py — UnifiedPredictor`
Fuses rule and AI signals: `blended = (1 - ai_weight) × rule_signed + ai_weight × ai_signed`. Falls back to rule-only when AI is disabled or unavailable.

### `src/trading/risk_manager.py — RiskManager`
Sequential gate: min_confidence → max_positions → max_position_size → available_cash → daily_loss_cap → R:R ratio. Returns a `TradeProposal` or `None`.

### `src/trading/broker.py — PaperBroker`
Simulated fills against `Portfolio`. Applies optional slippage in basis points. `RecordingBroker` is a thin test double.

### `src/trading/portfolio.py — Portfolio`
Tracks open `Position` objects, closed `Trade` history, equity curve snapshots, and cash balance. `Portfolio.equity(prices)` marks all open positions to market.

### `src/trading/state.py — StateStore`
JSON-backed persistence. `load_or_create()` restores the portfolio across restarts; `save()` serialises it after each cycle.

### `src/backtest/backtester.py — Backtester`
Bar-by-bar simulation with 200-bar indicator warmup. Checks exits (stop/target) before scoring each bar to prevent look-ahead bias.

### `src/data_fetcher.py — DataFetcher`
Thin wrapper around `yfinance`. Normalises MultiIndex columns, removes NaN rows, and returns `MarketData`.

### `src/scanner.py — WatchlistScanner`
`ThreadPoolExecutor`-based parallel screening. Reuses `SignalScorer` without charts or reporting for low-latency bulk scanning.

### Reporting (`src/reporting/`)
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
`Factor(category, name, direction, points, detail)` is the unit of information flowing between scoring, charts, and reports. Charts render factor bars; reports render factor lists; the AI prompt lists the top factors.

### Prompt caching
`AIPredictor` pins the system prompt with `cache_control: ephemeral`. A typical run sends ~1 500 cached tokens + ~200 uncached, reducing cost by ~90% on repeated calls.

### Broker abstraction
`AutoTrader` only speaks to `BaseBroker`. Swapping to a live broker requires implementing three methods: `get_quote`, `place_order`, `close_position`.

### Streamlit threading model
`AutoTrader.run()` is blocking. The Trading page runs it in a daemon `threading.Thread`, communicating with the UI via a `queue.Queue` stored in `st.session_state`. Each render call drains the queue and then calls `st.rerun()` after a short sleep for live updates.

### No look-ahead in backtesting
`Backtester` computes indicators only on bars `0..i` at each step, then checks exits before scoring — mimicking real-world execution where you can only act on information available at the time.
