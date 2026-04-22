"""Markdown report generator combining backtest results with predictions."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..backtest.backtester import BacktestResult
from ..prediction.predictor import Prediction
from .base import BaseReportWriter


class ReportWriter(BaseReportWriter):
    """Backtest + prediction markdown report writer."""

    RUN_PREFIX = "backtest"

    def new_run_dir(self, ticker: str) -> Path:  # type: ignore[override]
        return super().new_run_dir(ticker)

    # -------------------------------------------------------------- render
    def write(
        self,
        out_dir: Path,
        *,
        result: BacktestResult | None = None,
        prediction: Prediction | None = None,
        chart_paths: dict[str, Path] | None = None,
        title: str = "Prediction & Trading Report",
    ) -> Path:
        out_dir = Path(out_dir)
        lines: list[str] = [
            self.md_heading(1, title),
            "",
            f"_Generated: {self.stamp_iso()}_",
            "",
        ]

        if prediction is not None:
            lines.extend(self._render_prediction(prediction))

        if result is not None:
            lines.extend(self._render_backtest(result))

        if chart_paths:
            lines.append(self.md_heading(2, "Charts"))
            lines.append("")
            for name, path in chart_paths.items():
                rel = self.relpath(path, out_dir)
                lines.append(self.md_heading(3, name.title()))
                lines.append("")
                lines.append(self.md_image(name, rel))
                lines.append("")

        return self._write(out_dir / "report.md", lines)

    # -------------------------------------------------------- sub-sections
    def _render_prediction(self, p: Prediction) -> Iterable[str]:
        rows: list[list[str]] = [
            ["Ticker", f"**{p.ticker}**"],
            ["Direction", f"**{p.direction.upper()}**"],
            ["Confidence", f"**{p.confidence:.1%}**"],
            ["Current Price", f"${p.current_price:,.2f}"],
        ]
        if p.price_target is not None:
            rows.append(["Price Target", f"${p.price_target:,.2f}"])
        if p.target_date:
            rows.append(["Target Date", p.target_date])
        rows.append(["Risk Level", p.risk_level])
        rows.append(["Actionable",
                     "yes" if p.meta.get("actionable") else "no"])

        out = [self.md_heading(2, "Prediction Summary"), ""]
        out.extend(self.md_table(["Field", "Value"], rows))
        out.append("")

        if p.factors:
            out.append(self.md_heading(3, "Key Factors"))
            for f in p.factors:
                label = getattr(f, "label", None) or str(f)
                out.append(f"- {label}")
            out.append("")

        if p.ai_signal and p.ai_signal.narrative:
            out.append(self.md_heading(3, "AI Narrative"))
            out.append(p.ai_signal.narrative)
            out.append("")
        return out

    def _render_backtest(self, r: BacktestResult) -> Iterable[str]:
        s = r.summary()
        rows = [[k.replace("_", " ").title(), str(v)] for k, v in s.items()]
        out = [self.md_heading(2, "Backtest Results"), ""]
        out.extend(self.md_table(["Metric", "Value"], rows))
        out.append("")

        if r.portfolio.closed_trades:
            out.append(self.md_heading(3, "Trade Log"))
            out.append("")
            trade_rows = [
                [str(i), t.side, str(t.quantity),
                 f"${t.entry_price:.2f}", f"${t.exit_price:.2f}",
                 f"${t.pnl:+.2f}", f"{t.return_pct:+.2%}", t.reason]
                for i, t in enumerate(r.portfolio.closed_trades, 1)
            ]
            out.extend(self.md_table(
                ["#", "Side", "Qty", "Entry", "Exit", "P&L", "Return", "Reason"],
                trade_rows,
            ))
            out.append("")
        return out
