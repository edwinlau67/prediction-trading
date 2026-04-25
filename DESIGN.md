# Design Specification — Stock Market Prediction & Automated Trading System

| Field | Value |
|---|---|
| Version | 1.4 |
| Status | Active |
| Last updated | 2026-04-25 |

---

## 1. Purpose and Scope

Stock Market Prediction & Automated Trading System is an end-to-end platform that combines rule-based technical analysis, AI-assisted prediction via Claude, automated paper/live trading, bar-by-bar backtesting, and an interactive Streamlit web UI. It is designed for educational use and individual research.

**In scope:** signal generation, position management, paper and live brokerage abstraction, backtesting, reporting, web UI.

**Out of scope:** direct brokerage integration beyond the `BaseBroker` interface, real-time tick data, portfolio optimisation across multiple strategies simultaneously.

---

## 2. Source Lineage

| Source | Contribution |
|---|---|
| [`edwinlau67/stock-prediction`](https://github.com/edwinlau67/stock-prediction) | Claude tool-use predictor, `predictions.md`, six indicator categories, fundamental scoring |
| [`edwinlau67/automated-trading-systems`](https://github.com/edwinlau67/automated-trading-systems) | Multi-timeframe scoring, portfolio/position/trade primitives, ATR-based risk manager, bar-by-bar backtester |
| [`edwinlau67/algorithmic-trading-system`](https://github.com/edwinlau67/algorithmic-trading-system) | Algorithmic trading strategies, additional risk management patterns |

---

## 3. Architecture Overview

### Monorepo layout

```
prediction-trading/           ← uv workspace root (pyproject.toml)
├── backend/                  ← package: prediction-trading-backend
│   ├── src/prediction_trading/
│   │   ├── api/              ← FastAPI REST layer
│   │   ├── _cli/             ← CLI entry points (stock-predictor, …)
│   │   ├── prediction/
│   │   ├── trading/
│   │   ├── backtest/
│   │   ├── indicators/
│   │   ├── reporting/
│   │   ├── data_fetcher.py
│   │   ├── scanner.py
│   │   └── system.py
│   └── tests/
├── frontend/                 ← package: prediction-trading-frontend
│   ├── app.py                ← Streamlit entry point
│   └── ui/                   ← pages, components, theme, watchlist
├── config/
├── examples/
└── Makefile
```

### Component diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             USER INTERFACES                                 │
│  frontend/app.py (Streamlit)   stock-predictor   automated-trader           │
│  scan-watchlist                examples/                                    │
└──────────────┬──────────────────────────┬──────────────────────────────────┘
               │                          │
┌──────────────▼──────────────────────────▼──────────────────────────────────┐
│              REST API  (prediction_trading.api — FastAPI :8000)             │
│  POST /predict/   POST /scan/   POST /backtest/   GET+POST /trading/…       │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│            prediction_trading/system.py — PredictionTradingSystem           │
│  fetch()  predict()  backtest()  save_report()  build_auto_trader()         │
└──────┬───────────────────┬──────────────────┬───────────────────────────────┘
       │                   │                  │
┌──────▼──────────┐  ┌─────▼─────────────┐  ┌─▼───────────────────────────────┐
│  PREDICTION     │  │    TRADING        │  │          BACKTEST               │
│                 │  │                   │  │                                 │
│ SignalScorer    │  │ Portfolio         │  │ Backtester (bar-by-bar,         │
│ AIPredictor     │  │ RiskManager       │  │ 200-bar warmup, no look-ahead)  │
│ UnifiedPredictor│  │ AutoTrader        │  └─────────────────────────────────┘
└──────┬──────────┘  │ PaperBroker       │
       │             │ StateStore        │
┌──────▼──────────┐  └───────────────────┘
│ scanner.py      │
│ WatchlistScanner│ (parallel, no AI or charts)
└──────┬──────────┘
       │
┌──────▼──────────────────────────────────────────────────────────────────────┐
│                              REPORTING                                      │
│  PredictionChart   PredictionReportWriter   ChartBuilder   ReportWriter     │
│  results/predict_*/   results/backtest_*/   results/live_*/                 │
└──────┬──────────────────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────────────────┐
│                           INDICATORS & DATA                                 │
│  TechnicalIndicators (SMA/EMA, MACD, RSI, Stoch, BB, ATR, ADX, OBV)         │
│  SupportResistance (pivots, Fibonacci, swing trendlines)                    │
│  DataFetcher (yfinance OHLCV + fundamentals)                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Primary entry point

`prediction_trading/system.py:PredictionTradingSystem` is the single façade for all Python API usage. The REST API routers, CLI entry points, and UI pages construct it and call its methods. Direct use of sub-modules is permitted but not required.

---

## 4. Component Specifications

### 4.1 DataFetcher (`prediction_trading/data_fetcher.py`)

**Responsibility:** Fetch OHLCV history and fundamentals from Yahoo Finance.

**Interface:**

```python
DataFetcher(interval: str = "1d")
    .fetch(ticker, *, lookback_days=365, include_fundamentals=True) -> MarketData
    .fetch_history(ticker, *, lookback_days=None, start=None, end=None) -> pd.DataFrame
    .fetch_fundamentals(ticker) -> dict
```

**`MarketData` fields:** `ticker`, `ohlcv: pd.DataFrame`, `current_price: float`, `fundamentals: dict`.

**Constraints:**
- OHLCV index is a `DatetimeIndex` with timezone stripped.
- `fetch_fundamentals` is best-effort; exceptions are caught and an empty dict returned.
- The `interval` parameter accepts any yfinance-valid interval string (`"1d"`, `"1h"`, `"1wk"`, etc.).

---

### 4.2 TechnicalIndicators (`prediction_trading/indicators/technical.py`)

**Responsibility:** Stateless pandas/numpy indicator calculations. No external dependencies.

**Indicators computed by `compute_all(ohlcv)`:**

| Column | Formula |
|---|---|
| `SMA20`, `SMA50`, `SMA200` | Simple moving average |
| `EMA12`, `EMA20`, `EMA26` | Exponential moving average (`ewm`, `adjust=False`) |
| `MACD`, `MACD_signal`, `MACD_hist` | EMA12 − EMA26; signal = 9-period EMA of MACD |
| `RSI` | Wilder RSI (14); `fillna(50.0)` for early NaN |
| `Stoch_K`, `Stoch_D` | %K (14-period), %D (3-period SMA of %K) |
| `BB_upper`, `BB_mid`, `BB_lower` | 20-period SMA ± 2σ |
| `ATR` | Wilder ATR (14) via ewm |
| `ADX`, `+DI`, `−DI` | 14-period; `dx.fillna(50.0)` prevents NaN propagation when +DI = −DI = 0 |
| `OBV` | `cumsum(sign(close.diff()) * volume)` |
| `VolumeSpike` | Boolean: `volume > mean20 + 2σ` |

All methods accept `pd.Series` (or `pd.DataFrame` for `compute_all`) and return pandas objects. `compute_all` returns a copy with the indicators attached as additional columns.

---

### 4.3 SupportResistance (`prediction_trading/indicators/levels.py`)

**Responsibility:** Compute classic support/resistance levels.

| Output | Method |
|---|---|
| Pivot points (R2, R1, PP, S1, S2) | Classical formula on prior-day OHLC |
| Fibonacci retracement levels | 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100% over 6-month range |
| Swing trendlines | 5-bar swing-high / swing-low detection |

---

### 4.4 SignalScorer (`prediction_trading/prediction/signal_scorer.py`)

**Responsibility:** Emit `Factor` objects for each active indicator rule and compute a net direction + confidence.

**Scoring rules:**

| Category | Rule | Points |
|---|---|---|
| `trend` | Price above/below SMA50 / SMA200 | ±1 |
| `trend` | Golden Cross / Death Cross | ±2 |
| `trend` | MACD bullish / bearish crossover event | ±2 |
| `trend` | MACD above / below signal line | ±1 |
| `trend` | EMA12 vs EMA26 | ±1 |
| `momentum` | RSI < 30 / > 70 (oversold / overbought) | ±2 |
| `momentum` | RSI above / below 50 midline | ±1 |
| `momentum` | Stochastic %K/%D crossover | ±1 |
| `momentum` | Stochastic oversold (<20) / overbought (>80) | ±1 |
| `volatility` | Price outside Bollinger Band | ±1 |
| `volatility` | ATR regime (calm / elevated vs 20-day mean) | ±1 |
| `volume` | OBV trend (rising / falling) | ±1 |
| `volume` | Volume spike on up / down day | ±1 |
| `support` | Price above / below Pivot Point | ±1 |
| `support` | Rising support hold / support broken | ±1 |
| `fundamental` | P/E, PEG, growth, margins, ROE, D/E, CR, P/B | ±1 each |
| *(bonus)* | Weekly timeframe agrees with daily | ±2 |
| *(bonus)* | 4H timeframe agrees with daily | ±1 (= `max(1, multi_timeframe_bonus − 1)`) |

**Outputs:**

```
direction   = sign(net_points)                  # "bullish" | "bearish" | "neutral"
confidence  = min(1.0, abs(net_points) / 10.0) # 0..1  (10 points = 100%)
```

**Interface:**

```python
SignalScorer(
    categories: tuple[str, ...] | None = None,  # None = all six
    weights: dict | None = None,                 # legacy component weights
    multi_timeframe_bonus: int = 2,
)
    .score(
        df: pd.DataFrame,
        *,
        weekly: pd.DataFrame | None = None,
        hourly_4h: pd.DataFrame | None = None,
        fundamentals: dict | None = None,
    ) -> ScoredSignal
```

**`ScoredSignal` fields:** `direction`, `confidence`, `net_points`, `factors: list[Factor]`, plus normalised 5-component view (`trend`, `momentum`, `reversal`, `volatility`, `price_action`) for backtester compatibility.

**`Factor` fields:** `category`, `name`, `direction`, `points`, `detail`, `signed` (signed magnitude).

**Category filtering:** Rules in omitted categories are skipped entirely; the 5-component view treats them as 0.

---

### 4.5 AIPredictor (`prediction_trading/prediction/ai_predictor.py`)

**Responsibility:** Call the Anthropic Messages API using Claude tool-use and return an `AIPrediction`.

**Tool-use flow:**

```
AIPredictor ──► Anthropic Messages API
                    │  system:   SYSTEM_PROMPT  (cache_control: ephemeral)
                    │  tools:    [stock_prediction]
                    │  messages: [{user: "Predict {ticker}..."}]
                    ▼
            stop_reason == "tool_use"
                    │
                    ▼
       AIPredictor._predict_from_market(MarketData, timeframe)
                    │  local: yfinance OHLCV, TechnicalIndicators.compute_all,
                    │  SignalScorer.score, price target projection → JSON result
                    ▼
            Second API call with tool_result ──► narrative response
```

**Prompt caching:** The system prompt is tagged `cache_control: {"type": "ephemeral"}`. Repeated calls within 5 minutes incur ~10% of the first-call input token cost.

**Degraded mode:** When no `ANTHROPIC_API_KEY` is present, `AIPredictor` is constructed with `api_key=None` and the second API call is skipped; the local tool result is returned directly.

**`AIPrediction` fields:** `direction`, `confidence`, `price_target`, `target_date`, `risk_level`, `key_factors: list[str]`, `narrative`, `fundamentals`.

---

### 4.6 UnifiedPredictor (`prediction_trading/prediction/predictor.py`)

**Responsibility:** Fuse the rule-based signal and optional AI prediction into a single `Prediction`.

**Fusion formula:**

```python
rule_signed = sign(rule.direction) * rule.confidence   # ∈ [−1, +1]
ai_signed   = sign(ai.direction)   * ai.confidence

blended = (1 − ai_weight) * rule_signed + ai_weight * ai_signed

direction  = "bullish" if blended > 0.05 else "bearish" if blended < −0.05 else "neutral"
confidence = min(1.0, abs(blended))
```

When AI is disabled, `blended = rule_signed` (equivalent to `ai_weight = 0`).

**Interface:**

```python
UnifiedPredictor(
    scorer: SignalScorer | None = None,
    ai: AIPredictor | None = None,
    *,
    ai_enabled: bool = False,
    ai_weight: float = 0.5,
    min_confidence: float = 0.40,
    timeframe: str = "1w",
)
    .predict(
        ticker: str,
        df: pd.DataFrame,
        *,
        current_price: float,
        weekly: pd.DataFrame | None = None,
        hourly_4h: pd.DataFrame | None = None,
        fundamentals: dict | None = None,
    ) -> Prediction
```

**`Prediction` fields:** `ticker`, `direction`, `confidence`, `current_price`, `price_target`, `target_date`, `risk_level`, `rule_signal`, `ai_signal`, `factors`, `meta` (includes `actionable` flag: `confidence >= min_confidence and direction != "neutral"`).

---

### 4.7 Multi-Timeframe Confluence

`SignalScorer.score()` accepts three timeframe DataFrames:

| Parameter | Source | Bonus |
|---|---|---|
| `df` (required) | Daily OHLCV + indicators | Base scoring |
| `weekly` | `df.resample("W").agg(...)` | ±2 points when weekly direction agrees with daily |
| `hourly_4h` | 1h OHLCV resampled to 4H | ±`max(1, multi_timeframe_bonus − 1)` points when 4H agrees |

The 4H data must be fetched separately via `DataFetcher(interval="1h")` and resampled before passing. `system.predict(market, hourly_4h=df_4h)` is the canonical path.

---

### 4.8 Category Filtering

The `--indicators` CLI flag, the `indicators.categories` config key, and the Settings page UI all drive the same three things in lockstep:

1. **Scoring** — rules in omitted categories are skipped; their points are treated as 0.
2. **Chart panels** — only panels matching the active categories render; the three base panels (Price+Target, Confidence arc, Signal Factors bar) always render.
3. **AI tool output** — active categories are embedded in the system prompt so Claude's narrative stays consistent with the chart and factors.

All six categories are active by default: `trend`, `momentum`, `volatility`, `volume`, `support`, `fundamental`.

---

### 4.9 Portfolio (`prediction_trading/trading/portfolio.py`)

**Responsibility:** Track cash, open positions, closed trades, and the equity curve.

**Cash model (symmetric margin):** `open()` deducts `quantity × entry_price + commission` from cash for both long and short positions. This treats the full notional as margin posted.

**`close()` proceeds:**

| Side | Formula |
|---|---|
| `long` | `quantity × exit_price − commission` |
| `short` | `(2 × entry_price − exit_price) × quantity − commission` |

The short formula returns the posted collateral plus the unrealised P&L, net of commission.

**`equity(prices)` formula:**

```python
equity = cash + Σ (pos.unrealised(px) + pos.entry_price × pos.quantity)
```

This is algebraically equivalent to `cash + Σ (px × qty)` for longs and `cash + Σ (2×entry − px) × qty` for shorts — both correctly track mark-to-market equity under the margin model.

**Key properties:** `return_pct`, `win_rate`, `max_drawdown` (all computed from `equity_curve`).

---

### 4.10 RiskManager (`prediction_trading/trading/risk_manager.py`)

**Responsibility:** Gate every trade signal through eight sequential checks and size the position.

**Gates (evaluated in order):**

| # | Gate | Default |
|---|---|---|
| 1 | Direction is not neutral | — |
| 2 | `confidence >= min_confidence` | 0.40 |
| 3 | Open positions < `max_positions` | 5 |
| 4 | Ticker not already in portfolio | — |
| 5 | Daily loss cap not triggered | 2% of day-start equity |
| 6 | `atr > 0` | — |
| 7 | `reward_per_share / risk_per_share >= min_risk_reward` | 1.5 |
| 8 | `quantity >= 1` after sizing | — |

**Stop and target calculation:**

| Side | Stop | Target |
|---|---|---|
| Long | `price − stop_atr_mult × ATR` | `price + target_atr_mult × ATR` |
| Short | `price + stop_atr_mult × ATR` | `price − target_atr_mult × ATR` |

**Position sizing:**

```python
max_notional = equity × max_position_size_pct
quantity      = int(max_notional // price)
# reduce if cost > available cash
```

**`TradeProposal` fields:** `ticker`, `side`, `quantity`, `entry_price`, `stop_loss`, `take_profit`, `risk_per_share`, `risk_reward`, `rationale`.

**Default parameters** (all overridable via `config/default.yaml` or constructor kwargs):

| Parameter | Default |
|---|---|
| `min_confidence` | 0.40 |
| `max_positions` | 5 |
| `max_position_size_pct` | 0.05 (5%) |
| `max_daily_loss_pct` | 0.02 (2%) |
| `min_risk_reward` | 1.5 |
| `stop_loss_atr_mult` | 2.0 |
| `take_profit_atr_mult` | 3.0 |

---

### 4.11 Broker Abstraction (`prediction_trading/trading/broker.py`)

**`BaseBroker` interface:**

```python
class BaseBroker(ABC):
    def get_quote(self, ticker: str) -> float: ...
    def place_order(self, order: Order) -> Fill: ...
    def close_position(self, ticker: str, portfolio: Portfolio) -> Fill | None: ...
    def sync(self, portfolio: Portfolio) -> None: ...
```

**`PaperBroker`:** Fills at `quote ± (quote × slippage_bps / 10_000)`. Applies default 2%/3% stop/target if the order omits them.

**`RecordingBroker`:** Test double that records calls without hitting any market.

Real brokers (Alpaca, IBKR, etc.) implement `BaseBroker`.

---

### 4.12 AutoTrader (`prediction_trading/trading/auto_trader.py`)

**Responsibility:** Orchestrate repeated prediction → risk gate → order cycles.

**Single cycle (`run_once()`):**

```
for each ticker:
  1. Check open position for stop/take-profit → close if triggered
  2. mark(portfolio, prices)
  3. fetch OHLCV → compute indicators → UnifiedPredictor.predict()
  4. RiskManager.evaluate() → TradeProposal | None
  5. if proposal and not dry_run: broker.place_order() → record Fill
  6. StateStore.save() + append to trades.csv
```

**Continuous loop (`run()`):** Calls `run_once()`, sleeps `interval_seconds`, repeats until `max_cycles` reached or interrupted.

**Threading model (Streamlit UI):** The Trading page starts `AutoTrader.run_once()` in a `threading.Thread(daemon=True)`. A `queue.Queue` stored in `st.session_state` carries `CycleReport` objects from the thread back to the UI. Each call to `render()` drains the queue, then calls `st.rerun()` after a 10-second sleep for live updates.

**`CycleReport` fields:** `started_at`, `finished_at`, `actions: list[TickerAction]`, `equity`, `cash`, `errors`.

**`TickerAction` fields:** `ticker`, `timestamp`, `action`, `reason`, `direction`, `confidence`, `price`, `quantity`, `pnl`, `stop_loss`, `take_profit`.

---

### 4.13 Backtester (`prediction_trading/backtest/backtester.py`)

**Responsibility:** Replay a price series bar-by-bar using the live prediction and risk pipeline.

**Algorithm:**

```
1. Compute indicators on full OHLCV (warmup_bars=200 default).
2. Drop bars with NaN ATR or SMA50.
3. For each bar i (from 1 to N−1):
   a. Check open position for stop/take-profit → close if triggered.
   b. portfolio.mark(ts, {ticker: close})
   c. Skip if position already open (no stacking).
   d. predictor.predict(ticker, history[:i+1], current_price=close)
   e. risk.evaluate(prediction, portfolio, atr, ts)
   f. portfolio.open(Position(...)) if proposal is not None
4. EOD flush: close any remaining position at final bar price.
```

**No look-ahead guarantee:** The predictor only sees `ohlcv[:i+1]` at bar `i`.

**`BacktestResult.summary()` fields:** `ticker`, `period`, `initial_capital`, `final_equity`, `return_pct`, `max_drawdown_pct`, `trades`, `win_rate_pct`, `avg_win`, `avg_loss`, `profit_factor` (None when no losses or all losses are flat).

---

### 4.14 StateStore (`prediction_trading/trading/state.py`)

**Responsibility:** Persist and restore `Portfolio` state across restarts.

**`save(portfolio, path)`:** Writes JSON with `cash`, `initial_capital`, `commission_per_trade`, positions, closed trades, equity curve. All `datetime` values stored as ISO-8601 strings.

**`load_or_create(path, *, initial_capital, commission_per_trade)`:** Restores from JSON if the file exists; otherwise returns a fresh `Portfolio`.

---

### 4.15 WatchlistScanner (`prediction_trading/scanner.py`)

**Responsibility:** Screen multiple tickers in parallel with the rule-based engine only (no AI, no charting).

**Algorithm:**

```
WatchlistScanner.scan(tickers)
    │  ThreadPoolExecutor (default 4 workers)
    ▼
_scan_one(ticker)
    │  DataFetcher.fetch(include_fundamentals=False)
    │  TechnicalIndicators.compute_all
    │  SignalScorer.score → direction, confidence, top factors
    ▼
[ScanResult, …] sorted by confidence descending, filtered by min_confidence
```

Errors in individual tickers are caught and returned as `ScanResult(error=str(exc))` so one failure does not abort the scan.

**`ScanResult` fields:** `ticker`, `direction`, `confidence`, `top_factors: list[str]`, `current_price`, `error`.

---

### 4.16 REST API (`prediction_trading/api/`)

**Responsibility:** Thin FastAPI layer that exposes the core engine over HTTP. All business logic stays in `PredictionTradingSystem` and its dependencies; routers only handle request parsing and error mapping.

**Entry point:** `prediction_trading/api/main.py:app` — launched via `make api-dev` (uvicorn on `:8000`).

**Routers:**

| Router | Module | Path prefix | Methods | Delegates to |
|---|---|---|---|---|
| predict | `routers/predict.py` | `/predict` | `POST /` | `PredictionTradingSystem.predict()` |
| scan | `routers/scan.py` | `/scan` | `POST /` | `WatchlistScanner.scan()` |
| backtest | `routers/backtest.py` | `/backtest` | `POST /` | `PredictionTradingSystem.backtest()` |
| trading | `routers/trading.py` | `/trading` | `GET /status`, `POST /start` | `AutoTrader` |

**Health check:** `GET /health` → `{"status": "ok"}`.

**Schemas** (`api/schemas.py`, Pydantic v2):

| Schema | Direction | Key fields |
|---|---|---|
| `PredictRequest` | in | `ticker`, `timeframe`, `enable_ai`, `lookback_days`, `categories`, `use_4h` |
| `PredictResponse` | out | `ticker`, `direction`, `confidence`, `current_price`, `price_target`, `factors: list[FactorResponse]`, `meta` |
| `ScanRequest` | in | `tickers`, `categories`, `min_confidence`, `workers` |
| `ScanResponse` | out | `results: list[ScanResultResponse]`, `total` |
| `BacktestRequest` | in | `ticker`, `start`, `end`, `initial_capital`, `commission` |
| `BacktestResponse` | out | `stats: BacktestStatsResponse` |
| `TradingStartRequest` | in | `tickers`, `initial_capital`, `dry_run`, `enforce_market_hours` |
| `TradingStatusResponse` | out | `running`, `tickers`, `equity`, `cash`, `open_positions` |

**Configuration:** `api/deps.py:get_default_config()` loads `config/default.yaml` at startup via the lifespan hook.

---

## 5. Streamlit Web UI (`frontend/app.py`, `frontend/ui/`)

Entry point: `frontend/app.py` — launched via `make ui-dev` (`streamlit run frontend/app.py`, default port 8501). `frontend/` is a separate uv workspace package (`prediction-trading-frontend`) that lists `prediction-trading-backend` as a dependency.

Seven pages via a **top navigation bar** (sidebar nav was replaced). A light/dark theme toggle lives in the header. A **persistent watchlist sidebar** (`ui/watchlist.py`) shows live price badges and quick-links into the Predict page; it is rendered on every page via `render_sidebar()`.

Additional UI modules:
- `ui/theme.py` — CSS injection for light/dark themes via `inject_theme(dark: bool)`.
- `ui/watchlist.py` — watchlist state persisted to `watchlist.json`; tickers can be added/removed from any page.
- `ui/components.py` — shared Plotly chart helpers and a dark-mode color palette (`bullish=#00d25b`, `bearish=#ff4b4b`, `neutral=#8b949e`); re-used across the Dashboard, Predict, Backtest, and Trading pages.

### 5.1 Page inventory

| Page | Module | Responsibility |
|---|---|---|
| Dashboard | `ui/pages/dashboard.py` | Portfolio KPIs, Plotly equity curve, open positions, recent trades. Auto-refresh every 15 s when AutoTrader is running. |
| Predict | `ui/pages/predict.py` | Ticker + timeframe + category multiselect + AI toggle + 4H toggle + save-report checkbox. Calls `system.predict(market, hourly_4h=df_4h)`. Results cached in session state. |
| Scanner | `ui/pages/scanner.py` | Watchlist textarea, min-confidence slider, workers slider, category multiselect (default: all six). CSV export. |
| Backtest | `ui/pages/backtest.py` | Date pickers, capital/commission inputs. Calls `system.backtest()`. Equity curve + trade log. Save full report button. |
| Trading | `ui/pages/trading.py` | Start/stop AutoTrader (daemon thread + `queue.Queue`). Live cycle reports, positions monitor, error log. 10 s auto-rerun. |
| Alerts | `ui/pages/alerts.py` | Price/confidence/P&L trigger management. Triggers: price above/below, confidence ≥, daily P&L ≥/≤. Alert state persisted to `alerts.json`. |
| Settings | `ui/pages/settings.py` | Risk profile selector (conservative/moderate/aggressive). Sliders for all `default.yaml` sections including indicator categories. Saves on button click. |

### 5.2 Session state contract

All slow operations (predict, backtest, scan) store their result in `st.session_state` on completion. Subsequent widget interactions re-render without re-running the computation. Keys are defined as string constants in `ui/state.py`.

### 5.3 Trading page threading model

```
render() ──► checks TRADER_RUNNING
              │  True: drains TRADER_QUEUE into reports list; calls st.rerun() after 10 s sleep
              │  False: shows start form
              ▼
_start_trader() ──► builds PredictionTradingSystem + AutoTrader
                ──► stores trader in TRADER_INSTANCE
                ──► starts threading.Thread(target=_trader_loop, daemon=True)

_trader_loop(trader, interval, queue) ──► loop:
    report = trader.run_once()
    queue.put(report)
    time.sleep(interval)
```

The daemon thread is stopped implicitly when the main Streamlit process exits. The stop button sets `TRADER_RUNNING = False`; the loop exits on the next iteration check.

---

## 6. Reporting and Output

All runs write under `results/` with self-describing prefixes:

### 6.1 Prediction

```
results/predict_YYYYMMDD_HHMMSS/
├── predictions.md          # per-ticker: summary table, chart embed,
│                           # bullish/bearish factors, pivot levels, Fibonacci, narrative
└── charts/
    └── TICKER_TIMEFRAME.png  # dynamic multi-panel PNG
```

**Always-present chart panels:** Price + Target, Confidence arc gauge, Signal Factors bar chart.

**Category-conditional panels:**

| Panel | Category |
|---|---|
| MACD (12, 26, 9) | `trend` |
| RSI (14) | `momentum` |
| Stochastic (14, 3) | `momentum` |
| Volume + Spikes | `volume` |
| OBV | `volume` |
| ATR (14) | `volatility` |
| Support & Resistance | `support` |
| Fundamental grid (15 metrics) | `fundamental` |

### 6.2 Backtest

```
results/backtest_TICKER_YYYYMMDD_HHMMSS/
├── report.md
└── charts/
    ├── indicators.png   # price, MAs, Bollinger, MACD, RSI, ADX
    ├── signals.png      # close with buy/sell markers
    ├── performance.png  # equity curve + drawdown
    └── risk.png         # per-trade P&L and ATR
```

### 6.3 Live Trading

```
results/live_YYYYMMDD_HHMMSS/
├── portfolio_state.json    # Portfolio snapshot (resumable)
├── trades.csv              # append-only closed trade log
└── prediction_trading.log  # structured cycle log
```

---

## 7. Configuration

Single source of defaults: `config/default.yaml`. All values can be overridden by passing kwargs to `PredictionTradingSystem` or by editing the file via the Settings page.

### 7.1 Schema

```yaml
portfolio:
  initial_capital: 10000.0
  max_positions: 5
  max_position_size_pct: 0.05
  commission_per_trade: 1.0
  risk_profile: moderate

risk:
  max_daily_loss_pct: 0.02
  min_risk_reward: 1.5
  stop_loss_atr_mult: 2.0
  take_profit_atr_mult: 3.0

signals:
  min_confidence: 0.40
  confidence_scale: 10.0     # abs(net_points) for confidence = 1.0
  weights: {trend: 0.25, momentum: 0.25, reversal: 0.20, volatility: 0.15, price_action: 0.15}
  multi_timeframe_bonus: 2
  ai_weight: 0.50

indicators:
  categories: [trend, momentum, volatility, volume, support, fundamental]

ai:
  enabled: false
  model: claude-sonnet-4-6
  timeframe: 1w
  max_tokens: 2000

data:
  lookback_days: 365
  interval: 1d

trader:
  interval_seconds: 300
  enforce_market_hours: false
  slippage_bps: 0.0
  dry_run: false
```

### 7.2 Risk Profiles (`config/risk_profiles.yaml`)

| Profile | Position | Daily limit | Min conf | Stop ATR | Target ATR | Min R:R |
|---|---|---|---|---|---|---|
| conservative | 3% | 1% | 60% | 1.5× | 3.0× | 2.0 |
| moderate | 5% | 2% | 40% | 2.0× | 3.0× | 1.5 |
| aggressive | 10% | 5% | 30% | 2.5× | 4.0× | 1.2 |

Applied via the Settings page "Apply Profile" button, which merges the profile's `portfolio`, `risk`, and `signals` sections into `default.yaml`.

---

## 8. Testing

All tests run offline — no network, no API key required.

**Fixtures** (`tests/conftest.py`): `_synthetic_ohlcv()` generates deterministic OHLCV DataFrames via `numpy.random.default_rng`. Three fixtures: `ohlcv_uptrend`, `ohlcv_downtrend`, `ohlcv_sideways`.

**Test files:**

| File | Count | Coverage |
|---|---|---|
| `test_signal_scorer.py` | 10 | Uptrend/downtrend/sideways signals, weekly bonus, 4H bonus, category filtering, fundamental scoring, crossover detection |
| `test_risk_manager.py` | 11 | Each gate independently: neutral direction, confidence threshold, max positions, duplicate ticker, daily loss cap, invalid ATR, min R:R, proposal stops/target; default min_confidence value |
| `test_auto_trader.py` | 10 | Broker round-trip, slippage, state store, dry-run, stop-loss, trade/state persistence, market hours gate, loop max_cycles |
| `test_portfolio.py` | 6 | Open/close long (profit), insufficient cash error, equity mark, short position close cash, short equity mark, drawdown |
| `test_scanner.py` | 6 | Results returned and ranked, confidence filtering, per-ticker error isolation, category subset, worker count |
| `test_backtester.py` | 2 | End-to-end backtest with synthetic uptrend; profit_factor None on zero-PnL losses |
| `test_indicators.py` | 7 | SMA/EMA manual comparison, RSI bounded [0,100], MACD histogram sign, Bollinger envelope, ATR positive, compute_all columns, pivot/Fibonacci |
| `test_ai_predictor.py` | 5 | Offline fallback (no API key), tool-call construction, degraded mode, prompt caching headers |
| `test_data_fetcher.py` | 7 | OHLCV shape, DatetimeIndex tz-stripping, fundamentals best-effort, interval parameter, fetch_history date range |
| `test_reporting.py` | 8 | Prediction chart panel selection (always-present + category-conditional), report writer output structure, backtest chart builder |
| `test_unified_predictor.py` | 6 | AI/rule fusion formula, ai_weight=0 fallback, actionable flag, neutral deadband, min_confidence gate |

**Total: 78 tests.**

---

## 9. Known Constraints and Assumptions

| Constraint | Detail |
|---|---|
| Data source | Yahoo Finance via `yfinance`. Rate limits and data gaps are not explicitly handled; `DataFetcher` propagates exceptions from yfinance. |
| Short selling | The system generates short signals, but the cash model in `Portfolio` uses a symmetric margin approach (both sides deduct `price × qty`). Real short-sell proceeds are not modelled. |
| Indicator warmup | `SMA200` requires 200 bars; `compute_all` on fewer than 200 bars produces NaN columns. `Backtester` drops NaN rows after `compute_all`. |
| 4H data availability | 1H OHLCV from Yahoo Finance is available for approximately 730 days. The 4H fetch uses a 90-day lookback. |
| Thread safety | `AutoTrader` daemon thread reads `st.session_state.get(TRADER_RUNNING)` to detect stop requests. Streamlit's session state is not thread-safe; stop detection may lag by one sleep interval. |
| Prompt cache TTL | Anthropic ephemeral cache TTL is 5 minutes. Calls spaced more than 5 minutes apart pay full input token cost. |
