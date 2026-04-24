"""Tests for DataFetcher — mocked yfinance, no network."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.data_fetcher import DataFetcher, MarketData


def _make_ohlcv(n: int = 50, start_price: float = 100.0) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    close = start_price * np.exp(np.cumsum(rng.normal(0.001, 0.01, n)))
    high = close * 1.01
    low = close * 0.99
    idx = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame({
        "Open": close, "High": high, "Low": low,
        "Close": close, "Volume": 1_000_000.0,
    }, index=idx)


class TestFetchHistory:
    def test_returns_valid_dataframe(self):
        raw = _make_ohlcv(100)
        with patch("yfinance.download", return_value=raw):
            fetcher = DataFetcher()
            df = fetcher.fetch_history("AAPL", lookback_days=100)
        assert isinstance(df, pd.DataFrame)
        assert set(["Open", "High", "Low", "Close", "Volume"]).issubset(df.columns)
        assert len(df) > 0

    def test_interval_propagated_to_yfinance(self):
        raw = _make_ohlcv(30)
        with patch("yfinance.download", return_value=raw) as mock_dl:
            fetcher = DataFetcher(interval="1h")
            fetcher.fetch_history("AAPL", lookback_days=30)
        _, kwargs = mock_dl.call_args
        assert kwargs.get("interval") == "1h"

    def test_raises_on_empty_response(self):
        with patch("yfinance.download", return_value=pd.DataFrame()):
            fetcher = DataFetcher()
            with pytest.raises(ValueError, match="No price history"):
                fetcher.fetch_history("FAKE", lookback_days=30)

    def test_drops_invalid_ohlc_bars(self):
        raw = _make_ohlcv(10)
        # Corrupt one bar: set High below Close (invalid)
        raw.iloc[5, raw.columns.get_loc("High")] = raw.iloc[5]["Close"] * 0.5
        with patch("yfinance.download", return_value=raw):
            fetcher = DataFetcher()
            df = fetcher.fetch_history("AAPL", lookback_days=10)
        # Bad bar should be dropped
        assert len(df) == 9


class TestFetchFundamentals:
    def test_returns_subset_of_known_keys(self):
        mock_info = {
            "trailingPE": 25.0, "priceToBook": 3.5, "unknown_key": "ignore_me"
        }
        mock_ticker = MagicMock()
        mock_ticker.info = mock_info
        with patch("yfinance.Ticker", return_value=mock_ticker):
            fetcher = DataFetcher()
            fund = fetcher.fetch_fundamentals("AAPL")
        assert "trailingPE" in fund
        assert "unknown_key" not in fund

    def test_returns_empty_dict_on_exception(self):
        with patch("yfinance.Ticker", side_effect=RuntimeError("network error")):
            fetcher = DataFetcher()
            fund = fetcher.fetch_fundamentals("AAPL")
        assert fund == {}


class TestFetch:
    def test_returns_market_data(self):
        raw = _make_ohlcv(50)
        mock_ticker = MagicMock()
        mock_ticker.info = {"trailingPE": 20.0}
        with patch("yfinance.download", return_value=raw), \
             patch("yfinance.Ticker", return_value=mock_ticker):
            fetcher = DataFetcher()
            market = fetcher.fetch("AAPL", lookback_days=50)
        assert isinstance(market, MarketData)
        assert market.ticker == "AAPL"
        assert market.current_price > 0
