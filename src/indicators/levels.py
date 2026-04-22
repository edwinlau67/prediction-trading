"""Support/resistance, pivot points, and Fibonacci retracement levels."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class PivotLevels:
    pp: float
    r1: float
    r2: float
    s1: float
    s2: float


@dataclass
class FibonacciLevels:
    high: float
    low: float
    levels: dict[str, float]


class SupportResistance:
    """Classic pivot points + Fibonacci retracements + swing trendlines."""

    @staticmethod
    def pivot_points(high: float, low: float, close: float) -> PivotLevels:
        pp = (high + low + close) / 3.0
        r1 = 2.0 * pp - low
        s1 = 2.0 * pp - high
        r2 = pp + (high - low)
        s2 = pp - (high - low)
        return PivotLevels(pp=pp, r1=r1, r2=r2, s1=s1, s2=s2)

    @staticmethod
    def fibonacci(ohlcv: pd.DataFrame, lookback: int = 126) -> FibonacciLevels:
        tail = ohlcv.tail(lookback)
        hi = float(tail["High"].max())
        lo = float(tail["Low"].min())
        rng = hi - lo
        ratios = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)
        levels = {f"{int(r * 1000) / 10}%": hi - rng * r for r in ratios}
        return FibonacciLevels(high=hi, low=lo, levels=levels)

    @staticmethod
    def swing_points(series: pd.Series, window: int = 5) -> tuple[pd.Series, pd.Series]:
        """Detect local highs/lows using a centred rolling window."""
        rolling_max = series.rolling(window=window * 2 + 1, center=True).max()
        rolling_min = series.rolling(window=window * 2 + 1, center=True).min()
        highs = series[(series == rolling_max)]
        lows = series[(series == rolling_min)]
        return highs.dropna(), lows.dropna()

    @classmethod
    def trendlines(cls, ohlcv: pd.DataFrame, window: int = 5
                   ) -> dict[str, tuple[float, float]]:
        """Fit linear trendlines through recent swing highs and lows.

        Returns a dict of {"support": (slope, intercept), "resistance": ...}
        with values in bar-index space.
        """
        highs, lows = cls.swing_points(ohlcv["Close"], window=window)
        result: dict[str, tuple[float, float]] = {}

        def _fit(points: pd.Series) -> tuple[float, float] | None:
            if len(points) < 2:
                return None
            x = np.arange(len(ohlcv))[ohlcv.index.isin(points.index)]
            y = points.values
            if len(x) < 2:
                return None
            slope, intercept = np.polyfit(x, y, 1)
            return float(slope), float(intercept)

        sup = _fit(lows.tail(6))
        res = _fit(highs.tail(6))
        if sup is not None:
            result["support"] = sup
        if res is not None:
            result["resistance"] = res
        return result
