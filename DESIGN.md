# Design

This document describes the `prediction-trading` system — a merged, layered platform that combines **AI-assisted stock prediction**, **automated backtested trading**, and a **Streamlit web UI** for interactive use.

Source lineage:

| Source | Contribution |
|---|---|
| [`edwinlau67/stock-prediction`](https://github.com/edwinlau67/stock-prediction) | Claude tool-use predictor, rich `predictions.md`, six indicator categories, fundamental scoring |
| [`edwinlau67/automated-trading-systems`](https://github.com/edwinlau67/automated-trading-systems) | Multi-timeframe scoring, portfolio/position/trade primitives, ATR-based risk manager, bar-by-bar backtester, risk profiles |
| [`edwinlau67/algorithmic-trading-system`](https://github.com/edwinlau67/algorithmic-trading-system) | Comprehensive algorithmic trading system with multiple strategies, risk management, and backtesting capabilities |


---

## 1. Layered Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             USER INTERFACES                                 │
│  app.py (Streamlit UI)   stock_predictor.py   automated_trader.py           │
│  scan_watchlist.py       examples/                                          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────────┐
│                      src/system.py — PredictionTradingSystem                │
│  (high-level façade: fetch / predict / backtest / save_report /             │
│   build_auto_trader)                                                        │
└──────┬───────────────────┬──────────────────┬───────────────────────────────┘
       │                   │                  │
┌──────▼──────────┐  ┌─────▼─────────────┐   ┌▼───────────────────────────────┐
│  PREDICTION     │  │    TRADING        │   │          BACKTEST              │
│                 │  │                   │   │                                │
│ SignalScorer    │  │ Portfolio         │   │ Backtester (bar-by-bar,        │
│ AIPredictor     │  │ RiskManager       │   │ 200-bar warmup, no look-ahead) │
│ UnifiedPredictor│  │ AutoTrader        │   └────────────────────────────────┘
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

---

## 2. Streamlit Web UI

`app.py` is the entry point (`streamlit run app.py`, opens on `localhost:8501`). It renders six pages via a sidebar radio, each implemented as a `render()` function in `ui/pages/`.

```
app.py
ui/
  state.py        — st.session_state key constants + init_session_state()
  components.py   — shared widgets: metric_card, direction_badge,
                    confidence_badge, prediction_card, equity_chart, trade_log_table
  pages/
    dashboard.py  — portfolio KPIs, plotly equity curve, positions, trades
    predict.py    — ticker + timeframe + category inputs, AI toggle, 4H toggle,
                    runs PredictionTradingSystem, shows PredictionChart + factors
    scanner.py    — watchlist textarea, min-confidence slider, parallel scan,
                    BUY/SELL/HOLD table with CSV export
    backtest.py   — date pickers, capital/commission inputs, equity curve, trade log
    trading.py    — start/stop AutoTrader (daemon thread + queue.Queue),
                    live cycle reports, positions monitor
    settings.py   — risk profile selector, parameter sliders,
                    saves to config/default.yaml
```

**Threading model for the Trading page:** `AutoTrader.run()` is blocking. The Trading page runs it in a `threading.Thread(daemon=True)`. A `queue.Queue` stored in `st.session_state` carries `CycleReport` objects from the thread back to the UI. Each call to `render()` drains the queue, then calls `st.rerun()` after a 10-second sleep for live updates.

**Session state contract:** All slow operations (predict, backtest, scan) store their results in `st.session_state` on completion. Subsequent widget interactions re-render without re-running the computation.

---

## 3. The Scoring Model (`SignalScorer`)

The rule-based engine is **point-based** with optional category filtering and multi-timeframe confluence bonuses.

Each applicable rule emits a `Factor(category, name, direction, points, detail)`:

| Category | Rule | Points |
|---|---|---|
| `trend` | Price above/below SMA50 / SMA200 | ±1 |
| `trend` | Golden Cross / Death Cross | ±2 |
| `trend` | MACD bullish / bearish crossover event | ±2 |
| `trend` | MACD above / below signal | ±1 |
| `trend` | EMA12 vs EMA26 | ±1 |
| `momentum` | RSI < 30 / > 70 (oversold/overbought) | ±2 |
| `momentum` | RSI above/below 50 midline | ±1 |
| `momentum` | Stochastic %K/%D crossover | ±1 |
| `momentum` | Stochastic oversold / overbought | ±1 |
| `volatility` | Price outside Bollinger Band | ±1 |
| `volatility` | ATR regime (calm/elevated vs 20d mean) | ±1 |
| `volume` | OBV trend (rising/falling) | ±1 |
| `volume` | Volume spike on up / down day | ±1 |
| `support` | Price above / below Pivot Point | ±1 |
| `support` | Rising support hold / support broken | ±1 |
| `fundamental` | P/E, PEG, growth, margins, ROE, D/E, CR, P/B | ±1 each |
| *(bonus)* | Weekly timeframe agrees with daily | ±2 |
| *(bonus)* | 4H timeframe agrees with daily | ±1 |

```
direction   = sign(net_points)                 # bullish | bearish | neutral
confidence  = min(1.0, abs(net_points) / 10.0) # 0..1 (10 ≙ 100%)
```

The scorer also exposes a normalised 5-component view (`trend / momentum / reversal / volatility / price_action`) for backwards compatibility with the backtester.

### 4H Timeframe Confluence (v1.1)

`SignalScorer.score()` accepts an optional `hourly_4h` DataFrame alongside the existing `weekly`. When 4H agrees with the daily direction, a bonus of `max(1, multi_timeframe_bonus - 1)` points is added. Fetch 4H data via `DataFetcher(interval="1h")`, resample `4h`, enrich with `TechnicalIndicators.compute_all()`.

---

## 4. Category Filtering

The `--indicators` flag (and `config/default.yaml → indicators.categories`) drives three things in lockstep:

1. **Scoring** — rules in omitted categories are skipped entirely.
2. **Chart panels** — only matching optional panels render.
3. **AI tool output** — active categories are embedded in the system prompt so Claude's narrative stays consistent with the chart.

The three always-present chart panels (Price + Target, Confidence arc, Signal Factors) render regardless of selection.

---

## 5. Watchlist Scanner (`WatchlistScanner`)

`src/scanner.py` provides a lightweight, API-key-free screening path:

```
WatchlistScanner.scan(tickers)
    │  ThreadPoolExecutor (default 4 workers)
    ▼
_scan_one(ticker)
    │  DataFetcher.fetch (OHLCV only, no fundamentals)
    │  TechnicalIndicators.compute_all
    │  SignalScorer.score → direction, confidence, top factors
    ▼
[ScanResult, …] ranked by confidence descending
```

The Streamlit Scanner page wraps this with a textarea watchlist, confidence slider, and CSV export.

---

## 6. The Claude Tool-Use Flow

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
                    │  (local execution: yfinance OHLCV + fundamentals,
                    │   TechnicalIndicators.compute_all, SignalScorer.score,
                    │   price target projection, JSON result)
                    ▼
            Second API call with tool_result ──► narrative
```

The system prompt is tagged `cache_control: {type: "ephemeral"}` — repeated calls within 5 minutes cost ~10% of the first call. When no `ANTHROPIC_API_KEY` is set, the flow degrades transparently to returning the local tool output only.

---

## 7. Fused Prediction (`UnifiedPredictor`)

```python
blended = (1 - ai_weight) * rule_signed + ai_weight * ai_signed
```

`rule_signed` and `ai_signed` are confidence values in `[-1, +1]`. Direction flips at `|blended| > 0.05`; confidence = `|blended|` clipped to `[0, 1]`. When AI is disabled, fused output equals rule-based output, so the system works without any API key.

---

## 8. Risk Management

| Gate | Default | Description |
|---|---|---|
| `min_confidence` | 0.40 | Unified prediction must clear this to consider |
| `max_positions` | 5 | Concurrent open positions cap |
| `max_position_size_pct` | 0.05 (5%) | Max notional per position as fraction of equity |
| `max_daily_loss_pct` | 0.02 (2%) | Halts new entries once daily equity drawdown hit |
| `min_risk_reward` | 1.5 | Reward-per-share / risk-per-share floor |
| `stop_loss_atr_mult` | 2.0 × ATR | Stop distance |
| `take_profit_atr_mult` | 3.0 × ATR | Target distance |

### Risk Profiles

`config/risk_profiles.yaml` provides three presets applied via the Settings page:

| Profile | Position | Daily limit | Min conf | Stop ATR | Target ATR | Min R:R |
|---|---|---|---|---|---|---|
| conservative | 3% | 1% | 60% | 1.5× | 3.0× | 2.0 |
| moderate | 5% | 2% | 40% | 2.0× | 3.0× | 1.5 |
| aggressive | 10% | 5% | 30% | 2.5× | 4.0× | 1.2 |

All parameters are ultimately sourced from `config/default.yaml` (overrideable via `PredictionTradingSystem` kwargs).

---

## 9. Configuration

```
config/
  default.yaml            — system-wide defaults (portfolio, risk, signals, ai, data, trader)
  risk_profiles.yaml      — conservative / moderate / aggressive presets
  indicators_config.yaml  — per-indicator period/threshold reference
```

`_Config.load()` in `src/system.py` reads `default.yaml`. The Settings page writes changes back via `yaml.dump()`. Risk profiles are merged into the config dict on "Apply Profile" and saved.

---

## 10. Report and Chart Layout

Both pipelines write into `results/` with self-describing prefixed subfolders.

### Prediction (`stock_predictor.py` or Predict page)

```
results/predict_YYYYMMDD_HHMMSS/
├── predictions.md          # per-ticker: summary table, chart embed,
│                           # bullish/bearish factors, pivot levels, Fibonacci, narrative
└── charts/
    └── TICKER_TIMEFRAME.png  # dynamic multi-panel PNG
```

### Backtest (`Backtester` or Backtest page)

```
results/backtest_TICKER_YYYYMMDD_HHMMSS/
├── report.md
└── charts/
    ├── indicators.png
    ├── signals.png
    ├── performance.png
    └── risk.png
```

### Live Trading (`AutoTrader` or Trading page)

```
results/live_YYYYMMDD_HHMMSS/
├── portfolio_state.json    # persisted Portfolio (restored on restart)
└── trades.csv              # append-only closed trade log
```
