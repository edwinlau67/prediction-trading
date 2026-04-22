import numpy as np
import pandas as pd
import pytest

from src.indicators import TechnicalIndicators, SupportResistance


def test_sma_ema_match_manual(ohlcv_uptrend):
    close = ohlcv_uptrend["Close"]
    sma20 = TechnicalIndicators.sma(close, 20)
    assert sma20.iloc[-1] == pytest.approx(close.tail(20).mean(), rel=1e-9)

    ema = TechnicalIndicators.ema(close, 12)
    assert not ema.iloc[-1] != ema.iloc[-1]  # not NaN


def test_rsi_bounded(ohlcv_uptrend):
    rsi = TechnicalIndicators.rsi(ohlcv_uptrend["Close"])
    assert rsi.min() >= 0
    assert rsi.max() <= 100


def test_macd_histogram_sign(ohlcv_uptrend):
    m, s, h = TechnicalIndicators.macd(ohlcv_uptrend["Close"])
    pd.testing.assert_index_equal(m.index, ohlcv_uptrend.index)
    # histogram = MACD - signal
    diff = (m - s).dropna()
    assert np.allclose(diff.values, h.dropna().values, atol=1e-9)


def test_bollinger_envelope(ohlcv_uptrend):
    upper, mid, lower = TechnicalIndicators.bollinger(ohlcv_uptrend["Close"])
    mask = upper.notna() & lower.notna() & mid.notna()
    assert (upper[mask] >= mid[mask]).all()
    assert (lower[mask] <= mid[mask]).all()


def test_atr_positive(ohlcv_uptrend):
    atr = TechnicalIndicators.atr(ohlcv_uptrend["High"], ohlcv_uptrend["Low"],
                                  ohlcv_uptrend["Close"])
    assert (atr.dropna() >= 0).all()


def test_compute_all_adds_columns(ohlcv_uptrend):
    enriched = TechnicalIndicators.compute_all(ohlcv_uptrend)
    for col in ["SMA50", "RSI", "MACD", "BB_upper", "ATR", "ADX", "OBV"]:
        assert col in enriched.columns


def test_pivot_and_fib(ohlcv_uptrend):
    bar = ohlcv_uptrend.iloc[-1]
    piv = SupportResistance.pivot_points(bar["High"], bar["Low"], bar["Close"])
    assert piv.r1 > piv.pp > piv.s1
    fib = SupportResistance.fibonacci(ohlcv_uptrend, lookback=60)
    assert fib.high > fib.low
    assert set(fib.levels.keys()).issuperset({"0.0%", "100.0%"})
