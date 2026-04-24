"""Pure-pandas/numpy implementations of technical indicators.

Keeping these in-house avoids heavy dependencies like `ta-lib` while
covering everything used by both source projects: SMA, EMA, MACD, RSI,
Stochastic, Bollinger Bands, ATR, ADX, OBV, and classic volume stats.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class TechnicalIndicators:
    """Stateless calculator. All methods accept/return pandas objects."""

    # --- moving averages ---------------------------------------------------
    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(window=period, min_periods=period).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False, min_periods=period).mean()

    # --- momentum ----------------------------------------------------------
    @classmethod
    def macd(cls, close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
             ) -> tuple[pd.Series, pd.Series, pd.Series]:
        macd_line = cls.ema(close, fast) - cls.ema(close, slow)
        signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0.0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi.fillna(50.0)

    @staticmethod
    def stochastic(
        high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14,
        d_period: int = 3,
    ) -> tuple[pd.Series, pd.Series]:
        lowest = low.rolling(window=k_period, min_periods=k_period).min()
        highest = high.rolling(window=k_period, min_periods=k_period).max()
        k = 100.0 * (close - lowest) / (highest - lowest).replace(0.0, np.nan)
        d = k.rolling(window=d_period, min_periods=d_period).mean()
        return k, d

    # --- volatility --------------------------------------------------------
    @classmethod
    def bollinger(cls, close: pd.Series, period: int = 20, num_std: float = 2.0
                  ) -> tuple[pd.Series, pd.Series, pd.Series]:
        middle = cls.sma(close, period)
        std = close.rolling(window=period, min_periods=period).std()
        upper = middle + num_std * std
        lower = middle - num_std * std
        return upper, middle, lower

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
            ) -> pd.Series:
        prev_close = close.shift(1)
        tr = pd.concat([
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    @classmethod
    def adx(cls, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
            ) -> tuple[pd.Series, pd.Series, pd.Series]:
        up = high.diff()
        down = -low.diff()
        plus_dm = np.where((up > down) & (up > 0), up, 0.0)
        minus_dm = np.where((down > up) & (down > 0), down, 0.0)
        tr = pd.concat([
            (high - low).abs(),
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        plus_di = 100.0 * pd.Series(plus_dm, index=high.index).ewm(
            alpha=1 / period, adjust=False, min_periods=period).mean() / atr
        minus_di = 100.0 * pd.Series(minus_dm, index=high.index).ewm(
            alpha=1 / period, adjust=False, min_periods=period).mean() / atr
        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
        dx = dx.fillna(50.0)
        adx = dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        return adx, plus_di, minus_di

    # --- volume ------------------------------------------------------------
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        direction = np.sign(close.diff().fillna(0.0))
        return (direction * volume).cumsum()

    @staticmethod
    def volume_spikes(volume: pd.Series, window: int = 20, num_std: float = 2.0
                      ) -> pd.Series:
        mean = volume.rolling(window=window, min_periods=window).mean()
        std = volume.rolling(window=window, min_periods=window).std()
        return volume > (mean + num_std * std)

    # --- one-shot helper ---------------------------------------------------
    @classmethod
    def compute_all(cls, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """Attach all indicators as new columns. Returns a copy."""
        df = ohlcv.copy()
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        df["SMA20"] = cls.sma(close, 20)
        df["SMA50"] = cls.sma(close, 50)
        df["SMA200"] = cls.sma(close, 200)
        df["EMA12"] = cls.ema(close, 12)
        df["EMA20"] = cls.ema(close, 20)
        df["EMA26"] = cls.ema(close, 26)

        macd, signal, hist = cls.macd(close)
        df["MACD"] = macd
        df["MACD_signal"] = signal
        df["MACD_hist"] = hist

        df["RSI"] = cls.rsi(close)
        k, d = cls.stochastic(high, low, close)
        df["Stoch_K"] = k
        df["Stoch_D"] = d

        upper, mid, lower = cls.bollinger(close)
        df["BB_upper"] = upper
        df["BB_mid"] = mid
        df["BB_lower"] = lower

        df["ATR"] = cls.atr(high, low, close)
        adx, pdi, mdi = cls.adx(high, low, close)
        df["ADX"] = adx
        df["+DI"] = pdi
        df["-DI"] = mdi

        df["OBV"] = cls.obv(close, volume)
        df["VolumeSpike"] = cls.volume_spikes(volume)
        return df
