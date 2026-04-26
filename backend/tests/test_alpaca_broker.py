"""Tests for AlpacaBroker.

All tests mock alpaca-py — no API keys or network calls required.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from prediction_trading.trading.broker import Fill, Order


def _make_order(
    ticker: str = "AAPL",
    side: str = "long",
    qty: int = 10,
    order_type: str = "market",
    limit_price: float | None = None,
) -> Order:
    return Order(
        ticker=ticker,
        side=side,
        quantity=qty,
        order_type=order_type,
        limit_price=limit_price,
        submitted_at=datetime.now(timezone.utc),
    )


def _make_broker(paper: bool = True):
    mock_trading = MagicMock()
    mock_data = MagicMock()
    with patch.dict(os.environ, {"ALPACA_API_KEY": "k", "ALPACA_API_SECRET": "s"}), \
         patch("prediction_trading.trading.broker._ALPACA_TRADING_AVAILABLE", True), \
         patch("prediction_trading.trading.broker._AlpacaTradingClient", return_value=mock_trading), \
         patch("prediction_trading.trading.broker._AlpacaDataClient", return_value=mock_data):
        from prediction_trading.trading.broker import AlpacaBroker
        broker = AlpacaBroker(paper_trading=paper)
        broker._client = mock_trading
        broker._data_client = mock_data
    return broker, mock_trading, mock_data


class TestAlpacaBrokerGetQuote:
    def test_returns_ask_price(self):
        broker, _, mock_data = _make_broker()
        mock_quote = MagicMock()
        mock_quote.ask_price = 150.25
        mock_data.get_stock_latest_quote.return_value = {"AAPL": mock_quote}

        with patch("prediction_trading.trading.broker._LatestQuoteReq", MagicMock()):
            price = broker.get_quote("AAPL")

        assert price == 150.25

    def test_falls_back_to_latest_bar_on_quote_error(self):
        broker, _, mock_data = _make_broker()
        mock_data.get_stock_latest_quote.side_effect = RuntimeError("no quote")
        mock_bar = MagicMock()
        mock_bar.close = 149.99
        mock_data.get_stock_latest_bar.return_value = {"AAPL": mock_bar}

        with patch("prediction_trading.trading.broker._LatestQuoteReq", MagicMock()), \
             patch("prediction_trading.trading.broker._LatestBarReq", MagicMock()):
            price = broker.get_quote("AAPL")

        assert price == 149.99


class TestAlpacaBrokerPlaceOrder:
    def test_market_buy_returns_fill(self):
        broker, mock_trading, mock_data = _make_broker()
        mock_quote = MagicMock()
        mock_quote.ask_price = 150.0
        mock_data.get_stock_latest_quote.return_value = {"AAPL": mock_quote}

        mock_response = MagicMock()
        mock_response.id = "abc-123"
        mock_response.filled_avg_price = 150.10
        mock_trading.submit_order.return_value = mock_response

        order = _make_order("AAPL", "long", 5, "market")
        with patch("prediction_trading.trading.broker._MarketOrderReq", MagicMock()), \
             patch("prediction_trading.trading.broker._OrderSide") as mock_side, \
             patch("prediction_trading.trading.broker._TIF"):
            mock_side.BUY = "buy"
            fill = broker.place_order(order)

        assert fill is not None
        assert isinstance(fill, Fill)
        assert fill.fill_price == 150.10
        assert fill.broker_order_id == "abc-123"

    def test_zero_quantity_returns_none(self):
        broker, _, _ = _make_broker()
        order = _make_order("AAPL", "long", 0)
        fill = broker.place_order(order)
        assert fill is None

    def test_submit_error_returns_none(self):
        broker, mock_trading, _ = _make_broker()
        mock_trading.submit_order.side_effect = RuntimeError("rejected")
        order = _make_order("AAPL", "long", 10)

        with patch("prediction_trading.trading.broker._MarketOrderReq", MagicMock()), \
             patch("prediction_trading.trading.broker._OrderSide") as mock_side, \
             patch("prediction_trading.trading.broker._TIF"):
            mock_side.BUY = "buy"
            fill = broker.place_order(order)

        assert fill is None

    def test_limit_order_sends_limit_request(self):
        broker, mock_trading, _ = _make_broker()
        mock_response = MagicMock()
        mock_response.id = "lim-1"
        mock_response.filled_avg_price = 145.0
        mock_trading.submit_order.return_value = mock_response

        order = _make_order("MSFT", "long", 3, "limit", limit_price=145.0)
        mock_limit_cls = MagicMock()
        with patch("prediction_trading.trading.broker._LimitOrderReq", mock_limit_cls), \
             patch("prediction_trading.trading.broker._OrderSide") as mock_side, \
             patch("prediction_trading.trading.broker._TIF"):
            mock_side.BUY = "buy"
            broker.place_order(order)

        mock_limit_cls.assert_called_once()


class TestAlpacaBrokerClosePosition:
    def test_close_calls_alpaca_and_returns_none(self):
        broker, mock_trading, _ = _make_broker()
        result = broker.close_position("AAPL", reason="stop")
        mock_trading.close_position.assert_called_once_with("AAPL")
        assert result is None

    def test_close_swallows_alpaca_error(self):
        broker, mock_trading, _ = _make_broker()
        mock_trading.close_position.side_effect = RuntimeError("position not found")
        result = broker.close_position("NVDA")  # should not raise
        assert result is None


class TestAlpacaBrokerImportGuard:
    def test_unavailable_raises_import_error(self):
        with patch("prediction_trading.trading.broker._ALPACA_TRADING_AVAILABLE", False):
            from prediction_trading.trading.broker import AlpacaBroker
            with pytest.raises(ImportError, match="alpaca-py"):
                AlpacaBroker()
