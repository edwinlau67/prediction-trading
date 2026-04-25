"""Shared fixtures: synthetic OHLCV generator so tests don't hit Yahoo Finance."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _synthetic_ohlcv(bars: int = 400, seed: int = 7,
                     trend: float = 0.0003, vol: float = 0.015,
                     start_price: float = 100.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(trend, vol, size=bars)
    close = start_price * np.exp(np.cumsum(returns))
    high = close * (1.0 + np.abs(rng.normal(0.0, 0.01, size=bars)))
    low = close * (1.0 - np.abs(rng.normal(0.0, 0.01, size=bars)))
    open_ = close * (1.0 + rng.normal(0.0, 0.005, size=bars))
    volume = rng.integers(1_000_000, 5_000_000, size=bars).astype(float)
    index = pd.bdate_range("2022-01-03", periods=bars, freq="B")
    return pd.DataFrame({
        "Open": open_, "High": np.maximum(high, np.maximum(open_, close)),
        "Low": np.minimum(low, np.minimum(open_, close)),
        "Close": close, "Volume": volume,
    }, index=index)


@pytest.fixture
def ohlcv_uptrend() -> pd.DataFrame:
    return _synthetic_ohlcv(trend=0.0018, vol=0.012, seed=11)


@pytest.fixture
def ohlcv_downtrend() -> pd.DataFrame:
    return _synthetic_ohlcv(trend=-0.0018, vol=0.012, seed=17)


@pytest.fixture
def ohlcv_sideways() -> pd.DataFrame:
    return _synthetic_ohlcv(trend=0.00001, vol=0.008, seed=23)
