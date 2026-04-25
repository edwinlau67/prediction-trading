"""Shared building blocks for the chart + Markdown-report writers.

Both the prediction pipeline (`predict_<stamp>/predictions.md`) and the
backtest pipeline (`backtest_<ticker>_<stamp>/report.md`) live under a
common `results/` root, render PNGs into a `charts/` subdirectory, and
embed them with relative Markdown image links. This module hosts the
pieces they have in common:

* :class:`BaseChart` — matplotlib initialisation + ``_save()`` helper.
* :class:`BaseReportWriter` — run-folder creation, Markdown utilities,
  and relative-path resolution for embedded assets.
* Shared colour constants used by both chart classes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


# ---------------------------------------------------------------- palette
COLOR_BULL = "#2ca02c"
COLOR_BEAR = "#d62728"
COLOR_NEUTRAL = "#7f7f7f"
COLOR_PRICE = "#1f77b4"
COLOR_WARN = "#ff7f0e"
COLOR_ACCENT = "#9467bd"

RISK_COLORS = {
    "low": COLOR_BULL,
    "medium": COLOR_WARN,
    "high": COLOR_BEAR,
}
DIRECTION_COLORS = {
    "bullish": COLOR_BULL,
    "bearish": COLOR_BEAR,
    "neutral": COLOR_NEUTRAL,
}


def direction_color(direction: str) -> str:
    return DIRECTION_COLORS.get(direction, COLOR_NEUTRAL)


# =========================================================================
# Charts
# =========================================================================
class BaseChart:
    """Shared matplotlib configuration and save helper for chart builders."""

    DEFAULT_STYLE = "seaborn-v0_8-whitegrid"

    def __init__(self, style: str | None = None) -> None:
        try:
            plt.style.use(style or self.DEFAULT_STYLE)
        except Exception:
            plt.style.use("default")

    @staticmethod
    def _save(fig, path: str | Path, *, dpi: int = 120,
              bbox_inches: str | None = None) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        kwargs: dict = {"dpi": dpi}
        if bbox_inches is not None:
            kwargs["bbox_inches"] = bbox_inches
        fig.savefig(path, **kwargs)
        plt.close(fig)
        return path


# =========================================================================
# Reports
# =========================================================================
class BaseReportWriter:
    """Shared run-folder + Markdown utilities for report writers.

    Subclasses declare ``RUN_PREFIX`` (e.g. ``"predict"`` or ``"backtest"``)
    and get :meth:`new_run_dir` for free.
    """

    #: Prefix applied to every run folder created by this writer.
    RUN_PREFIX: str = "run"
    #: Name of the chart subdirectory inside each run folder.
    CHARTS_SUBDIR: str = "charts"

    def __init__(self, out_root: str | Path = "results") -> None:
        self.out_root = Path(out_root)

    # ------------------------------------------------------------ folders
    def new_run_dir(self, *parts: str) -> Path:
        """Create and return ``<out_root>/<prefix>[_<parts>]_<stamp>/``.

        Any extra positional arguments are inserted between the prefix and
        the timestamp (e.g. the ticker symbol for backtests). The
        ``charts/`` subdir is created eagerly.
        """
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        middle = "_".join(p for p in parts if p)
        name = f"{self.RUN_PREFIX}_{middle}_{stamp}" if middle \
            else f"{self.RUN_PREFIX}_{stamp}"
        path = self.out_root / name
        (path / self.CHARTS_SUBDIR).mkdir(parents=True, exist_ok=True)
        return path

    def charts_dir(self, run_dir: str | Path) -> Path:
        return Path(run_dir) / self.CHARTS_SUBDIR

    # -------------------------------------------------------- markdown
    @staticmethod
    def relpath(target: str | Path, base: str | Path) -> str:
        """Return a markdown-safe relative path for embedding assets."""
        t = Path(target).resolve()
        b = Path(base).resolve()
        try:
            return str(t.relative_to(b))
        except ValueError:
            return Path(target).name

    @staticmethod
    def md_table(headers: Iterable[str], rows: Iterable[Iterable[str]]
                 ) -> list[str]:
        """Render a simple Markdown table and return its lines."""
        headers = list(headers)
        out = ["| " + " | ".join(headers) + " |",
               "|" + "|".join(["---"] * len(headers)) + "|"]
        for row in rows:
            out.append("| " + " | ".join(str(c) for c in row) + " |")
        return out

    @staticmethod
    def md_heading(level: int, text: str) -> str:
        return f"{'#' * max(1, min(level, 6))} {text}"

    @staticmethod
    def md_image(alt: str, src: str | Path) -> str:
        return f"![{alt}]({src})"

    @staticmethod
    def stamp_iso() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # ------------------------------------------------------- writing
    @staticmethod
    def _write(path: Path, lines: Iterable[str]) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join(lines).rstrip() + "\n"
        path.write_text(text, encoding="utf-8")
        return path
