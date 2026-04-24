"""Screen a watchlist in parallel and print a ranked confidence table.

No API key required — rule-based only.

Run:
    python examples/05_watchlist_scan.py
    python examples/05_watchlist_scan.py --tickers AAPL MSFT NVDA TSLA META
    python examples/05_watchlist_scan.py --min-confidence 0.4 --indicators trend momentum
    python examples/05_watchlist_scan.py --workers 8 --csv scan_results.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scanner import WatchlistScanner  # noqa: E402

_DEFAULT_TICKERS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "META",
    "GOOGL", "AMZN", "AMD", "INTC", "QCOM",
]

_ALL_CATEGORIES = ("trend", "momentum", "volatility", "volume", "support", "fundamental")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", nargs="+", default=_DEFAULT_TICKERS)
    parser.add_argument("--indicators", nargs="+", default=list(_ALL_CATEGORIES),
                        choices=_ALL_CATEGORIES, metavar="CAT")
    parser.add_argument("--min-confidence", type=float, default=0.0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--csv", metavar="FILE", help="Export results to CSV file")
    args = parser.parse_args()

    scanner = WatchlistScanner(
        categories=tuple(args.indicators),
        min_confidence=args.min_confidence,
        workers=args.workers,
    )

    print(f"Scanning {len(args.tickers)} tickers with {args.workers} workers…")
    results = scanner.scan(args.tickers)

    label = {"bullish": "BUY", "bearish": "SELL", "neutral": "HOLD"}
    header = f"{'Ticker':<8} {'Signal':<6} {'Conf':>6}  {'Price':>8}  Top Factors"
    print("\n" + header)
    print("-" * 72)
    for r in results:
        if r.error:
            print(f"{r.ticker:<8} {'ERROR':<6} {'':>6}  {'':>8}  {r.error}")
            continue
        sig = label.get(r.direction, r.direction.upper())
        price = f"${r.current_price:.2f}" if r.current_price else "n/a"
        factors = ", ".join(r.top_factors[:3])
        print(f"{r.ticker:<8} {sig:<6} {r.confidence:5.0%}  {price:>8}  {factors}")

    if args.csv:
        path = Path(args.csv)
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["ticker", "direction", "confidence", "price", "top_factors", "error"],
            )
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "ticker": r.ticker,
                    "direction": r.direction,
                    "confidence": f"{r.confidence:.3f}",
                    "price": f"{r.current_price:.2f}" if r.current_price else "",
                    "top_factors": "; ".join(r.top_factors),
                    "error": r.error or "",
                })
        print(f"\nExported: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
