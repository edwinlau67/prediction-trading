# Quick Reference

## Launch Commands

```bash
# Streamlit UI (self-contained, no API required)
uv run streamlit run frontend/app.py

# Dash UI (requires API running first: make api-dev)
make dash-dev    # uv run python dash-frontend/app.py → http://localhost:8050

# REST API server
uv run uvicorn prediction_trading.api.main:app --reload

# CLI — prediction
uv run stock-predictor --tickers AAPL TSLA --timeframe 1m
uv run stock-predictor --tickers NVDA --no-ai --indicators trend momentum

# CLI — watchlist scan
uv run scan-watchlist AAPL MSFT NVDA TSLA --min-confidence 0.4 --workers 8

# CLI — paper trading
uv run automated-trader --tickers AAPL TSLA --dry-run --once
uv run automated-trader --tickers AAPL --interval 300 --market-hours

# Tests (offline, no API key)
uv run pytest backend/tests/ -v

# Single test file
uv run pytest backend/tests/test_signal_scorer.py -v
```

---

## Streamlit UI Pages (`make ui-dev` → `:8501`)

| Page | Icon | Primary Action |
|---|---|---|
| Dashboard | 📊 | Portfolio KPIs, equity curve, open positions/trades, risk metrics |
| Predict | 🔮 | Single-ticker prediction — signal card, timing rec, candlestick chart |
| Scanner | 🔍 | Bulk watchlist scan → BUY/SELL/HOLD ranked table + CSV export |
| Backtest | 📅 | Historical simulation → 8 KPIs, equity curve, trade log, save report |
| Trading | ⚡ | Start/stop AutoTrader; live equity, positions, cycle report |
| Portfolio Builder | 🧱 | Correlation heatmap, diversification score, sector exposure |
| Alerts | 🔔 | Create price/confidence/P&L triggers; check & triggered log |
| Settings | ⚙️ | Risk profiles, all config sliders → saves `config/default.yaml` |

**Shared Streamlit UI elements:**

| Element | Location | Notes |
|---|---|---|
| Theme toggle | Header (top-right) | 🌙 Dark / ☀️ Light |
| Config Info Bar | Below page title (all pages except Settings) | Data source · Broker · AI model or "disabled" |
| Sidebar watchlist | Left sidebar | Click ticker → opens in Predict; persisted to `watchlist.json` |
| `alerts.json` | Working directory | Alert state persisted across browser refreshes |

---

## Dash UI Pages (`make api-dev` + `make dash-dev` → `:8050`)

Dash UI is a REST client — start `make api-dev` first. Navbar has an **Auto / Dark / Light** theme switcher; a global config status bar (Data · Feed · Model · Broker) sits between the navbar and page content.

| Page | Route | Primary Action |
|---|---|---|
| Dashboard | `/` | 10 s live polling — equity KPIs, equity curve (360 pts), positions/trades/risk tabs |
| Predict | `/predict` | Prediction with per-run model selector; tabs: Signal · Factors · Analysis (multi-panel) · Fundamentals · Market · AI Narrative |
| Scanner | `/scanner` | Watchlist scan; auto-refresh (30 s); results stored cross-page in `scan-results-store` |
| **Analytics** | `/analytics` | **Dash-only** — confidence histogram, direction donut, factor frequency, category heatmap, ticker scatter |
| Trading | `/trading` | Start AutoTrader via API; last-cycle actions table (OPEN/CLOSE/ERROR); 10 s polling |
| Backtest | `/backtest` | 8 KPI cards; equity curve, candlestick+trade markers, Trade Log DataTable |
| Alerts | `/alerts` | Create/check/delete alerts; localStorage persistence via `alerts-store` |
| Portfolio Builder | `/portfolio` | Holdings cards; Diversification Score; Correlation Heatmap; Sector Exposure |
| Settings | `/settings` | 8 accordion sections; GET/PUT `/config/` API |

Full Dash page reference: [`docs/TRADING_SYSTEM_GUIDE.md#dash-ui`](TRADING_SYSTEM_GUIDE.md#dash-ui)

---

## Indicator Categories

| Category | Key Rules | Points |
|---|---|---|
| `trend` | Price vs SMA50/200, Golden/Death Cross, MACD crossover, EMA12 vs EMA26 | ±1 to ±2 |
| `momentum` | RSI oversold (<30) / overbought (>70), RSI midline, Stochastic cross | ±1 to ±2 |
| `volatility` | Bollinger Band touches, ATR elevated / calm | ±1 |
| `volume` | OBV rising/falling, Volume spike on up/down day | ±1 |
| `support` | Price vs Pivot Point, Trendline hold / break | ±1 |
| `fundamental` | P/E, PEG, Rev/Earnings growth, Net margin, ROE, D/E, Current ratio, P/B | ±1 each |
| `news` | Headline sentiment (keyword ratio), earnings beat/miss | ±2 |
| `macro` | VIX regime, yield curve spread (10Y−2Y), SPY vs SMA50 | ±1 to ±2 |
| `sector` | Stock vs sector ETF (30d), sector ETF vs SPY (30d) | ±1 |
| *(bonus)* | Weekly timeframe agrees with daily | ±2 |
| *(bonus)* | 4H timeframe agrees with daily | ±1 |

**Confidence formula:** `min(1.0, |net_points| / 10.0)`

---

## Signal Interpretation

| Direction | Confidence | Meaning |
|---|---|---|
| `bullish` | ≥ min_confidence | Long entry candidate |
| `bearish` | ≥ min_confidence | Short entry candidate |
| `neutral` | any | Skip — net points near zero |
| any | < min_confidence | Skip — weak signal |

Default `min_confidence` = **0.40**

---

## Key Config Parameters (`config/default.yaml`)

```yaml
portfolio:
  initial_capital: 10000.0       # starting equity
  max_positions: 5               # max concurrent positions
  max_position_size_pct: 0.05    # 5% of equity per trade
  commission_per_trade: 1.0      # flat fee

risk:
  max_daily_loss_pct: 0.02       # halt at -2% intraday
  min_risk_reward: 1.5           # reward must be ≥ 1.5× risk
  stop_loss_atr_mult: 2.0        # stop = entry ± ATR × 2
  take_profit_atr_mult: 3.0      # target = entry ± ATR × 3

signals:
  min_confidence: 0.40           # signal gate
  multi_timeframe_bonus: 2       # weekly confluence bonus
  ai_weight: 0.50                # 0=rule-only, 1=AI-only

ai:
  enabled: true                  # set ANTHROPIC_API_KEY to use Claude
  model: claude-sonnet-4-6
  timeframe: 1m

data:
  source: yfinance               # "yfinance" | "alpaca" | "both" (default: yfinance)
```

---

## Risk Profiles

| Profile | Position | Daily limit | Min conf | Stop ATR | Target ATR |
|---|---|---|---|---|---|
| **Conservative** | 3% | 1% | 60% | 1.5× | 3.0× |
| **Moderate** (default) | 5% | 2% | 40% | 2.0× | 3.0× |
| **Aggressive** | 10% | 5% | 30% | 2.5× | 4.0× |

Apply in Settings page or directly in `config/default.yaml` → `config/risk_profiles.yaml`.

---

## Python API Cheat Sheet

```python
from prediction_trading import PredictionTradingSystem
from prediction_trading.scanner import WatchlistScanner

# Predict
sys = PredictionTradingSystem("AAPL")
pred = sys.predict(sys.fetch())
print(pred.direction, pred.confidence, pred.price_target)

# Predict with AI
sys = PredictionTradingSystem("AAPL", enable_ai=True)
pred = sys.predict(sys.fetch())

# Backtest
sys = PredictionTradingSystem("TSLA", initial_capital=25_000)
result = sys.backtest("2023-01-01", "2024-01-01")
print(result.summary())

# Save report (markdown + charts)
out = sys.save_report(prediction=pred)       # or result=result
print(out)  # → results/predict_YYYYMMDD_HHMMSS/

# Scan watchlist
scanner = WatchlistScanner(min_confidence=0.4, workers=8)
for r in scanner.scan(["AAPL","MSFT","NVDA","TSLA"]):
    print(r.ticker, r.direction, f"{r.confidence:.0%}")

# Paper AutoTrader
sys = PredictionTradingSystem("AAPL")
trader = sys.build_auto_trader(
    tickers=["AAPL", "MSFT"],
    state_path="results/live/portfolio_state.json",
    dry_run=True,
)
report = trader.run_once()
```

---

## Output Locations

```
results/
  predict_YYYYMMDD_HHMMSS/
    predictions.md
    charts/
      TICKER_1w.png
  backtest_TICKER_YYYYMMDD_HHMMSS/
    report.md
    charts/
      indicators.png
      signals.png
      performance.png
      risk.png
  live_YYYYMMDD_HHMMSS/
    portfolio_state.json
    trades.csv
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Only for AI | `sk-ant-...` |
| `CLAUDE_MODEL` | No | Override model (default: `claude-sonnet-4-6`) |
| `ALPACA_API_KEY` | Only for Alpaca | Alpaca brokerage key |
| `ALPACA_API_SECRET` | Only for Alpaca | Alpaca brokerage secret |

---

## Timeframe Values

`1d` `1w` `1m` `3m` `6m` `ytd` `1y` `2y` `5y`

Used with `--timeframe` CLI flag, `ai.timeframe` config, or `UnifiedPredictor(timeframe=...)`.
