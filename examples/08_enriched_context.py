"""Prediction using enriched context: news sentiment, macro indicators, sector strength.

The news/macro/sector scoring categories require external data fetched via
``DataFetcher.fetch(..., include_enriched=True)``.  This example shows how to
fetch that data, inspect the three context objects, and run ``SignalScorer``
directly so the enriched factors appear in the output.

Requires live internet. No API key needed.

Run:
    uv run python examples/08_enriched_context.py
    uv run python examples/08_enriched_context.py --ticker NVDA
    uv run python examples/08_enriched_context.py --ticker TSLA --categories trend news macro sector
    uv run python examples/08_enriched_context.py --ticker AAPL --data-source alpaca
"""
from __future__ import annotations

import argparse
import sys

from prediction_trading.data_fetcher import create_data_fetcher
from prediction_trading.indicators import TechnicalIndicators
from prediction_trading.prediction import SignalScorer

_ENRICHED_CATEGORIES = ("trend", "momentum", "news", "macro", "sector")


def _fmt_bool(val: bool | None) -> str:
    if val is None:
        return "n/a"
    return "yes" if val else "no"


def _print_contexts(market) -> None:
    nc = market.news_context
    mc = market.macro_context
    sc = market.sector_context

    print("\n── News context ─────────────────────────────────────────────────────")
    if nc is None:
        print("  (not available)")
    else:
        print(f"  Sentiment score : {nc.sentiment_score:+.2f}  "
              f"(articles: {nc.article_count})")
        print(f"  Earnings beat   : {_fmt_bool(nc.earnings_beat)}  "
              f"miss: {_fmt_bool(nc.earnings_miss)}")
        days = nc.earnings_upcoming_days
        print(f"  Earnings in     : {'n/a' if days is None else f'{days} days'}")
        for headline in nc.recent_headlines[:3]:
            print(f"    • {headline[:90]}")

    print("\n── Macro context ────────────────────────────────────────────────────")
    if mc is None:
        print("  (not available)")
    else:
        vix = f"{mc.vix:.1f}" if mc.vix is not None else "n/a"
        y10 = f"{mc.yield_10y:.2f}%" if mc.yield_10y is not None else "n/a"
        y2  = f"{mc.yield_2y:.2f}%" if mc.yield_2y is not None else "n/a"
        sprd = f"{mc.yield_spread:+.2f}%" if mc.yield_spread is not None else "n/a"
        print(f"  VIX             : {vix}")
        print(f"  10Y / 2Y yield  : {y10} / {y2}  (spread {sprd})")
        print(f"  SPY above SMA50 : {_fmt_bool(mc.spy_above_sma50)}")

    print("\n── Sector context ───────────────────────────────────────────────────")
    if sc is None:
        print("  (not available)")
    else:
        vs_s = f"{sc.vs_sector:+.1f}%" if sc.vs_sector is not None else "n/a"
        vs_spy = f"{sc.sector_vs_spy:+.1f}%" if sc.sector_vs_spy is not None else "n/a"
        print(f"  Sector          : {sc.sector} ({sc.sector_etf})")
        print(f"  Stock vs sector : {vs_s}  (30d)")
        print(f"  Sector vs SPY   : {vs_spy}  (30d)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument(
        "--categories", nargs="+", default=list(_ENRICHED_CATEGORIES),
        choices=("trend", "momentum", "volatility", "volume",
                 "support", "fundamental", "news", "macro", "sector"),
        metavar="CAT",
    )
    parser.add_argument("--data-source", choices=["yfinance", "alpaca", "both"],
                        default="yfinance", help="OHLCV data source (default: yfinance).")
    args = parser.parse_args()
    ticker = args.ticker.upper()

    # ── Fetch with enriched=True ──────────────────────────────────────────────
    print(f"Fetching enriched data for {ticker}…")
    fetcher = create_data_fetcher(args.data_source)
    market = fetcher.fetch(ticker, include_enriched=True)

    _print_contexts(market)

    # ── Score with enriched categories ───────────────────────────────────────
    print("\n── Scoring ──────────────────────────────────────────────────────────")
    scorer = SignalScorer(categories=tuple(args.categories))
    df = TechnicalIndicators.compute_all(market.ohlcv)
    signal = scorer.score(
        df,
        news_context=market.news_context,
        macro_context=market.macro_context,
        sector_context=market.sector_context,
    )

    arrow = {"bullish": "↑", "bearish": "↓"}.get(signal.direction, "→")
    confidence = min(1.0, abs(signal.net_points) / 10)
    print(f"\n  {ticker}: {arrow} {signal.direction.upper()}  "
          f"(net {signal.net_points:+d} pts, conf {confidence:.0%})")

    print("\n  All factors:")
    for f in signal.factors:
        marker = "+" if f.direction == "bullish" else "-"
        pts = f"{f.signed:+d}" if f.signed else "  0"
        detail = f"  [{f.detail}]" if f.detail else ""
        print(f"    [{marker}] [{f.category:<11}] {f.name:<35} {pts} pts{detail}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
