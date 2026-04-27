"""ETF metadata lookup and portfolio correlation analysis.

Demonstrates ETFAnalyzer — per-ticker metadata from the built-in catalogue
(no network needed for common ETFs), then portfolio-level correlation,
diversification score, sector exposure, and actionable recommendations.

Run (no API key needed):
    uv run python examples/10_etf_portfolio.py
    uv run python examples/10_etf_portfolio.py --tickers SPY QQQ XLK BND GLD TLT VEA
    uv run python examples/10_etf_portfolio.py --lookback 90
"""
from __future__ import annotations

import argparse
import sys

from prediction_trading.etf import ETFAnalyzer


def _print_corr_matrix(corr) -> None:
    tickers = list(corr.columns)
    col_w = 8
    header = f"{'':>{col_w}}" + "".join(f"{t:>{col_w}}" for t in tickers)
    print(header)
    print("-" * len(header))
    for t in tickers:
        row = f"{t:>{col_w}}"
        for t2 in tickers:
            row += f"{corr.loc[t, t2]:>{col_w}.2f}"
        print(row)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tickers", nargs="+", default=["SPY", "QQQ", "XLK", "BND", "GLD"],
        help="ETF tickers to analyse (default: SPY QQQ XLK BND GLD)",
    )
    parser.add_argument(
        "--lookback", type=int, default=252,
        help="Trading-day lookback for correlation (default: 252)",
    )
    args = parser.parse_args()
    tickers = [t.upper() for t in args.tickers]

    analyzer = ETFAnalyzer()

    # ── Part 1: per-ticker metadata ───────────────────────────────────────────
    print("=== ETF Metadata ===")
    print(f"{'Ticker':<6}  {'Name':<38}  {'Category':<30}  {'Index':<22}  {'ER%':>5}  ETF?")
    print("-" * 112)
    for ticker in tickers:
        info = analyzer.get_etf_info(ticker)
        er = f"{info.expense_ratio:.2f}" if info.expense_ratio is not None else "n/a"
        print(
            f"{info.ticker:<6}  {info.name:<38}  {info.category:<30}  "
            f"{info.tracked_index:<22}  {er:>5}  {'yes' if info.is_etf else 'no'}"
        )

    # ── Part 2: portfolio analysis ────────────────────────────────────────────
    print(f"\n=== Portfolio Analysis  ({args.lookback}-day lookback) ===")
    print("Fetching price history…")
    analysis = analyzer.analyze_portfolio(tickers, lookback_days=args.lookback)

    print(f"\nDiversification score: {analysis.diversification_score:.2f} / 1.00")
    print("  (1.00 = perfectly uncorrelated; 0.00 = all move in lockstep)")

    if not analysis.correlation_matrix.empty:
        print("\nCorrelation matrix (daily returns):")
        _print_corr_matrix(analysis.correlation_matrix)

    if analysis.sector_exposure:
        print("\nSector exposure (equal-weighted):")
        for sector, weight in sorted(
            analysis.sector_exposure.items(), key=lambda x: x[1], reverse=True
        ):
            bar = "█" * int(weight * 40)
            print(f"  {sector:<22} {weight:>5.0%}  {bar}")

    if analysis.recommendations:
        print("\nRecommendations:")
        for rec in analysis.recommendations:
            print(f"  • {rec}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
