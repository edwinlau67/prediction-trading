# Examples

Five annotated end-to-end examples. All run offline except where AI or live market data is noted.

---

## 1. Single-Ticker Prediction (Rule-Based)

Predict AAPL using technical indicators only. No API key needed.

```python
from src import PredictionTradingSystem
from src.prediction import SignalScorer

# 1. Create system — loads config/default.yaml
system = PredictionTradingSystem("AAPL")

# 2. Fetch 1 year of OHLCV + fundamentals from Yahoo Finance
market = system.fetch(lookback_days=365)

print(f"Fetched {len(market.ohlcv)} bars. Last close: ${market.current_price:.2f}")

# 3. Run prediction (rule-based only — ai.enabled=false by default)
prediction = system.predict(market)

print(f"Direction:   {prediction.direction}")
print(f"Confidence:  {prediction.confidence:.0%}")
print(f"Price target:{prediction.price_target:.2f}" if prediction.price_target else "N/A")

# 4. Print the top factors driving the signal
for factor in prediction.factors[:8]:
    marker = "↑" if factor.direction == "bullish" else "↓"
    print(f"  {marker} [{factor.category}] {factor.name} — {factor.detail}")

# 5. Save chart + markdown report to results/
out_dir = system.save_report(prediction=prediction)
print(f"\nReport written: {out_dir}")
```

Expected output:
```
Fetched 252 bars. Last close: $198.45
Direction:   bullish
Confidence:  70%
Price target: 213.00
  ↑ [trend] Price above SMA50 — $198.45 > $182.30
  ↑ [trend] Price above SMA200 — $198.45 > $171.20
  ↑ [momentum] RSI above midline — RSI=58.3 > 50
  ↑ [volume] OBV rising — on-balance volume trending up
  ...
```

---

## 2. AI-Powered Prediction with 4H Confluence

Uses Claude for narrative analysis and the new 4H timeframe confluence signal.

**Requires:** `ANTHROPIC_API_KEY` in `.env` and live internet access.

```python
from src import PredictionTradingSystem
from src.data_fetcher import DataFetcher
from src.indicators import TechnicalIndicators
from src.prediction import SignalScorer

# 1. System with AI enabled
system = PredictionTradingSystem("NVDA", enable_ai=True)
market = system.fetch()

# 2. Fetch 4H data separately (yfinance supports 1h interval)
fetcher_4h = DataFetcher(interval="1h")
ohlcv_1h = fetcher_4h.fetch_history("NVDA", lookback_days=90)

# Resample 1h → 4h
rules = {"Open": "first", "High": "max", "Low": "min",
         "Close": "last", "Volume": "sum"}
ohlcv_4h = ohlcv_1h.resample("4h").agg(rules).dropna()
df_4h = TechnicalIndicators.compute_all(ohlcv_4h)

# 3. Score with daily + weekly + 4H confluence
df_daily = TechnicalIndicators.compute_all(market.ohlcv)
weekly_df = TechnicalIndicators.compute_all(
    system._to_weekly(market.ohlcv)
)

signal = system.scorer.score(
    df_daily,
    weekly=weekly_df,
    hourly_4h=df_4h,
    fundamentals=market.fundamentals,
)
print(f"Rule signal: {signal.direction} ({signal.confidence:.0%})")
print(f"Net points: {signal.net_points} / 10")

# 4H confluence factor will appear if 4H agrees with daily:
for f in signal.factors:
    if "confluence" in f.name.lower():
        print(f"  Confluence: {f.name} (+{f.points} pts)")

# 4. Full AI-fused prediction
prediction = system.predict(market)
print(f"\nFused prediction: {prediction.direction} {prediction.confidence:.0%}")

# AI narrative is in prediction.ai_signal.narrative
if prediction.ai_signal:
    print("\nAI Analysis:")
    print(prediction.ai_signal.narrative[:500])

system.save_report(prediction=prediction)
```

---

## 3. Full Backtest with Analysis

Backtest TSLA over 2 years and analyse the results.

```python
from src import PredictionTradingSystem

system = PredictionTradingSystem(
    "TSLA",
    initial_capital=25_000,
)

# Run bar-by-bar backtest (200-bar warmup, then live simulation)
result = system.backtest("2022-01-01", "2024-01-01")
stats = result.summary()

print("=" * 50)
print(f"TSLA Backtest 2022–2024")
print("=" * 50)
print(f"Total Return:   {stats['return_pct']:+.2f}%")
print(f"Max Drawdown:   {stats['max_drawdown_pct']:.2f}%")
print(f"Win Rate:       {stats['win_rate_pct']:.1f}%")
print(f"Profit Factor:  {stats.get('profit_factor', 'N/A')}")
print(f"Total Trades:   {stats['total_trades']}")
print(f"Wins / Losses:  {stats['winning_trades']} / {stats['losing_trades']}")

# Print trade details
portfolio = result.portfolio
print(f"\nFinal Equity: ${portfolio.equity({}):.2f}")
print(f"\nLast 10 trades:")
for trade in portfolio.closed_trades[-10:]:
    result_str = "WIN " if trade.is_win else "LOSS"
    print(f"  {result_str} {trade.ticker:6} {trade.side:5} "
          f"${trade.entry_price:.2f}→${trade.exit_price:.2f} "
          f"P&L: ${trade.pnl:+.2f} ({trade.return_pct*100:+.1f}%)  "
          f"Reason: {trade.reason}")

# Save full report with 4 chart PNGs
out_dir = system.save_report(result=result)
print(f"\nReport: {out_dir}")
```

---

## 4. Watchlist Scan with CSV Export

Screen a 20-ticker watchlist in parallel and export the results.

```python
import csv
from src.scanner import WatchlistScanner

WATCHLIST = [
    "AAPL", "MSFT", "NVDA", "TSLA", "META",
    "GOOGL", "AMZN", "AMD", "INTC", "QCOM",
    "JPM", "GS", "BAC", "WFC", "C",
    "JNJ", "PFE", "ABBV", "MRK", "UNH",
]

scanner = WatchlistScanner(
    categories=("trend", "momentum", "volume"),   # fast — skip fundamentals
    lookback_days=180,
    min_confidence=0.30,
    workers=8,
)

print(f"Scanning {len(WATCHLIST)} tickers with 8 workers...")
results = scanner.scan(WATCHLIST)

print(f"\n{'Ticker':<8} {'Signal':<10} {'Conf':>6}  Top Factors")
print("-" * 70)
for r in results:
    if r.error:
        print(f"{r.ticker:<8} ERROR     {'':>6}  {r.error}")
        continue
    label = {"bullish": "BUY", "bearish": "SELL", "neutral": "HOLD"}[r.direction]
    factors = ", ".join(r.top_factors[:3])
    print(f"{r.ticker:<8} {label:<10} {r.confidence:5.0%}  {factors}")

# Export to CSV
with open("scan_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(
        f, fieldnames=["ticker", "direction", "confidence", "price", "top_factors", "error"]
    )
    writer.writeheader()
    for r in results:
        writer.writerow({
            "ticker": r.ticker,
            "direction": r.direction,
            "confidence": f"{r.confidence:.3f}",
            "price": f"{r.current_price:.2f}" if r.current_price else "",
            "top_factors": "; ".join(r.top_factors),
            "error": r.error or "",
        })
print("\nExported: scan_results.csv")
```

---

## 5. Paper AutoTrader with State Persistence

Run two cycles of paper trading, persist state, then restore and inspect.

```python
from pathlib import Path
from src import PredictionTradingSystem
from src.trading.state import StateStore

STATE_PATH = "results/example_live/portfolio_state.json"
TRADE_LOG = "results/example_live/trades.csv"
Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)

# ── First run: 1 cycle ────────────────────────────────────────────────────────
system = PredictionTradingSystem(
    "AAPL",
    initial_capital=10_000,
)
trader = system.build_auto_trader(
    tickers=["AAPL", "MSFT", "NVDA"],
    state_path=STATE_PATH,
    trade_log_path=TRADE_LOG,
    dry_run=True,                   # signals only; no real fills
)

print("Running cycle 1...")
reports = trader.run(once=True)
for report in reports:
    print(f"Cycle finished at {report.finished_at}")
    for action in report.actions:
        print(f"  {action.ticker}: {action.action} — {action.detail}")

# ── Restore from state ─────────────────────────────────────────────────────────
print("\nRestoring portfolio from state file...")
store = StateStore(STATE_PATH)
portfolio = store.load_or_create(initial_capital=10_000.0)
print(f"Cash:      ${portfolio.cash:,.2f}")
print(f"Positions: {list(portfolio.positions.keys())}")
print(f"Trades:    {len(portfolio.closed_trades)}")
print(f"Equity:    ${portfolio.equity({}):,.2f}")

# ── Second run: continue from persisted state ─────────────────────────────────
system2 = PredictionTradingSystem("AAPL", initial_capital=10_000)
trader2 = system2.build_auto_trader(
    tickers=["AAPL", "MSFT", "NVDA"],
    state_path=STATE_PATH,          # loads existing portfolio
    trade_log_path=TRADE_LOG,
    dry_run=True,
)

print("\nRunning cycle 2...")
reports2 = trader2.run(once=True)
print(f"After cycle 2 — Equity: ${trader2.portfolio.equity({}):.2f}")
```

---

## Using Custom Indicator Categories

```python
from src.prediction.signal_scorer import SignalScorer
from src.indicators import TechnicalIndicators
from src.data_fetcher import DataFetcher

fetcher = DataFetcher()
market = fetcher.fetch("SPY")
df = TechnicalIndicators.compute_all(market.ohlcv)

# Score using only trend and volume (ignore momentum, volatility, support, fundamental)
scorer = SignalScorer(
    categories=("trend", "volume"),
    confidence_scale=6.0,       # lower scale → higher confidence with fewer rules
    multi_timeframe_bonus=1,
)
signal = scorer.score(df, fundamentals=market.fundamentals)
print(f"SPY: {signal.direction} ({signal.confidence:.0%}) — {signal.net_points} pts")
print(f"Bullish factors: {[f.name for f in signal.bullish_factors]}")
print(f"Bearish factors: {[f.name for f in signal.bearish_factors]}")
```
