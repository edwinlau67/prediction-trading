"""Tests for AIPredictor — mocked Anthropic API, no network, no API key."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.prediction.ai_predictor import AIPredictor, AIPrediction


def _make_ohlcv(n: int = 250) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.001, 0.01, n)))
    high = close * 1.01
    low = close * 0.99
    idx = pd.bdate_range("2023-01-01", periods=n)
    return pd.DataFrame({"Open": close, "High": high, "Low": low,
                         "Close": close, "Volume": 1_000_000.0}, index=idx)


def _make_predictor(api_key: str | None = "sk-ant-fake") -> AIPredictor:
    from src.data_fetcher import DataFetcher
    fetcher = MagicMock(spec=DataFetcher)
    from src.data_fetcher import MarketData
    fetcher.fetch.return_value = MarketData(
        ticker="AAPL", ohlcv=_make_ohlcv(), current_price=175.0,
        fundamentals={"trailingPE": 28.0},
    )
    return AIPredictor(api_key=api_key, data_fetcher=fetcher)


def _tool_use_response(tool_result: dict) -> MagicMock:
    """First API response: asks to call the tool."""
    msg = MagicMock()
    msg.stop_reason = "tool_use"
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "stock_prediction"
    tool_block.id = "tool_abc123"
    tool_block.input = {"ticker": "AAPL", "timeframe": "1w"}
    msg.content = [tool_block]
    return msg


def _narrative_response(narrative: str = "AAPL looks bullish.") -> MagicMock:
    """Second API response: narrative text."""
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = narrative
    msg.content = [text_block]
    return msg


class TestToolUseFlow:
    def test_two_api_calls_made(self):
        predictor = _make_predictor()
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _tool_use_response({}),
            _narrative_response(),
        ]
        predictor._client = mock_client  # internal attribute name

        result = predictor.predict("AAPL", timeframe="1w")
        assert mock_client.messages.create.call_count == 2
        assert isinstance(result, AIPrediction)

    def test_result_has_expected_fields(self):
        predictor = _make_predictor()
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _tool_use_response({}),
            _narrative_response("Stock looks good."),
        ]
        predictor._client = mock_client

        result = predictor.predict("AAPL", timeframe="1w")
        assert result.ticker == "AAPL"
        assert result.direction in {"bullish", "bearish", "neutral"}
        assert 0.0 <= result.confidence <= 1.0

    def test_prompt_cache_control_in_system_message(self):
        predictor = _make_predictor()
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _tool_use_response({}),
            _narrative_response(),
        ]
        predictor._client = mock_client
        predictor.predict("AAPL", timeframe="1w")

        first_call_kwargs = mock_client.messages.create.call_args_list[0][1]
        system = first_call_kwargs.get("system", [])
        if isinstance(system, list):
            cache_tags = [
                b.get("cache_control") for b in system
                if isinstance(b, dict)
            ]
            assert any(c is not None for c in cache_tags), \
                "cache_control not found in system message blocks"

    def test_categories_embedded_in_system_prompt(self):
        predictor = _make_predictor()
        predictor.categories = ("trend", "momentum")
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [
            _tool_use_response({}),
            _narrative_response(),
        ]
        predictor._client = mock_client
        predictor.predict("AAPL", timeframe="1w")

        first_call_kwargs = mock_client.messages.create.call_args_list[0][1]
        system = first_call_kwargs.get("system", [])
        system_text = (
            system if isinstance(system, str)
            else " ".join(b.get("text", "") for b in system if isinstance(b, dict))
        )
        assert "trend" in system_text or "momentum" in system_text


class TestDegradedMode:
    def test_no_api_key_returns_local_result(self):
        """Without an API key, AIPredictor should still return a valid AIPrediction
        derived from the local tool execution (no second API call)."""
        from src.data_fetcher import DataFetcher, MarketData
        fetcher = MagicMock(spec=DataFetcher)
        fetcher.fetch.return_value = MarketData(
            ticker="AAPL", ohlcv=_make_ohlcv(), current_price=175.0,
            fundamentals={},
        )
        predictor = AIPredictor(api_key=None, data_fetcher=fetcher)
        result = predictor.predict("AAPL", timeframe="1w")
        assert isinstance(result, AIPrediction)
        assert result.ticker == "AAPL"
        assert result.direction in {"bullish", "bearish", "neutral"}
