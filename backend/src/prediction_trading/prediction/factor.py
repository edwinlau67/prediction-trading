"""Shared factor model used by rule-based, fundamental, and AI scoring."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["bullish", "bearish", "neutral"]
IndicatorCategory = Literal[
    "trend", "momentum", "volatility", "volume", "support", "fundamental",
    "news", "macro", "sector",
]
ALL_CATEGORIES: tuple[IndicatorCategory, ...] = (
    "trend", "momentum", "volatility", "volume", "support", "fundamental",
    "news", "macro", "sector",
)


@dataclass
class Factor:
    """A single scored signal, emitted by any of the scorers."""

    category: IndicatorCategory
    name: str                # "Golden Cross", "RSI oversold", ...
    direction: Direction     # "bullish" | "bearish" | "neutral"
    points: int              # positive for bullish, negative for bearish
    detail: str = ""         # free-form short description shown in charts/reports

    @property
    def signed(self) -> int:
        return self.points if self.direction == "bullish" else -self.points

    @property
    def label(self) -> str:
        if self.detail:
            return f"{self.name} — {self.detail}"
        return self.name

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "name": self.name,
            "direction": self.direction,
            "points": self.points,
            "detail": self.detail,
        }
