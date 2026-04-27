# Examples

Ten annotated end-to-end examples. All run offline except where AI or live market data is noted.

---

## 1. Single-Ticker Prediction (Rule-Based)

Predict AAPL using technical indicators only. No API key needed.

```bash
uv run python examples/01_predict.py --ticker AAPL
ANTHROPIC_API_KEY=... uv run python examples/01_predict.py --ticker AAPL --ai
```

```python
from prediction_trading import PredictionTradingSystem
from prediction_trading.prediction import SignalScorer

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

```bash
uv run python examples/06_4h_confluence.py --ticker AAPL
uv run python examples/06_4h_confluence.py --ticker NVDA --ai
uv run python examples/06_4h_confluence.py --ticker TSLA --timeframe 1m --ai
```

```python
from prediction_trading import PredictionTradingSystem
from prediction_trading.data_fetcher import DataFetcher
from prediction_trading.indicators import TechnicalIndicators

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

```bash
uv run python examples/02_backtest.py --ticker AAPL
uv run python examples/02_backtest.py --ticker TSLA --start 2022-01-01 --end 2024-01-01 --capital 25000
uv run python examples/02_backtest.py --ticker NVDA --ai
```

```python
from prediction_trading import PredictionTradingSystem

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
print(f"Total Trades:   {stats['trades']}")
print(f"Avg Win / Loss: ${stats['avg_win']:+.2f} / ${stats['avg_loss']:+.2f}")

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

```bash
uv run python examples/05_watchlist_scan.py
uv run python examples/05_watchlist_scan.py --tickers AAPL MSFT NVDA TSLA META
uv run python examples/05_watchlist_scan.py --min-confidence 0.4 --indicators trend momentum
uv run python examples/05_watchlist_scan.py --workers 8 --csv scan_results.csv
```

```python
import csv
from prediction_trading.scanner import WatchlistScanner

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

```bash
uv run python examples/04_automated_trading.py --tickers AAPL TSLA
uv run python examples/04_automated_trading.py --tickers AAPL MSFT NVDA --dry-run
uv run python examples/04_automated_trading.py --tickers AAPL --broker alpaca
# Alpaca requires: ALPACA_API_KEY and ALPACA_API_SECRET in environment
```

```python
from pathlib import Path
from prediction_trading import PredictionTradingSystem
from prediction_trading.trading.state import StateStore

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
report = trader.run_once()
print(f"Cycle finished at {report.finished_at}")
for action in report.actions:
    print(f"  {action.ticker}: {action.action} — {action.reason}")

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
report2 = trader2.run_once()
print(f"After cycle 2 — Equity: ${trader2.portfolio.equity({}):.2f}")
```

---

## 6. Custom Indicator Categories

Filter scoring to specific categories using the Python API directly. No standalone script — run inline.

```python
from prediction_trading.prediction.signal_scorer import SignalScorer
from prediction_trading.indicators import TechnicalIndicators
from prediction_trading.data_fetcher import DataFetcher

fetcher = DataFetcher()
market = fetcher.fetch("SPY")
df = TechnicalIndicators.compute_all(market.ohlcv)

# Score using only trend and volume (ignore all other categories)
# Available categories: trend, momentum, volatility, volume, support, fundamental,
#                       news, macro, sector
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

---

## 7. Enriched Context (News / Macro / Sector)

Fetch and inspect the three enriched context objects, then score with the `news`, `macro`, and `sector` categories enabled.

**Requires:** live internet (yfinance). No API key needed.

```bash
uv run python examples/08_enriched_context.py
uv run python examples/08_enriched_context.py --ticker NVDA
uv run python examples/08_enriched_context.py --ticker TSLA --categories trend news macro sector
```

```python
from prediction_trading.data_fetcher import DataFetcher
from prediction_trading.indicators import TechnicalIndicators
from prediction_trading.prediction import SignalScorer

ticker = "AAPL"
fetcher = DataFetcher()

# include_enriched=True populates news_context, macro_context, sector_context
market = fetcher.fetch(ticker, include_enriched=True)

nc, mc, sc = market.news_context, market.macro_context, market.sector_context

if nc:
    print(f"News sentiment : {nc.sentiment_score:+.2f}  ({nc.article_count} articles)")
    print(f"Earnings beat  : {nc.earnings_beat}  miss: {nc.earnings_miss}")
    for h in nc.recent_headlines[:3]:
        print(f"  • {h[:80]}")

if mc:
    print(f"VIX            : {mc.vix}")
    print(f"Yield spread   : {mc.yield_spread:+.2f}%  SPY>SMA50: {mc.spy_above_sma50}")

if sc:
    print(f"Sector         : {sc.sector} ({sc.sector_etf})")
    print(f"Stock vs sector: {sc.vs_sector:+.1f}%  sector vs SPY: {sc.sector_vs_spy:+.1f}%")

# Score with all nine categories (enriched contexts are passed explicitly)
df = TechnicalIndicators.compute_all(market.ohlcv)
scorer = SignalScorer(categories=("trend", "momentum", "news", "macro", "sector"))
signal = scorer.score(
    df,
    news_context=nc,
    macro_context=mc,
    sector_context=sc,
)

arrow = {"bullish": "↑", "bearish": "↓"}.get(signal.direction, "→")
print(f"\n{ticker}: {arrow} {signal.direction.upper()}  "
      f"(net {signal.net_points:+d} pts, conf {signal.confidence:.0%})")
for f in signal.factors:
    marker = "+" if f.direction == "bullish" else "-"
    print(f"  [{marker}] [{f.category:<11}] {f.name:<35} {f.signed:+d} pts")
```

---

## 8. REST API Client

Call the FastAPI server programmatically. Start the server first, then run the client:

```bash
# Terminal 1 — start the server
uv run uvicorn prediction_trading.api.main:app --reload

# Terminal 2 — run the client
uv run python examples/07_rest_api.py
uv run python examples/07_rest_api.py --base-url http://localhost:8000
```

```python
import json, urllib.request

BASE = "http://localhost:8000"

def post(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())

# Health check
import urllib.request as _ur
with _ur.urlopen(f"{BASE}/health") as r:
    print(json.loads(r.read()))   # {"status": "ok"}

# Single prediction
pred = post("/predict/", {"ticker": "AAPL", "lookback_days": 365})
print(f"{pred['ticker']}: {pred['direction']} ({pred['confidence']:.0%})")

# Watchlist scan
scan = post("/scan/", {"tickers": ["AAPL", "MSFT", "NVDA", "TSLA"], "workers": 4})
for r in scan["results"]:
    print(f"{r['ticker']:6} {r['direction']:8} {r['confidence']:.0%}")

# Backtest
bt = post("/backtest/", {"ticker": "AAPL", "start": "2023-01-01", "end": "2024-01-01"})
stats = bt["stats"]
print(f"Return: {stats['return_pct']:+.2f}%  Trades: {stats['trades']}")

# Start AutoTrader session (dry run)
started = post("/trading/start", {"tickers": ["AAPL", "MSFT"], "initial_capital": 10000.0, "dry_run": True})
print(f"Running: {started['running']}  Tickers: {started['tickers']}")

# AutoTrader status
import urllib.request as _ur
with _ur.urlopen(f"{BASE}/trading/status") as r:
    status = json.loads(r.read())
print(f"Equity: ${status.get('equity', 0):,.2f}  Open positions: {len(status.get('open_positions', []))}")
```

---

## 9. Timing Recommendation

Get an actionable entry/exit signal with price levels and R:R ratio. No API key needed.

```bash
uv run python examples/09_timing_recommendation.py --ticker AAPL
uv run python examples/09_timing_recommendation.py --ticker NVDA --timeframe 1m
ANTHROPIC_API_KEY=... uv run python examples/09_timing_recommendation.py --ticker AAPL --ai
```

```python
from prediction_trading import PredictionTradingSystem

system = PredictionTradingSystem("AAPL")
market = system.fetch()
prediction = system.predict(market)

t = prediction.timing
if t:
    print(f"Action:      {t.action}")
    print(f"Reason:      {t.reason}")
    print(f"Horizon:     {t.time_horizon}")
    if t.entry_price:
        print(f"Entry:       ${t.entry_price:,.2f}")
    if t.stop_loss:
        print(f"Stop loss:   ${t.stop_loss:,.2f}")
    if t.take_profit:
        print(f"Take profit: ${t.take_profit:,.2f}")
    if t.entry_price and t.stop_loss and t.take_profit:
        risk = abs(t.entry_price - t.stop_loss)
        reward = abs(t.take_profit - t.entry_price)
        if risk > 0:
            print(f"R:R ratio:   {reward / risk:.2f}")
```

Seven possible `TimingAction` values:

| Action | Meaning |
|--------|---------|
| `BUY_NOW` | Strong bullish — enter at market price |
| `BUY_ON_DIP` | Bullish but overextended — wait for SMA50 pullback |
| `BUY_ON_BREAKOUT` | Near resistance — buy on confirmed breakout |
| `SELL_NOW` | Strong bearish — exit at market price |
| `SELL_TRAILING` | Near price target — protect gains with trailing stop |
| `HOLD` | Directional bias present but confidence too low |
| `WAIT` | No clear signal — stay in cash |

---

## 10. ETF Portfolio Analysis

Lookup ETF metadata and analyse portfolio-level correlation, diversification, and sector exposure. No API key needed.

```bash
uv run python examples/10_etf_portfolio.py
uv run python examples/10_etf_portfolio.py --tickers SPY QQQ XLK BND GLD TLT VEA
uv run python examples/10_etf_portfolio.py --lookback 90
```

```python
from prediction_trading.etf import ETFAnalyzer

analyzer = ETFAnalyzer()

# Per-ticker metadata (uses built-in catalogue — no network needed for common ETFs)
info = analyzer.get_etf_info("SPY")
print(f"{info.ticker}: {info.name} | {info.category} | ER: {info.expense_ratio}%")

# Portfolio analysis — fetches price history via yfinance
analysis = analyzer.analyze_portfolio(["SPY", "QQQ", "XLK", "BND", "GLD"])
print(f"Diversification score: {analysis.diversification_score:.2f}")
print("Sector exposure:", analysis.sector_exposure)
for rec in analysis.recommendations:
    print(f"  • {rec}")
```

Built-in catalogue covers 30+ ETFs (broad market, SPDR sectors, bonds, gold, silver, international). Unknown tickers fall back to yfinance.
