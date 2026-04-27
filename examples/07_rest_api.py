"""Interact with the Prediction Trading REST API.

Start the server first:
    uv run uvicorn prediction_trading.api.main:app --reload

Then run this script:
    uv run python examples/07_rest_api.py
    uv run python examples/07_rest_api.py --base-url http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def _post(base_url: str, path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def _get(base_url: str, path: str) -> dict:
    with urllib.request.urlopen(f"{base_url}{path}", timeout=10) as resp:
        return json.loads(resp.read())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    # ── Health check ──────────────────────────────────────────────────────────
    try:
        health = _get(base, "/health")
    except urllib.error.URLError as exc:
        print(f"Cannot reach server at {base}: {exc}")
        print("Start it with: uv run uvicorn prediction_trading.api.main:app --reload")
        return 1

    print(f"Server status: {health['status']}\n")

    # ── Single-ticker prediction ──────────────────────────────────────────────
    print("=== POST /predict/ ===")
    pred = _post(base, "/predict/", {"ticker": "AAPL", "lookback_days": 365})
    print(f"Ticker:     {pred['ticker']}")
    print(f"Direction:  {pred['direction']}")
    print(f"Confidence: {pred['confidence']:.1%}")
    print(f"Price:      ${pred['current_price']:,.2f}")
    if pred.get("price_target"):
        print(f"Target:     ${pred['price_target']:,.2f} (by {pred.get('target_date')})")
    print("Top factors:")
    for f in pred.get("factors", [])[:5]:
        print(f"  [{f['category']}] {f['name']} ({f['direction']}, {f['points']:+d}pts)")

    # ── Watchlist scan ────────────────────────────────────────────────────────
    print("\n=== POST /scan/ ===")
    scan = _post(base, "/scan/", {
        "tickers": ["AAPL", "MSFT", "NVDA", "TSLA"],
        "min_confidence": 0.0,
        "workers": 4,
    })
    label = {"bullish": "BUY", "bearish": "SELL", "neutral": "HOLD"}
    print(f"{'Ticker':<8} {'Signal':<6} {'Conf':>6}  {'Price':>8}  Top Factors")
    print("-" * 60)
    for r in scan.get("results", []):
        if r.get("error"):
            print(f"{r['ticker']:<8} ERROR   {r['error']}")
            continue
        sig = label.get(r["direction"], r["direction"].upper())
        price = f"${r['current_price']:.2f}" if r.get("current_price") else "n/a"
        factors = ", ".join(r.get("top_factors", [])[:3])
        print(f"{r['ticker']:<8} {sig:<6} {r['confidence']:5.0%}  {price:>8}  {factors}")

    # ── Backtest ──────────────────────────────────────────────────────────────
    print("\n=== POST /backtest/ ===")
    bt = _post(base, "/backtest/", {
        "ticker": "AAPL",
        "start": "2023-01-01",
        "end": "2024-01-01",
        "initial_capital": 10000.0,
    })
    stats = bt.get("stats", {})
    print(f"Ticker:       {stats.get('ticker', 'AAPL')}")
    print(f"Period:       {stats.get('period', '')}")
    print(f"Return:       {stats.get('return_pct', 0):.2f}%")
    print(f"Max drawdown: {stats.get('max_drawdown_pct', 0):.2f}%")
    print(f"Trades:       {stats.get('trades', 0)}")
    print(f"Win rate:     {stats.get('win_rate_pct', 0):.1f}%")

    # ── AutoTrader: start ─────────────────────────────────────────────────────
    print("\n=== POST /trading/start ===")
    try:
        started = _post(base, "/trading/start", {
            "tickers": ["AAPL", "MSFT"],
            "initial_capital": 10000.0,
            "dry_run": True,
        })
        print(f"Running: {started.get('running')}")
        print(f"Tickers: {started.get('tickers')}")
    except Exception as exc:
        print(f"(skipped — {exc})")

    # ── AutoTrader: status ────────────────────────────────────────────────────
    print("\n=== GET /trading/status ===")
    try:
        status = _get(base, "/trading/status")
        print(f"Running:        {status.get('running')}")
        print(f"Tickers:        {status.get('tickers')}")
        equity = status.get("equity")
        cash = status.get("cash")
        if equity is not None:
            print(f"Equity:         ${equity:,.2f}")
        if cash is not None:
            print(f"Cash:           ${cash:,.2f}")
        positions = status.get("open_positions", [])
        print(f"Open positions: {len(positions)}")
    except Exception as exc:
        print(f"(skipped — {exc})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
