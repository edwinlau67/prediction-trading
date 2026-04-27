"""Standalone timing recommendation demo.

Fetches a prediction and displays the full TimingRecommendation — action,
entry/stop/target levels, horizon, and a computed risk/reward ratio.

Run:
    uv run python examples/09_timing_recommendation.py --ticker AAPL
    uv run python examples/09_timing_recommendation.py --ticker AAPL --data-source alpaca
    ANTHROPIC_API_KEY=... uv run python examples/09_timing_recommendation.py --ticker AAPL --ai

For direct use of the lower-level API:
    from prediction_trading.prediction.timing import compute_timing
    timing = compute_timing(scored_signal, ohlcv_df, prediction)
"""
from __future__ import annotations

import argparse
import sys

from prediction_trading import PredictionTradingSystem
from prediction_trading.data_fetcher import create_data_fetcher

# One-line descriptions for all 7 TimingAction values.
_ACTION_DESCRIPTIONS: dict[str, str] = {
    "BUY_NOW":         "Strong buy signal — enter at market price",
    "BUY_ON_DIP":      "Bullish but overextended — wait for pullback to SMA50",
    "BUY_ON_BREAKOUT": "Near key resistance — buy on confirmed breakout above",
    "SELL_NOW":        "Strong sell signal — exit at market price",
    "SELL_TRAILING":   "Near price target — protect gains with trailing stop",
    "HOLD":            "Directional bias present but confidence too low for action",
    "WAIT":            "No clear directional bias — stay in cash",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--ai", action="store_true",
                        help="Enable Claude-based prediction fusion.")
    parser.add_argument("--timeframe", default="1w")
    parser.add_argument("--data-source", choices=["yfinance", "alpaca", "both"],
                        default="yfinance", help="OHLCV data source (default: yfinance).")
    args = parser.parse_args()

    system = PredictionTradingSystem(ticker=args.ticker, enable_ai=args.ai)
    system.cfg.ai["timeframe"] = args.timeframe
    system.cfg.data["source"] = args.data_source
    system.data_fetcher = create_data_fetcher(
        args.data_source, interval=system.cfg.data.get("interval", "1d")
    )
    if system.ai_predictor is not None:
        system.ai_predictor._data_fetcher = system.data_fetcher
    market = system.fetch()
    prediction = system.predict(market)

    print(f"\n=== {prediction.ticker} — Timing Recommendation ===")
    print(f"Direction:  {prediction.direction}  ({prediction.confidence:.0%} confidence)")
    print(f"Price:      ${prediction.current_price:,.2f}")

    t = prediction.timing
    if t is None:
        print("\nNo timing recommendation available.")
        return 0

    print(f"\nAction:      {t.action}")
    print(f"  → {_ACTION_DESCRIPTIONS.get(t.action, t.action)}")
    print(f"Reason:      {t.reason}")
    print(f"Horizon:     {t.time_horizon}")

    if t.entry_price is not None:
        print(f"\nEntry:       ${t.entry_price:,.2f}")
    if t.stop_loss is not None:
        print(f"Stop loss:   ${t.stop_loss:,.2f}")
    if t.take_profit is not None:
        print(f"Take profit: ${t.take_profit:,.2f}")

    if (t.entry_price is not None
            and t.stop_loss is not None
            and t.take_profit is not None):
        risk = abs(t.entry_price - t.stop_loss)
        reward = abs(t.take_profit - t.entry_price)
        if risk > 0:
            print(f"R:R ratio:   {reward / risk:.2f}")

    print("\n--- All possible actions ---")
    for action, desc in _ACTION_DESCRIPTIONS.items():
        marker = "►" if action == t.action else " "
        print(f"  {marker} {action:<20} {desc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
