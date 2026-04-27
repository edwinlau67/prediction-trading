"""Compare predictions and backtests across multiple tickers.

Run:
    uv run python examples/03_multi_ticker.py --tickers AAPL MSFT GOOGL TSLA
    uv run python examples/03_multi_ticker.py --tickers AAPL MSFT --data-source alpaca
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from prediction_trading import PredictionTradingSystem
from prediction_trading.data_fetcher import create_data_fetcher


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+",
                        default=["AAPL", "MSFT", "GOOGL", "TSLA"])
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default="2024-01-01")
    parser.add_argument("--ai", action="store_true")
    parser.add_argument("--data-source", choices=["yfinance", "alpaca", "both"],
                        default="yfinance", help="OHLCV data source (default: yfinance).")
    args = parser.parse_args()

    rows = []
    for ticker in args.tickers:
        system = PredictionTradingSystem(ticker=ticker, enable_ai=args.ai)
        system.cfg.data["source"] = args.data_source
        system.data_fetcher = create_data_fetcher(
            args.data_source, interval=system.cfg.data.get("interval", "1d")
        )
        if system.ai_predictor is not None:
            system.ai_predictor._data_fetcher = system.data_fetcher
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
