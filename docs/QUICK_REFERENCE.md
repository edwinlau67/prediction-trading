# Quick Reference

## Launch Commands

```bash
# Web UI (recommended)
uv run streamlit run frontend/app.py

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

## Indicator Categories

| Category | Key Rules | Points |
|---|---|---|
| `trend` | Price vs SMA50/200, Golden/Death Cross, MACD crossover, EMA12 vs EMA26 | ±1 to ±2 |
| `momentum` | RSI oversold (<30) / overbought (>70), RSI midline, Stochastic cross | ±1 to ±2 |
| `volatility` | Bollinger Band touches, ATR elevated / calm | ±1 |
| `volume` | OBV rising/falling, Volume spike on up/down day | ±1 |
| `support` | Price vs Pivot Point, Trendline hold / break | ±1 |
| `fundamental` | P/E, PEG, Rev/Earnings growth, Net margin, ROE, D/E, Current ratio, P/B | ±1 each |
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
  model: claude-opus-4-7
  timeframe: 1m
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
| `CLAUDE_MODEL` | No | Override model (default: `claude-opus-4-7`) |

---

## Timeframe Values

`1d` `1w` `1m` `3m` `6m` `ytd` `1y` `2y` `5y`

Used with `--timeframe` CLI flag, `ai.timeframe` config, or `UnifiedPredictor(timeframe=...)`.
