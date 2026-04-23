# prediction-trading

Automated **stock trading + AI-powered prediction** system.

This project merges two upstream repositories into one end-to-end pipeline:

| Source                                                                                             | Contribution                                                                                         |
| -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [`edwinlau67/stock-prediction`](https://github.com/edwinlau67/stock-prediction)                    | Claude (Anthropic) tool-use predictor, rich `predictions.md` + dynamic multi-panel analysis chart, six indicator categories, fundamental scoring. |
| [`edwinlau67/automated-trading-systems`](https://github.com/edwinlau67/automated-trading-systems) | Multi-timeframe weighted scoring, portfolio / position / trade primitives, ATR-based risk manager, bar-by-bar backtester, performance reports. |
| [`edwinlau67/algorithmic-trading-system`](https://github.com/edwinlau67/algorithmic-trading-system) | Comprehensive algorithmic trading system with multiple strategies, risk management, and backtesting capabilities |

Every feature from `stock-prediction`'s README — including the CLI, the
six `--indicators` categories, the dynamic chart panels (confidence arc
gauge, MACD, RSI, Stochastic, Volume+Spikes, OBV, Support/Resistance,
ATR, Fundamental grid), the `predictions.md` layout, and the
`results/YYYYMMDD_HHMMSS/` output folder — is present.

## Project structure

```
prediction-trading/
├── stock_predictor.py                  # CLI mirroring stock-prediction (primary predictor)
├── automated_trader.py                 # CLI for the live / paper trading engine
├── scan_watchlist.py                   # CLI for parallel rule-based watchlist screening
├── app.py                              # Streamlit web UI entry point
├── config/
│   ├── default.yaml                    # portfolio, risk, signal, trader, AI defaults
│   ├── risk_profiles.yaml              # conservative / moderate / aggressive presets
│   └── indicators_config.yaml          # per-indicator period/threshold reference
├── DESIGN.md                           # architecture and scoring model
├── docs/
│   ├── TRADING_SYSTEM_GUIDE.md         # full end-to-end walkthrough
│   ├── API_REFERENCE.md                # Python API reference
│   ├── ARCHITECTURE.md                 # architecture deep-dive
│   ├── EXAMPLES.md                     # annotated code examples
│   └── QUICK_REFERENCE.md              # CLI/API cheat-sheet
├── ui/
│   ├── state.py                        # session_state key constants
│   ├── components.py                   # shared widgets (metric cards, charts, tables)
│   └── pages/                          # one module per Streamlit page
├── src/
│   ├── system.py                       # PredictionTradingSystem (predict / backtest / build_auto_trader)
│   ├── data_fetcher.py                 # yfinance wrapper (OHLCV + fundamentals)
│   ├── indicators/
│   │   ├── technical.py                # SMA, EMA, MACD, RSI, Stoch, BB, ATR, ADX, OBV
│   │   └── levels.py                   # pivots, Fibonacci, swing trendlines
│   ├── scanner.py                      # WatchlistScanner — parallel rule-based screening
│   ├── prediction/
│   │   ├── factor.py                   # Factor model + IndicatorCategory enum
│   │   ├── signal_scorer.py            # point-based scorer with category filtering
│   │   ├── ai_predictor.py             # Claude tool-use predictor (offline fallback)
│   │   └── predictor.py                # UnifiedPredictor — fuses rules + AI
│   ├── trading/
│   │   ├── portfolio.py                # Portfolio / Position / Trade
│   │   ├── risk_manager.py             # sizing + stops + R:R + daily loss cap
│   │   ├── broker.py                   # BaseBroker, PaperBroker, RecordingBroker
│   │   ├── state.py                    # JSON portfolio persistence (stop/resume)
│   │   └── auto_trader.py              # AutoTrader — live/paper loop runner
│   ├── backtest/backtester.py          # bar-by-bar engine
│   ├── reporting/
│   │   ├── base.py                     # BaseChart + BaseReportWriter (shared helpers)
│   │   ├── prediction_chart.py         # dynamic multi-panel analysis chart
│   │   ├── prediction_report.py        # predictions.md writer
│   │   ├── charts.py                   # 4-chart backtest dashboard
│   │   └── report.py                   # backtest report.md
│   └── logger.py
├── examples/                           # predict + backtest + live-trading examples
└── tests/                              # 32 unit + integration tests
```

## Web UI

The fastest way to use the system is the Streamlit dashboard:

```bash
streamlit run app.py          # opens http://localhost:8501
```

Six pages: **Dashboard** · **Predict** · **Scanner** · **Backtest** · **Trading** · **Settings**

| Doc | Contents |
| --- | -------- |
| [`docs/TRADING_SYSTEM_GUIDE.md`](docs/TRADING_SYSTEM_GUIDE.md) | Full end-to-end walkthrough |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Python API reference |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Architecture deep-dive |
| [`docs/EXAMPLES.md`](docs/EXAMPLES.md) | Annotated code examples |
| [`docs/QUICK_REFERENCE.md`](docs/QUICK_REFERENCE.md) | CLI/API cheat-sheet |

## Quick start

```bash
git clone <this-repo> prediction-trading
cd prediction-trading
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Optional — enable the Claude-powered predictor
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

## CLI — `stock_predictor.py`

The CLI is a drop-in equivalent of `stock-prediction`'s `stock_predictor.py`.

### Run with defaults

```bash
python stock_predictor.py
# → AAPL (1w), TSLA (1w), INTC (1w) with all six indicator categories
```

### Specify tickers and timeframe

```bash
python stock_predictor.py --tickers NVDA
python stock_predictor.py --tickers MSFT --timeframe 3m
python stock_predictor.py --tickers GOOG AMZN --timeframe 1d
python stock_predictor.py --tickers AAPL --model claude-opus-4-7
```

### Select indicator categories

Omitting a category removes it from both the scoring engine and the chart panels.

```bash
# Trend + momentum only
python stock_predictor.py --tickers AAPL --indicators trend momentum

# Volatility + volume only
python stock_predictor.py --tickers TSLA --indicators volatility volume

# Fundamentals only
python stock_predictor.py --tickers MSFT --indicators fundamental

# Single category
python stock_predictor.py --tickers NVDA --indicators support
```

### Full option list

```
usage: stock_predictor.py [-h] [--tickers TICKER [TICKER ...]]
                          [--timeframe {1d,1w,1m,3m,6m,ytd,1y,2y,5y}]
                          [--model MODEL]
                          [--indicators INDICATOR [INDICATOR ...]]
                          [--no-ai] [--out OUT]

  --tickers     One or more stock ticker symbols (default: AAPL TSLA INTC)
  --timeframe   Prediction timeframe: 1d 1w 1m 3m 6m ytd 1y 2y 5y (default: 1w)
  --model       Claude model ID (default: claude-sonnet-4-6)
  --indicators  Indicator categories (default: all six)
                Choices: trend momentum volatility volume support fundamental
  --no-ai            Skip the Claude call; rule-based-only run.
  --thinking-budget  Token budget for extended thinking (0 = disabled, e.g. 10000).
  --out              Output root directory (default: results/)
```

### Supported timeframes and models

| Timeframe | Meaning      |
| --------- | ------------ |
| 1d        | 1 day        |
| 1w        | 1 week       |
| 1m        | 1 month      |
| 3m        | 3 months     |
| 6m        | 6 months     |
| ytd       | Year to date |
| 1y        | 1 year       |
| 2y        | 2 years      |
| 5y        | 5 years      |

| Model ID                    | Notes                             |
| --------------------------- | --------------------------------- |
| `claude-sonnet-4-6`         | Default — fast and cost-effective |
| `claude-opus-4-7`           | Most capable, higher cost         |
| `claude-haiku-4-5-20251001` | Fastest and cheapest              |

## Output

**Predictions and backtests both land in the same `results/` root**, each
in its own self-describing, timestamped subfolder:

```
results/
├── predict_20260422_074503/            ← stock_predictor.py output
│   ├── predictions.md                  # multi-ticker markdown with embedded charts
│   └── charts/
│       ├── AAPL_1w.png
│       ├── TSLA_1m.png
│       └── INTC_1m.png
│
└── backtest_AAPL_20260422_075022/      ← PredictionTradingSystem.save_report output
    ├── report.md                       # backtest stats + prediction + trade log
    └── charts/
        ├── indicators.png
        ├── signals.png
        ├── performance.png
        └── risk.png
```

The `predict_` / `backtest_` prefix is applied automatically so runs from
both pipelines remain cleanly separated while sharing a single root.

### `predictions.md` — sections per ticker

| Section                                 | Content                                                                            |
| --------------------------------------- | ---------------------------------------------------------------------------------- |
| 📊 Prediction Summary                   | Direction, confidence, current price, price target + %, target date, risk level, net score |
| Embedded chart                          | Inline PNG with every selected panel                                               |
| 🟢 Key Bullish Factors                  | Up to 8 bullish factors with scoring detail (`+N pts`)                             |
| 🔴 Key Risk Factors / Bearish Signals   | Up to 8 bearish factors                                                            |
| 📐 Technical Levels to Watch            | Pivot points — R2, R1, PP, S1, S2                                                  |
| 📏 Fibonacci Retracement Levels         | 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100% of 6-month range                         |
| 📝 Analysis                             | Claude narrative (or deterministic summary when AI disabled)                       |

### Analysis chart panels

Three panels are always rendered:

1. **Price + Target** — 6-month close with projected target and (selectable) MA / Bollinger overlays.
2. **Confidence & Risk** — arc gauge showing confidence %, coloured direction pill, ATR-derived risk pill.
3. **Technical Signal Factors** — horizontal bar chart of the top scored factors (green = bullish, red = bearish).

Optional panels (present only when the matching `--indicators` category is selected):

| Panel                    | Category     |
| ------------------------ | ------------ |
| MACD (12, 26, 9)         | `trend`      |
| RSI (14)                 | `momentum`   |
| Stochastic (14, 3)       | `momentum`   |
| Volume + Spikes          | `volume`     |
| OBV                      | `volume`     |
| Support & Resistance     | `support`    |
| ATR (14)                 | `volatility` |
| Fundamental Indicators   | `fundamental` (15-metric colour-coded grid) |

## Technical indicators

All computed from Yahoo Finance OHLCV (1-year daily) + fundamentals snapshot.

### `trend`
SMA50, SMA200, EMA12/20/26, MACD (12/26/9), Golden Cross, Death Cross, MACD crossover, price vs SMA checks.

### `momentum`
RSI (14): oversold <30 / midline 50 / overbought >70.
Stochastic (14, 3): %K/%D crossover, oversold <20 / overbought >80.

### `volatility`
Bollinger Bands (20, 2σ), ATR (14) — ATR > 1.3× 20-day mean → high risk; < 0.8× → low risk.

### `volume`
OBV (trend), Volume Spike (>20-day mean + 2σ).

### `fundamental`
P/E (TTM), Forward P/E, P/B, P/S, EV/EBITDA, PEG, Revenue Growth, EPS Growth, Net Margin, Operating Margin, ROE, Debt/Equity, Current Ratio, Dividend Yield, Short Ratio.

### `support`
Trendlines (5-bar swing detection), Pivot Points (R2/R1/PP/S1/S2), Fibonacci Retracement (0%–100% over 6-month range).

Direction and confidence come from scoring — no random guessing. See
[`DESIGN.md`](DESIGN.md) for the full point table.

## Backtester

The same prediction engine powers an automated backtester built on
`Portfolio` + `RiskManager`:

```python
from src import PredictionTradingSystem

system = PredictionTradingSystem(
    ticker="AAPL", initial_capital=10_000, enable_ai=True,
)
result = system.backtest("2023-01-01", "2024-01-01")
prediction = system.predict()
system.save_report(result=result, prediction=prediction)
```

This produces a `results/backtest_AAPL_<timestamp>/` folder with:

| File                     | Contents                                       |
| ------------------------ | ---------------------------------------------- |
| `report.md`              | Backtest stats + trade log + prediction        |
| `charts/indicators.png`  | Price, MAs, Bollinger, MACD, RSI, ADX          |
| `charts/signals.png`     | Close with buy/sell markers per trade          |
| `charts/performance.png` | Equity curve + drawdown                        |
| `charts/risk.png`        | Per-trade P&L and ATR                          |

## Automated trading

`automated_trader.py` runs the same prediction + risk engine on a live
schedule. Orders are routed through a pluggable broker — the default
`PaperBroker` simulates fills against the latest yfinance quote, and any
real broker (Alpaca, IBKR, Binance, …) plugs in by implementing
`BaseBroker` (`get_quote`, `place_order`, `close_position`).

### CLI

```bash
# Single dry-run cycle (no orders submitted), emit signals only
python automated_trader.py --tickers AAPL TSLA --dry-run --once

# Paper-trade every 5 minutes (unlimited), persist portfolio state
python automated_trader.py --tickers AAPL MSFT NVDA --interval 300

# Claude-fused predictions + enforce US equities market hours
ANTHROPIC_API_KEY=sk-ant-... python automated_trader.py \
    --tickers AAPL --ai --market-hours --cycles 12 --interval 300
```

Each cycle, for every ticker, the engine:

1. Refreshes OHLCV + indicators, closes any position that hits its stop
   or take-profit.
2. Marks the portfolio to the latest quote.
3. Asks `UnifiedPredictor` for a signal and offers it to `RiskManager`
   (position sizing, R:R, daily loss cap, concurrency limit).
4. Submits an approved order through the broker, records the fill in
   `trades.csv`, and snapshots the portfolio to `portfolio_state.json`
   so a fresh start resumes exactly where it left off.

### Output folder

```
results/live_20260422_081000/
├── portfolio_state.json      # resumable snapshot (cash, positions, trades, equity curve)
├── trades.csv                # every open / close action logged with ts, price, qty, pnl, reason
└── prediction_trading.log    # structured cycle log
```

### Python API

```python
from src import PredictionTradingSystem

system = PredictionTradingSystem(
    ticker="AAPL", initial_capital=25_000, enable_ai=True,
)
trader = system.build_auto_trader(
    tickers=["AAPL", "MSFT", "NVDA"],
    state_path="results/live/portfolio_state.json",
    trade_log_path="results/live/trades.csv",
    dry_run=False,
    enforce_market_hours=True,
)
# one-shot cycle
report = trader.run_once()
print(report.opened, report.closed, report.equity)

# continuous loop — every 5 min, up to 24 cycles
trader.run(interval_seconds=300, max_cycles=24)
```

### Config (`config/default.yaml`)

```yaml
trader:
  interval_seconds: 300        # seconds between cycles
  enforce_market_hours: false  # only trade 09:30–16:00 ET, Mon–Fri
  slippage_bps: 0.0            # paper-broker slippage model (basis points)
  dry_run: false               # signals only, never place orders
```

All portfolio sizing, stop / take-profit ATR multiples, min R:R, daily
loss cap, and min confidence still come from the existing `portfolio:`
/ `risk:` / `signals:` sections, so backtest parameters and live
parameters stay in lockstep.

### Risk profiles

`config/risk_profiles.yaml` ships three presets selectable from the Settings page:

| Profile | Position size | Daily limit | Min confidence | Stop ATR | Target ATR | Min R:R |
| ------- | ------------- | ----------- | -------------- | -------- | ---------- | ------- |
| conservative | 3% | 1% | 60% | 1.5× | 3.0× | 2.0 |
| moderate | 5% | 2% | 40% | 2.0× | 3.0× | 1.5 |
| aggressive | 10% | 5% | 30% | 2.5× | 4.0× | 1.2 |

## Watchlist scanner

`scan_watchlist.py` screens many tickers in parallel with the rule-based
engine (no API key needed) and prints a ranked confidence table.

```bash
# Scan a list of tickers (all six indicator categories)
python scan_watchlist.py AAPL TSLA NVDA MSFT GOOG

# Only show results with ≥ 40% confidence
python scan_watchlist.py AAPL TSLA NVDA --min-confidence 0.4

# Restrict to specific indicator categories
python scan_watchlist.py AAPL TSLA --indicators trend momentum

# Increase parallelism
python scan_watchlist.py $(cat my_watchlist.txt) --workers 8
```

Output is a colour-coded terminal table sorted by confidence descending,
showing direction, confidence %, current price, and top 3 scored factors.

`WatchlistScanner` is also available as a Python API (`src/scanner.py`):

```python
from src.scanner import WatchlistScanner

results = WatchlistScanner(min_confidence=0.4, workers=8).scan(["AAPL", "TSLA", "NVDA"])
for r in results:
    print(r.ticker, r.direction, r.confidence)
```

## Prompt caching

The Claude system prompt carries `cache_control: {type: "ephemeral"}`.
On repeated calls within a 5-minute window, Anthropic serves the cached
prefix at ~10% of input token cost (same mechanism as `stock-prediction`).

## Running tests

```bash
pytest tests/ -v
# 32 passed
```

All tests use synthetic OHLCV fixtures, so they run offline and without
an API key.

## Disclaimer

For educational and research purposes only. Predictions are derived from
technical and fundamental signals, but past performance does not guarantee
future results.
