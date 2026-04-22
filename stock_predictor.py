#!/usr/bin/env python3
"""Stock predictor CLI — mirrors ``edwinlau67/stock-prediction``.

Runs AI-assisted or purely rule-based predictions for one or more tickers
and writes a ``predictions.md`` plus per-ticker chart PNGs into
``results/YYYYMMDD_HHMMSS/``.

Usage
-----
    python stock_predictor.py
    python stock_predictor.py --tickers AAPL TSLA NVDA
    python stock_predictor.py --tickers MSFT --timeframe 3m
    python stock_predictor.py --tickers NVDA --indicators trend momentum
    ANTHROPIC_API_KEY=sk-ant-... python stock_predictor.py --tickers AAPL --model claude-opus-4-7
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.data_fetcher import DataFetcher  # noqa: E402
from src.indicators import TechnicalIndicators  # noqa: E402
from src.logger import get_logger  # noqa: E402
from src.prediction import (  # noqa: E402
    ALL_CATEGORIES, AIPredictor, SignalScorer, UnifiedPredictor,
)
from src.reporting import (  # noqa: E402
    PredictionChart, PredictionReportEntry, PredictionReportWriter,
)


SUPPORTED_MODELS = (
    "claude-sonnet-4-6",
    "claude-opus-4-7",
    "claude-haiku-4-5-20251001",
)
SUPPORTED_TIMEFRAMES = ("1d", "1w", "1m", "3m", "6m", "ytd", "1y", "2y", "5y")


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="AI-powered stock predictor using Claude tool use."
    )
    ap.add_argument(
        "--tickers", nargs="+", default=["AAPL", "TSLA", "INTC"],
        help="One or more stock ticker symbols (default: AAPL TSLA INTC)",
    )
    ap.add_argument(
        "--timeframe", choices=SUPPORTED_TIMEFRAMES, default="1w",
        help="Prediction timeframe (default: 1w)",
    )
    ap.add_argument(
        "--model", default=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
        help="Claude model ID (default: claude-sonnet-4-6)",
    )
    ap.add_argument(
        "--indicators", nargs="+", choices=ALL_CATEGORIES, default=list(ALL_CATEGORIES),
        metavar="INDICATOR",
        help="Indicator categories to include (default: all six)",
    )
    ap.add_argument(
        "--no-ai", action="store_true",
        help="Skip the Claude call; emit a rule-based-only prediction.",
    )
    ap.add_argument(
        "--out", default="results",
        help="Root directory for run output (default: results).",
    )
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    log = get_logger()
    cats = tuple(args.indicators)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    use_ai = bool(api_key) and not args.no_ai

    data_fetcher = DataFetcher()
    scorer = SignalScorer(categories=cats)
    ai = AIPredictor(
        api_key=api_key if use_ai else None,
        model=args.model,
        data_fetcher=data_fetcher,
        categories=cats,
    ) if use_ai else None
    predictor = UnifiedPredictor(
        scorer=scorer, ai=ai, ai_enabled=use_ai,
        ai_weight=0.5, min_confidence=0.0, timeframe=args.timeframe,
    )

    writer = PredictionReportWriter(out_root=args.out)
    chart = PredictionChart()
    run_dir = writer.new_run_dir()

    print(f"\nRun folder: {run_dir}")
    print(f"Timeframe : {args.timeframe}")
    print(f"Model     : {args.model if use_ai else '(AI disabled — rule-based only)'}")
    print(f"Indicators: {', '.join(sorted(cats))}")
    print(f"Tickers   : {', '.join(args.tickers)}\n")

    entries: list[PredictionReportEntry] = []
    for ticker in args.tickers:
        try:
            print(f"→ {ticker} …", flush=True)
            market = data_fetcher.fetch(ticker.upper(), lookback_days=365)
            df = TechnicalIndicators.compute_all(market.ohlcv)
            weekly = market.ohlcv.resample("W").agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum",
            }).dropna()
            weekly_df = TechnicalIndicators.compute_all(weekly)

            prediction = predictor.predict(
                ticker=market.ticker, df=df,
                current_price=market.current_price,
                weekly=weekly_df,
                fundamentals=market.fundamentals,
            )

            chart_path = run_dir / "charts" / f"{market.ticker}_{args.timeframe}.png"
            chart.render(
                prediction, market.ohlcv,
                categories=cats, timeframe=args.timeframe,
                out_path=chart_path,
            )

            entries.append(PredictionReportEntry(
                prediction=prediction,
                timeframe=args.timeframe,
                chart_path=chart_path,
                ohlcv=market.ohlcv,
            ))

            tgt = (f" → ${prediction.price_target:.2f}" if prediction.price_target
                   else "")
            print(f"   {prediction.direction.upper():<8} "
                  f"conf={prediction.confidence:.0%}  "
                  f"current=${prediction.current_price:.2f}{tgt}")
        except Exception as exc:
            log.exception("Prediction failed for %s", ticker)
            print(f"   FAILED: {exc}")

    if not entries:
        print("\nNo predictions succeeded.")
        return 1

    report = writer.write(run_dir, entries, model=args.model if use_ai else None,
                          categories=cats)
    print(f"\nReport: {report}")
    print(f"Charts: {run_dir / 'charts'}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
