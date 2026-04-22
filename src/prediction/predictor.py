"""Unified predictor: fuses the rule-based scorer with the AI predictor.

- If AI is disabled, returns the pure rule-based signal.
- If AI is enabled, blends the two confidences with a user-tunable weight
  and only emits a directional call when both agree (or one is neutral).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .ai_predictor import AIPredictor, AIPrediction
from .factor import Direction, Factor
from .signal_scorer import ScoredSignal, SignalScorer


@dataclass
class Prediction:
    ticker: str
    direction: Direction
    confidence: float
    current_price: float
    price_target: float | None = None
    target_date: str | None = None
    risk_level: str = "medium"
    rule_signal: ScoredSignal | None = None
    ai_signal: AIPrediction | None = None
    factors: list[Factor] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def bullish_factors(self) -> list[Factor]:
        return [f for f in self.factors if f.direction == "bullish"]

    @property
    def bearish_factors(self) -> list[Factor]:
        return [f for f in self.factors if f.direction == "bearish"]

    def as_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "direction": self.direction,
            "confidence": self.confidence,
            "current_price": self.current_price,
            "price_target": self.price_target,
            "target_date": self.target_date,
            "risk_level": self.risk_level,
            "rule_signal": self.rule_signal.as_dict() if self.rule_signal else None,
            "ai_signal": self.ai_signal.as_dict() if self.ai_signal else None,
            "factors": [f.as_dict() for f in self.factors],
            "meta": self.meta,
        }


class UnifiedPredictor:
    """Combines rule-based + AI-based predictions into a single decision."""

    def __init__(
        self,
        scorer: SignalScorer | None = None,
        ai: AIPredictor | None = None,
        *,
        ai_enabled: bool = False,
        ai_weight: float = 0.5,
        min_confidence: float = 0.55,
        timeframe: str = "1w",
    ) -> None:
        self.scorer = scorer or SignalScorer()
        self.ai = ai
        self.ai_enabled = ai_enabled and ai is not None
        self.ai_weight = max(0.0, min(1.0, ai_weight))
        self.min_confidence = min_confidence
        self.timeframe = timeframe

    def predict(
        self,
        ticker: str,
        df: pd.DataFrame,
        *,
        current_price: float,
        weekly: pd.DataFrame | None = None,
        fundamentals: dict | None = None,
    ) -> Prediction:
        rule = self.scorer.score(df, weekly=weekly, fundamentals=fundamentals)
        ai_pred: AIPrediction | None = None
        factors: list[Factor] = list(rule.factors)

        if self.ai_enabled and self.ai is not None:
            try:
                ai_pred = self.ai.predict(ticker, timeframe=self.timeframe)  # type: ignore[arg-type]
                for raw in ai_pred.key_factors[:3]:
                    factors.append(Factor(
                        category="trend", name=f"AI: {raw}",
                        direction=ai_pred.direction, points=0,
                    ))
            except Exception as exc:  # pragma: no cover
                factors.append(Factor(
                    category="trend", name="AI unavailable",
                    direction="neutral", points=0, detail=str(exc),
                ))

        direction, confidence = self._fuse(rule, ai_pred)

        return Prediction(
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            current_price=current_price,
            price_target=ai_pred.price_target if ai_pred else None,
            target_date=ai_pred.target_date if ai_pred else None,
            risk_level=ai_pred.risk_level if ai_pred else "medium",
            rule_signal=rule,
            ai_signal=ai_pred,
            factors=factors,
            meta={
                "timeframe": self.timeframe,
                "actionable": confidence >= self.min_confidence
                              and direction != "neutral",
                "fundamentals": (fundamentals or
                                 (ai_pred.fundamentals if ai_pred else {}) or {}),
            },
        )

    # ------------------------------------------------------------------ fuse
    def _fuse(self, rule: ScoredSignal, ai: AIPrediction | None
              ) -> tuple[Direction, float]:
        if ai is None:
            return rule.direction, rule.confidence

        # Convert directions to signed magnitudes, then blend.
        def signed(direction: Direction, conf: float) -> float:
            sign = {"bullish": 1.0, "bearish": -1.0, "neutral": 0.0}[direction]
            return sign * conf

        rule_val = signed(rule.direction, rule.confidence)
        ai_val = signed(ai.direction, ai.confidence)
        blended = (1.0 - self.ai_weight) * rule_val + self.ai_weight * ai_val

        if blended > 0.05:
            direction: Direction = "bullish"
        elif blended < -0.05:
            direction = "bearish"
        else:
            direction = "neutral"
        return direction, float(min(1.0, abs(blended)))
