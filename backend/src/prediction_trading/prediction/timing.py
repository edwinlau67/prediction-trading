"""Entry/exit timing recommendation engine.

Rule-based, stateless. Reads indicator columns already present on the OHLCV
DataFrame after TechnicalIndicators.compute_all() has been called.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import numpy as np
import pandas as pd

from .signal_scorer import ScoredSignal

if TYPE_CHECKING:
    from .predictor import Prediction

TimingAction = Literal[
    "BUY_NOW", "BUY_ON_DIP", "BUY_ON_BREAKOUT",
    "SELL_NOW", "SELL_TRAILING", "HOLD", "WAIT",
]


@dataclass
class TimingRecommendation:
    action: TimingAction
    reason: str
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    time_horizon: str = "1w"

    def as_dict(self) -> dict:
        return {
            "action": self.action,
            "reason": self.reason,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "time_horizon": self.time_horizon,
        }


# ── helpers ────────────────────────────────────────────────────────────────

def _col_last(df: pd.DataFrame, col: str) -> float | None:
    if col not in df.columns:
        return None
    val = df[col].iloc[-1]
    return float(val) if not (val is None or (isinstance(val, float) and np.isnan(val))) else None


def _get_rsi(df: pd.DataFrame) -> float:
    v = _col_last(df, "RSI")
    return v if v is not None else 50.0


def _get_atr(df: pd.DataFrame) -> float:
    v = _col_last(df, "ATR")
    return v if v is not None else 0.0


def _get_sma(df: pd.DataFrame, n: int) -> float | None:
    return _col_last(df, f"SMA{n}")


def _nearest_resistance(df: pd.DataFrame) -> float | None:
    """Pivot R1 computed from the prior bar's H/L/C."""
    if len(df) < 2:
        return None
    try:
        from ..indicators.levels import SupportResistance
        prior = df.iloc[-2]
        piv = SupportResistance.pivot_points(
            float(prior["High"]), float(prior["Low"]), float(prior["Close"])
        )
        return piv.r1
    except Exception:
        return None


# ── main entry point ───────────────────────────────────────────────────────

def compute_timing(
    scored_signal: ScoredSignal,
    ohlcv: pd.DataFrame,
    prediction: "Prediction",
) -> TimingRecommendation:
    """Derive an actionable timing recommendation from a scored prediction."""
    direction = prediction.direction
    confidence = prediction.confidence
    price = prediction.current_price
    target = prediction.price_target
    time_horizon = prediction.meta.get("timeframe", "1w")

    rsi = _get_rsi(ohlcv)
    atr = _get_atr(ohlcv)
    sma50 = _get_sma(ohlcv, 50)
    resistance = _nearest_resistance(ohlcv)

    def _stop_long(entry: float) -> float | None:
        return round(entry - 2.0 * atr, 2) if atr > 0 else None

    def _stop_short(entry: float) -> float | None:
        return round(entry + 2.0 * atr, 2) if atr > 0 else None

    def _take_profit_long(entry: float) -> float | None:
        if target is not None:
            return round(target, 2)
        return round(entry + 3.0 * atr, 2) if atr > 0 else None

    def _take_profit_short(entry: float) -> float | None:
        return round(entry - 3.0 * atr, 2) if atr > 0 else None

    # 1. No clear signal
    if direction == "neutral" or confidence < 0.4:
        return TimingRecommendation(
            action="WAIT",
            reason=f"No clear directional bias (confidence {confidence:.0%})",
            time_horizon=time_horizon,
        )

    if direction == "bullish":
        # 2. Near or at price target — recommend trailing stop
        if target is not None and price >= 0.90 * target:
            return TimingRecommendation(
                action="SELL_TRAILING",
                reason=f"Price at {price / target:.0%} of target ${target:.2f} — protect gains with trailing stop",
                stop_loss=_stop_long(price),
                take_profit=round(target, 2),
                time_horizon=time_horizon,
            )

        # 3. Overextended — wait for dip
        pct_above_sma50 = (price / sma50 - 1.0) if sma50 else 0.0
        if rsi > 65 or pct_above_sma50 > 0.05:
            entry_dip = round(sma50 * 1.01, 2) if sma50 else None
            reason_parts = []
            if rsi > 65:
                reason_parts.append(f"RSI={rsi:.0f} (overextended)")
            if pct_above_sma50 > 0.05:
                reason_parts.append(f"{pct_above_sma50:.0%} above SMA50")
            return TimingRecommendation(
                action="BUY_ON_DIP",
                reason=f"Bullish but {', '.join(reason_parts)} — wait for pullback to SMA50",
                entry_price=entry_dip,
                stop_loss=_stop_long(entry_dip) if entry_dip else None,
                take_profit=_take_profit_long(entry_dip or price),
                time_horizon=time_horizon,
            )

        # 4. Approaching key resistance — wait for breakout confirmation
        if resistance is not None and price >= 0.97 * resistance and price < resistance:
            entry_bo = round(resistance * 1.005, 2)
            return TimingRecommendation(
                action="BUY_ON_BREAKOUT",
                reason=f"Approaching resistance at ${resistance:.2f} — buy on confirmed breakout",
                entry_price=entry_bo,
                stop_loss=_stop_long(entry_bo),
                take_profit=_take_profit_long(entry_bo),
                time_horizon=time_horizon,
            )

        # 5. Strong buy signal
        if confidence >= 0.5 and rsi < 65:
            return TimingRecommendation(
                action="BUY_NOW",
                reason=f"Bullish signal, RSI={rsi:.0f}, confidence {confidence:.0%}",
                entry_price=round(price, 2),
                stop_loss=_stop_long(price),
                take_profit=_take_profit_long(price),
                time_horizon=time_horizon,
            )

        # 6. Weak bullish — hold / wait for confirmation
        return TimingRecommendation(
            action="HOLD",
            reason=f"Bullish bias but confidence {confidence:.0%} — wait for stronger signal",
            time_horizon=time_horizon,
        )

    # direction == "bearish"
    # 7. Strong sell signal
    if confidence >= 0.5:
        return TimingRecommendation(
            action="SELL_NOW",
            reason=f"Bearish signal, RSI={rsi:.0f}, confidence {confidence:.0%}",
            entry_price=round(price, 2),
            stop_loss=_stop_short(price),
            take_profit=_take_profit_short(price),
            time_horizon=time_horizon,
        )

    # 8. Weak bearish — hold
    return TimingRecommendation(
        action="HOLD",
        reason=f"Bearish bias but confidence {confidence:.0%} — insufficient for action",
        time_horizon=time_horizon,
    )
