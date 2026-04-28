# Design Specification — Stock Market Prediction Trading System

| Field | Value |
|---|---|
| Version | 1.5 |
| Status | Active |
| Last updated | 2026-04-28 |

---

## 1. Purpose and Scope

Stock Market Prediction Trading System is an end-to-end platform that combines rule-based technical analysis, AI-assisted prediction via Claude, automated paper/live trading, bar-by-bar backtesting, and an interactive Streamlit web UI. It is designed for educational use and individual research.

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
├── frontend/                 ← package: prediction-trading-frontend (Streamlit, dev)
│   ├── app.py                ← Streamlit entry point
│   └── ui/                   ← pages, components, theme, watchlist
├── dash-frontend/            ← package: prediction-trading-dash (Plotly Dash, production)
│   ├── app.py                ← Dash entry point (gunicorn-compatible `server`)
│   └── dash_ui/              ← pages, components, theme, api client
├── config/
├── examples/
└── Makefile
```

### Component diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             USER INTERFACES                                 │
│  dash-frontend/app.py (Plotly Dash, :8050)   frontend/app.py (Streamlit)    │
│  stock-predictor   automated-trader   scan-watchlist   examples/            │
└──────────────┬──────────────────────────┬───────────────────────────────────┘
               │                          │
┌──────────────▼──────────────────────────▼───────────────────────────────────┐
│              REST API  (prediction_trading.api — FastAPI :8000)             │
│  POST /predict/   GET /predict/macro   POST /scan/   POST /backtest/        │
│  GET+POST /trading/…   POST /portfolio/analyze   GET+PUT /config/           │
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

**Responsibility:** Fetch OHLCV history, fundamentals, and optional enriched market context (news, macro, sector) from Yahoo Finance.

**Interface:**

```python
DataFetcher(interval: str = "1d")
    .fetch(ticker, *, lookback_days=365, include_fundamentals=True, include_enriched=False) -> MarketData
    .fetch_history(ticker, *, lookback_days=None, start=None, end=None) -> pd.DataFrame
    .fetch_fundamentals(ticker) -> dict
    .fetch_news_context(ticker) -> NewsContext
    .fetch_macro_context() -> MacroContext
    .fetch_sector_context(ticker, stock_ohlcv) -> SectorContext
```

**`MarketData` fields:** `ticker`, `ohlcv: pd.DataFrame`, `current_price: float`, `fundamentals: dict`, `interval: str`, `news_context: NewsContext | None`, `macro_context: MacroContext | None`, `sector_context: SectorContext | None`.

**Enriched context dataclasses:**

| Dataclass | Fields |
|---|---|
| `NewsContext` | `sentiment_score: float` (−1..1 keyword ratio), `article_count: int`, `recent_headlines: list[str]`, `earnings_beat: bool|None`, `earnings_miss: bool|None`, `earnings_upcoming_days: int|None` |
| `MacroContext` | `vix: float|None`, `yield_10y: float|None`, `yield_2y: float|None`, `yield_spread: float|None` (10Y−2Y), `spy_above_sma50: bool|None` |
| `SectorContext` | `sector: str`, `sector_etf: str`, `stock_30d_return: float|None`, `sector_30d_return: float|None`, `spy_30d_return: float|None`, `vs_sector: float|None`, `sector_vs_spy: float|None` |

**Constraints:**
- OHLCV index is a `DatetimeIndex` with timezone stripped.
- `fetch_fundamentals` is best-effort; exceptions are caught and an empty dict returned.
- `include_enriched=False` by default; set to `True` to populate the three context fields on `MarketData`. `AIPredictor` always calls `fetch(..., include_enriched=True)`.
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
| `news` | News sentiment score (keyword ratio) bullish / bearish | ±2 |
| `news` | Recent earnings beat / miss | ±2 |
| `news` | Upcoming earnings within 30 days | 0 (note only) |
| `macro` | VIX < 15 (calm) / > 30 (fear) | ±2 / ±1 |
| `macro` | Yield curve spread (10Y−2Y) positive / negative | ±1 |
| `macro` | SPY above / below 50-day SMA | ±1 |
| `sector` | Stock 30-day return vs sector ETF outperforming / underperforming | ±1 |
| `sector` | Sector ETF 30-day return vs SPY outperforming / underperforming | ±1 |
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
    categories: tuple[str, ...] | None = None,  # None = all nine
    weights: dict | None = None,                 # legacy component weights
    multi_timeframe_bonus: int = 2,
)
    .score(
        df: pd.DataFrame,
        *,
        weekly: pd.DataFrame | None = None,
        hourly_4h: pd.DataFrame | None = None,
        fundamentals: dict | None = None,
        news_context: NewsContext | None = None,
        macro_context: MacroContext | None = None,
        sector_context: SectorContext | None = None,
    ) -> ScoredSignal
```

**`ScoredSignal` fields:** `direction`, `confidence`, `net_points`, `factors: list[Factor]`, plus normalised 5-component view (`trend`, `momentum`, `reversal`, `volatility`, `price_action`) for backtester compatibility.

**`Factor` fields:** `category`, `name`, `direction`, `points`, `detail`, `signed` (signed magnitude).

**Category filtering:** Rules in omitted categories are skipped entirely; the 5-component view treats them as 0. News, macro, and sector factors require the corresponding context object to be passed; if `None`, the category is silently skipped regardless of the categories filter.

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
                    │  SignalScorer.score (with news/macro/sector contexts),
                    │  price target projection → JSON result
                    │  tool result includes optional "news", "macro", "sector" dicts
                    ▼
            Second API call with tool_result ──► narrative response (≤500 words)
```

The Claude narrative is instructed to comment on news sentiment/earnings, VIX/yield-curve regime, and sector relative strength when those fields are present in the tool result.

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

All nine categories are active by default: `trend`, `momentum`, `volatility`, `volume`, `support`, `fundamental`, `news`, `macro`, `sector`.

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
| predict | `routers/predict.py` | `/predict` | `POST /`, `GET /macro` | `PredictionTradingSystem.predict()`, `DataFetcher.fetch_macro_context()` |
| scan | `routers/scan.py` | `/scan` | `POST /` | `WatchlistScanner.scan()` |
| backtest | `routers/backtest.py` | `/backtest` | `POST /` | `PredictionTradingSystem.backtest()` |
| trading | `routers/trading.py` | `/trading` | `GET /status`, `POST /start` | `AutoTrader` |
| portfolio | `routers/portfolio.py` | `/portfolio` | `POST /analyze` | `ETFAnalyzer.analyze_portfolio()` |
| config | `routers/config.py` | `/config` | `GET /`, `PUT /` | reads/writes `config/default.yaml` |

**Health check:** `GET /health` → `{"status": "ok"}`.

**`GET /predict/macro`:** Returns major market indexes (SPY, QQQ, DIA, IWM, VIX, etc.) with `price`, `change_1d_pct`, `change_5d_pct`, `change_30d_pct`, and `above_sma50` for each. Used by the Dash Predict page to render the Market Index Overview table without re-running a full prediction.

**`PUT /config/` write semantics:** Loads `config/default.yaml`, merges the request body keys (only those in `_ALLOWED_KEYS = {portfolio, risk, signals, indicators, ai, trader, data, broker}`), and writes the merged document back as YAML (`default_flow_style=False, sort_keys=False`). API restart is required for runtime objects to pick up the new values.

**Schemas** (`api/schemas.py`, Pydantic v2):

| Schema | Direction | Key fields |
|---|---|---|
| `PredictRequest` | in | `ticker`, `timeframe`, `enable_ai`, `lookback_days`, `categories`, `use_4h` |
| `PredictResponse` | out | `ticker`, `direction`, `confidence`, `current_price`, `price_target`, `factors: list[FactorResponse]`, `timing: TimingResponse \| None`, `indicators`, `levels`, `fundamentals`, `ohlcv: list[dict]`, `meta` |
| `ScanRequest` | in | `tickers`, `categories`, `min_confidence`, `workers` |
| `ScanResponse` | out | `results: list[ScanResultResponse]`, `total` |
| `BacktestRequest` | in | `ticker`, `start`, `end`, `initial_capital`, `commission` |
| `BacktestResponse` | out | `stats: BacktestStatsResponse`, `trades: list[TradeResponse]`, `equity_curve: list[EquityPointResponse]`, `ohlcv: list[dict]` |
| `TradingStartRequest` | in | `tickers`, `initial_capital`, `dry_run`, `enforce_market_hours`, `interval_seconds`, `state_path` |
| `TradingStatusResponse` | out | `running`, `tickers`, `equity`, `cash`, `open_positions`, `cycle_count`, `positions: list[PositionResponse]`, `recent_trades: list[RecentTradeResponse]`, `last_cycle: dict \| None` |
| `PortfolioAnalyzeRequest` | in | `tickers`, `lookback_days` |
| `PortfolioAnalysisResponse` | out | `tickers`, `diversification_score`, `correlation_matrix: dict[str, dict[str, float]]`, `sector_exposure: dict[str, float]`, `recommendations: list[str]`, `etf_infos: list[ETFInfoResponse]` |
| `ETFInfoResponse` | out | `ticker`, `name`, `category`, `tracked_index`, `expense_ratio`, `is_etf` |

**Configuration:** `api/deps.py:get_default_config()` loads `config/default.yaml` at startup via the lifespan hook.

---

## 5. Web UIs

The system ships **two parallel front-ends**, both depending on `prediction-trading-backend` via uv workspace dependency:

| UI | Package | Framework | Entry point | Default port | Make target | Role |
|---|---|---|---|---|---|---|
| Streamlit | `prediction-trading-frontend` (`frontend/`) | Streamlit | `frontend/app.py` | 8501 | `make ui-dev` | Reference / dev iteration. Calls the engine in-process via `PredictionTradingSystem`. |
| Dash | `prediction-trading-dash` (`dash-frontend/`) | Plotly Dash + dash-bootstrap-components | `dash-frontend/app.py` | 8050 | `make dash-dev` | Production dashboard. Talks to FastAPI over HTTP only; deployable behind gunicorn (`server = app.server`). |

The Streamlit UI imports backend modules directly (single-process). The Dash UI is a thin HTTP client of the REST API in §4.16, with no direct backend imports — `dash-frontend/pyproject.toml` does not depend on `prediction-trading-backend`. Both UIs share the same dark-on-light color palette (`GREEN=#26d96a`, `RED=#ff6464`, `BLUE=#58a6ff`, `YELLOW=#f0b429`, `MUTED=#b0b8c4`).

### 5.1 Streamlit Web UI (`frontend/app.py`, `frontend/ui/`)

Entry point: `frontend/app.py` — launched via `make ui-dev` (`streamlit run frontend/app.py`, default port 8501). `frontend/` is a separate uv workspace package (`prediction-trading-frontend`) that lists `prediction-trading-backend` as a dependency.

Eight pages via a **top navigation bar** (sidebar nav was replaced). A light/dark theme toggle lives in the header. A **persistent watchlist sidebar** (`ui/watchlist.py`) shows live price badges and quick-links into the Predict page; it is rendered on every page via `render_sidebar()`.

Additional UI modules:
- `ui/theme.py` — CSS injection for light/dark themes via `inject_theme(dark: bool)`.
- `ui/watchlist.py` — watchlist state persisted to `watchlist.json`; tickers can be added/removed from any page.
- `ui/components.py` — shared Plotly chart helpers and a dark-mode color palette (`bullish=#00d25b`, `bearish=#ff4b4b`, `neutral=#8b949e`); re-used across the Dashboard, Predict, Backtest, and Trading pages.

#### 5.1.1 Page inventory

| Page | Module | Responsibility |
|---|---|---|
| Dashboard | `ui/pages/dashboard.py` | Portfolio KPIs, Plotly equity curve, open positions, recent trades. Auto-refresh every 15 s when AutoTrader is running. |
| Predict | `ui/pages/predict.py` | Ticker + timeframe + category multiselect + AI toggle + 4H toggle + save-report checkbox. Calls `system.predict(market, hourly_4h=df_4h)`. Results cached in session state. |
| Scanner | `ui/pages/scanner.py` | Watchlist textarea, min-confidence slider, workers slider, category multiselect (default: all nine). CSV export. |
| Backtest | `ui/pages/backtest.py` | Date pickers, capital/commission inputs. Calls `system.backtest()`. Equity curve + trade log. Save full report button. |
| Trading | `ui/pages/trading.py` | Start/stop AutoTrader (daemon thread + `queue.Queue`). Live cycle reports, positions monitor, error log. 10 s auto-rerun. |
| Portfolio Builder | `ui/pages/portfolio_builder.py` | ETF metadata lookup, correlation heatmap, sector exposure breakdown, and diversification recommendations. Uses `ETFAnalyzer`. |
| Alerts | `ui/pages/alerts.py` | Price/confidence/P&L trigger management. Triggers: price above/below, confidence ≥, daily P&L ≥/≤. Alert state persisted to `alerts.json`. |
| Settings | `ui/pages/settings.py` | Risk profile selector (conservative/moderate/aggressive). Sliders for all `default.yaml` sections including indicator categories. Saves on button click. |

#### 5.1.2 Session state contract

All slow operations (predict, backtest, scan) store their result in `st.session_state` on completion. Subsequent widget interactions re-render without re-running the computation. Keys are defined as string constants in `ui/state.py`.

#### 5.1.3 Trading page threading model

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

#### 5.1.4 Per-page UI specification

Developer-facing widget inventory for each page. Covers session state keys, widget types and value ranges, and helper functions from `ui/components.py`.

##### 5.1.4.1 Dashboard (`ui/pages/dashboard.py`)

Session state keys read: `TRADER_INSTANCE` (live AutoTrader), `BT_RESULT` (last backtest).
Portfolio load priority: (1) live AutoTrader from session state, (2) backtest result from session state, (3) file upload (`st.file_uploader` → parse `portfolio_state.json`).

Layout:
- `config_info_bar()` caption at top.
- Two tabs: `tab_overview`, `tab_risk`.
- Overview: 4-column `metric_card()` row; `equity_chart()` (Plotly, height 300); `st.dataframe` for positions (styled by Unrealised P&L sign); `trade_log_table()` for last 20 closed trades.
- Risk: 4-column `metric_card()` row; `st.progress()` bar for daily loss vs cap; horizontal `go.Bar` chart (Plotly) for position concentration.
- Auto-refresh: `<meta http-equiv="refresh" content="15">` injected via `st.markdown` when AutoTrader is running.

##### 5.1.4.2 Predict (`ui/pages/predict.py`)

Session state keys: `PREDICT_RESULT`, `PREDICT_TICKER`, `PREDICT_OHLCV`, `PREDICT_CHART_PATH`, `PREDICT_DATA_FEED`, `PREDICT_MACRO_CONTEXT`.

Widgets:
- `st.text_input("Ticker")` — prefilled from `PREDICT_TICKER`.
- `st.selectbox("Timeframe")` — values: `1d 1w 1m 3m 6m ytd 1y 2y 5y`.
- `st.multiselect("Categories")` — options: `["trend","momentum","volatility","volume","support","fundamental"]` (6 only; news/macro/sector excluded from UI).
- `st.toggle("Enable AI")`, `st.toggle("4H Confluence")`, `st.checkbox("Save report")`.

Result tabs: `tab_signal` calls `prediction_card()`, `_render_timing_card()`, `_render_index_table()`; `tab_chart` calls `candlestick_chart()` (Plotly, height 420); `tab_static` renders `st.image()` from `PREDICT_CHART_PATH`.

##### 5.1.4.3 Scanner (`ui/pages/scanner.py`)

Session state key: `SCAN_RESULTS`.

Widgets:
- `st.text_area("Watchlist")` — prefilled from `WATCHLIST_TICKERS`.
- `st.slider("Min Confidence", 0.0, 1.0, 0.40, step=0.05)`.
- `st.slider("Parallel Workers", 1, 16, 4)`.
- `st.multiselect("Categories")` — same 6 options as Predict (news/macro/sector not shown).

Results: 4-column summary cards; `st.columns([1,1,1,1,3,2])` grid per row; `st.download_button` with `io.BytesIO` CSV buffer.

##### 5.1.4.4 Backtest (`ui/pages/backtest.py`)

Session state keys: `BT_RESULT`, `BT_TICKER`, `BT_OHLCV`, `BT_TRADES`.

Widgets: `st.text_input("Ticker")`, `st.date_input("Start/End Date")`, `st.number_input("Initial Capital")`, `st.number_input("Commission")`. Validates end > start before enabling run.

Result tabs: `tab_equity` → `equity_chart()`; `tab_candle` → `candlestick_chart()` with `buy_signals`/`sell_signals` trade markers (height 500); `tab_log` → `st.dataframe` (scrollable, max-height 500px). Save button calls `system.save_report(result=result)`.

##### 5.1.4.5 Trading (`ui/pages/trading.py`)

Session state keys: `TRADER_RUNNING`, `TRADER_INSTANCE`, `TRADER_THREAD`, `TRADER_QUEUE`, `TRADER_REPORTS`, `TRADER_ERRORS`.

Stopped state widgets (inside `st.form("trader_config")`): tickers textarea, `st.number_input("Cycle Interval", 60, 3600, 300, step=60)`, dry-run checkbox, market-hours checkbox, state-path text input.

Running state widgets: status `metric_card()`; stop button (`st.button` outside form); 3 KPI `metric_card()` calls; `equity_chart()`; positions dataframe; last-cycle expander with actions dataframe and errors expander. Auto-rerun: `time.sleep(10); st.rerun()` after draining queue.

##### 5.1.4.6 Portfolio Builder (`ui/pages/portfolio_builder.py`)

Widgets: `st.text_area("Tickers")`, `st.slider("Lookback Days", 30, 1260, 252)`.

Output components: holdings cards in groups of 4 (`st.columns(4)`) with ETF/Stock badge based on `ETFAnalyzer.is_etf()`; diversification score displayed as `st.metric` with color via `st.markdown`; correlation heatmap as `go.Heatmap` with custom colorscale; sector exposure as `go.Bar`; recommendations as `st.warning` (high correlation/expense) or `st.info` (other).

##### 5.1.4.7 Alerts (`ui/pages/alerts.py`)

Session state keys: `ALERTS_LIST`, `ALERTS_TRIGGERED`. Persisted to `alerts.json` via `_load_alerts()` / `_save_alerts()`.

Three tabs: `tab_active`, `tab_create`, `tab_log`.
- Active: iterates `ALERTS_LIST`; per-alert `st.columns([5,1])` with info col and delete button keyed by index. "Check Now" calls `_check_alerts()` → `yfinance.Ticker(t).fast_info.last_price`.
- Create: ticker `st.text_input`, trigger-type `st.selectbox` (5 options), value `st.number_input`, create button.
- Log: reversed slice of last 50 triggered entries as `st.dataframe`; "Clear Log" button resets `ALERTS_TRIGGERED`.

HTML escaping applied to all user-supplied ticker inputs before rendering.

##### 5.1.4.8 Settings (`ui/pages/settings.py`)

Session state keys: `ACTIVE_PROFILE`, `SETTINGS_DIRTY`.

Sections and widgets:
- Risk profile: `st.selectbox` (conservative/moderate/aggressive) + Apply button → merges preset into form state.
- Portfolio: 2-column layout with `st.number_input` for capital/commission and `st.slider` for position count and max size %.
- Risk: 2-column sliders for max daily loss, min R:R, stop ATR mult, take-profit ATR mult.
- Signals: sliders for min confidence, 4H bonus points, AI weight.
- Indicator categories: `st.multiselect` — all 9 categories (including news/macro/sector, unlike Predict/Scanner pages).
- AI: toggle, `st.selectbox` for model (`claude-sonnet-4-6`, `claude-opus-4-7`, `claude-haiku-4-5-20251001`), timeframe selectbox, max-tokens number input.
- AutoTrader: interval number input, dry-run/market-hours toggles, slippage slider.
- Data source: `st.radio` (yfinance/alpaca/both); alpaca info box shown when alpaca/both selected.
- Broker: `st.radio` (paper/alpaca); Alpaca paper mode toggle disabled when broker != alpaca.
- Save button: `yaml.dump(config)` to `config/default.yaml`. Success toast notes that AutoTrader restart is required.

---

### 5.2 Dash Web UI (`dash-frontend/app.py`, `dash-frontend/dash_ui/`)

Entry point: `dash-frontend/app.py` — launched via `make dash-dev` (`uv run python dash-frontend/app.py`, default port 8050). The Dash app uses pages auto-discovery (`use_pages=True`, `pages_folder="dash_ui/pages"`) and exposes `server = app.server` so it can be served by gunicorn in production.

Unlike the Streamlit UI, the Dash UI does **not** import the backend Python package. All data flow goes through HTTP calls to the FastAPI server (default `http://localhost:8000`) via the thin `dash_ui/api.py` client. This decouples the dashboard process from the engine and lets the two scale independently.

#### 5.2.1 Architecture

```
Browser ──► Dash app (:8050)
              │ dash.page_container, dcc.Store (session/local), dcc.Interval
              │ Bootstrap DARKLY theme + custom CSS (dash_ui/theme.py)
              ▼
            dash_ui/api.py  (requests, timeouts: 10 s short / 60 s long)
              ▼
          FastAPI (:8000)  → PredictionTradingSystem, AutoTrader, ETFAnalyzer, ...
```

**Top-level layout (`app.py`):**
- `dcc.Store(scan-results-store)`, `predict-result-store`, `app-config-store` (session storage), `theme-store` (local), `current-theme-store` (memory) — the only cross-page state.
- `dcc.Interval(config-load-interval)` fires once on startup to call `GET /config/` and `GET /trading/status`, which populates a global status bar with API-online/offline indicator.
- A `dbc.Navbar` with a brand link, page links rendered from `dash.page_registry` sorted by `order`, and a 3-button theme toggle (auto / dark / light).
- A clientside callback (pure JavaScript, no Python round-trip) sets `data-bs-theme` on `<html>` and writes the resolved theme back to `current-theme-store`. Charts that need to recolor on theme change subscribe to `current-theme-store` and pass the resolved layout to `theme.get_plotly_layout(theme_name)`.

**Theme module (`dash_ui/theme.py`):** Exposes the shared color palette, two Plotly layout dicts (`PLOTLY_DARK_LAYOUT`, `PLOTLY_LIGHT_LAYOUT`), and a `CUSTOM_CSS` string that defines CSS variables for `[data-bs-theme="dark"]` / `[data-bs-theme="light"]` and `@media (prefers-color-scheme: light)` for the auto mode.

**API client (`dash_ui/api.py`):** Thin wrapper over `requests` with `_SHORT=10s` (status/health/config) and `_LONG=60s` (predict/scan/backtest/macro/portfolio) timeouts. One function per backend endpoint: `predict`, `scan`, `backtest`, `trading_status`, `trading_start`, `predict_macro`, `portfolio_analyze`, `get_config`, `put_config`, `health_check`.

#### 5.2.2 Cross-page state contract

Three keys live on the top-level layout and persist via Dash storage:

| Store ID | Storage | Written by | Read by |
|---|---|---|---|
| `scan-results-store` | `session` | `pages/scanner.py` after a successful `/scan/` | `pages/analytics.py` for histogram/pie/factor charts |
| `predict-result-store` | `session` | `pages/predict.py` after a successful `/predict/` (also stores `result["macro"]`) | `pages/analytics.py` adds the single prediction into the analytics dataset |
| `app-config-store` | `session` | startup callback, refreshed by Settings save | global status bar, future config-aware widgets |
| `theme-store` | `local` | theme-toggle clientside callback | persists across sessions (localStorage) |
| `current-theme-store` | `memory` | clientside callback (resolves auto → dark/light) | every page that renders a Plotly figure |

Per-page stores: `bt-store` (Backtest, session), `equity-history-store` (Dashboard, memory, last 360 polls), `alerts-store` (Alerts, **local**), `trade-ui-state` (Trading, session).

#### 5.2.3 Page inventory

| Page | Module | Path | Order | Responsibility |
|---|---|---|---|---|
| Dashboard | `pages/home.py` | `/` | 0 | Live KPIs, equity curve, positions/trades/risk tabs. Polls `/trading/status` every 10 s via `dcc.Interval`. |
| Predict | `pages/predict.py` | `/predict` | 1 | Single-ticker prediction. Calls `/predict/` then `/predict/macro`. Renders Signal / Factors / Analysis / Fundamentals / Market / AI Narrative tabs. |
| Scanner | `pages/scanner.py` | `/scanner` | 2 | Bulk scan via `/scan/`. Optional 30 s auto-refresh, CSV export via `dcc.Download`. |
| Trading | `pages/trading.py` | `/trading` | 3 | Start AutoTrader via `/trading/start`. Polls `/trading/status` every 10 s for KPIs, positions, last cycle actions. Stop is **not** wired to an API endpoint — only resets the UI; physical stop requires an API restart. |
| Analytics | `pages/analytics.py` | `/analytics` | 4 | Visualises `scan-results-store` + `predict-result-store`. Five tabs: confidence histogram, direction pie, factor frequency (top 20), category heatmap, ticker scatter. Theme-reactive. |
| Backtest | `pages/backtest.py` | `/backtest` | 5 | Calls `/backtest/`. Equity curve / candlestick + trades / trade log tabs. |
| Alerts | `pages/alerts.py` | `/alerts` | 6 | Active / Create / Triggered tabs. Persisted to `localStorage` (no backend). "Check Now" calls `yfinance.Ticker(t).fast_info.last_price` directly from the Dash process — the only place the Dash UI imports a non-HTTP data source. |
| Portfolio Builder | `pages/portfolio.py` | `/portfolio` | 7 | Calls `/portfolio/analyze`. ETF/Stock cards, diversification score, correlation heatmap, sector exposure bar, recommendations. |
| Settings | `pages/settings.py` | `/settings` | 8 | Calls `GET /config/` on load (one-shot interval), `PUT /config/` on Save. Accordion UI for portfolio / risk / signals / indicator categories / AI / auto-trader / data source / broker sections. |

#### 5.2.4 Components module (`dash_ui/components.py`)

Public functions (~660 LOC) used across pages:

| Helper | Purpose |
|---|---|
| `status_bar(config_data, api_online)` | Top-of-page status row showing API health, model, data source, broker. |
| `kpi_card(title, value, delta, delta_positive)` | Reusable KPI tile (used on Dashboard, Trading, Backtest, Predict). |
| `direction_badge(direction)` | Pill badge ("BUY" / "SELL" / "HOLD") tinted by `theme.DIRECTION_COLORS`. |
| `factor_bar_chart(factors, ...)` | Horizontal Plotly bar of signed factor points. |
| `confidence_gauge(direction, confidence, ...)` | Plotly indicator gauge in `direction` color. |
| `equity_line_chart(equity_points, ...)` | Equity curve line chart with optional initial-capital reference line. |
| `candlestick_chart(ohlcv, ...)` | OHLCV candlestick + volume sub-panel (Plotly subplots). |
| `analysis_chart(ohlcv, indicators, levels, timing=...)` | Multi-row analysis chart: price + MAs + Bollinger + entry/stop/target lines, MACD, RSI, Stochastic, ATR, Volume, OBV. ~260 LOC. |
| `fundamentals_chart(fundamentals, ticker, ...)` | Grid of fundamental metric cards (P/E, PEG, ROE, D/E, etc.). |
| `index_performance_chart(indexes, ...)` | Horizontal bar of 1D/5D/30D returns for major market indexes. |
| `scan_results_table(results)` | `dash_table.DataTable` for scanner output with conditional row coloring. |

#### 5.2.5 Live polling model

Dash uses `dcc.Interval` rather than threads (the Streamlit pattern in §5.1.3):

```
Dashboard:   dcc.Interval(10 s) → callback → api.trading_status() → KPIs, equity history, positions/trades/risk
Trading:     dcc.Interval(10 s) → callback → api.trading_status() → banner, KPIs, positions, last cycle
Scanner:     dcc.Interval(30 s, disabled by default) → callback → api.scan() (only when auto-refresh switch is on)
Analytics:   dcc.Interval(30 s) → callback → re-renders charts from stores (no network call)
```

Equity history on the Dashboard is accumulated client-side in `equity-history-store` (capped at 360 points = 1 hour at 10 s polling) — the API does not yet return a live equity curve.

#### 5.2.6 Differences from the Streamlit UI

| Concern | Streamlit (§5.1) | Dash (§5.2) |
|---|---|---|
| Backend coupling | Direct Python imports | HTTP only (REST API) |
| Default port | 8501 | 8050 |
| State store | `st.session_state` (server) | `dcc.Store` (browser session/local) |
| Live updates | `st.rerun()` after `time.sleep()` in main thread; AutoTrader runs in a daemon thread inside the Streamlit process | `dcc.Interval` callbacks; AutoTrader runs inside the FastAPI process |
| Theme | Light/dark CSS injection via `inject_theme(dark)` | CSS variables + `data-bs-theme` attribute, switched by clientside callback |
| Watchlist sidebar | Persistent `ui/watchlist.py` rendered on every page | Not present — quick-links and watchlist live inside the Scanner textarea |
| Stop AutoTrader | Sets a session flag the daemon thread polls each cycle | No live stop — UI button only resets the dashboard view; physical stop requires API restart |
| Production deploy | `streamlit run` only | Exposes `server` (Flask WSGI) for gunicorn / uvicorn-workers |
| News / macro / sector category controls | Hidden in Predict and Scanner; shown only in Settings | Shown in all three pages (Predict, Scanner, Settings) |

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
  categories: [trend, momentum, volatility, volume, support, fundamental, news, macro, sector]

ai:
  enabled: true
  model: claude-opus-4-7
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
| `test_alpaca_broker.py` | 9 | AlpacaBroker: market/limit orders, quote fallback (IEX → latest bar → yfinance), error swallowing on close, fill propagation |
| `test_alpaca_data_fetcher.py` | 13 | AlpacaDataFetcher: OHLCV fetch, invalid-bar filtering, feed-label propagation; _MergedDataFetcher yfinance fallback; create_data_fetcher factory dispatch |
| `test_etf_analyzer.py` | 15 | ETFAnalyzer: catalogue lookup (case-insensitive), is_etf, unknown-ticker yfinance fallback, correlation matrix shape + diagonal, sector exposure, diversification score, high-correlation recommendations |

**Total: 115 tests.**

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
