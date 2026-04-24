"""Tests for UnifiedPredictor fusion logic (no network, no API key)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.prediction.predictor import UnifiedPredictor
from src.prediction.ai_predictor import AIPrediction
from src.prediction.signal_scorer import SignalScorer, ScoredSignal


def _make_scored(direction: str, confidence: float) -> ScoredSignal:
    ss = ScoredSignal(direction=direction, confidence=confidence)
    return ss


def _make_ai(direction: str, confidence: float) -> AIPrediction:
    return AIPrediction(
        ticker="TEST", timeframe="1w", direction=direction, confidence=confidence,
        current_price=100.0, price_target=110.0, target_date="2026-05-01",
        risk_level="medium", key_factors=["factor1"],
    )


def _make_predictor(ai_weight: float = 0.5, ai_enabled: bool = False,
                    min_confidence: float = 0.0) -> UnifiedPredictor:
    scorer = MagicMock(spec=SignalScorer)
    return UnifiedPredictor(
        scorer=scorer, ai=None,
        ai_weight=ai_weight, ai_enabled=ai_enabled, min_confidence=min_confidence,
    )


def _mock_score(predictor: UnifiedPredictor, signal: ScoredSignal) -> None:
    predictor.scorer.score.return_value = signal


import pandas as pd
import numpy as np


def _minimal_df() -> pd.DataFrame:
    """50-bar OHLCV with indicators pre-computed."""
    rng = np.random.default_rng(42)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.001, 0.01, 50)))
    high = close * 1.01
    low = close * 0.99
    idx = pd.bdate_range("2024-01-01", periods=50)
    return pd.DataFrame({"Open": close, "High": high, "Low": low,
                         "Close": close, "Volume": 1_000_000.0}, index=idx)


class TestFusionFormula:
    def test_rule_only_when_ai_disabled(self):
        df = _minimal_df()
        predictor = UnifiedPredictor(min_confidence=0.0)
        result = predictor.predict("TEST", df, current_price=100.0)
        assert result.ai_signal is None
        assert result.rule_signal is not None

    def test_bullish_rule_bullish_ai_higher_confidence(self):
        predictor = _make_predictor(ai_weight=0.5, ai_enabled=True, min_confidence=0.0)
        rule = _make_scored("bullish", 0.6)
        ai_pred = _make_ai("bullish", 0.8)
        _mock_score(predictor, rule)
        predictor.ai = MagicMock()
        predictor.ai.predict.return_value = ai_pred
        predictor.ai_enabled = True

        df = _minimal_df()
        result = predictor.predict("TEST", df, current_price=100.0)
        # blended = 0.5 * 0.6 + 0.5 * 0.8 = 0.70
        assert result.direction == "bullish"
        assert abs(result.confidence - 0.70) < 0.01

    def test_direction_neutral_at_zero_threshold(self):
        predictor = _make_predictor(ai_weight=0.5, ai_enabled=True, min_confidence=0.0)
        rule = _make_scored("bullish", 0.1)   # +0.1
        ai_pred = _make_ai("bearish", 0.1)    # -0.1
        _mock_score(predictor, rule)
        predictor.ai = MagicMock()
        predictor.ai.predict.return_value = ai_pred
        predictor.ai_enabled = True

        df = _minimal_df()
        result = predictor.predict("TEST", df, current_price=100.0)
        # blended = 0.5*0.1 + 0.5*(-0.1) = 0.0 → neutral
        assert result.direction == "neutral"

    def test_ai_weight_zero_equals_rule_only(self):
        predictor = _make_predictor(ai_weight=0.0, ai_enabled=True, min_confidence=0.0)
        rule = _make_scored("bullish", 0.7)
        ai_pred = _make_ai("bearish", 0.9)  # opposite direction
        _mock_score(predictor, rule)
        predictor.ai = MagicMock()
        predictor.ai.predict.return_value = ai_pred
        predictor.ai_enabled = True

        df = _minimal_df()
        result = predictor.predict("TEST", df, current_price=100.0)
        # weight=0 → pure rule: bullish 0.7
        assert result.direction == "bullish"
        assert abs(result.confidence - 0.7) < 0.01

    def test_actionable_flag_false_below_min_confidence(self):
        predictor = _make_predictor(ai_weight=0.0, ai_enabled=False, min_confidence=0.50)
        rule = _make_scored("bullish", 0.30)
        _mock_score(predictor, rule)

        df = _minimal_df()
        result = predictor.predict("TEST", df, current_price=100.0)
        assert result.meta.get("actionable") is False

    def test_actionable_flag_true_above_min_confidence(self):
        predictor = _make_predictor(ai_weight=0.0, ai_enabled=False, min_confidence=0.20)
        rule = _make_scored("bullish", 0.60)
        _mock_score(predictor, rule)

        df = _minimal_df()
        result = predictor.predict("TEST", df, current_price=100.0)
        assert result.meta.get("actionable") is True
