"""Run a single automated-trading cycle against a paper or Alpaca broker.

This example mirrors what ``automated-trader --once --dry-run`` does,
but as a plain Python script so you can inspect the returned
:class:`~prediction_trading.trading.CycleReport` object.

Run:
    uv run python examples/04_automated_trading.py --tickers AAPL TSLA
    uv run python examples/04_automated_trading.py --tickers AAPL --broker alpaca
    uv run python examples/04_automated_trading.py --tickers AAPL --data-source alpaca

Alpaca requires env vars: ALPACA_API_KEY and ALPACA_API_SECRET.
Install the SDK first: uv pip install alpaca-py
"""
from __future__ import annotations

import argparse
import sys

from prediction_trading import PredictionTradingSystem
from prediction_trading.data_fetcher import create_data_fetcher
from prediction_trading.trading.broker import AlpacaBroker


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+",
                        default=["AAPL", "MSFT", "NVDA"])
    parser.add_argument("--capital", type=float, default=10_000.0)
    parser.add_argument("--ai", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--broker", choices=["paper", "alpaca"], default="paper",
                        help="Broker backend (default: paper). "
                             "alpaca requires ALPACA_API_KEY + ALPACA_API_SECRET.")
    parser.add_argument("--data-source", choices=["yfinance", "alpaca", "both"],
                        default="yfinance", help="OHLCV data source (default: yfinance).")
    args = parser.parse_args()

    system = PredictionTradingSystem(
        ticker=args.tickers[0],
        initial_capital=args.capital,
        enable_ai=args.ai,
    )
    system.cfg.data["source"] = args.data_source
    system.data_fetcher = create_data_fetcher(
        args.data_source, interval=system.cfg.data.get("interval", "1d")
    )
    if system.ai_predictor is not None:
        system.ai_predictor._data_fetcher = system.data_fetcher

    broker = AlpacaBroker(paper_trading=True) if args.broker == "alpaca" else None
    trader = system.build_auto_trader(
        tickers=args.tickers,
        broker=broker,
        dry_run=args.dry_run,
    )

    report = trader.run_once()

    print("\n=== Cycle report ===")
    print(f"Equity: ${report.equity:,.2f}" if report.equity else "Equity: n/a")
    print(f"Cash  : ${report.cash:,.2f}" if report.cash else "Cash: n/a")
    print(f"Errors: {len(report.errors)}")
    print("\nActions:")
    for a in report.actions:
        tag = f"[{a.action.upper():<5}] {a.ticker:<6}"
        extras = []
        if a.direction:
            extras.append(a.direction)
        if a.confidence is not None:
            extras.append(f"conf={a.confidence:.0%}")
        if a.price is not None:
            extras.append(f"${a.price:.2f}")
        if a.quantity is not None:
            extras.append(f"qty={a.quantity}")
        print(f"  {tag} {' '.join(extras):<30} {a.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
