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
uv run pytest backend/tests/ -v   # 14 test files, all offline — no API key needed
uv run stock-predictor --tickers AAPL --no-ai
```

---

## Launch the Web UI

```bash
make ui-dev    # or: uv run streamlit run frontend/app.py
```

Opens at `http://localhost:8501`.

### Getting Started

**Header:** The app name appears at the top-left. A **🌙 Dark / ☀️ Light** toggle in the top-right switches the entire UI between a dark (`#0f1318` background) and light theme.

**Top navigation bar:** Eight icon+label buttons select the active page. The active page button is highlighted in green; inactive buttons show a gray border.

**Config Info Bar:** A one-line caption below the page title on every page except Settings shows: `Data source · Broker type · AI model` (or "AI disabled"). Use this to confirm your active configuration at a glance before running predictions or trades.

**Sidebar watchlist:** A persistent left sidebar shows a list of saved tickers with live price badges. Click **＋** to add a ticker; click **✕** to remove one. Clicking a ticker name navigates to the Predict page with that ticker pre-filled. The watchlist is saved to `watchlist.json` and survives page navigation and browser refreshes.

---

### Page Reference

#### 1. Dashboard (📊)

**Purpose:** Monitor your live or most recent portfolio — equity growth, open positions, and risk metrics — all in one view.

**Loading portfolio data (in priority order):**
1. Automatically reads from a running AutoTrader (if started on the Trading page in the same session).
2. Falls back to the results of a completed Backtest run in the same session.
3. Shows a file uploader — drag in a saved `results/live_*/portfolio_state.json`.

**Overview tab:**

| Widget | Description |
|---|---|
| Portfolio Value | Total equity (cash + unrealised positions), with return % vs initial capital |
| Cash Available | Uninvested cash balance |
| Day P&L | Intraday profit/loss in $ and as a % of initial capital |
| Open Positions | Count of open positions / max allowed (e.g., `2 / 5`) |
| Equity Curve | Plotly line chart with area fill; dashed initial-capital baseline; hoverable data points |
| Open Positions table | Ticker · Side · Qty · Entry $ · Current $ · Unrealised P&L $ · Return % · Stop $ · Target $ |
| Recent Trades table | Last 20 closed trades: Ticker · Side · Qty · Entry · Exit · P&L · Return % · Result (Win/Loss) · Reason |

**Risk tab:**

| Widget | Description |
|---|---|
| Max Drawdown % | Largest peak-to-trough equity decline |
| Win Rate % | Percentage of closed trades that were profitable |
| Profit Factor | Gross wins / gross losses (>1 = net positive) |
| Total Trades | Number of closed trades |
| Daily Loss vs Cap | Colored progress bar showing today's loss vs the 2% daily cap |
| Position Concentration | Horizontal bar chart: % of portfolio equity by ticker |

**Auto-refresh:** While the AutoTrader is running, the page refreshes every 15 seconds automatically.

---

#### 2. Predict (🔮)

**Purpose:** Run a rule-based or AI-assisted prediction for a single ticker and explore the signal, timing, and price chart.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Ticker Symbol | Any valid ticker (e.g., `AAPL`) | Pre-filled from watchlist click |
| Timeframe | `1d` `1w` `1m` `3m` `6m` `ytd` `1y` `2y` `5y` | `1w` |
| Indicator Categories | multiselect: trend · momentum · volatility · volume · support · fundamental | all six |
| Enable AI (Claude) | toggle | off — requires `ANTHROPIC_API_KEY` in `.env` |
| 4H Confluence | toggle | off — fetches 1H OHLCV, resamples to 4H, adds up to ±1 bonus point |
| Save report | checkbox | off — writes `results/predict_*/predictions.md` + PNG |

Click **Run Prediction** (disabled until a ticker is entered).

**Signal tab** (first result tab):

- **Prediction card:** Direction badge (`BUY` / `SELL` / `HOLD`) + confidence % with progress bar; Current Price · Price Target (with % change) · Risk Level (Low/Medium/High); up to 5 Bullish Factors (▲) and 5 Bearish Factors (▼) with detail text.
- **Timing Recommendation card** (when available): Action label — one of `BUY NOW` · `BUY ON DIP` · `BREAKOUT ENTRY` · `SELL NOW` · `TRAILING STOP` · `HOLD` · `WAIT` — with color-coded badge; Entry $ · Stop Loss $ · Take Profit $.
- **Market Index table:** VIX, SPY, QQQ, DXY — Price · 1D % · 5D % · 30D % · Trend (↑ Above / ↓ Below SMA50). Green/red color-coded. Requires macro context (fetched automatically when AI is on or enriched context is available).

**Candlestick Chart tab:**

Interactive Plotly OHLC chart (last 120 bars):
- Bullish (green) / bearish (red) candles
- SMA20 (gold) and SMA50 (blue) overlays
- Entry price line (blue dot), stop loss line (red dash), take profit line (green dash) with labels
- Volume sub-panel below (bars colored per candle direction)

**Analysis Chart tab:**

Static multi-panel matplotlib PNG — the same image written to `results/` when "Save report" is checked. Shows price + target, confidence gauge, and category-conditional indicator panels.

**Session caching:** Results are stored in session state. Switching tabs or adjusting the page does not re-run the prediction. Click **Run Prediction** again to refresh.

---

#### 3. Scanner (🔍)

**Purpose:** Screen a list of tickers simultaneously and surface the strongest BUY and SELL signals.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Watchlist | One ticker per line (textarea) | Sidebar watchlist tickers |
| Min Confidence | 0.00–1.00 (step 0.05) | 0.40 |
| Parallel Workers | 1–16 | 4 |
| Indicator Categories | multiselect: trend · momentum · volatility · volume · support · fundamental | all six |

Click **Scan Watchlist**. A spinner shows the count of tickers being processed.

**Results:**

- **4 summary cards:** Total Scanned · BUY count · SELL count · HOLD/below-threshold count.
- **Results table:** Ticker · Signal · Confidence % · Price $ · Top Factors (top-3 scoring factors). Sorted by confidence descending. Per-row errors shown in red.
- **CSV Export button:** Downloads the full results table as a `.csv` file.

**Note:** The scanner skips AI calls and chart generation — it is rule-based only. The news/macro/sector categories are not available from the UI multiselect; use the CLI (`--indicators`) for those. For a deeper analysis of any result, click that ticker in the sidebar watchlist to open it in Predict.

---

#### 4. Backtest (📅)

**Purpose:** Simulate the prediction and risk engine over a historical date range and evaluate strategy performance.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Ticker | Any valid ticker | — |
| Start Date | Date picker | 1 year ago |
| End Date | Date picker | Today |
| Initial Capital ($) | Number input | 10,000 |
| Commission Per Trade ($) | Number input | 1.00 |

Click **Run Backtest** (validates end > start).

**Results — 8 KPI cards:**

Total Return % · Max Drawdown % · Win Rate % · Profit Factor · Total Trades · Avg Win $ · Avg Loss $ · Final Equity $

**Equity Curve tab:** Plotly area chart with initial capital baseline. Hover shows date and equity value.

**Candlestick + Trades tab:** Interactive OHLC chart (same as Predict) with trade markers overlaid — green triangle-up at each buy entry, red triangle-down at each sell exit.

**Trade Log tab:** Full scrollable table of every trade: Ticker · Side · Qty · Entry $ · Exit $ · P&L $ · Return % · Result (Win/Loss) · Reason (stop/target/end-of-data).

**Save Full Report button:** Writes `report.md` + four chart PNGs to `results/backtest_TICKER_YYYYMMDD_HHMMSS/`.

**Interpreting results:**
- Profit Factor > 1.5 is a reasonable baseline for a working strategy.
- Win rate alone is misleading — a 40% win rate with 3:1 R:R is net profitable.
- Max Drawdown drives position sizing: if uncomfortable, reduce `max_position_size_pct` in Settings.
- Compare against buy-and-hold over the same period for context.

---

#### 5. Trading (⚡)

**Purpose:** Start, monitor, and stop the AutoTrader — a live paper-trading loop that runs predictions and places orders on a configurable cycle.

**Stopped state — start form:**

| Control | Values | Default |
|---|---|---|
| Tickers | One per line (textarea) | — |
| Cycle Interval | 60–3600 seconds | 300 (5 min) |
| Dry Run | toggle | on — signals only, no orders placed |
| Enforce Market Hours | toggle | off — when on, only trades 09:30–16:00 ET Mon–Fri |
| State File Path | text input | `results/live/portfolio_state.json` |

Click **Start AutoTrader**.

**Running state — live dashboard:**

- **Status card:** "🟢 Running — N cycles completed" + **Stop AutoTrader** button.
- **3 KPI cards:** Portfolio Value (with return %) · Cash Available · Open Positions count.
- **Equity Curve:** Plotly chart, updates each cycle.
- **Open Positions table:** same columns as Dashboard.
- **Last Cycle panel:** table of actions taken this cycle (Ticker · Action · Direction · Confidence · Price · Reason); errors expander shows per-ticker exceptions from the last cycle.
- **Error Log expander:** full error history across all cycles (last 20 entries).

**Auto-refresh:** The page reruns every 10 seconds while the AutoTrader is running.

**Threading:** AutoTrader runs in a daemon thread. Results are passed to the UI via a `queue.Queue`. The thread stops when you click **Stop AutoTrader** or when the Streamlit process exits. Reloading the browser page will show stale portfolio data until the next cycle completes and the queue is drained.

---

#### 6. Portfolio Builder (🧱)

**Purpose:** Analyse a multi-ticker portfolio of stocks and ETFs for correlation, sector exposure, and diversification.

**Inputs:**

| Control | Values | Default |
|---|---|---|
| Tickers | One per line (stocks and/or ETFs) | `SPY QQQ XLK BND GLD` |
| Lookback Period | 30–1260 trading days | 252 (one year) |

Click **Analyze Portfolio**.

**Results:**

- **Holdings cards** (one per ticker): ETF badge or Stock badge · display name · for ETFs: category and expense ratio %.
- **Diversification Score:** 0–1 (higher = lower average pairwise correlation = better diversification). Green ≥ 0.5, orange ≥ 0.25, red < 0.25.
- **Correlation Matrix heatmap:** Pairwise return correlations color-coded: red (≥ 0.85 highly correlated) → orange (≥ 0.60) → light green (< 0.30) → light blue (negative).
- **Sector Exposure bar chart:** Equal-weighted GICS sector breakdown (horizontal bars, % weight).
- **Recommendations list:** Flags pairs with correlation > 0.85 as candidates for replacement; suggests sector gaps; warns on high expense ratios.

---

#### 7. Alerts (🔔)

**Purpose:** Create price, confidence, and P&L triggers that fire when a condition is met, with a persistent log of all triggered alerts.

**Active Alerts tab:**

One card per alert: Ticker (bold) · Created timestamp (gray) · Trigger condition (color-coded green if "above"/"≥", red if "below"/"≤") · **✕ Delete** button.

**Check Alerts Now button:** Manually evaluates all active alerts against current prices via yfinance. Alerts that fire are moved to the Triggered Log and shown as toast notifications.

**Create Alert tab:**

| Field | Options |
|---|---|
| Ticker | Text input (default: AAPL) |
| Trigger Type | Price above · Price below · Confidence ≥ · Daily P&L ≥ · Daily P&L ≤ |
| Value | $ for price triggers; 0–100 for confidence/P&L % |

Click **Create Alert** → success toast.

**Triggered Log tab:** Last 50 triggered alerts (newest first): Ticker · Fired timestamp · Condition · Actual value at trigger. **Clear Log** button removes all entries.

**Persistence:** Alerts are saved to `alerts.json` in the working directory and survive page navigation and browser refreshes. They are **not** evaluated automatically in the background — use **Check Alerts Now** or pair with the Trading page for continuous monitoring.

---

#### 8. Settings (⚙️)

**Purpose:** Configure all system parameters and save them to `config/default.yaml`.

The Config Info Bar does **not** appear on this page — Settings is where those values are set.

**Risk Profile section:**

Select a preset (Conservative / Moderate / Aggressive) and click **Apply Profile** to pre-fill the form fields below. Review the values before saving — Apply does not write to disk.

**Portfolio section:**

| Parameter | Range | Default |
|---|---|---|
| Initial Capital ($) | 1,000–10,000,000 | 10,000 |
| Max Concurrent Positions | 1–50 | 5 |
| Max Position Size (% of equity) | 1%–50% | 5% |
| Commission Per Trade ($) | 0–100 | 1.00 |

**Risk Management section:**

| Parameter | Range | Default |
|---|---|---|
| Max Daily Loss % (halt trigger) | 0.5%–10% | 2% |
| Min Risk:Reward Ratio | 0.5–10 | 1.5 |
| Stop Loss ATR Multiplier | 0.5–10 | 2.0 |
| Take Profit ATR Multiplier | 0.5–20 | 3.0 |

**Signal Settings section:**

| Parameter | Range | Default |
|---|---|---|
| Min Confidence Threshold | 0–1 | 0.40 |
| 4H Confluence Bonus (points) | 0–10 | 1 |
| AI Weight (0 = rule-only, 1 = AI-only) | 0–1 | 0.50 |

**Indicator Categories:** Multiselect of all nine categories (trend · momentum · volatility · volume · support · fundamental · news · macro · sector). Unchecking a category removes it from scoring, chart panels, and AI context.

**AI / Claude Settings:**

| Parameter | Options / Range | Default |
|---|---|---|
| Enable AI Predictor | toggle | off |
| Claude Model | claude-sonnet-4-6 · claude-opus-4-7 · claude-haiku-4-5-20251001 | claude-sonnet-4-6 |
| AI Prediction Timeframe | 1d 1w 1m 3m 6m ytd 1y 2y 5y | 1m |
| Max Response Tokens | 500–8,000 | 2,000 |

**Auto-Trader Settings:**

| Parameter | Range | Default |
|---|---|---|
| Cycle Interval (seconds) | 60–3600 | 300 |
| Dry Run (signals only) | toggle | off |
| Enforce Market Hours | toggle | off |
| Simulated Slippage (basis points) | 0–100 | 0 |

**Data Source:** yfinance (default) · alpaca · both. Selecting alpaca or both requires `ALPACA_API_KEY` and `ALPACA_API_SECRET` in `.env`.

**Broker:** paper (default) · alpaca.

**Save Settings button:** Writes all values to `config/default.yaml`. Changes take effect immediately for new predictions and scans. The AutoTrader must be stopped and restarted to pick up new settings.

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
  model: claude-sonnet-4-6
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
