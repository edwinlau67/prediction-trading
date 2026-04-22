"""Claude-powered stock predictor.

Ports the core idea from ``stock-prediction``: expose the rule-based engine
as an Anthropic *tool*, let Claude call it, and have the model return a
structured analysis. Works without an API key — falls back to returning
the raw tool output so the system still functions offline / in tests.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover
    Anthropic = None  # type: ignore[assignment]

from ..data_fetcher import DataFetcher, MarketData
from ..indicators import TechnicalIndicators, SupportResistance
from .factor import ALL_CATEGORIES, Direction
from .signal_scorer import SignalScorer


Timeframe = Literal["1d", "1w", "1m", "3m", "6m", "ytd", "1y", "2y", "5y"]
_TIMEFRAME_DAYS: dict[str, int] = {
    "1d": 1, "1w": 7, "1m": 30, "3m": 90, "6m": 180,
    "ytd": 365, "1y": 365, "2y": 730, "5y": 1825,
}


@dataclass
class AIPrediction:
    ticker: str
    timeframe: str
    direction: Direction
    confidence: float
    current_price: float
    price_target: float
    target_date: str
    risk_level: str
    key_factors: list[str] = field(default_factory=list)
    fundamentals: dict[str, Any] = field(default_factory=dict)
    narrative: str = ""
    raw_tool_output: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "timeframe": self.timeframe,
            "direction": self.direction,
            "confidence": self.confidence,
            "current_price": self.current_price,
            "price_target": self.price_target,
            "target_date": self.target_date,
            "risk_level": self.risk_level,
            "key_factors": self.key_factors,
            "fundamentals": self.fundamentals,
            "narrative": self.narrative,
        }


STOCK_PREDICTION_TOOL = {
    "name": "stock_prediction",
    "description": (
        "Compute a data-driven stock prediction from live Yahoo Finance "
        "data. Fetches OHLCV history, computes technical indicators "
        "(SMA, EMA, MACD, RSI, Bollinger, ATR, ADX, OBV, Stochastic, "
        "pivots, Fibonacci) and fundamental ratios, then returns a "
        "direction/confidence/price-target structure."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {"type": "string", "description": "Stock symbol, e.g. AAPL."},
            "timeframe": {
                "type": "string",
                "enum": list(_TIMEFRAME_DAYS.keys()),
                "description": "Prediction horizon.",
            },
        },
        "required": ["ticker"],
    },
}

SYSTEM_PROMPT = """You are a disciplined equities analyst. When asked for a
prediction you MUST call the `stock_prediction` tool exactly once with the
requested ticker and timeframe. After the tool returns, write a concise
analysis that:

1. Restates direction, confidence, current price, and price target.
2. Lists up to 5 bullish factors and up to 5 bearish/risk factors using the
   tool's key_factors and the fundamentals it returned.
3. Notes the risk level and what could invalidate the thesis.
4. Ends with a 2-4 sentence narrative.

Do not invent numbers. Use only values returned by the tool. Keep the
response under 400 words.
"""


class AIPredictor:
    """Runs the Claude tool-use loop; falls back to local tool output."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2000,
        data_fetcher: DataFetcher | None = None,
        categories: tuple[str, ...] | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self.data_fetcher = data_fetcher or DataFetcher()
        self.categories = tuple(categories) if categories else ALL_CATEGORIES
        self._client = None
        if self.api_key and Anthropic is not None:
            self._client = Anthropic(api_key=self.api_key)

    # ------------------------------------------------------------------ core
    def predict(self, ticker: str, timeframe: Timeframe = "1w") -> AIPrediction:
        tool_output = self._run_tool(ticker, timeframe)
        narrative = ""

        if self._client is not None:
            narrative = self._run_claude(ticker, timeframe, tool_output)

        return AIPrediction(
            ticker=tool_output["ticker"],
            timeframe=tool_output["timeframe"],
            direction=tool_output["direction"],
            confidence=tool_output["confidence"],
            current_price=tool_output["current_price"],
            price_target=tool_output["price_target"],
            target_date=tool_output["target_date"],
            risk_level=tool_output["risk_level"],
            key_factors=tool_output.get("key_factors", []),
            fundamentals=tool_output.get("fundamentals", {}),
            narrative=narrative,
            raw_tool_output=tool_output,
        )

    # ---------------------------------------------------------------- tool
    def _run_tool(self, ticker: str, timeframe: str) -> dict[str, Any]:
        """Local implementation of the `stock_prediction` tool.

        Returns the same schema Claude sees so offline callers can consume
        it directly.
        """
        market = self.data_fetcher.fetch(ticker, lookback_days=365)
        return self._predict_from_market(market, timeframe)

    def _predict_from_market(self, market: MarketData, timeframe: str
                             ) -> dict[str, Any]:
        df = TechnicalIndicators.compute_all(market.ohlcv)
        score = SignalScorer(categories=self.categories).score(
            df, fundamentals=market.fundamentals,
        )

        row = df.iloc[-1]
        atr = float(row.get("ATR", 0.0) or 0.0)
        atr_mean = float(df["ATR"].tail(20).mean() or 0.0)
        if atr_mean and atr > 1.3 * atr_mean:
            risk = "high"
        elif atr_mean and atr < 0.8 * atr_mean:
            risk = "low"
        else:
            risk = "medium"

        days = _TIMEFRAME_DAYS.get(timeframe, 7)
        # Project target using recent drift and confidence-weighted magnitude.
        recent = df["Close"].tail(60)
        daily_drift = float(recent.pct_change().mean() or 0.0)
        projected_move = daily_drift * days
        sign = {"bullish": 1.0, "bearish": -1.0, "neutral": 0.0}[score.direction]
        magnitude = max(abs(projected_move), 0.01) * (0.5 + score.confidence)
        target = market.current_price * (1.0 + sign * magnitude)

        pivots = SupportResistance.pivot_points(
            float(row["High"]), float(row["Low"]), float(row["Close"])
        )
        fib = SupportResistance.fibonacci(market.ohlcv)

        # Emit up to 6 top factors as plain strings (the format Claude expects).
        top = sorted(score.factors, key=lambda f: abs(f.signed), reverse=True)[:6]
        key_factors = [f.label for f in top] or [
            f"{score.direction.title()} bias from technical model "
            f"(confidence {score.confidence:.0%})"
        ]

        return {
            "ticker": market.ticker,
            "timeframe": timeframe,
            "direction": score.direction,
            "confidence": round(score.confidence, 3),
            "current_price": round(market.current_price, 4),
            "price_target": round(target, 4),
            "target_date": (datetime.utcnow() + timedelta(days=days)).date().isoformat(),
            "risk_level": risk,
            "key_factors": key_factors,
            "fundamentals": market.fundamentals,
            "pivots": pivots.__dict__,
            "fibonacci": fib.levels,
            "scoring_components": score.components,
            "category_points": score.category_points,
            "indicators": sorted(self.categories),
        }

    # ---------------------------------------------------------------- Claude
    def _run_claude(self, ticker: str, timeframe: str,
                    tool_output: dict[str, Any]) -> str:
        """Run the tool-use exchange and return Claude's narrative."""
        user_msg = (
            f"Predict {ticker.upper()} over a {timeframe} horizon. "
            "Call the stock_prediction tool, then write the analysis."
        )
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]

        try:
            response = self._client.messages.create(  # type: ignore[union-attr]
                model=self.model,
                max_tokens=self.max_tokens,
                system=[{"type": "text", "text": SYSTEM_PROMPT,
                         "cache_control": {"type": "ephemeral"}}],
                tools=[STOCK_PREDICTION_TOOL],
                messages=messages,
            )

            # Handle a single tool_use -> tool_result round-trip.
            if response.stop_reason == "tool_use":
                tool_use = next(b for b in response.content if b.type == "tool_use")
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(tool_output),
                    }],
                })
                response = self._client.messages.create(  # type: ignore[union-attr]
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=[{"type": "text", "text": SYSTEM_PROMPT,
                             "cache_control": {"type": "ephemeral"}}],
                    tools=[STOCK_PREDICTION_TOOL],
                    messages=messages,
                )
            return "".join(
                b.text for b in response.content if getattr(b, "type", "") == "text"
            ).strip()
        except Exception as exc:  # pragma: no cover - network/runtime guard
            return f"[Claude call failed: {exc}]"
