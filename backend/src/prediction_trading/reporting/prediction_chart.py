"""Dynamic multi-panel analysis chart for a single prediction.

Mirrors the behaviour of ``stock-prediction``:

* Always-present panels:
    1. Price + Target          (6-month price, projected target, overlays)
    2. Confidence & Risk       (arc gauge + risk pill + direction label)
    3. Technical Signal Factors (horizontal bar chart of scored factors)

* Optional panels (included only when the matching category is selected):
    - MACD                     (trend)
    - RSI                      (momentum)
    - Stochastic               (momentum)
    - Volume + Spikes          (volume)
    - OBV                      (volume)
    - Support & Resistance     (support)
    - ATR                      (volatility)
    - Fundamental Indicators   (fundamental)

The figure height scales with panel count.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..indicators import SupportResistance, TechnicalIndicators
from ..prediction.factor import ALL_CATEGORIES, Factor
from ..prediction.predictor import Prediction
from .base import (
    BaseChart, COLOR_ACCENT, COLOR_BEAR, COLOR_BULL, COLOR_NEUTRAL,
    COLOR_PRICE, COLOR_WARN, RISK_COLORS, direction_color,
)


class PredictionChart(BaseChart):
    """Render the stock-prediction-style analysis chart."""

    # ------------------------------------------------------------------ api
    def render(
        self,
        prediction: Prediction,
        ohlcv: pd.DataFrame,
        *,
        categories: Iterable[str] | None = None,
        timeframe: str = "1w",
        out_path: str | Path,
    ) -> Path:
        categories = tuple(c for c in (categories or ALL_CATEGORIES)
                           if c in ALL_CATEGORIES)
        df = TechnicalIndicators.compute_all(ohlcv)

        panels = self._panel_spec(categories, prediction)
        fig_height = 3 * len(panels) + 2
        fig = plt.figure(figsize=(14, fig_height))
        gs = fig.add_gridspec(len(panels), 1, hspace=0.45)

        for i, panel in enumerate(panels):
            ax = fig.add_subplot(gs[i, 0])
            panel(ax, prediction, df, categories, timeframe)

        fig.suptitle(
            f"{prediction.ticker} — {timeframe} forecast "
            f"({prediction.direction.upper()}, "
            f"{prediction.confidence:.0%} confidence)",
            fontsize=15, fontweight="bold", y=0.995,
        )
        return self._save(fig, out_path, bbox_inches="tight")

    # ------------------------------------------------------------ panel set
    def _panel_spec(self, cats: tuple[str, ...], p: Prediction) -> list:
        panels: list = [self._panel_price_target]

        # always-on: confidence/risk + signal factors
        panels.append(self._panel_confidence_arc)
        panels.append(self._panel_signal_factors)

        if "trend" in cats:
            panels.append(self._panel_macd)
        if "momentum" in cats:
            panels.append(self._panel_rsi)
            panels.append(self._panel_stoch)
        if "volume" in cats:
            panels.append(self._panel_volume)
            panels.append(self._panel_obv)
        if "support" in cats:
            panels.append(self._panel_support)
        if "volatility" in cats:
            panels.append(self._panel_atr)
        if "fundamental" in cats:
            has_fund = bool(p.meta.get("fundamentals")) or (
                p.ai_signal is not None and bool(p.ai_signal.fundamentals)
            ) or any(
                f.category == "fundamental" for f in (p.rule_signal.factors
                                                      if p.rule_signal else [])
            )
            if has_fund:
                panels.append(self._panel_fundamentals)
        return panels

    # =============================================================== panels
    def _panel_price_target(self, ax, p: Prediction, df, cats, tf) -> None:
        tail = df.tail(126)                   # ~6 months
        ax.plot(tail.index, tail["Close"], color=COLOR_PRICE, label="Close")

        if "trend" in cats:
            for col, color in (("SMA50", COLOR_WARN), ("SMA200", COLOR_BEAR),
                               ("EMA20", COLOR_BULL)):
                if col in tail and tail[col].notna().any():
                    ax.plot(tail.index, tail[col], label=col, alpha=0.8,
                            color=color, linewidth=1.2)
        if "volatility" in cats and "BB_upper" in tail:
            ax.fill_between(tail.index, tail["BB_lower"], tail["BB_upper"],
                            color="grey", alpha=0.12, label="Bollinger")

        # Price target projection
        if p.price_target is not None and p.target_date:
            target_dt = pd.to_datetime(p.target_date)
            last_dt = tail.index[-1]
            ax.plot([last_dt, target_dt], [p.current_price, p.price_target],
                    linestyle="--", linewidth=2, color=direction_color(p.direction),
                    label=f"Target ${p.price_target:.2f}")
            ax.scatter([target_dt], [p.price_target], s=60,
                       color=direction_color(p.direction), zorder=3)

        ax.set_title(f"Price + {tf} Target "
                     f"(current ${p.current_price:.2f})", fontweight="bold")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)

    def _panel_confidence_arc(self, ax, p: Prediction, df, cats, tf) -> None:
        ax.set_aspect("equal")
        ax.set_xlim(-1.2, 2.6)
        ax.set_ylim(-0.3, 1.2)
        ax.axis("off")

        # Confidence arc gauge (0..1 -> 0..180°)
        theta = np.linspace(np.pi, 0.0, 181)
        ax.plot(np.cos(theta), np.sin(theta), color="#cccccc", linewidth=10, solid_capstyle="butt")
        filled = int(180 * p.confidence)
        if filled > 0:
            theta_fill = np.linspace(np.pi, np.pi - np.pi * p.confidence, filled + 1)
            ax.plot(np.cos(theta_fill), np.sin(theta_fill),
                    color=direction_color(p.direction),
                    linewidth=10, solid_capstyle="butt")
        ax.text(0.0, -0.05, f"{p.confidence:.0%}", ha="center", va="top",
                fontsize=22, fontweight="bold",
                color=direction_color(p.direction))
        ax.text(0.0, -0.25, "CONFIDENCE", ha="center", va="top",
                fontsize=8, color="#555")

        # Direction pill
        dir_color = direction_color(p.direction)
        ax.add_patch(mpatches.FancyBboxPatch(
            (1.3, 0.75), 1.1, 0.25, boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=0, facecolor=dir_color, alpha=0.85))
        ax.text(1.85, 0.875, p.direction.upper(), ha="center", va="center",
                fontsize=12, fontweight="bold", color="white")

        # Risk pill (ATR-derived)
        risk_color = RISK_COLORS.get(p.risk_level, COLOR_NEUTRAL)
        ax.add_patch(mpatches.FancyBboxPatch(
            (1.3, 0.35), 1.1, 0.25, boxstyle="round,pad=0.02,rounding_size=0.12",
            linewidth=0, facecolor=risk_color, alpha=0.85))
        ax.text(1.85, 0.475, f"RISK: {p.risk_level.upper()}", ha="center",
                va="center", fontsize=11, fontweight="bold", color="white")

        # Target text
        if p.price_target is not None:
            ax.text(1.85, 0.10, f"Target ${p.price_target:.2f}",
                    ha="center", va="center", fontsize=10, color="#222")
            if p.target_date:
                ax.text(1.85, -0.05, f"by {p.target_date}",
                        ha="center", va="center", fontsize=8, color="#666")

        ax.set_title("Confidence & Risk", fontweight="bold")

    def _panel_signal_factors(self, ax, p: Prediction, df, cats, tf) -> None:
        rule = p.rule_signal
        if rule is None or not rule.factors:
            ax.text(0.5, 0.5, "No scored factors", ha="center", va="center")
            ax.axis("off")
            return

        # top 10 by absolute points, bullish first then bearish
        factors = sorted(rule.factors, key=lambda f: (-abs(f.signed), f.category))[:10]
        labels = [f"[{f.category[:4]}] {f.name}" for f in factors]
        vals = [f.signed for f in factors]
        colors = [COLOR_BULL if v > 0 else COLOR_BEAR if v < 0 else COLOR_NEUTRAL
                  for v in vals]
        y = np.arange(len(factors))
        ax.barh(y, vals, color=colors, alpha=0.85)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.axvline(0, color="black", linewidth=0.5)
        ax.invert_yaxis()
        max_abs = max((abs(v) for v in vals), default=1)
        ax.set_xlim(-max_abs - 1, max_abs + 1)
        ax.set_title(f"Signal Factors (net {rule.net_points:+d} pts)",
                     fontweight="bold")
        ax.grid(axis="x", alpha=0.3)

    def _panel_macd(self, ax, p: Prediction, df, cats, tf) -> None:
        tail = df.tail(126)
        colors = [COLOR_BULL if v >= 0 else COLOR_BEAR for v in tail["MACD_hist"].fillna(0)]
        ax.bar(tail.index, tail["MACD_hist"], color=colors, alpha=0.5, width=1.0,
               label="Histogram")
        ax.plot(tail.index, tail["MACD"], color=COLOR_PRICE, label="MACD")
        ax.plot(tail.index, tail["MACD_signal"], color=COLOR_WARN, label="Signal")
        ax.axhline(0, color="black", linewidth=0.5)
        last = tail.iloc[-1]
        cross = "above signal" if last["MACD"] > last["MACD_signal"] else "below signal"
        ax.set_title(f"MACD (12,26,9) — currently {cross}", fontweight="bold")
        ax.legend(loc="upper left", fontsize=8)

    def _panel_rsi(self, ax, p: Prediction, df, cats, tf) -> None:
        tail = df.tail(126)
        ax.plot(tail.index, tail["RSI"], color=COLOR_ACCENT, label="RSI(14)")
        ax.axhline(70, color=COLOR_BEAR, linestyle="--", linewidth=0.7)
        ax.axhline(30, color=COLOR_BULL, linestyle="--", linewidth=0.7)
        ax.fill_between(tail.index, 70, 100, alpha=0.08, color=COLOR_BEAR)
        ax.fill_between(tail.index, 0, 30, alpha=0.08, color=COLOR_BULL)
        ax.set_ylim(0, 100)
        current = float(tail["RSI"].iloc[-1])
        zone = "overbought" if current > 70 else "oversold" if current < 30 else "neutral"
        ax.set_title(f"RSI(14) = {current:.1f} ({zone})", fontweight="bold")

    def _panel_stoch(self, ax, p: Prediction, df, cats, tf) -> None:
        tail = df.tail(126)
        ax.plot(tail.index, tail["Stoch_K"], color=COLOR_PRICE, label="%K")
        ax.plot(tail.index, tail["Stoch_D"], color=COLOR_WARN, label="%D")
        ax.axhline(80, color=COLOR_BEAR, linestyle="--", linewidth=0.7)
        ax.axhline(20, color=COLOR_BULL, linestyle="--", linewidth=0.7)
        ax.fill_between(tail.index, 80, 100, alpha=0.08, color=COLOR_BEAR)
        ax.fill_between(tail.index, 0, 20, alpha=0.08, color=COLOR_BULL)
        ax.set_ylim(0, 100)
        last = tail.iloc[-1]
        ax.set_title(f"Stochastic (14,3) — %K={last['Stoch_K']:.1f} "
                     f"%D={last['Stoch_D']:.1f}", fontweight="bold")
        ax.legend(loc="upper left", fontsize=8)

    def _panel_volume(self, ax, p: Prediction, df, cats, tf) -> None:
        tail = df.tail(126)
        colors = []
        closes = tail["Close"].values
        for i, v in enumerate(tail["Volume"].values):
            if i == 0 or closes[i] >= closes[i - 1]:
                colors.append(COLOR_BULL)
            else:
                colors.append(COLOR_BEAR)
        ax.bar(tail.index, tail["Volume"], color=colors, alpha=0.6, width=1.0)
        mean_vol = tail["Volume"].rolling(20).mean()
        ax.plot(tail.index, mean_vol, color="black", linewidth=1.0,
                linestyle="--", label="20d mean")
        if "VolumeSpike" in tail:
            spikes = tail[tail["VolumeSpike"].fillna(False)]
            if not spikes.empty:
                ax.scatter(spikes.index, spikes["Volume"], marker="^",
                           s=60, color="gold", edgecolor="black", zorder=3,
                           label="Spike")
        ax.set_title("Volume + Spikes", fontweight="bold")
        ax.legend(loc="upper left", fontsize=8)

    def _panel_obv(self, ax, p: Prediction, df, cats, tf) -> None:
        tail = df.tail(126)
        obv = tail["OBV"]
        rising = obv.iloc[-1] > obv.iloc[0]
        color = COLOR_BULL if rising else COLOR_BEAR
        ax.plot(tail.index, obv, color=color, linewidth=1.4)
        ax.fill_between(tail.index, obv, obv.min(), alpha=0.15, color=color)
        trend = "rising" if rising else "falling"
        ax.set_title(f"OBV — {trend}", fontweight="bold")

    def _panel_support(self, ax, p: Prediction, df, cats, tf) -> None:
        tail = df.tail(60)
        ax.plot(tail.index, tail["Close"], color=COLOR_PRICE, label="Close")

        fib = SupportResistance.fibonacci(df, lookback=126)
        xlim = (tail.index[0], tail.index[-1])
        for label, level in fib.levels.items():
            ax.hlines(level, xlim[0], xlim[1], color="#888", linestyles=":",
                      linewidth=0.8)
            ax.text(xlim[1], level, f" {label} ${level:.2f}",
                    fontsize=7, color="#666", va="center")

        last = df.iloc[-1]
        piv = SupportResistance.pivot_points(
            float(last["High"]), float(last["Low"]), float(last["Close"]),
        )
        pivots = {"PP": piv.pp, "R1": piv.r1, "R2": piv.r2,
                  "S1": piv.s1, "S2": piv.s2}
        for label, lvl in pivots.items():
            color = COLOR_BEAR if label.startswith("R") else \
                    COLOR_BULL if label.startswith("S") else COLOR_WARN
            ax.hlines(lvl, xlim[0], xlim[1], color=color, linestyles="--",
                      linewidth=0.9, alpha=0.7)
            ax.text(xlim[0], lvl, f" {label} ${lvl:.2f}", fontsize=8,
                    color=color, va="center")
        ax.set_title("Support & Resistance (Fib + Pivots)", fontweight="bold")

    def _panel_atr(self, ax, p: Prediction, df, cats, tf) -> None:
        tail = df.tail(126)
        atr_mean = tail["ATR"].rolling(20).mean()
        colors = [COLOR_BEAR if a > m else COLOR_BULL
                  for a, m in zip(tail["ATR"], atr_mean.fillna(tail["ATR"].mean()))]
        ax.plot(tail.index, tail["ATR"], color=COLOR_WARN, linewidth=1.3)
        ax.plot(tail.index, atr_mean, color="black", linestyle="--",
                linewidth=0.8, label="20d mean")
        ax.fill_between(tail.index, tail["ATR"], atr_mean, where=(tail["ATR"] > atr_mean),
                        alpha=0.15, color=COLOR_BEAR)
        ax.fill_between(tail.index, tail["ATR"], atr_mean, where=(tail["ATR"] <= atr_mean),
                        alpha=0.15, color=COLOR_BULL)
        current = float(tail["ATR"].iloc[-1])
        mean = float(atr_mean.iloc[-1]) if not np.isnan(atr_mean.iloc[-1]) else current
        ratio = current / mean if mean else 1.0
        ax.set_title(f"ATR(14) = {current:.2f} ({ratio:.2f}× 20d mean)",
                     fontweight="bold")
        ax.legend(loc="upper left", fontsize=8)

    def _panel_fundamentals(self, ax, p: Prediction, df, cats, tf) -> None:
        fund = p.meta.get("fundamentals") or (
            p.ai_signal.fundamentals if p.ai_signal else {}
        ) or {}
        metrics = [
            ("P/E (TTM)", "trailingPE", "value"),
            ("Forward P/E", "forwardPE", "value"),
            ("P/B", "priceToBook", "value"),
            ("P/S", "priceToSalesTrailing12Months", "value"),
            ("EV/EBITDA", "enterpriseToEbitda", "value"),
            ("PEG", "pegRatio", "value"),
            ("Rev Growth", "revenueGrowth", "pct"),
            ("EPS Growth", "earningsGrowth", "pct"),
            ("Net Margin", "profitMargins", "pct"),
            ("Op Margin", "operatingMargins", "pct"),
            ("ROE", "returnOnEquity", "pct"),
            ("D/E", "debtToEquity", "value"),
            ("Current Ratio", "currentRatio", "value"),
            ("Div Yield", "dividendYield", "pct"),
            ("Short Ratio", "shortRatio", "value"),
        ]
        ax.axis("off")
        cols, rows = 5, 3
        for idx, (label, key, kind) in enumerate(metrics):
            col, row = idx % cols, idx // cols
            x = col / cols
            y = 1.0 - (row + 1) / rows
            val = fund.get(key)
            color, text = self._fund_color(key, val, kind)
            ax.add_patch(mpatches.FancyBboxPatch(
                (x + 0.005, y + 0.02), 1 / cols - 0.015, 1 / rows - 0.04,
                transform=ax.transAxes,
                boxstyle="round,pad=0.01,rounding_size=0.02",
                facecolor=color, alpha=0.55, edgecolor="none",
            ))
            ax.text(x + 0.5 / cols, y + 0.7 / rows, label,
                    transform=ax.transAxes, ha="center", fontsize=9, color="#333")
            ax.text(x + 0.5 / cols, y + 0.35 / rows, text,
                    transform=ax.transAxes, ha="center", fontsize=11,
                    fontweight="bold", color="#111")
        ax.set_title("Fundamentals", fontweight="bold")

    # ----------------------------------------------------- fundamental colour
    @staticmethod
    def _fund_color(key: str, val, kind: str) -> tuple[str, str]:
        if val is None:
            return ("#e0e0e0", "n/a")
        try:
            v = float(val)
        except (TypeError, ValueError):
            return ("#e0e0e0", "n/a")
        text = f"{v*100:.1f}%" if kind == "pct" else f"{v:.2f}"
        # Simple green/amber/red rules.
        good = amber = bad = None
        rules = {
            "trailingPE": (lambda v: 0 < v < 15, lambda v: 15 <= v <= 35, lambda v: v > 35 or v <= 0),
            "forwardPE": (lambda v: 0 < v < 15, lambda v: 15 <= v <= 30, lambda v: v > 30 or v <= 0),
            "priceToBook": (lambda v: 0 < v < 2, lambda v: 2 <= v <= 5, lambda v: v > 5),
            "pegRatio": (lambda v: 0 < v < 1, lambda v: 1 <= v <= 2, lambda v: v > 2 or v <= 0),
            "revenueGrowth": (lambda v: v > 0.10, lambda v: 0 < v <= 0.10, lambda v: v <= 0),
            "earningsGrowth": (lambda v: v > 0.15, lambda v: 0 < v <= 0.15, lambda v: v <= 0),
            "profitMargins": (lambda v: v > 0.15, lambda v: 0 < v <= 0.15, lambda v: v <= 0),
            "operatingMargins": (lambda v: v > 0.15, lambda v: 0 < v <= 0.15, lambda v: v <= 0),
            "returnOnEquity": (lambda v: v > 0.15, lambda v: 0 < v <= 0.15, lambda v: v <= 0),
            "debtToEquity": (lambda v: v < 50, lambda v: 50 <= v <= 200, lambda v: v > 200),
            "currentRatio": (lambda v: v >= 1.5, lambda v: 1.0 <= v < 1.5, lambda v: v < 1.0),
        }
        good, amber, bad = rules.get(key, (None, None, None))
        if good and good(v):
            return (COLOR_BULL, text)
        if bad and bad(v):
            return (COLOR_BEAR, text)
        if amber and amber(v):
            return (COLOR_WARN, text)
        return ("#c0c0c0", text)
