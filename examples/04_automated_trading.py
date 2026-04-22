"""Run a single automated-trading cycle against a live paper broker.

This example mirrors what ``automated_trader.py --once --dry-run`` does,
but as a plain Python script so you can inspect the returned
:class:`~src.trading.CycleReport` object.

Run:
    python examples/04_automated_trading.py --tickers AAPL TSLA
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import PredictionTradingSystem  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+",
                        default=["AAPL", "MSFT", "NVDA"])
    parser.add_argument("--capital", type=float, default=10_000.0)
    parser.add_argument("--ai", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    system = PredictionTradingSystem(
        ticker=args.tickers[0],
        initial_capital=args.capital,
        enable_ai=args.ai,
    )
    trader = system.build_auto_trader(
        tickers=args.tickers,
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
