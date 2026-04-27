"""Prediction with 4H timeframe confluence bonus.

Fetches 1-hour OHLCV, resamples to 4H, and passes it to the predictor.
When the 4H signal agrees with the daily signal, an extra point is awarded.

Requires live internet. No API key needed unless --ai is passed.

Run:
    uv run python examples/06_4h_confluence.py --ticker AAPL
    uv run python examples/06_4h_confluence.py --ticker NVDA --ai
    uv run python examples/06_4h_confluence.py --ticker AAPL --data-source alpaca
"""
from __future__ import annotations

import argparse
import sys

from prediction_trading import PredictionTradingSystem
from prediction_trading.data_fetcher import create_data_fetcher
from prediction_trading.indicators import TechnicalIndicators

_RESAMPLE_RULES = {"Open": "first", "High": "max", "Low": "min",
                   "Close": "last", "Volume": "sum"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--ai", action="store_true",
                        help="Enable Claude AI fusion (requires ANTHROPIC_API_KEY).")
    parser.add_argument("--timeframe", default="1w")
    parser.add_argument("--data-source", choices=["yfinance", "alpaca", "both"],
                        default="yfinance", help="OHLCV data source (default: yfinance).")
    args = parser.parse_args()

    # ── Daily prediction (baseline, no 4H) ───────────────────────────────────
    system = PredictionTradingSystem(ticker=args.ticker, enable_ai=args.ai)
    system.cfg.ai["timeframe"] = args.timeframe
    system.cfg.data["source"] = args.data_source
    system.data_fetcher = create_data_fetcher(
        args.data_source, interval=system.cfg.data.get("interval", "1d")
    )
    if system.ai_predictor is not None:
        system.ai_predictor._data_fetcher = system.data_fetcher
    market = system.fetch()

    baseline = system.predict(market)
    print(f"\n=== {args.ticker} — daily-only signal ===")
    print(f"Direction:  {baseline.direction}  ({baseline.confidence:.0%})")
    print(f"Net points: {baseline.rule_signal.net_points if baseline.rule_signal else 'n/a'}")

    # ── Fetch and resample 1h → 4H ───────────────────────────────────────────
    print("\nFetching 1h OHLCV for 4H confluence…")
    fetcher_1h = create_data_fetcher(args.data_source, interval="1h")
    ohlcv_1h = fetcher_1h.fetch_history(args.ticker, lookback_days=90)
    ohlcv_4h = ohlcv_1h.resample("4h").agg(_RESAMPLE_RULES).dropna()
    df_4h = TechnicalIndicators.compute_all(ohlcv_4h)
    print(f"4H bars fetched: {len(df_4h)}")

    # ── Prediction with 4H confluence ────────────────────────────────────────
    fused = system.predict(market, hourly_4h=df_4h)
    print(f"\n=== {args.ticker} — with 4H confluence ===")
    print(f"Direction:  {fused.direction}  ({fused.confidence:.0%})")
    print(f"Net points: {fused.rule_signal.net_points if fused.rule_signal else 'n/a'}")

    # Show whether a confluence bonus was awarded
    if fused.rule_signal:
        confluence = [f for f in fused.rule_signal.factors
                      if "confluence" in f.name.lower() or "4h" in f.name.lower()]
        if confluence:
            for f in confluence:
                print(f"  Bonus: {f.name} ({'+' if f.signed > 0 else ''}{f.signed} pts)")
        else:
            print("  No 4H confluence bonus (directions disagreed or data insufficient)")

    print("\nTop factors:")
    for f in fused.factors[:8]:
        marker = "↑" if f.direction == "bullish" else "↓"
        print(f"  {marker} [{f.category}] {f.name}")

    if fused.ai_signal and fused.ai_signal.narrative:
        print("\nAI narrative:")
        print(fused.ai_signal.narrative[:600])

    return 0


if __name__ == "__main__":
    sys.exit(main())
