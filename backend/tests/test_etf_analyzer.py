"""Tests for ETFAnalyzer — no network calls required."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from prediction_trading.etf import ETFAnalyzer, ETFInfo, PortfolioAnalysis


class TestGetETFInfo:
    def test_catalogue_lookup_spy(self):
        analyzer = ETFAnalyzer()
        info = analyzer.get_etf_info("SPY")
        assert info.ticker == "SPY"
        assert info.is_etf is True
        assert info.expense_ratio == 0.0945
        assert "S&P 500" in info.tracked_index

    def test_catalogue_lookup_case_insensitive(self):
        analyzer = ETFAnalyzer()
        info = analyzer.get_etf_info("qqq")
        assert info.ticker == "QQQ"
        assert info.is_etf is True

    def test_unknown_ticker_yfinance_etf(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "quoteType": "ETF",
            "longName": "Hypothetical ETF",
            "category": "US Large Blend",
            "annualReportExpenseRatio": 0.15,
        }
        analyzer = ETFAnalyzer()
        with patch("prediction_trading.etf.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            info = analyzer.get_etf_info("HYPO")

        assert info.ticker == "HYPO"
        assert info.is_etf is True
        assert info.expense_ratio == 0.15

    def test_unknown_ticker_stock(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"quoteType": "EQUITY", "longName": "Acme Corp"}
        analyzer = ETFAnalyzer()
        with patch("prediction_trading.etf.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            info = analyzer.get_etf_info("ACME")

        assert info.is_etf is False

    def test_yfinance_error_returns_stub(self):
        analyzer = ETFAnalyzer()
        with patch("prediction_trading.etf.yf") as mock_yf:
            mock_yf.Ticker.side_effect = RuntimeError("network error")
            info = analyzer.get_etf_info("FAIL")

        assert info.ticker == "FAIL"
        assert info.is_etf is False


class TestIsETF:
    def test_spy_is_etf(self):
        assert ETFAnalyzer().is_etf("SPY") is True

    def test_qqq_is_etf(self):
        assert ETFAnalyzer().is_etf("QQQ") is True

    def test_unknown_non_etf(self):
        with patch("prediction_trading.etf.yf") as mock_yf:
            mock_yf.Ticker.return_value.info = {"quoteType": "EQUITY"}
            assert ETFAnalyzer().is_etf("AAPL") is False


class TestAnalyzePortfolio:
    def _make_prices(self, tickers: list[str], n: int = 60) -> pd.DataFrame:
        import numpy as np
        rng = np.random.default_rng(42)
        data = {}
        for i, t in enumerate(tickers):
            prices = 100.0 + rng.normal(0, 1, n).cumsum() + i * 5
            data[t] = prices
        idx = pd.date_range("2024-01-01", periods=n, freq="D")
        return pd.DataFrame(data, index=idx)

    def test_correlation_matrix_shape(self):
        tickers = ["SPY", "QQQ", "BND"]
        analyzer = ETFAnalyzer()
        prices = self._make_prices(tickers)

        with patch("prediction_trading.etf.ETFAnalyzer._fetch_closes", return_value=prices):
            result = analyzer.analyze_portfolio(tickers, lookback_days=60)

        assert result.correlation_matrix.shape == (3, 3)
        assert list(result.correlation_matrix.index) == tickers

    def test_diagonal_is_one(self):
        tickers = ["SPY", "GLD"]
        analyzer = ETFAnalyzer()
        prices = self._make_prices(tickers)

        with patch("prediction_trading.etf.ETFAnalyzer._fetch_closes", return_value=prices):
            result = analyzer.analyze_portfolio(tickers, lookback_days=60)

        for t in tickers:
            assert abs(result.correlation_matrix.loc[t, t] - 1.0) < 1e-10

    def test_diversification_score_between_0_and_1(self):
        tickers = ["SPY", "QQQ", "BND", "GLD"]
        analyzer = ETFAnalyzer()
        prices = self._make_prices(tickers)

        with patch("prediction_trading.etf.ETFAnalyzer._fetch_closes", return_value=prices):
            result = analyzer.analyze_portfolio(tickers, lookback_days=60)

        assert 0.0 <= result.diversification_score <= 1.0

    def test_high_correlation_flagged_in_recommendations(self):
        tickers = ["SPY", "IVV"]  # S&P 500 ETFs — extremely correlated
        analyzer = ETFAnalyzer()
        # Construct perfectly correlated prices
        idx = pd.date_range("2024-01-01", periods=60, freq="D")
        prices = pd.DataFrame(
            {"SPY": range(60, 120), "IVV": [x * 1.01 for x in range(60, 120)]},
            index=idx,
            dtype=float,
        )

        with patch("prediction_trading.etf.ETFAnalyzer._fetch_closes", return_value=prices):
            result = analyzer.analyze_portfolio(tickers, lookback_days=60)

        has_corr_rec = any("correlation" in r.lower() for r in result.recommendations)
        assert has_corr_rec, f"Expected correlation recommendation, got: {result.recommendations}"

    def test_single_ticker_returns_no_matrix(self):
        analyzer = ETFAnalyzer()
        prices = self._make_prices(["SPY"])

        with patch("prediction_trading.etf.ETFAnalyzer._fetch_closes", return_value=prices):
            result = analyzer.analyze_portfolio(["SPY"], lookback_days=60)

        assert any("at least 2" in r for r in result.recommendations)

    def test_sector_exposure_sums_to_one(self):
        tickers = ["SPY", "QQQ", "BND"]
        analyzer = ETFAnalyzer()
        prices = self._make_prices(tickers)

        with patch("prediction_trading.etf.ETFAnalyzer._fetch_closes", return_value=prices):
            result = analyzer.analyze_portfolio(tickers, lookback_days=60)

        total = sum(result.sector_exposure.values())
        assert abs(total - 1.0) < 1e-9

    def test_bonds_missing_recommendation(self):
        tickers = ["SPY", "QQQ", "XLK"]
        analyzer = ETFAnalyzer()
        prices = self._make_prices(tickers)

        with patch("prediction_trading.etf.ETFAnalyzer._fetch_closes", return_value=prices):
            result = analyzer.analyze_portfolio(tickers, lookback_days=60)

        has_bond_rec = any("bond" in r.lower() for r in result.recommendations)
        assert has_bond_rec
