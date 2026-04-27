"""Quick prediction: rule-based + optional AI fusion.

Outputs direction, confidence, price target, risk level, key factors,
and a TimingRecommendation (entry/stop/target levels with R:R ratio).

Run:
    uv run python examples/01_predict.py --ticker AAPL
    uv run python examples/01_predict.py --ticker AAPL --data-source alpaca
    ANTHROPIC_API_KEY=... uv run python examples/01_predict.py --ticker AAPL --ai
"""
from __future__ import annotations

import argparse
import sys

from prediction_trading import PredictionTradingSystem
from prediction_trading.data_fetcher import create_data_fetcher


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--ai", action="store_true",
                        help="Enable Claude-based prediction fusion.")
    parser.add_argument("--timeframe", default="1w")
    parser.add_argument("--data-source", choices=["yfinance", "alpaca", "both"],
                        default="yfinance", help="OHLCV data source (default: yfinance).")
    args = parser.parse_args()

    system = PredictionTradingSystem(
        ticker=args.ticker, enable_ai=args.ai,
    )
    system.cfg.ai["timeframe"] = args.timeframe
    system.cfg.data["source"] = args.data_source
    system.data_fetcher = create_data_fetcher(
        args.data_source, interval=system.cfg.data.get("interval", "1d")
    )
    if system.ai_predictor is not None:
        system.ai_predictor._data_fetcher = system.data_fetcher
    market = system.fetch()
    prediction = system.predict(market)

    print(f"\n=== {prediction.ticker} prediction ===")
    print(f"Direction:     {prediction.direction}")
    print(f"Confidence:    {prediction.confidence:.1%}")
    print(f"Current price: ${prediction.current_price:,.2f}")
    if prediction.price_target is not None:
        print(f"Price target:  ${prediction.price_target:,.2f} "
              f"(by {prediction.target_date})")
    print(f"Risk level:    {prediction.risk_level}")
    print(f"Actionable:    {prediction.meta.get('actionable')}")
    print("\nFactors:")
    for f in prediction.factors[:8]:
        print(f"  - {f}")
    if prediction.ai_signal and prediction.ai_signal.narrative:
        print("\nAI narrative:")
        print(prediction.ai_signal.narrative)
    if prediction.timing is not None:
        t = prediction.timing
        print(f"\nTiming:        {t.action}  — {t.reason}")
        print(f"  Horizon:     {t.time_horizon}")
        if t.entry_price is not None:
            print(f"  Entry:       ${t.entry_price:,.2f}")
        if t.stop_loss is not None:
            print(f"  Stop loss:   ${t.stop_loss:,.2f}")
        if t.take_profit is not None:
            print(f"  Take profit: ${t.take_profit:,.2f}")
        if (t.entry_price is not None
                and t.stop_loss is not None
                and t.take_profit is not None):
            risk = abs(t.entry_price - t.stop_loss)
            reward = abs(t.take_profit - t.entry_price)
            if risk > 0:
                print(f"  R:R ratio:   {reward / risk:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
