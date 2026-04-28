# Stock Market Prediction Trading System

> AI-powered stock prediction and paper trading system built on technical indicators, Claude AI, and a full end-to-end trading engine.

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Web UI](#web-ui)
- [REST API](#rest-api)
- [CLI Usage](#cli-usage)
  - [stock-predictor](#stock-predictor)
  - [automated-trader](#automated-trader)
  - [scan-watchlist](#scan-watchlist)
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
- **Nine indicator categories**: trend, momentum, volatility, volume, support, fundamental, news, macro, sector
- **Timing recommendations**: actionable entry/stop/target levels with R:R ratio (`TimingRecommendation`)
- **ETF analyzer**: built-in catalogue for 30+ ETFs, portfolio correlation, diversification score, sector exposure
- **Bar-by-bar backtester** with full performance reports and four chart panels
- **Paper trading engine** with ATR-based risk management and portfolio persistence
- **Alpaca broker integration** for live/paper trading via `AlpacaBroker`
- **Watchlist scanner** for parallel bulk signal scoring (no API key required)
- **FastAPI REST API** with OpenAPI docs at `/docs`
- **Two web UIs:** Streamlit (`frontend/`, 8 pages, self-contained) and Dash (`dash-frontend/`, 9 pages, connects to REST API) — both with live trading dashboards; Streamlit offers a Dark/Light header toggle, Dash offers Auto/Dark/Light theme switching with a global config status bar

---

## Quick Start

```bash
git clone <this-repo> prediction-trading
cd prediction-trading

# Install all packages (requires uv — https://docs.astral.sh/uv/)
uv sync --all-packages

# Optional — enable Claude AI predictions
cp .env.example .env
# Edit .env and set: ANTHROPIC_API_KEY=sk-ant-...
```

Run a prediction without an API key:

```bash
uv run stock-predictor --tickers AAPL --no-ai
```

Or use `make`:

```bash
make install      # uv sync --all-packages
make test         # pytest backend/tests/
make ui-dev       # streamlit run frontend/app.py  → :8501
make api-dev      # uvicorn on :8000
make dash-dev     # uv run python dash-frontend/app.py  → :8050 (needs api-dev)
```

---

## Project Structure

```
prediction-trading/
├── backend/
│   ├── src/prediction_trading/   # core Python package
│   │   ├── _cli/                 # stock_predictor, automated_trader, scan_watchlist
│   │   ├── api/                  # FastAPI app (routers: predict, scan, backtest, trading)
│   │   ├── prediction/           # SignalScorer, AIPredictor, UnifiedPredictor
│   │   ├── trading/              # Portfolio, RiskManager, AutoTrader, PaperBroker
│   │   ├── backtest/             # bar-by-bar Backtester
│   │   ├── indicators/           # TechnicalIndicators, SupportResistance
│   │   ├── reporting/            # chart + markdown output
│   │   ├── data_fetcher.py
│   │   ├── scanner.py
│   │   └── system.py             # PredictionTradingSystem (primary facade)
│   └── tests/                    # 115 tests across 14 files, no network or API key required
├── frontend/
│   ├── app.py                    # Streamlit entry point (self-contained, :8501)
│   └── ui/                       # pages, components, theme, watchlist
├── dash-frontend/
│   ├── app.py                    # Dash entry point (requires API on :8000, serves :8050)
│   └── dash_ui/                  # pages, components, theme, api client
├── config/
│   ├── default.yaml
│   └── risk_profiles.yaml
├── docs/                         # guides, API reference, examples
├── examples/                     # annotated usage scripts
└── results/                      # run outputs (gitignored)
```

---

## Web UIs

Two web interfaces are available. Both share the same prediction engine but differ in architecture and capabilities.

### Streamlit UI (`frontend/`)

```bash
make ui-dev    # or: uv run streamlit run frontend/app.py
# opens http://localhost:8501
```

Self-contained — calls the Python backend directly, no API server required.

**Layout:** An 8-button **top navigation bar** selects the active page. A **🌙 Dark / ☀️ Light** toggle in the header switches the full theme. A **persistent sidebar watchlist** shows live price badges for saved tickers; clicking any ticker navigates to the Predict page. All pages except Settings show a **Config Info Bar** (data source · broker · AI model/status).

| Page | Icon | Key Features |
|---|---|---|
| **Dashboard** | 📊 | Portfolio Value, Cash, Day P&L, and Open Positions KPI cards; Plotly equity curve with initial-capital baseline; Open Positions table (entry/current/stop/target); Recent Trades table (last 20); Risk tab with Max Drawdown, Win Rate, Profit Factor, daily-loss bar, and concentration chart. Auto-refreshes every 15 s while AutoTrader is running. |
| **Predict** | 🔮 | Single-ticker prediction with timeframe and category multiselect. Signal tab: direction badge, confidence bar, Timing Recommendation card (BUY NOW / BUY ON DIP / BREAKOUT ENTRY / SELL NOW / TRAILING STOP / HOLD / WAIT), and Market Index table (VIX/SPY/QQQ/DXY with 1D/5D/30D % changes). Candlestick tab: interactive Plotly OHLC with SMA20/50, entry/stop/target lines, and volume sub-panel. Analysis tab: static matplotlib multi-panel chart. |
| **Scanner** | 🔍 | Watchlist textarea, min-confidence and parallel-workers sliders. Returns BUY/SELL/HOLD summary cards, a ranked results table with top factors, and a CSV export button. |
| **Backtest** | 📅 | Ticker, date range, capital, and commission inputs. Produces 8 KPI cards (return, drawdown, win rate, profit factor, trades, avg win/loss, final equity), equity curve, candlestick+trade-marker chart, and full trade log. Save Full Report writes markdown + PNGs to `results/`. |
| **Trading** | ⚡ | Start/stop AutoTrader (daemon thread). Running view shows live equity curve, open positions, last-cycle action table, cycle error log, and a Stop button. Cycle interval 60–3600 s; Dry Run and Market Hours toggles. Auto-refreshes every 10 s. |
| **Portfolio Builder** | 🧱 | Multi-ticker holdings cards (ETF/stock badge, category, expense ratio); Diversification Score (0–1); Correlation Matrix heatmap; Sector Exposure bar chart; recommendation list for high-correlation pairs and sector gaps. |
| **Alerts** | 🔔 | Create Price above/below, Confidence ≥, or Daily P&L triggers. Active Alerts tab with delete buttons; Check Now evaluates against live prices. Triggered Log (last 50). State persisted to `alerts.json`. |
| **Settings** | ⚙️ | Risk profile presets (conservative/moderate/aggressive). Full parameter controls for portfolio, risk, signals, indicator categories, AI/Claude model, AutoTrader, data source, and broker. Saves to `config/default.yaml`. |

### Dash UI (`dash-frontend/`)

```bash
# Start the API first (Dash UI is a REST client)
make api-dev    # uvicorn on :8000

# Then start the Dash UI
make dash-dev   # or: uv run python dash-frontend/app.py
# opens http://localhost:8050
```

Real-time dashboard using Plotly Dash + Bootstrap. Connects to the FastAPI backend at `localhost:8000` via `dash_ui/api.py`. Features `dcc.Interval` polling (no page reloads), `dcc.Store` cross-page state sharing, an **Auto / Dark / Light** theme switcher in the navbar (clientside, no round-trip), a global config status bar (Data · Feed · Model · Broker), and a dedicated **Analytics** page absent from the Streamlit UI.

| Page | Route | Key Features |
|---|---|---|
| **Dashboard** | `/` | Live 10 s polling of `/trading/status`; KPI row; equity curve (up to 360 points); tabs: Open Positions, Recent Trades, Risk KPIs. |
| **Predict** | `/predict` | Per-run Claude model selector; tabs: **Signal** (gauge + timing + index table), **Factors (N)** bar chart, **Analysis** (multi-panel candlestick + EMAs + MACD + RSI + Stochastic + volume), **Fundamentals** (valuation + growth bars), **Market** (1D/5D/30D index bars), **AI Narrative**. Result stored in `predict-result-store`. |
| **Scanner** | `/scanner` | Watchlist scan with auto-refresh toggle (30 s); CSV export; results stored in `scan-results-store`. |
| **Analytics** | `/analytics` | **Dash-only.** Visualizes data from Scanner + Predict stores: Confidence Distribution histogram, Direction donut, Factor Frequency bar, Category Heatmap (9 categories × tickers), Ticker Confidence scatter. |
| **Trading** | `/trading` | Start form with cycle-interval slider (60–3600 s); running view: status banner, positions table, last-cycle actions (OPEN/CLOSE/ERROR color-coded). |
| **Backtest** | `/backtest` | 8 KPI cards; tabs: Equity Curve, Candlestick+Trades (buy ▲ / sell ▼ markers), Trade Log DataTable. |
| **Alerts** | `/alerts` | Create/delete/check alerts; Triggered Log; state in `localStorage` via `alerts-store`. |
| **Portfolio Builder** | `/portfolio` | Holdings cards (ETF/Stock badge); Diversification Score; Correlation Heatmap; Sector Exposure bar chart; recommendations. |
| **Settings** | `/settings` | 8 accordion sections; loads from `GET /config/`, saves via `PUT /config/`. |

For the full Dash UI walkthrough see [`docs/DASH_UI_GUIDE.md`](docs/DASH_UI_GUIDE.md). For the full Streamlit walkthrough see [`docs/TRADING_SYSTEM_GUIDE.md`](docs/TRADING_SYSTEM_GUIDE.md).

---

## REST API

```bash
make api-dev   # or: uv run uvicorn prediction_trading.api.main:app --reload --port 8000
# OpenAPI docs at http://localhost:8000/docs
```

Endpoints mirror the Python API:

| Method | Path | Action |
|--------|------|--------|
| `POST` | `/predict/` | Run prediction for one ticker |
| `POST` | `/scan/` | Scan a watchlist of tickers |
| `POST` | `/backtest/` | Run a backtest over a date range |
| `POST` | `/trading/start` | Initialise an AutoTrader session |
| `GET`  | `/trading/status` | Current AutoTrader state (equity, positions) |

See `docs/API_REFERENCE.md` or `/docs` for full schema details.

---

## CLI Usage

### `stock-predictor`

The primary prediction CLI.

```bash
# Rule-based only (no API key needed)
uv run stock-predictor --tickers AAPL --no-ai

# AI-fused prediction with Claude
uv run stock-predictor --tickers AAPL TSLA --timeframe 1m

# Select specific indicator categories
uv run stock-predictor --tickers NVDA --indicators trend momentum

# Enable 4H confluence bonus
uv run stock-predictor --tickers AAPL --4h

# Use a specific Claude model
uv run stock-predictor --tickers AAPL --model claude-opus-4-7
```

**Full options:**

```
--tickers           One or more ticker symbols (default: AAPL TSLA INTC)
--timeframe         1d | 1w | 1m | 3m | 6m | ytd | 1y | 2y | 5y (default: 1w)
--model             Claude model ID (default: claude-sonnet-4-6)
--indicators        trend | momentum | volatility | volume | support | fundamental | news | macro | sector
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

### `automated-trader`

Paper-trades on a live schedule using the same prediction and risk engine.

```bash
# Single dry-run cycle (signals only, no orders)
uv run automated-trader --tickers AAPL TSLA --dry-run --once

# Paper-trade every 5 minutes, persist portfolio state
uv run automated-trader --tickers AAPL MSFT NVDA --interval 300

# AI-fused, market-hours only, 12 cycles
ANTHROPIC_API_KEY=sk-ant-... uv run automated-trader \
    --tickers AAPL --ai --market-hours --cycles 12 --interval 300
```

---

### `scan-watchlist`

Screens tickers in parallel with the rule-based engine. No API key required.

```bash
uv run scan-watchlist --tickers AAPL TSLA NVDA MSFT GOOG

# Filter by minimum confidence
uv run scan-watchlist --tickers AAPL TSLA NVDA --min-confidence 0.4

# Restrict indicator categories
uv run scan-watchlist --tickers AAPL TSLA --indicators trend momentum

# Increase parallelism
uv run scan-watchlist $(cat my_watchlist.txt) --workers 8
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
| `news` | Keyword-based headline sentiment score, recent earnings beat/miss, upcoming earnings calendar |
| `macro` | VIX regime (calm/fear), yield curve spread (10Y−2Y), SPY vs 50-day SMA |
| `sector` | Stock 30-day return vs sector ETF (XLK, XLV, XLF…), sector ETF vs SPY |

Confidence is deterministic: `min(1.0, abs(net_points) / 10)`. See [`DESIGN.md`](DESIGN.md) for the full point table.

---

## Backtester

```python
from prediction_trading.system import PredictionTradingSystem

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
from prediction_trading.system import PredictionTradingSystem

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
from prediction_trading.scanner import WatchlistScanner

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
make test          # uv run pytest backend/tests/ -v
make test-cov      # with coverage report
```

All 115 tests across 14 files use synthetic OHLCV fixtures (`backend/tests/conftest.py`) — no network or API key required.

---

## Documentation

| Document | Contents |
|----------|----------|
| [`docs/TRADING_SYSTEM_GUIDE.md`](docs/TRADING_SYSTEM_GUIDE.md) | Full end-to-end walkthrough including Streamlit UI per-page reference |
| [`docs/DASH_UI_GUIDE.md`](docs/DASH_UI_GUIDE.md) | Dash UI per-page reference (all 9 pages) |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Python and REST API reference |
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
