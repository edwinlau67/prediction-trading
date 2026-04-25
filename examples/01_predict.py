"""Quick prediction: rule-based + optional AI fusion.

Run:
    uv run python examples/01_predict.py --ticker AAPL
    ANTHROPIC_API_KEY=... uv run python examples/01_predict.py --ticker AAPL --ai
"""
from __future__ import annotations

import argparse
import sys

from prediction_trading import PredictionTradingSystem


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--ai", action="store_true",
                        help="Enable Claude-based prediction fusion.")
    parser.add_argument("--timeframe", default="1w")
    args = parser.parse_args()

    system = PredictionTradingSystem(
        ticker=args.ticker, enable_ai=args.ai,
    )
    system.cfg.ai["timeframe"] = args.timeframe
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
