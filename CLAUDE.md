# CLAUDE.md

We're building the app described in @DESIGN.md. Read that file for general architectural tasks or to double-check the exact database structure, tech stack or application architecture.

Keep your replies extremely concise and focus on conveying the key information. No unnecessary fluff, no long code snippets.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add ANTHROPIC_API_KEY=sk-ant-... to enable AI
```

## Common commands

```bash
# Predict (rule-based, no API key needed)
python stock_predictor.py --tickers AAPL --no-ai

# Predict with Claude AI
python stock_predictor.py --tickers AAPL TSLA --timeframe 1m

# Filter indicator categories
python stock_predictor.py --tickers NVDA --indicators trend momentum

# Automated paper trading (one cycle, dry run)
python automated_trader.py --tickers AAPL TSLA --dry-run --once

# Continuous paper trading every 5 min, market hours only
python automated_trader.py --tickers AAPL --interval 300 --market-hours

# Launch Streamlit web UI
streamlit run app.py

# Scan watchlist (bulk signal scoring)
python scan_watchlist.py --tickers AAPL TSLA NVDA

# Run all tests (offline — no API key required)
pytest tests/ -v

# Run a single test file
pytest tests/test_signal_scorer.py -v
```

## Architecture

The system has four layers, wired together by `src/system.py:PredictionTradingSystem` (the primary entry point for Python API usage):

```
CLI entrypoints (stock_predictor.py, automated_trader.py, scan_watchlist.py)
Web UI          (streamlit run app.py → ui/ — 7 pages)
        │
src/system.py — PredictionTradingSystem (facade)
        │
src/prediction/     ← scoring + AI fusion
src/reporting/      ← chart + markdown output
        │
src/trading/        ← Portfolio, RiskManager, AutoTrader, PaperBroker
src/backtest/       ← bar-by-bar Backtester
        │
src/indicators/     ← TechnicalIndicators, SupportResistance
src/data_fetcher.py ← yfinance OHLCV + fundamentals
ui/                 ← Streamlit web app (Dashboard, Predict, Scanner, Backtest, Trading, Alerts, Settings)
```

### Prediction pipeline

1. `SignalScorer` emits `Factor(category, name, direction, points, detail)` objects for each active indicator category. Net points → direction + confidence (`min(1.0, abs(points)/10)`).
2. `AIPredictor` uses Claude tool-use: the model calls the `stock_prediction` tool → local execution fetches data and runs `SignalScorer` → second API call returns a narrative. The system prompt carries `cache_control: {type: "ephemeral"}` for prompt caching.
3. `UnifiedPredictor` blends: `(1 - ai_weight) * rule_signed + ai_weight * ai_signed`. Default `ai_weight = 0.5` from `config/default.yaml`. Falls back to rule-only when AI is disabled.

### Category filtering (`--indicators`)

Passing `--indicators trend momentum` (or setting `indicators.categories` in `config/default.yaml`) controls three things in lockstep: which scoring rules run, which chart panels render, and what the AI tool result reports. The three base chart panels (Price+Target, Confidence arc gauge, Signal Factors bar chart) always render.

### Trading / risk management

`RiskManager` gates every signal: `min_confidence` (0.40), max positions (5), max position size (5% equity), daily loss cap (2%), min R:R (1.5). Stops and take-profits are ATR-multiples (2× and 3× by default). All defaults live in `config/default.yaml` and can be overridden via `PredictionTradingSystem` kwargs.

`AutoTrader` runs a cycle loop: refresh data → close expired positions → score signal → risk-check → place order via `BaseBroker`. `PaperBroker` is the default; real brokers implement `get_quote / place_order / close_position`. State persists to `portfolio_state.json` via `StateStore`.

### Output structure

All runs write under `results/` with self-describing prefixes:
- `results/predict_YYYYMMDD_HHMMSS/` — `predictions.md` + `charts/*.png`
- `results/backtest_TICKER_YYYYMMDD_HHMMSS/` — `report.md` + four chart PNGs
- `results/live_YYYYMMDD_HHMMSS/` — `portfolio_state.json`, `trades.csv`, log

### Tests

All 52 tests across 11 files use synthetic OHLCV fixtures defined in `tests/conftest.py` (`ohlcv_uptrend`, `ohlcv_downtrend`, `ohlcv_sideways`) — no network or API key required.

### Config

`config/default.yaml` is the single source of defaults. `PredictionTradingSystem` accepts `config_path` to load an alternative file; individual sections can also be overridden by passing kwargs (e.g. `initial_capital=25_000`, `enable_ai=True`).
