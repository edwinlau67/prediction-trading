# CLAUDE.md

We're building the app described in @DESIGN.md. Read that file for general architectural tasks or to double-check the exact database structure, tech stack or application architecture.

Keep your replies extremely concise and focus on conveying the key information. No unnecessary fluff, no long code snippets.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
# Install uv if needed: https://docs.astral.sh/uv/getting-started/installation/
make install          # uv sync --all-packages
cp .env.example .env  # then add ANTHROPIC_API_KEY=sk-ant-... to enable AI
```

## Common commands

```bash
# Predict (rule-based, no API key needed)
uv run stock-predictor --tickers AAPL --no-ai

# Predict with Claude AI
uv run stock-predictor --tickers AAPL TSLA --timeframe 1m

# Filter indicator categories
uv run stock-predictor --tickers NVDA --indicators trend momentum

# Automated paper trading (one cycle, dry run)
uv run automated-trader --tickers AAPL TSLA --dry-run --once

# Continuous paper trading every 5 min, market hours only
uv run automated-trader --tickers AAPL --interval 300 --market-hours

# Launch Streamlit web UI
make ui-dev           # streamlit run frontend/app.py

# Launch REST API
make api-dev          # uvicorn on :8000 with --reload

# Scan watchlist (bulk signal scoring)
uv run scan-watchlist AAPL TSLA NVDA

# Run all tests (offline — no API key required)
make test             # uv run pytest backend/tests/ -v

# Run a single test file
uv run pytest backend/tests/test_signal_scorer.py -v

# Lint / format / type-check
make lint
make fmt
make type-check
```

## Architecture

Monorepo (uv workspace): `backend/` (core engine + FastAPI + CLI) and `frontend/` (Streamlit UI) are separate packages wired together by `prediction_trading/system.py:PredictionTradingSystem`.

```
CLI entry points (stock-predictor, automated-trader, scan-watchlist)
Web UI           (frontend/app.py → frontend/ui/ — 7 pages)
REST API         (prediction_trading/api/ — FastAPI :8000)
        │
prediction_trading/system.py — PredictionTradingSystem (facade)
        │
prediction_trading/prediction/  ← scoring + AI fusion
prediction_trading/reporting/   ← chart + markdown output
        │
prediction_trading/trading/     ← Portfolio, RiskManager, AutoTrader, PaperBroker
prediction_trading/backtest/    ← bar-by-bar Backtester
        │
prediction_trading/indicators/  ← TechnicalIndicators, SupportResistance
prediction_trading/data_fetcher.py ← yfinance OHLCV + fundamentals
frontend/ui/                    ← Streamlit pages + shared components
```

### Prediction pipeline

1. `SignalScorer` emits `Factor(category, name, direction, points, detail)` objects for each active indicator category. Net points → direction + confidence (`min(1.0, abs(points)/10)`).
2. `AIPredictor` uses Claude tool-use: the model calls the `stock_prediction` tool → local execution fetches data (with `include_enriched=True`) and runs `SignalScorer` (passing `news_context`, `macro_context`, `sector_context`) → second API call returns a narrative (≤500 words). The system prompt carries `cache_control: {type: "ephemeral"}` for prompt caching.
3. `UnifiedPredictor` blends: `(1 - ai_weight) * rule_signed + ai_weight * ai_signed`. Default `ai_weight = 0.5` from `config/default.yaml`. Falls back to rule-only when AI is disabled.

### Category filtering (`--indicators`)

Passing `--indicators trend momentum` (or setting `indicators.categories` in `config/default.yaml`) controls three things in lockstep: which scoring rules run, which chart panels render, and what the AI tool result reports. The three base chart panels (Price+Target, Confidence arc gauge, Signal Factors bar chart) always render. Nine categories available: `trend`, `momentum`, `volatility`, `volume`, `support`, `fundamental`, `news`, `macro`, `sector`. The `news`/`macro`/`sector` categories also require the corresponding context from `include_enriched=True` fetching.

### Trading / risk management

`RiskManager` gates every signal: `min_confidence` (0.40), max positions (5), max position size (5% equity), daily loss cap (2%), min R:R (1.5). Stops and take-profits are ATR-multiples (2× and 3× by default). All defaults live in `config/default.yaml` and can be overridden via `PredictionTradingSystem` kwargs.

`AutoTrader` runs a cycle loop: refresh data → close expired positions → score signal → risk-check → place order via `BaseBroker`. `PaperBroker` is the default; real brokers implement `get_quote / place_order / close_position`. State persists to `portfolio_state.json` via `StateStore`.

### Output structure

All runs write under `results/` with self-describing prefixes:
- `results/predict_YYYYMMDD_HHMMSS/` — `predictions.md` + `charts/*.png`
- `results/backtest_TICKER_YYYYMMDD_HHMMSS/` — `report.md` + four chart PNGs
- `results/live_YYYYMMDD_HHMMSS/` — `portfolio_state.json`, `trades.csv`, log

### Tests

All 78 tests across 11 files use synthetic OHLCV fixtures defined in `tests/conftest.py` (`ohlcv_uptrend`, `ohlcv_downtrend`, `ohlcv_sideways`) — no network or API key required.

### Config

`config/default.yaml` is the single source of defaults. `PredictionTradingSystem` accepts `config_path` to load an alternative file; individual sections can also be overridden by passing kwargs (e.g. `initial_capital=25_000`, `enable_ai=True`).
