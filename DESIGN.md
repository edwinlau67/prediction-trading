# Design

This document describes how `prediction-trading` merges two upstream
projects ([`edwinlau67/stock-prediction`](https://github.com/edwinlau67/stock-prediction)
and [`edwinlau67/automated-trading-systems`](https://github.com/edwinlau67/automated-trading-systems))
into a single, layered system that handles both **AI-assisted stock
prediction** (with rich Markdown/PNG output) and **automated backtested
trading** (with portfolio/risk management).

## 1. Layered architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLI entrypoints                           │
│   stock_predictor.py         examples/02_backtest.py              │
│   automated_trader.py        examples/03_multi_ticker.py          │
│   scan_watchlist.py          examples/01_predict.py               │
└──────────────────┬───────────────────────────────┬────────────────┘
                   │                               │
┌──────────────────▼───────────────┐   ┌──────────▼──────────────────┐
│  prediction/ (merged engine)     │   │  system.py                   │
│  • factor.Factor, categories     │   │  PredictionTradingSystem     │
│  • SignalScorer (point-based)    │   │  (high-level façade that     │
│  • AIPredictor (Claude tool use) │   │   wires everything together) │
│  • UnifiedPredictor (fuse)       │   └──────────┬──────────────────┘
└──────────────────┬───────────────┘              │
                   │ also used by                 │
┌──────────────────▼───────────────┐              │
│  scanner.py                      │              │
│  • WatchlistScanner (parallel)   │              │
│  • ScanResult                    │              │
└──────────────────────────────────┘              │
                   │                               │
┌──────────────────▼───────────────────────────────▼──────────────────┐
│  reporting/                                                          │
│  • PredictionChart    (dynamic multi-panel analysis chart, PNG)      │
│  • PredictionReport   (predictions.md with 6 sections per ticker)    │
│  • ChartBuilder       (4-chart backtest dashboard)                   │
│  • ReportWriter       (backtest report.md + trade log)               │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────────┐
│  trading/   backtest/                                                │
│  • Portfolio / Position / Trade   • Backtester (bar-by-bar loop)     │
│  • RiskManager (sizing, R:R, stops, daily loss cap)                  │
└──────────────────┬───────────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────────────────────┐
│  indicators/     data_fetcher.py                                     │
│  • TechnicalIndicators (SMA/EMA, MACD, RSI, Stoch, BB, ATR, ADX, OBV)│
│  • SupportResistance (pivots, Fibonacci, swing trendlines)           │
│  • DataFetcher (yfinance history + fundamentals)                     │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. The scoring model (`SignalScorer`)

The rule-based engine is **point-based** (mirroring `stock-prediction`)
with optional category filtering and multi-timeframe confluence bonuses
(from `automated-trading-systems`).

Each applicable rule emits a `Factor(category, name, direction, points, detail)`:

| Category       | Rule                                    | Points |
| -------------- | --------------------------------------- | ------ |
| `trend`        | Price above/below SMA50 / SMA200         | ±1     |
| `trend`        | Golden Cross / Death Cross               | ±2     |
| `trend`        | MACD bullish / bearish crossover event   | ±2     |
| `trend`        | MACD above / below signal                | ±1     |
| `trend`        | EMA12 vs EMA26                           | ±1     |
| `momentum`     | RSI < 30 / > 70 (oversold/overbought)    | ±2     |
| `momentum`     | RSI above/below 50 midline               | ±1     |
| `momentum`     | Stochastic %K/%D crossover               | ±1     |
| `momentum`     | Stochastic oversold / overbought         | ±1     |
| `volatility`   | Price outside Bollinger band             | ±1     |
| `volatility`   | ATR regime (calm/elevated vs 20d mean)   | ±1     |
| `volume`       | OBV trend (rising/falling)               | ±1     |
| `volume`       | Volume spike on up / down day            | ±1     |
| `support`      | Price above / below Pivot                | ±1     |
| `support`      | Rising support hold / support broken     | ±1     |
| `fundamental`  | P/E, PEG, growth, margins, ROE, D/E, CR  | ±1 each|
| (confluence)   | Weekly timeframe agrees with daily       | +2 or -2|

Confidence is computed as:

```
direction   = sign(net_points)                 # bullish | bearish | neutral
confidence  = min(1.0, abs(net_points) / 10.0) # 0..1 (10 ≙ 100%)
```

For backwards compatibility, the scorer also exposes a normalised
5-component view (`trend / momentum / reversal / volatility / price_action`)
used by the backtester's weighted logic.

## 3. Category filtering

The `--indicators` flag (and `config/default.yaml → indicators.categories`)
drives three things:

1. **Scoring** — rules belonging to omitted categories are skipped.
2. **Chart panels** — only matching optional panels are rendered.
3. **AI tool output** — the `indicators` field in the Claude tool result
   tells the model which categories are active so its narrative stays
   consistent.

The three always-present chart panels (Price + Target, Confidence & Risk
arc gauge, Signal Factors bar chart) render regardless of selection.

## 4. Watchlist scanner (`WatchlistScanner`)

`src/scanner.py` provides a lightweight, API-key-free screening path that
reuses `SignalScorer` without the chart or reporting stack:

```
scan_watchlist.py ──► WatchlistScanner.scan(tickers)
                           │  ThreadPoolExecutor (default 4 workers)
                           ▼
                      _scan_one(ticker)
                           │  DataFetcher.fetch (OHLCV only, no fundamentals)
                           │  TechnicalIndicators.compute_all
                           │  SignalScorer.score → direction, confidence, top factors
                           ▼
                      [ScanResult, …] ranked by confidence descending
```

Category filtering (`--indicators`) works identically to `stock_predictor.py`
— only the specified categories contribute to scoring.

## 5. The Claude tool-use flow

```
CLI ──► AIPredictor ──► Anthropic Messages API
                            │  system:  SYSTEM_PROMPT  (cache_control: ephemeral)
                            │  tools:   [stock_prediction]
                            │  messages: [{user: "Predict {ticker} ..."}]
                            ▼
                    stop_reason == "tool_use"
                            │
                            ▼
           AIPredictor._predict_from_market(MarketData, timeframe)
                            │   (local execution of the tool;
                            │    fetches yfinance OHLCV + fundamentals,
                            │    computes indicators, runs SignalScorer,
                            │    projects price target, returns JSON)
                            ▼
                    Second API call with tool_result ───► narrative
```

The system prompt is tagged with `cache_control: {type: "ephemeral"}` so
repeated calls within 5 minutes are served at ~10% input cost (identical
to `stock-prediction`). When no `ANTHROPIC_API_KEY` is set the flow
transparently degrades to returning just the local tool output.

**Active category injection** — the active `--indicators` categories are
embedded in the system prompt so Claude's narrative only references scored
indicators, keeping the text consistent with the chart.

**Extended thinking** — pass `--thinking-budget N` (e.g. `10000`) to
`stock_predictor.py` to enable Claude's extended thinking on both API
calls. Disabled by default (`0`).

## 6. Fused prediction (`UnifiedPredictor`)

```python
blended = (1 - ai_weight) * rule_signed + ai_weight * ai_signed
#       rule_signed and ai_signed are ±confidence (neutral = 0)
```

Direction flips at |blended| > 0.05; confidence = |blended| (clipped 0..1).
When the AI is disabled the fused output is identical to the rule-based
output, so the trading pipeline works without any API key.

## 7. Report and chart layout

Both pipelines write into a **single `results/` root** with self-describing
prefixed subfolders, so predictions and backtests live side by side.

### 7a. Prediction CLI — `stock_predictor.py`

```
results/
└── predict_YYYYMMDD_HHMMSS/
    ├── predictions.md                 # multi-ticker markdown report
    └── charts/
        ├── AAPL_1w.png                # dynamic analysis chart
        ├── TSLA_1m.png
        └── INTC_1m.png
```

`predictions.md` per-ticker sections:

1. 📊 Prediction Summary table
2. Embedded analysis chart PNG
3. 🟢 Key Bullish Factors
4. 🔴 Key Risk Factors / Bearish Signals
5. 📐 Technical Levels to Watch — pivot points (R2/R1/PP/S1/S2)
6. 📏 Fibonacci Retracement Levels (0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%)
7. 📝 Analysis (Claude narrative, or deterministic fallback)

### 7b. Backtest — `PredictionTradingSystem.save_report`

```
results/
└── backtest_TICKER_YYYYMMDD_HHMMSS/
    ├── report.md
    └── charts/
        ├── indicators.png
        ├── signals.png
        ├── performance.png
        └── risk.png
```

## 8. Risk management

| Gate                        | Default          | Description                                      |
| --------------------------- | ---------------- | ------------------------------------------------ |
| `min_confidence`            | 0.40             | Unified prediction must clear this to consider   |
| `max_positions`             | 5                | Concurrent open positions cap                    |
| `max_position_size_pct`     | 0.05 (5%)        | Max notional per position as fraction of equity  |
| `max_daily_loss_pct`        | 0.02 (2%)        | Halts new entries once daily equity drawdown hit |
| `min_risk_reward`           | 1.5              | Reward-per-share / risk-per-share floor          |
| `stop_loss_atr_mult`        | 2.0 × ATR        | Stop distance                                    |
| `take_profit_atr_mult`      | 3.0 × ATR        | Target distance                                  |

All configurable in `config/default.yaml`.
