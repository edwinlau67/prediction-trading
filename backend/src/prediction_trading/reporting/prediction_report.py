"""Markdown report writer matching stock-prediction's ``predictions.md`` layout.

Supports a per-run folder with multiple tickers, each rendered as its
own section with embedded chart, pivot table, Fibonacci table, and
narrative.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..indicators.levels import SupportResistance
from ..prediction.predictor import Prediction
from .base import BaseReportWriter


@dataclass
class PredictionReportEntry:
    prediction: Prediction
    timeframe: str
    chart_path: Path
    ohlcv: object   # pd.DataFrame, kept loose to avoid a circular import


class PredictionReportWriter(BaseReportWriter):
    """Writes ``predictions.md`` for one or more tickers into a run folder."""

    RUN_PREFIX = "predict"

    def new_run_dir(self) -> Path:  # type: ignore[override]
        return super().new_run_dir()

    def write(
        self,
        run_dir: Path,
        entries: Iterable[PredictionReportEntry],
        *,
        model: str | None = None,
        categories: Iterable[str] | None = None,
    ) -> Path:
        run_dir = Path(run_dir)
        entries = list(entries)

        header_rows: list[list[str]] = [
            ["Tickers", ", ".join(e.prediction.ticker for e in entries)],
            ["Timeframes", ", ".join(sorted({e.timeframe for e in entries}))],
        ]
        if model:
            header_rows.append(["Model", model])
        if categories:
            header_rows.append(["Indicator categories",
                                ", ".join(sorted(categories))])

        lines: list[str] = [
            self.md_heading(1, "Stock Predictions"),
            "",
            f"_Generated: {self.stamp_iso()}_",
            "",
        ]
        lines.extend(self.md_table(["Setting", "Value"], header_rows))
        lines.append("")
        lines.append("---")
        lines.append("")

        for entry in entries:
            lines.extend(self._render_ticker(entry, run_dir))
            lines.append("---")
            lines.append("")

        return self._write(run_dir / "predictions.md", lines)

    # ---------------------------------------------------- per-ticker section
    def _render_ticker(self, entry: PredictionReportEntry, run_dir: Path
                       ) -> list[str]:
        p = entry.prediction
        out: list[str] = [self.md_heading(2, f"{p.ticker} ({entry.timeframe})"), ""]

        # 📊 Prediction Summary
        out.append(self.md_heading(3, "📊 Prediction Summary"))
        out.append("")
        summary_rows: list[list[str]] = [
            ["Direction", f"**{p.direction.upper()}**"],
            ["Confidence", f"**{p.confidence:.1%}**"],
            ["Current Price", f"${p.current_price:,.2f}"],
        ]
        if p.price_target is not None:
            change = (p.price_target - p.current_price) / p.current_price * 100.0
            summary_rows.append([
                "Price Target", f"${p.price_target:,.2f} ({change:+.2f}%)",
            ])
        if p.target_date:
            summary_rows.append(["Target Date", p.target_date])
        summary_rows.append(["Risk Level", p.risk_level])
        if p.rule_signal:
            summary_rows.append([
                "Net score",
                f"{p.rule_signal.net_points:+d} pts across "
                f"{len(p.rule_signal.factors)} factors",
            ])
        out.extend(self.md_table(["Field", "Value"], summary_rows))
        out.append("")

        # Embedded chart
        rel_chart = self.relpath(entry.chart_path, run_dir)
        out.append(self.md_image(f"{p.ticker} analysis", rel_chart))
        out.append("")

        # 🟢 Key Bullish Factors
        if p.bullish_factors:
            out.append(self.md_heading(3, "🟢 Key Bullish Factors"))
            out.append("")
            for i, f in enumerate(p.bullish_factors[:8], 1):
                out.append(f"{i}. **{f.name}** — {f.detail or f.category}"
                           f" _({f.points:+d} pts)_")
            out.append("")

        # 🔴 Key Risk Factors / Bearish Signals
        if p.bearish_factors:
            out.append(self.md_heading(3, "🔴 Key Risk Factors / Bearish Signals"))
            out.append("")
            for i, f in enumerate(p.bearish_factors[:8], 1):
                out.append(f"{i}. **{f.name}** — {f.detail or f.category}"
                           f" _(-{f.points} pts)_")
            out.append("")

        # 📐 Technical Levels to Watch (pivots)
        last_bar = entry.ohlcv.iloc[-1]
        piv = SupportResistance.pivot_points(
            float(last_bar["High"]), float(last_bar["Low"]),
            float(last_bar["Close"]),
        )
        out.append(self.md_heading(3, "📐 Technical Levels to Watch"))
        out.append("")
        out.extend(self.md_table(["Level", "Price"], [
            ["R2", f"${piv.r2:,.2f}"],
            ["R1", f"${piv.r1:,.2f}"],
            ["**PP**", f"**${piv.pp:,.2f}**"],
            ["S1", f"${piv.s1:,.2f}"],
            ["S2", f"${piv.s2:,.2f}"],
        ]))
        out.append("")

        # 📏 Fibonacci Retracement Levels
        fib = SupportResistance.fibonacci(entry.ohlcv)
        out.append(self.md_heading(3, "📏 Fibonacci Retracement Levels"))
        out.append("")
        out.append(f"_6-month range: ${fib.low:,.2f} → ${fib.high:,.2f}_")
        out.append("")
        out.extend(self.md_table(
            ["Level", "Price"],
            [[label, f"${price:,.2f}"] for label, price in fib.levels.items()],
        ))
        out.append("")

        # ⏱ Timing Recommendation
        if p.timing is not None:
            out.append(self.md_heading(3, "⏱ Timing Recommendation"))
            out.append("")
            out.append(f"**Action:** `{p.timing.action}`")
            out.append("")
            out.append(f"**Rationale:** {p.timing.reason}")
            out.append("")
            timing_rows: list[list[str]] = []
            if p.timing.entry_price is not None:
                timing_rows.append(["Entry Price", f"${p.timing.entry_price:,.2f}"])
            if p.timing.stop_loss is not None:
                timing_rows.append(["Stop Loss", f"${p.timing.stop_loss:,.2f}"])
            if p.timing.take_profit is not None:
                timing_rows.append(["Take Profit", f"${p.timing.take_profit:,.2f}"])
            timing_rows.append(["Time Horizon", p.timing.time_horizon])
            out.extend(self.md_table(["Field", "Value"], timing_rows))
            out.append("")

        # 📝 Analysis
        out.append(self.md_heading(3, "📝 Analysis"))
        out.append("")
        if p.ai_signal and p.ai_signal.narrative:
            out.append(p.ai_signal.narrative)
        else:
            out.append(self._default_narrative(p))
        out.append("")

        return out

    # --------------------------------------------------------- narrative
    @staticmethod
    def _default_narrative(p: Prediction) -> str:
        top_bull = [f.name for f in p.bullish_factors[:3]]
        top_bear = [f.name for f in p.bearish_factors[:3]]
        parts: list[str] = [
            f"The technical model projects a **{p.direction}** stance on "
            f"{p.ticker} with {p.confidence:.0%} confidence over the coming "
            f"{p.meta.get('timeframe', 'window')}."
        ]
        if top_bull:
            parts.append("Bullish support comes from " + ", ".join(top_bull) + ".")
        if top_bear:
            parts.append("Key risks include " + ", ".join(top_bear) + ".")
        if p.price_target is not None:
            delta = (p.price_target - p.current_price) / p.current_price * 100.0
            parts.append(
                f"The projected price target is ${p.price_target:,.2f} "
                f"({delta:+.2f}% from current), assuming the scored signals "
                f"continue to dominate; position sizing should respect the "
                f"{p.risk_level} volatility regime."
            )
        return " ".join(parts)
