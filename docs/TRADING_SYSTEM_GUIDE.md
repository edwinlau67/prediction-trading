# Trading System Guide

## Table of Contents

1. [Installation](#installation)
2. [Launch the Web UI](#launch-the-web-ui)
3. [CLI Usage](#cli-usage)
4. [REST API](#rest-api)
5. [Python API](#python-api)
6. [Backtesting](#backtesting)
7. [Live / Paper Trading](#live--paper-trading)
8. [Watchlist Scanning](#watchlist-scanning)
9. [Configuration Guide](#configuration-guide)
10. [AI Integration](#ai-integration)
11. [Extending the System](#extending-the-system)

---

## Installation

```bash
git clone <repo>
cd prediction-trading
uv sync
cp .env.example .env
# Add your Anthropic key to enable AI (optional):
# ANTHROPIC_API_KEY=sk-ant-...
```

Verify:
```bash
uv run pytest backend/tests/ -v   # 11 test files, all offline — no API key needed
uv run stock-predictor --tickers AAPL --no-ai
```

---

## Launch the Web UI

```bash
uv run streamlit run frontend/app.py
```

Opens at `http://localhost:8501`. Seven pages via a top navigation bar (with a light/dark theme toggle in the header). A persistent watchlist sidebar shows live price badges on every page.

| Page | What it does |
|---|---|
| **Dashboard** | Portfolio overview — equity curve, open positions, recent trades |
| **Predict** | Run rule-based or AI prediction for any ticker with interactive charts |
| **Scanner** | Parallel watchlist scan with BUY/SELL/HOLD table and CSV export |
| **Backtest** | Historical simulation with equity curve, metrics, and trade log |
| **Trading** | Start/stop AutoTrader, monitor live portfolio and cycle reports |
| **Alerts** | Manage price/confidence/P&L triggers; alert state persisted to `alerts.json` |
| **Settings** | Apply risk profiles, tune all parameters, save to `config/default.yaml` |

---

## CLI Usage

### `stock-predictor` — Prediction report

```bash
# Rule-based (no API key needed)
uv run stock-predictor --tickers AAPL --no-ai

# Multi-ticker with Claude AI
uv run stock-predictor --tickers AAPL TSLA NVDA --timeframe 1m

# Filter indicator categories (faster, fewer panels)
uv run stock-predictor --tickers MSFT --indicators trend momentum volatility

# Extended thinking budget
uv run stock-predictor --tickers GOOG --thinking-budget 10000
```

Output: `results/predict_YYYYMMDD_HHMMSS/predictions.md` + PNG charts

### `scan-watchlist` — Watchlist scan

```bash
# Scan tickers with default settings
uv run scan-watchlist AAPL MSFT NVDA TSLA GOOGL

# Filter by confidence and categories
uv run scan-watchlist AAPL TSLA NVDA --min-confidence 0.4 --indicators trend momentum

# Use more parallel workers
uv run scan-watchlist $(cat my_watchlist.txt | tr '\n' ' ') --workers 8
```

Output: Ranked table to stdout, sorted by confidence descending.

### `automated-trader` — Paper trading

```bash
# Single cycle, dry run (signals only)
uv run automated-trader --tickers AAPL TSLA --dry-run --once

# Continuous every 5 minutes, market hours only
uv run automated-trader --tickers AAPL MSFT NVDA --interval 300 --market-hours

# With AI signals
uv run automated-trader --tickers AAPL --ai --interval 600
```

Output: `results/live_YYYYMMDD_HHMMSS/portfolio_state.json` + `trades.csv`

---

## REST API

Start the server:

```bash
uv run uvicorn prediction_trading.api.main:app --reload
# Interactive docs at http://localhost:8000/docs
```

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check |
| `/predict/` | POST | Single-ticker prediction |
| `/scan/` | POST | Parallel watchlist scan |
| `/backtest/` | POST | Bar-by-bar backtest |
| `/trading/start` | POST | Initialise AutoTrader session |
| `/trading/status` | GET | Current AutoTrader state |

Example with `curl`:

```bash
curl -s -X POST http://localhost:8000/predict/ \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "lookback_days": 365}' | python3 -m json.tool
```

---

## Python API

The fastest path for scripting or Jupyter notebooks:

```python
from prediction_trading import PredictionTradingSystem

# Predict
system = PredictionTradingSystem("AAPL")
market = system.fetch()
pred = system.predict(market)
print(f"{pred.ticker}: {pred.direction} {pred.confidence:.0%} → ${pred.price_target:.2f}")

# Save chart + markdown report
out_dir = system.save_report(prediction=pred)
print(f"Report: {out_dir}")

# Backtest
system2 = PredictionTradingSystem("TSLA", initial_capital=25_000)
result = system2.backtest("2023-01-01", "2024-01-01")
print(result.summary())

# Multi-ticker scan
from prediction_trading.scanner import WatchlistScanner
scanner = WatchlistScanner(min_confidence=0.4, workers=8)
results = scanner.scan(["AAPL", "MSFT", "NVDA", "TSLA", "META"])
for r in results:
    print(f"{r.ticker}: {r.direction} {r.confidence:.0%}")
```

---

## Backtesting

### Via the UI

1. Go to **Backtest** page
2. Enter ticker, date range, capital, commission
3. Click **Run Backtest**
4. Review metrics (return%, max drawdown, win rate, profit factor)
5. Inspect equity curve and trade log
6. Click **Save Full Report** to write markdown + charts to `results/`

### Via the API

```python
from prediction_trading import PredictionTradingSystem

system = PredictionTradingSystem(
    "AAPL",
    initial_capital=10_000,
    config_path="config/default.yaml",
)
result = system.backtest("2022-01-01", "2024-01-01")
stats = result.summary()

print(f"Return:       {stats['return_pct']:+.2f}%")
print(f"Max Drawdown: {stats['max_drawdown_pct']:.2f}%")
print(f"Win Rate:     {stats['win_rate_pct']:.1f}%")
print(f"Profit Factor:{stats['profit_factor']:.2f}")
print(f"Total Trades: {stats['trades']}")

out = system.save_report(result=result)
print(f"Report: {out}")
```

### Interpreting results

- **Profit factor > 1.5** is a reasonable threshold for a working strategy.
- **Max drawdown** drives position sizing — if uncomfortable, lower `max_position_size_pct`.
- **Win rate** alone is misleading. A 40% win rate with 3:1 average R:R is very profitable.
- Compare against buy-and-hold over the same period for context.

---

## Live / Paper Trading

### Start via the UI

1. Go to **Trading** page
2. Enter tickers, interval, enable Dry Run for testing
3. Click **Start AutoTrader**
4. Monitor equity curve and cycle reports
5. Click **Stop AutoTrader** to halt

### Start via the CLI

```bash
# Paper trading, one cycle
uv run automated-trader --tickers AAPL MSFT --dry-run --once

# Continuous, every 5 minutes, persist state
uv run automated-trader --tickers AAPL MSFT NVDA --interval 300
```

### State persistence

Portfolio state is saved to `results/live_*/portfolio_state.json` after each cycle. If the process restarts, `StateStore.load_or_create()` restores open positions and cash balance. Trade history is appended to `trades.csv`.

### Switching to a real broker

Implement `BaseBroker`:

```python
from prediction_trading.trading.broker import BaseBroker, Order, Fill
from prediction_trading.trading.portfolio import Trade

class MyBroker(BaseBroker):
    def get_quote(self, ticker: str) -> float:
        return my_api.last_price(ticker)

    def place_order(self, order: Order) -> Fill | None:
        resp = my_api.submit_order(order.ticker, order.quantity, order.side)
        return Fill(ticker=order.ticker, price=resp.fill_price, ...)

    def close_position(self, ticker, reason, quote=None, when=None) -> Trade | None:
        ...

system = PredictionTradingSystem("AAPL")
trader = system.build_auto_trader(
    tickers=["AAPL", "MSFT"],
    broker=MyBroker(),
    dry_run=False,
)
trader.run()
```

---

## Watchlist Scanning

The scanner is optimised for fast screening — it skips chart generation and AI calls.

```python
from prediction_trading.scanner import WatchlistScanner

scanner = WatchlistScanner(
    categories=("trend", "momentum"),   # only score these categories
    lookback_days=180,
    min_confidence=0.35,
    workers=8,
)
results = scanner.scan([
    "AAPL", "MSFT", "NVDA", "TSLA", "META",
    "GOOGL", "AMZN", "JPM", "GS", "BAC",
])

# Results sorted by confidence descending
for r in results:
    if r.error:
        print(f"{r.ticker}: ERROR — {r.error}")
    else:
        factors = ", ".join(r.top_factors[:3])
        print(f"{r.ticker:6} {r.direction:8} {r.confidence:5.0%}  {factors}")
```

---

## Configuration Guide

All defaults live in `config/default.yaml`. Every value can be overridden at `PredictionTradingSystem` instantiation.

### Risk profiles

The UI Settings page offers three presets from `config/risk_profiles.yaml`:

| Profile | Position size | Daily loss limit | Min confidence | Min R:R |
|---|---|---|---|---|
| Conservative | 3% | 1% | 60% | 2.0 |
| Moderate (default) | 5% | 2% | 40% | 1.5 |
| Aggressive | 10% | 5% | 30% | 1.2 |

### Key parameters

| Parameter | Path in YAML | Effect |
|---|---|---|
| `initial_capital` | `portfolio.initial_capital` | Starting portfolio value |
| `max_positions` | `portfolio.max_positions` | Max concurrent open positions |
| `max_position_size_pct` | `portfolio.max_position_size_pct` | Max equity per position |
| `min_confidence` | `signals.min_confidence` | Signal strength gate (0–1) |
| `stop_loss_atr_mult` | `risk.stop_loss_atr_mult` | Stop = entry ± ATR × mult |
| `take_profit_atr_mult` | `risk.take_profit_atr_mult` | Target = entry ± ATR × mult |
| `max_daily_loss_pct` | `risk.max_daily_loss_pct` | Halt trading at this daily drawdown |
| `ai_weight` | `signals.ai_weight` | 0 = pure rule-based, 1 = pure AI |
| `multi_timeframe_bonus` | `signals.multi_timeframe_bonus` | Points added when weekly agrees |
| `categories` | `indicators.categories` | Which rule categories to run |

### Indicator categories

Filter to specific categories for faster runs or to test isolated signals:

```yaml
indicators:
  categories:
    - trend       # SMA/EMA/MACD/Golden Cross
    - momentum    # RSI/Stochastic
    - volatility  # Bollinger/ATR
    - volume      # OBV/Volume spike
    - support     # Pivot points/Trendlines
    - fundamental # P/E, ROE, margins…
    - news        # Headline sentiment, earnings beat/miss (requires internet)
    - macro       # VIX, yield curve, SPY trend (requires internet)
    - sector      # Sector ETF relative strength (requires internet)
    # Comment out any category to exclude it from scoring
```

---

## AI Integration

### Setup

Add to `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Enable in config:
```yaml
ai:
  enabled: true
  model: claude-opus-4-7
  timeframe: 1m
  max_tokens: 2000
```

Or pass to the system directly:
```python
system = PredictionTradingSystem("AAPL", enable_ai=True, api_key="sk-ant-...")
```

### How it works

1. System prompt (cached with `cache_control: ephemeral`) instructs Claude to call the `stock_prediction` tool.
2. Claude calls the tool → local code fetches data with `include_enriched=True` (adds news, macro, sector context) and runs `SignalScorer` → returns structured result with optional `news`, `macro`, `sector` dicts.
3. Second API call: Claude receives tool result and returns a narrative (≤500 words) that comments on news sentiment/earnings, VIX/yield-curve, and sector relative strength when those fields are present.
4. `UnifiedPredictor` blends the AI confidence with the rule-based score.

### Prompt caching

The system prompt is ~1 500 tokens and is cached after the first call. Subsequent calls for the same ticker in the same session hit the cache, reducing cost by ~90%. Cache TTL is 5 minutes.

### Timeframes

The `timeframe` parameter controls the prediction window: `1d`, `1w`, `1m`, `3m`, `6m`, `ytd`, `1y`, `2y`, `5y`.

---

## Extending the System

### Adding a new indicator category

1. Add the category name to `factor.py:ALL_CATEGORIES`.
2. Add a `_<category>_factors(self, df)` method to `SignalScorer` following the existing pattern.
3. Call it inside `SignalScorer.score()` with an `if "<category>" in self.categories:` guard.
4. Optionally add a chart panel to `PredictionChart.render()`.

### Adding a new indicator to an existing category

Add the rule inside the appropriate `_<category>_factors` method. Each rule should:
- Check that the required column exists in `df` (use `self._v(row.get("COL_NAME"))`)
- Return a `Factor` with an appropriate `points` value (1 for weak signals, 2 for strong crossovers)

### Implementing a real broker

See [Switching to a real broker](#switching-to-a-real-broker) above.

### Adding a new report format

Subclass `BaseReportWriter` and `BaseChart` from `prediction_trading/reporting/base.py`. Follow the pattern in `PredictionReportWriter` and `PredictionChart`.
