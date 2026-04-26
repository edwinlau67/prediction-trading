"""Tests for AlpacaDataFetcher, _MergedDataFetcher, and create_data_fetcher.

All tests mock alpaca-py so no API keys or network calls are required.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_ohlcv(n: int = 30) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "Open":   [100.0 + i for i in range(n)],
            "High":   [105.0 + i for i in range(n)],
            "Low":    [95.0 + i for i in range(n)],
            "Close":  [102.0 + i for i in range(n)],
            "Volume": [1_000_000] * n,
        },
        index=idx,
    )


def _make_alpaca_bars_response(ticker: str, n: int = 30):
    """Return a mock bars response mimicking alpaca-py BarsResponse."""
    idx = pd.MultiIndex.from_tuples(
        [(ticker, ts) for ts in pd.date_range("2024-01-01", periods=n, freq="D")],
        names=["symbol", "timestamp"],
    )
    df = pd.DataFrame(
        {
            "open":   [100.0 + i for i in range(n)],
            "high":   [105.0 + i for i in range(n)],
            "low":    [95.0 + i for i in range(n)],
            "close":  [102.0 + i for i in range(n)],
            "volume": [1_000_000] * n,
        },
        index=idx,
    )
    mock_resp = MagicMock()
    mock_resp.df = df
    return mock_resp


# ---------------------------------------------------------------------------
# create_data_fetcher
# ---------------------------------------------------------------------------
class TestCreateDataFetcher:
    def test_yfinance_returns_datafetcher(self):
        from prediction_trading.data_fetcher import DataFetcher, create_data_fetcher
        fetcher = create_data_fetcher("yfinance")
        assert isinstance(fetcher, DataFetcher)

    def test_unknown_source_raises(self):
        from prediction_trading.data_fetcher import create_data_fetcher
        with pytest.raises(ValueError, match="Unknown data source"):
            create_data_fetcher("polygon")

    @patch.dict(os.environ, {"ALPACA_API_KEY": "test-key", "ALPACA_API_SECRET": "test-secret"})
    def test_alpaca_returns_alpaca_fetcher(self):
        mock_client = MagicMock()
        with patch("prediction_trading.data_fetcher._AlpacaHistClient", return_value=mock_client), \
             patch("prediction_trading.data_fetcher._ALPACA_AVAILABLE", True):
            from prediction_trading.data_fetcher import create_data_fetcher, AlpacaDataFetcher
            fetcher = create_data_fetcher("alpaca")
            assert isinstance(fetcher, AlpacaDataFetcher)

    @patch.dict(os.environ, {"ALPACA_API_KEY": "test-key", "ALPACA_API_SECRET": "test-secret"})
    def test_both_returns_merged_fetcher(self):
        mock_client = MagicMock()
        with patch("prediction_trading.data_fetcher._AlpacaHistClient", return_value=mock_client), \
             patch("prediction_trading.data_fetcher._ALPACA_AVAILABLE", True):
            from prediction_trading.data_fetcher import create_data_fetcher, _MergedDataFetcher
            fetcher = create_data_fetcher("both")
            assert isinstance(fetcher, _MergedDataFetcher)

    def test_alpaca_unavailable_raises_import_error(self):
        with patch("prediction_trading.data_fetcher._ALPACA_AVAILABLE", False):
            from prediction_trading.data_fetcher import create_data_fetcher
            with pytest.raises(ImportError, match="alpaca-py"):
                create_data_fetcher("alpaca")


# ---------------------------------------------------------------------------
# AlpacaDataFetcher.fetch_history
# ---------------------------------------------------------------------------
def _alpaca_patches():
    """Context manager that mocks all alpaca-py module-level symbols."""
    mock_tf_unit = MagicMock()
    mock_tf_unit.Minute = "minute"
    mock_tf_unit.Hour = "hour"
    mock_tf_unit.Day = "day"
    mock_tf_unit.Week = "week"
    mock_alpaca_tf = MagicMock(return_value=MagicMock())
    return (
        patch("prediction_trading.data_fetcher._ALPACA_AVAILABLE", True),
        patch("prediction_trading.data_fetcher._TFUnit", mock_tf_unit),
        patch("prediction_trading.data_fetcher._AlpacaTF", mock_alpaca_tf),
        patch("prediction_trading.data_fetcher._StockBarsRequest", MagicMock()),
    )


class TestAlpacaDataFetcher:
    def _make_fetcher(self):
        mock_client_instance = MagicMock()
        patches = _alpaca_patches()
        for p in patches:
            p.start()
        try:
            with patch.dict(os.environ, {"ALPACA_API_KEY": "k", "ALPACA_API_SECRET": "s"}), \
                 patch("prediction_trading.data_fetcher._AlpacaHistClient", return_value=mock_client_instance):
                from prediction_trading.data_fetcher import AlpacaDataFetcher
                fetcher = AlpacaDataFetcher()
                fetcher._alpaca_client = mock_client_instance
        finally:
            for p in patches:
                p.stop()
        return fetcher, mock_client_instance

    def _run_fetch(self, fetcher, mock_client, ticker, lookback_days):
        patches = _alpaca_patches()
        for p in patches:
            p.start()
        try:
            return fetcher.fetch_history(ticker, lookback_days=lookback_days)
        finally:
            for p in patches:
                p.stop()

    def test_fetch_history_returns_ohlcv_dataframe(self):
        fetcher, mock_client = self._make_fetcher()
        mock_client.get_stock_bars.return_value = _make_alpaca_bars_response("AAPL", 30)
        df = self._run_fetch(fetcher, mock_client, "AAPL", 30)
        assert not df.empty
        assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.tz is None  # timezone stripped

    def test_fetch_history_drops_invalid_ohlc_bars(self):
        fetcher, mock_client = self._make_fetcher()
        resp = _make_alpaca_bars_response("TSLA", 5)
        resp.df.iloc[2, resp.df.columns.get_loc("low")] = 999.0  # low > high
        mock_client.get_stock_bars.return_value = resp
        df = self._run_fetch(fetcher, mock_client, "TSLA", 5)
        assert len(df) == 4  # one bad bar dropped

    def test_fetch_history_raises_on_empty_response(self):
        fetcher, mock_client = self._make_fetcher()
        mock_resp = MagicMock()
        mock_resp.df = pd.DataFrame()
        mock_client.get_stock_bars.return_value = mock_resp
        with pytest.raises(ValueError, match="No price history"):
            self._run_fetch(fetcher, mock_client, "NONE", 10)

    def test_uses_sip_feed_when_available(self):
        fetcher, mock_client = self._make_fetcher()
        mock_client.get_stock_bars.return_value = _make_alpaca_bars_response("AAPL", 10)
        self._run_fetch(fetcher, mock_client, "AAPL", 10)
        assert fetcher._last_feed == "alpaca/SIP"

    def test_falls_back_to_iex_when_sip_fails(self):
        fetcher, mock_client = self._make_fetcher()
        good_resp = _make_alpaca_bars_response("AAPL", 10)
        mock_client.get_stock_bars.side_effect = [
            RuntimeError("subscription does not permit SIP"),
            good_resp,
        ]
        df = self._run_fetch(fetcher, mock_client, "AAPL", 10)
        assert fetcher._last_feed == "alpaca/IEX"
        assert not df.empty


# ---------------------------------------------------------------------------
# _MergedDataFetcher fallback
# ---------------------------------------------------------------------------
class TestMergedDataFetcher:
    def _make_merged(self):
        with patch.dict(os.environ, {"ALPACA_API_KEY": "k", "ALPACA_API_SECRET": "s"}), \
             patch("prediction_trading.data_fetcher._ALPACA_AVAILABLE", True), \
             patch("prediction_trading.data_fetcher._AlpacaHistClient", return_value=MagicMock()):
            from prediction_trading.data_fetcher import _MergedDataFetcher
            return _MergedDataFetcher()

    def test_falls_back_to_yfinance_on_alpaca_error(self):
        yf_df = _make_ohlcv(20)
        merged = self._make_merged()
        merged._alpaca.fetch_history = MagicMock(side_effect=RuntimeError("Alpaca down"))
        with patch.object(type(merged).__bases__[0], "fetch_history", return_value=yf_df):
            df = merged.fetch_history("SPY", lookback_days=20)
        assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]

    def test_propagates_alpaca_feed_label(self):
        merged = self._make_merged()
        merged._alpaca._last_feed = "alpaca/SIP"
        merged._alpaca.fetch_history = MagicMock(return_value=_make_ohlcv(10))
        merged.fetch_history("AAPL", lookback_days=10)
        assert merged._last_feed == "alpaca/SIP"

    def test_sets_yfinance_feed_label_on_alpaca_failure(self):
        yf_df = _make_ohlcv(10)
        merged = self._make_merged()
        merged._alpaca.fetch_history = MagicMock(side_effect=RuntimeError("down"))
        with patch.object(type(merged).__bases__[0], "fetch_history", return_value=yf_df):
            merged.fetch_history("SPY", lookback_days=10)
        assert merged._last_feed == "yfinance"
