"""Run a full backtest and write a Markdown + charts report.

Run:
    uv run python examples/02_backtest.py --ticker AAPL
    uv run python examples/02_backtest.py --ticker AAPL --data-source alpaca
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from prediction_trading import PredictionTradingSystem
from prediction_trading.data_fetcher import create_data_fetcher


def main() -> int:
    _today = datetime.now()
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--start", default=(_today - timedelta(days=365)).strftime("%Y-%m-%d"))
    parser.add_argument("--end", default=_today.strftime("%Y-%m-%d"))
    parser.add_argument("--capital", type=float, default=10_000.0)
    parser.add_argument("--ai", action="store_true")
    parser.add_argument("--data-source", choices=["yfinance", "alpaca", "both"],
                        default="yfinance", help="OHLCV data source (default: yfinance).")
    args = parser.parse_args()

    system = PredictionTradingSystem(
        ticker=args.ticker,
        initial_capital=args.capital,
        enable_ai=args.ai,
    )
    system.cfg.data["source"] = args.data_source
    system.data_fetcher = create_data_fetcher(
        args.data_source, interval=system.cfg.data.get("interval", "1d")
    )
    if system.ai_predictor is not None:
        system.ai_predictor._data_fetcher = system.data_fetcher

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
