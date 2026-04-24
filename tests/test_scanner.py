"""Tests for WatchlistScanner — uses patched DataFetcher to avoid network calls."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.data_fetcher import MarketData
from src.scanner import ScanResult, WatchlistScanner


def _make_market(ohlcv) -> MarketData:
    return MarketData(
        ticker="SYNTH",
        ohlcv=ohlcv,
        current_price=float(ohlcv["Close"].iloc[-1]),
        fundamentals={},
    )


@pytest.fixture
def mock_fetcher(ohlcv_uptrend):
    market = _make_market(ohlcv_uptrend)
    with patch("src.scanner.DataFetcher") as MockFetcher:
        instance = MockFetcher.return_value
        instance.fetch.return_value = market
        yield instance


def test_scan_returns_results(mock_fetcher):
    scanner = WatchlistScanner()
    results = scanner.scan(["AAPL", "MSFT"])
    assert len(results) == 2
    assert all(isinstance(r, ScanResult) for r in results)


def test_scan_results_ranked_by_confidence(mock_fetcher):
    scanner = WatchlistScanner()
    results = scanner.scan(["A", "B", "C"])
    confs = [r.confidence for r in results if r.error is None]
    assert confs == sorted(confs, reverse=True)


def test_scan_min_confidence_filters(mock_fetcher):
    scanner = WatchlistScanner(min_confidence=0.99)
    results = scanner.scan(["AAPL"])
    # With min_confidence=0.99 almost nothing should pass unless synthetic data hits it
    for r in results:
        assert r.error is not None or r.confidence >= 0.99


def test_scan_isolates_errors():
    with patch("src.scanner.DataFetcher") as MockFetcher:
        instance = MockFetcher.return_value
        instance.fetch.side_effect = RuntimeError("network error")
        scanner = WatchlistScanner()
        results = scanner.scan(["BAD"])
    assert len(results) == 1
    assert results[0].error is not None
    assert results[0].direction == "neutral"


def test_scan_categories_subset(mock_fetcher):
    scanner = WatchlistScanner(categories=("trend", "momentum"))
    results = scanner.scan(["AAPL"])
    assert len(results) == 1
    assert results[0].error is None


def test_scan_workers_respected(mock_fetcher):
    scanner = WatchlistScanner(workers=2)
    assert scanner.workers == 2
    results = scanner.scan(["A", "B", "C", "D"])
    assert len(results) == 4
