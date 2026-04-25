#!/usr/bin/env python3
"""Automated trading CLI — prediction-driven live/paper trading.

Wires the same prediction + risk engine used by ``stock-predictor`` and
the backtester into a scheduled trade loop. Paper trading is the default
so it is safe to run without a broker account.

Usage
-----
    # Single cycle, dry-run (no orders submitted), using defaults
    automated-trader --tickers AAPL TSLA --dry-run --once

    # Paper-trade every 5 minutes, persist state, log trades
    automated-trader --tickers AAPL MSFT NVDA --interval 300

    # Enforce US equities market hours and use Claude-fused predictions
    ANTHROPIC_API_KEY=sk-ant-... automated-trader --tickers AAPL --ai --market-hours
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from prediction_trading import PredictionTradingSystem
from prediction_trading.reporting.base import BaseReportWriter


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Prediction-driven automated trading engine.",
    )
    ap.add_argument(
        "--tickers", nargs="+", required=True,
        help="Watchlist of stock ticker symbols.",
    )
    ap.add_argument(
        "--capital", type=float, default=10_000.0,
        help="Initial paper capital (default: 10000).",
    )
    ap.add_argument(
        "--interval", type=int, default=300,
        help="Seconds between cycles (default: 300).",
    )
    ap.add_argument(
        "--cycles", type=int, default=None,
        help="Run at most N cycles then exit (default: unlimited).",
    )
    ap.add_argument(
        "--once", action="store_true",
        help="Run a single cycle and exit (equivalent to --cycles 1).",
    )
    ap.add_argument(
        "--ai", action="store_true",
        help="Fuse Claude predictions with rule-based scoring.",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Emit signals to the log but never submit orders.",
    )
    ap.add_argument(
        "--market-hours", action="store_true",
        help="Only trade during US equities regular session (09:30–16:00 ET).",
    )
    ap.add_argument(
        "--run-name", default=None,
        help="Custom name for the results folder (default: auto-stamped).",
    )
    ap.add_argument(
        "--out", default="results",
        help="Root directory for the run folder (default: results/).",
    )
    return ap.parse_args()


def _make_run_dir(out_root: str, run_name: str | None) -> Path:
    writer = BaseReportWriter(out_root=out_root)
    writer.RUN_PREFIX = "live"
    if run_name:
        path = Path(out_root) / run_name
        path.mkdir(parents=True, exist_ok=True)
        return path
    return writer.new_run_dir()


def main() -> None:
    args = _parse_args()
    run_dir = _make_run_dir(args.out, args.run_name)

    print(f"\nRun folder : {run_dir}")
    print(f"Tickers    : {', '.join(args.tickers)}")
    print(f"Capital    : ${args.capital:,.2f}")
    print(f"AI fusion  : {'enabled' if args.ai else 'disabled'}")
    print(f"Mode       : {'DRY-RUN' if args.dry_run else 'paper trading'}")
    print(f"Market hrs : {'enforced' if args.market_hours else 'always on'}")
    print(f"Interval   : {args.interval}s")

    system = PredictionTradingSystem(
        ticker=args.tickers[0],
        initial_capital=args.capital,
        enable_ai=args.ai,
    )
    trader = system.build_auto_trader(
        tickers=args.tickers,
        state_path=run_dir / "portfolio_state.json",
        trade_log_path=run_dir / "trades.csv",
        log_dir=run_dir,
        dry_run=args.dry_run,
        enforce_market_hours=args.market_hours,
    )

    max_cycles = 1 if args.once else args.cycles
    try:
        if max_cycles == 1:
            report = trader.run_once()
            _print_cycle(1, report)
        else:
            reports = trader.run(
                interval_seconds=args.interval, max_cycles=max_cycles,
            )
            for i, rep in enumerate(reports, 1):
                _print_cycle(i, rep)
    except KeyboardInterrupt:
        print("\nStopping (Ctrl-C). State saved to", run_dir / "portfolio_state.json")
        sys.exit(0)

    print(f"\nTrade log  : {run_dir / 'trades.csv'}")
    print(f"State file : {run_dir / 'portfolio_state.json'}")


def _print_cycle(index: int, report) -> None:
    print(f"\n── Cycle {index} @ {report.started_at.isoformat(timespec='seconds')}")
    if report.equity is not None:
        print(f"   equity=${report.equity:,.2f}  cash=${report.cash:,.2f}")
    if not report.actions:
        print("   (no actions)")
        return
    for action in report.actions:
        extras = []
        if action.confidence is not None:
            extras.append(f"conf={action.confidence:.0%}")
        if action.price is not None:
            extras.append(f"${action.price:.2f}")
        if action.quantity is not None:
            extras.append(f"qty={action.quantity}")
        if action.pnl is not None:
            extras.append(f"pnl=${action.pnl:.2f}")
        extras_str = " ".join(extras)
        print(f"   [{action.action.upper():<5}] {action.ticker:<6} "
              f"{action.direction or '-':<8} {extras_str}  {action.reason}")


if __name__ == "__main__":
    main()
