#!/usr/bin/env python3
"""Watchlist scanner CLI.

Scans multiple tickers with the rule-based engine and prints a ranked table.
No API key required.

Usage
-----
    scan-watchlist AAPL TSLA NVDA MSFT
    scan-watchlist AAPL TSLA --min-confidence 0.4
    scan-watchlist AAPL TSLA --indicators trend momentum
"""
from __future__ import annotations

import argparse
import sys

from prediction_trading.prediction.factor import ALL_CATEGORIES
from prediction_trading.scanner import WatchlistScanner


BULL = "\033[32m"
BEAR = "\033[31m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _color(direction: str, text: str) -> str:
    if direction == "bullish":
        return f"{BULL}{text}{RESET}"
    if direction == "bearish":
        return f"{BEAR}{text}{RESET}"
    return text


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Rule-based watchlist scanner.")
    ap.add_argument("tickers", nargs="+", help="Ticker symbols to scan.")
    ap.add_argument(
        "--indicators", nargs="+", choices=ALL_CATEGORIES, default=list(ALL_CATEGORIES),
        metavar="INDICATOR",
        help="Indicator categories to include (default: all six).",
    )
    ap.add_argument(
        "--min-confidence", type=float, default=0.0, metavar="FLOAT",
        help="Only show results at or above this confidence (0.0–1.0).",
    )
    ap.add_argument(
        "--workers", type=int, default=4,
        help="Number of parallel fetch threads (default: 4).",
    )
    return ap.parse_args()


def main() -> None:
    args = _parse_args()
    cats = tuple(args.indicators)

    scanner = WatchlistScanner(
        categories=cats,
        min_confidence=args.min_confidence,
        workers=args.workers,
    )

    print(f"\nScanning {len(args.tickers)} ticker(s)…\n")
    results = scanner.scan([t.upper() for t in args.tickers])

    if not results:
        print("No results meet the confidence threshold.")
        sys.exit(0)

    col_w = [8, 10, 12, 10, 50]
    header = (
        f"{'Ticker':<{col_w[0]}} {'Direction':<{col_w[1]}} "
        f"{'Confidence':>{col_w[2]}} {'Price':>{col_w[3]}}  Top factors"
    )
    print(f"{BOLD}{header}{RESET}")
    print("-" * 95)

    for r in results:
        if r.error:
            print(f"{'  ' + r.ticker:<{col_w[0]}} {'ERROR':<{col_w[1]}}  {r.error}")
            continue
        conf_str = f"{r.confidence:.1%}"
        factors = " | ".join(r.top_factors) if r.top_factors else "—"
        row = (
            f"{r.ticker:<{col_w[0]}} "
            f"{r.direction:<{col_w[1]}} "
            f"{conf_str:>{col_w[2]}} "
            f"${r.current_price:>{col_w[3] - 1}.2f}  "
            f"{factors}"
        )
        print(_color(r.direction, row))

    print()


if __name__ == "__main__":
    main()
