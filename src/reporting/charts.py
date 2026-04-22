"""Backtest chart generators: indicators, signals, performance, risk."""
from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from ..backtest.backtester import BacktestResult
from ..indicators import TechnicalIndicators
from .base import (
    BaseChart, COLOR_BEAR, COLOR_BULL, COLOR_PRICE, COLOR_WARN, COLOR_ACCENT,
)


class ChartBuilder(BaseChart):
    """Renders the four standard backtest chart PNGs into a ``charts/`` dir."""

    # --------------------------------------------------------------- public
    def save_all(self, result: BacktestResult, out_dir: Path, ohlcv
                 ) -> dict[str, Path]:
        out_dir = Path(out_dir)
        charts_dir = out_dir / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)
        enriched = TechnicalIndicators.compute_all(ohlcv)
        return {
            "indicators": self.indicators_chart(enriched, charts_dir),
            "signals": self.signals_chart(result, enriched, charts_dir),
            "performance": self.performance_chart(result, charts_dir),
            "risk": self.risk_chart(result, enriched, charts_dir),
        }

    # --------------------------------------------------------- indicators
    def indicators_chart(self, df, charts_dir: Path) -> Path:
        fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True,
                                 gridspec_kw={"height_ratios": [3, 1, 1, 1]})
        axes[0].plot(df.index, df["Close"], label="Close", color=COLOR_PRICE)
        for col, color in (("SMA20", COLOR_WARN), ("SMA50", COLOR_BULL),
                           ("SMA200", COLOR_BEAR)):
            if col in df and df[col].notna().any():
                axes[0].plot(df.index, df[col], label=col, color=color, alpha=0.8)
        if "BB_upper" in df:
            axes[0].fill_between(df.index, df["BB_lower"], df["BB_upper"],
                                 alpha=0.1, color="grey", label="Bollinger")
        axes[0].set_title("Price + Moving Averages + Bollinger")
        axes[0].legend(loc="upper left")

        axes[1].plot(df.index, df["MACD"], label="MACD", color=COLOR_PRICE)
        axes[1].plot(df.index, df["MACD_signal"], label="Signal", color=COLOR_WARN)
        axes[1].bar(df.index, df["MACD_hist"], label="Hist", color="grey", alpha=0.4)
        axes[1].axhline(0, color="black", linewidth=0.5)
        axes[1].set_title("MACD")
        axes[1].legend(loc="upper left")

        axes[2].plot(df.index, df["RSI"], color=COLOR_ACCENT)
        axes[2].axhline(70, color=COLOR_BEAR, linestyle="--", linewidth=0.6)
        axes[2].axhline(30, color=COLOR_BULL, linestyle="--", linewidth=0.6)
        axes[2].set_ylim(0, 100)
        axes[2].set_title("RSI (14)")

        axes[3].plot(df.index, df["ADX"], label="ADX", color="#17becf")
        axes[3].plot(df.index, df["+DI"], label="+DI", color=COLOR_BULL, alpha=0.6)
        axes[3].plot(df.index, df["-DI"], label="-DI", color=COLOR_BEAR, alpha=0.6)
        axes[3].axhline(25, color="black", linestyle="--", linewidth=0.5)
        axes[3].set_title("ADX / +DI / -DI")
        axes[3].legend(loc="upper left")

        axes[-1].xaxis.set_major_locator(mdates.AutoDateLocator())
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        fig.tight_layout()
        return self._save(fig, charts_dir / "indicators.png")

    # ------------------------------------------------------------ signals
    def signals_chart(self, result: BacktestResult, df, charts_dir: Path) -> Path:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df.index, df["Close"], color=COLOR_PRICE, label="Close")
        for trade in result.portfolio.closed_trades:
            color = COLOR_BULL if trade.side == "long" else COLOR_BEAR
            ax.scatter(trade.entry_time, trade.entry_price, marker="^",
                       color=color, s=80, zorder=3)
            ax.scatter(trade.exit_time, trade.exit_price, marker="v",
                       color="black", s=60, zorder=3)
        ax.set_title(f"{result.ticker} — Signals & Trades "
                     f"({len(result.portfolio.closed_trades)} trades)")
        ax.legend(loc="upper left")
        fig.tight_layout()
        return self._save(fig, charts_dir / "signals.png")

    # ------------------------------------------------------- performance
    def performance_chart(self, result: BacktestResult, charts_dir: Path) -> Path:
        curve = result.portfolio.equity_curve
        if not curve:
            return charts_dir / "performance.png"

        times, equities = zip(*curve)
        equities = np.asarray(equities, dtype=float)
        peak = np.maximum.accumulate(equities)
        dd = (equities - peak) / peak * 100.0

        fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
        axes[0].plot(times, equities, color=COLOR_PRICE, label="Equity")
        axes[0].axhline(result.portfolio.initial_capital, color="grey",
                        linestyle="--", label="Initial Capital")
        axes[0].set_title(f"Equity Curve — return {result.portfolio.return_pct:+.2f}%")
        axes[0].legend(loc="upper left")

        axes[1].fill_between(times, dd, 0, color=COLOR_BEAR, alpha=0.4)
        axes[1].set_title(f"Drawdown — max {result.portfolio.max_drawdown:.2f}%")
        axes[1].set_ylabel("%")
        fig.tight_layout()
        return self._save(fig, charts_dir / "performance.png")

    # -------------------------------------------------------------- risk
    def risk_chart(self, result: BacktestResult, df, charts_dir: Path) -> Path:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        trades = result.portfolio.closed_trades
        if trades:
            pnls = [t.pnl for t in trades]
            axes[0].bar(range(len(pnls)),
                        pnls,
                        color=[COLOR_BULL if p > 0 else COLOR_BEAR for p in pnls])
            axes[0].axhline(0, color="black", linewidth=0.5)
            axes[0].set_title("Per-Trade P&L ($)")
            axes[0].set_xlabel("Trade #")
        else:
            axes[0].text(0.5, 0.5, "No trades", ha="center", va="center")
            axes[0].set_axis_off()

        if "ATR" in df and df["ATR"].notna().any():
            axes[1].plot(df.index, df["ATR"], color=COLOR_WARN)
            axes[1].set_title("ATR (14) — Volatility")
        else:
            axes[1].set_axis_off()

        fig.tight_layout()
        return self._save(fig, charts_dir / "risk.png")
