"""Run a full backtest and write a Markdown + charts report.

Run:
    python examples/02_backtest.py --ticker AAPL --start 2023-01-01 --end 2024-01-01
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import PredictionTradingSystem  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2024-01-01")
    parser.add_argument("--capital", type=float, default=10_000.0)
    parser.add_argument("--ai", action="store_true")
    args = parser.parse_args()

    system = PredictionTradingSystem(
        ticker=args.ticker,
        initial_capital=args.capital,
        enable_ai=args.ai,
    )

    result = system.backtest(args.start, args.end)
    prediction = system.predict(system._market)

    print("\n=== Backtest Stats ===")
    for k, v in result.summary().items():
        print(f"  {k:>20}: {v}")

    out_dir = system.save_report(result=result, prediction=prediction)
    print(f"\nReport saved: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
