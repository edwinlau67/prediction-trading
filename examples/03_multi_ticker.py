"""Compare predictions and backtests across multiple tickers.

Run:
    python examples/03_multi_ticker.py --tickers AAPL MSFT GOOGL TSLA
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import PredictionTradingSystem  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+",
                        default=["AAPL", "MSFT", "GOOGL", "TSLA"])
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2024-01-01")
    parser.add_argument("--ai", action="store_true")
    args = parser.parse_args()

    rows = []
    for ticker in args.tickers:
        system = PredictionTradingSystem(ticker=ticker, enable_ai=args.ai)
        result = system.backtest(args.start, args.end)
        prediction = system.predict(system._market)
        s = result.summary()
        rows.append({
            "ticker": ticker,
            "return_pct": s["return_pct"],
            "max_dd_pct": s["max_drawdown_pct"],
            "trades": s["trades"],
            "win_rate": s["win_rate_pct"],
            "next_direction": prediction.direction,
            "next_confidence": f"{prediction.confidence:.0%}",
        })

    print("\n" + pd.DataFrame(rows).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
