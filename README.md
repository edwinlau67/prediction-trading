# Stock Market Prediction & Automated Trading System

> AI-powered stock prediction and paper trading system built on technical indicators, Claude AI, and a full end-to-end trading engine.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Web UI](#web-ui)
- [CLI Usage](#cli-usage)
  - [stock\_predictor.py](#stock_predictorpy)
  - [automated\_trader.py](#automated_traderpy)
  - [scan\_watchlist.py](#scan_watchlistpy)
- [Output Structure](#output-structure)
- [Technical Indicators](#technical-indicators)
- [Backtester](#backtester)
- [Automated Trading](#automated-trading)
- [Watchlist Scanner](#watchlist-scanner)
- [Configuration](#configuration)
- [Testing](#testing)
- [Documentation](#documentation)
- [References](#references)
- [Disclaimer](#disclaimer)

---

## Features

- **AI-powered predictions** via Claude tool-use with prompt caching
- **Six indicator categories**: trend, momentum, volatility, volume, support, fundamental
- **Bar-by-bar backtester** with full performance reports and four chart panels
- **Paper trading engine** with ATR-based risk management and portfolio persistence
- **Watchlist scanner** for parallel bulk signal scoring (no API key required)
- **Streamlit web UI** with seven pages, live price badges, and light/dark theme

---

## Quick Start

```bash
git clone <this-repo> prediction-trading
cd prediction-trading
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional — enable Claude AI predictions
cp .env.example .env
# Edit .env and set: ANTHROPIC_API_KEY=sk-ant-...
```

Run a prediction without an API key:

```bash
python stock_predictor.py --tickers AAPL --no-ai
```

---

## Web UI

```bash
streamlit run app.py    # opens http://localhost:8501
```

Seven pages: **Dashboard** · **Predict** · **Scanner** · **Backtest** · **Trading** · **Alerts** · **Settings**

Navigation uses a top bar with a light/dark theme toggle. A persistent watchlist sidebar shows live price badges and quick-links to the Predict page.

---

## CLI Usage

### `stock_predictor.py`

The primary prediction CLI. Mirrors the `stock-prediction` interface exactly.

```bash
# Rule-based only (no API key needed)
python stock_predictor.py --tickers AAPL --no-ai

# AI-fused prediction with Claude
python stock_predictor.py --tickers AAPL TSLA --timeframe 1m

# Select specific indicator categories
python stock_predictor.py --tickers NVDA --indicators trend momentum

# Enable 4H confluence bonus
python stock_predictor.py --tickers AAPL --4h

# Use a specific Claude model
python stock_predictor.py --tickers AAPL --model claude-opus-4-7
```

**Full options:**

```
--tickers           One or more ticker symbols (default: AAPL TSLA INTC)
--timeframe         1d | 1w | 1m | 3m | 6m | ytd | 1y | 2y | 5y (default: 1w)
--model             Claude model ID (default: claude-sonnet-4-6)
--indicators        trend | momentum | volatility | volume | support | fundamental
--no-ai             Rule-based only; skip the Claude call
--4h                Enable 4H confluence bonus (resamples 1h OHLCV to 4H)
--thinking-budget   Extended thinking token budget (0 = disabled)
--out               Output root directory (default: results/)
```

**Supported timeframes:**

| Flag  | Meaning      | Flag | Meaning    |
|-------|--------------|------|------------|
| `1d`  | 1 day        | `1y` | 1 year     |
| `1w`  | 1 week       | `2y` | 2 years    |
| `1m`  | 1 month      | `5y` | 5 years    |
| `3m`  | 3 months     | `ytd`| Year-to-date |
| `6m`  | 6 months     |      |            |

**Supported models:**

| Model ID                    | Notes                             |
|-----------------------------|-----------------------------------|
| `claude-sonnet-4-6`         | Default — fast and cost-effective |
| `claude-opus-4-7`           | Most capable, higher cost         |
| `claude-haiku-4-5-20251001` | Fastest and cheapest              |

---

### `automated_trader.py`

Paper-trades on a live schedule using the same prediction and risk engine.

```bash
# Single dry-run cycle (signals only, no orders)
python automated_trader.py --tickers AAPL TSLA --dry-run --once

# Paper-trade every 5 minutes, persist portfolio state
python automated_trader.py --tickers AAPL MSFT NVDA --interval 300

# AI-fused, market-hours only, 12 cycles
ANTHROPIC_API_KEY=sk-ant-... python automated_trader.py \
    --tickers AAPL --ai --market-hours --cycles 12 --interval 300
```

---

### `scan_watchlist.py`

Screens tickers in parallel with the rule-based engine. No API key required.

```bash
python scan_watchlist.py --tickers AAPL TSLA NVDA MSFT GOOG

# Filter by minimum confidence
python scan_watchlist.py --tickers AAPL TSLA NVDA --min-confidence 0.4

# Restrict indicator categories
python scan_watchlist.py --tickers AAPL TSLA --indicators trend momentum

# Increase parallelism
python scan_watchlist.py $(cat my_watchlist.txt) --workers 8
```

Output is a colour-coded terminal table sorted by confidence descending, showing direction, confidence %, current price, and top 3 scored factors.

---

## Output Structure

All runs write into `results/` with timestamped, self-describing subfolders:

```
results/
├── predict_20260422_074503/
│   ├── predictions.md
│   └── charts/
│       ├── AAPL_1w.png
│       └── TSLA_1m.png
│
└── backtest_AAPL_20260422_075022/
    ├── report.md
    └── charts/
        ├── indicators.png
        ├── signals.png
        ├── performance.png
        └── risk.png
```

### `predictions.md` sections

| Section | Content |
|---------|---------|
| Prediction Summary | Direction, confidence, price target, risk level, net score |
| Embedded chart | Inline PNG with every selected panel |
| Key Bullish Factors | Up to 8 bullish factors with point scores |
| Key Risk Factors | Up to 8 bearish factors with point scores |
| Technical Levels | Pivot points — R2, R1, PP, S1, S2 |
| Fibonacci Levels | 0%–100% retracement over 6-month range |
| Analysis | Claude narrative (or deterministic summary when AI is off) |

### Chart panels

Three panels are always rendered: **Price + Target**, **Confidence & Risk** arc gauge, **Technical Signal Factors** bar chart.

Optional panels per `--indicators` category:

| Panel | Category |
|-------|----------|
| MACD (12, 26, 9) | `trend` |
| RSI (14) | `momentum` |
| Stochastic (14, 3) | `momentum` |
| Volume + Spikes | `volume` |
| OBV | `volume` |
| Support & Resistance | `support` |
| ATR (14) | `volatility` |
| Fundamental Indicators (15-metric grid) | `fundamental` |

---

## Technical Indicators

All computed from Yahoo Finance OHLCV (1-year daily) plus a fundamentals snapshot.

| Category | Indicators |
|----------|------------|
| `trend` | SMA50/200, EMA12/20/26, MACD (12/26/9), Golden/Death Cross, price vs MA checks |
| `momentum` | RSI (14): <30 oversold / >70 overbought; Stochastic (14, 3): %K/%D crossover |
| `volatility` | Bollinger Bands (20, 2σ), ATR (14) high/low risk thresholds |
| `volume` | OBV trend, Volume Spike (>20-day mean + 2σ) |
| `fundamental` | P/E, Forward P/E, P/B, P/S, EV/EBITDA, PEG, Revenue Growth, EPS Growth, Net Margin, Operating Margin, ROE, Debt/Equity, Current Ratio, Dividend Yield, Short Ratio |
| `support` | Trendlines (5-bar swing), Pivot Points (R2/R1/PP/S1/S2), Fibonacci (0%–100%) |

Confidence is deterministic: `min(1.0, abs(net_points) / 10)`. See [`DESIGN.md`](DESIGN.md) for the full point table.

---

## Backtester

```python
from src import PredictionTradingSystem

system = PredictionTradingSystem(ticker="AAPL", initial_capital=10_000, enable_ai=True)
result = system.backtest("2023-01-01", "2024-01-01")
prediction = system.predict()
system.save_report(result=result, prediction=prediction)
```

Produces a `results/backtest_AAPL_<timestamp>/` folder:

| File | Contents |
|------|----------|
| `report.md` | Backtest stats, trade log, prediction |
| `charts/indicators.png` | Price, MAs, Bollinger, MACD, RSI, ADX |
| `charts/signals.png` | Close with buy/sell markers |
| `charts/performance.png` | Equity curve + drawdown |
| `charts/risk.png` | Per-trade P&L and ATR |

---

## Automated Trading

`AutoTrader` runs prediction + risk management on a live schedule. Orders route through a pluggable broker — `PaperBroker` is the default; real brokers implement `BaseBroker` (`get_quote`, `place_order`, `close_position`).

Each cycle per ticker:
1. Refreshes OHLCV + indicators; closes positions at stop or take-profit.
2. Marks portfolio to latest quote.
3. Asks `UnifiedPredictor` for a signal; `RiskManager` gates sizing, R:R, daily loss cap.
4. Submits the approved order, records the fill in `trades.csv`, snapshots to `portfolio_state.json`.

### Python API

```python
from src import PredictionTradingSystem

system = PredictionTradingSystem(ticker="AAPL", initial_capital=25_000, enable_ai=True)
trader = system.build_auto_trader(
    tickers=["AAPL", "MSFT", "NVDA"],
    state_path="results/live/portfolio_state.json",
    trade_log_path="results/live/trades.csv",
    enforce_market_hours=True,
)

report = trader.run_once()                        # one-shot cycle
trader.run(interval_seconds=300, max_cycles=24)   # continuous loop
```

### Risk profiles

`config/risk_profiles.yaml` ships three presets, selectable from the Settings page:

| Profile | Position size | Daily limit | Min confidence | Stop ATR | Target ATR | Min R:R |
|---------|---------------|-------------|----------------|----------|------------|---------|
| conservative | 3% | 1% | 60% | 1.5× | 3.0× | 2.0 |
| moderate | 5% | 2% | 40% | 2.0× | 3.0× | 1.5 |
| aggressive | 10% | 5% | 30% | 2.5× | 4.0× | 1.2 |

### Live output folder

```
results/live_20260422_081000/
├── portfolio_state.json    # resumable snapshot (cash, positions, equity curve)
├── trades.csv              # every open/close with timestamp, price, qty, P&L, reason
└── prediction_trading.log  # structured cycle log
```

---

## Watchlist Scanner

```python
from src.scanner import WatchlistScanner

results = WatchlistScanner(min_confidence=0.4, workers=8).scan(["AAPL", "TSLA", "NVDA"])
for r in results:
    print(r.ticker, r.direction, r.confidence)
```

---

## Configuration

`config/default.yaml` is the single source of defaults. Pass `config_path` to `PredictionTradingSystem` to load an alternative file, or override individual values via kwargs (e.g. `initial_capital=25_000`).

Key trader settings:

```yaml
trader:
  interval_seconds: 300        # seconds between cycles
  enforce_market_hours: false  # only trade 09:30–16:00 ET, Mon–Fri
  slippage_bps: 0.0            # paper-broker slippage model (basis points)
  dry_run: false               # signals only, never place orders
```

---

## Testing

```bash
pytest tests/ -v     # 78 tests across 11 files
```

All tests use synthetic OHLCV fixtures (`tests/conftest.py`) — no network or API key required.

---

## Documentation

| Document | Contents |
|----------|----------|
| [`docs/TRADING_SYSTEM_GUIDE.md`](docs/TRADING_SYSTEM_GUIDE.md) | Full end-to-end walkthrough |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Python API reference |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architecture deep-dive |
| [`docs/EXAMPLES.md`](docs/EXAMPLES.md) | Annotated code examples |
| [`docs/QUICK_REFERENCE.md`](docs/QUICK_REFERENCE.md) | CLI/API cheat-sheet |
| [`DESIGN.md`](DESIGN.md) | Full design specification and point table |

---

## References

This project merges and extends three upstream repositories:

| Repository | Contribution |
|------------|-------------|
| [`edwinlau67/stock-prediction`](https://github.com/edwinlau67/stock-prediction) | Claude tool-use predictor, `predictions.md` layout, dynamic multi-panel analysis chart, six indicator categories, fundamental scoring |
| [`edwinlau67/automated-trading-systems`](https://github.com/edwinlau67/automated-trading-systems) | Multi-timeframe weighted scoring, portfolio/position/trade primitives, ATR-based risk manager, bar-by-bar backtester, performance reports |
| [`edwinlau67/algorithmic-trading-system`](https://github.com/edwinlau67/algorithmic-trading-system) | Algorithmic trading strategies, extended risk management patterns, and additional backtesting capabilities |

---

## Disclaimer

For educational and research purposes only. Predictions are derived from technical and fundamental signals — past performance does not guarantee future results.
