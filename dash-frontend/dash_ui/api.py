"""HTTP client for FastAPI backend. All calls go to localhost:8000."""
from __future__ import annotations

import requests

API_BASE = "http://localhost:8000"
_SHORT = 10   # seconds — status/health
_LONG = 60    # seconds — predict/scan (can be slow)


def _get(path: str, timeout: int = _SHORT) -> dict:
    r = requests.get(f"{API_BASE}{path}", timeout=timeout)
    r.raise_for_status()
    return r.json()


def _post(path: str, payload: dict, timeout: int = _SHORT) -> dict:
    r = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _put(path: str, payload: dict, timeout: int = _SHORT) -> dict:
    r = requests.put(f"{API_BASE}{path}", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def health_check() -> dict:
    return _get("/health")


def predict(
    ticker: str,
    timeframe: str = "1w",
    enable_ai: bool = False,
    categories: list[str] | None = None,
    lookback_days: int = 365,
    use_4h: bool = False,
) -> dict:
    return _post(
        "/predict/",
        {
            "ticker": ticker.upper(),
            "timeframe": timeframe,
            "enable_ai": enable_ai,
            "categories": categories,
            "lookback_days": lookback_days,
            "use_4h": use_4h,
        },
        timeout=_LONG,
    )


def scan(
    tickers: list[str],
    min_confidence: float = 0.0,
    categories: list[str] | None = None,
    workers: int = 4,
) -> dict:
    return _post(
        "/scan/",
        {
            "tickers": [t.upper() for t in tickers],
            "min_confidence": min_confidence,
            "categories": categories,
            "workers": workers,
        },
        timeout=_LONG,
    )


def backtest(
    ticker: str,
    start: str,
    end: str,
    initial_capital: float = 10_000.0,
    commission: float = 1.0,
) -> dict:
    return _post(
        "/backtest/",
        {
            "ticker": ticker.upper(),
            "start": start,
            "end": end,
            "initial_capital": initial_capital,
            "commission": commission,
        },
        timeout=_LONG,
    )


def trading_status() -> dict:
    return _get("/trading/status")


def trading_start(
    tickers: list[str],
    initial_capital: float = 10_000.0,
    dry_run: bool = True,
    enforce_market_hours: bool = False,
    interval_seconds: int = 300,
    state_path: str | None = None,
) -> dict:
    return _post(
        "/trading/start",
        {
            "tickers": [t.upper() for t in tickers],
            "initial_capital": initial_capital,
            "dry_run": dry_run,
            "enforce_market_hours": enforce_market_hours,
            "interval_seconds": interval_seconds,
            "state_path": state_path,
        },
    )


def predict_macro() -> dict:
    return _get("/predict/macro", timeout=_LONG)


def portfolio_analyze(tickers: list[str], lookback_days: int = 252) -> dict:
    return _post(
        "/portfolio/analyze",
        {"tickers": [t.upper() for t in tickers], "lookback_days": lookback_days},
        timeout=_LONG,
    )


def get_config() -> dict:
    return _get("/config/")


def put_config(cfg: dict) -> dict:
    return _put("/config/", cfg)
