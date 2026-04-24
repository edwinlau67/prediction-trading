"""Scanner page — parallel watchlist screening."""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from ui.components import direction_badge
from ui.state import SCAN_RESULTS

_ALL_CATEGORIES = ["trend", "momentum", "volatility", "volume", "support", "fundamental"]

_DEFAULT_WATCHLIST = "AAPL\nMSFT\nNVDA\nTSLA\nGOOGL\nAMZN\nMETA"


def render() -> None:
    st.title("Scanner")
    st.caption("Screen a watchlist in parallel and rank by signal confidence.")

    # ── Inputs ────────────────────────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        raw = st.text_area(
            "Watchlist (one ticker per line)",
            value=_DEFAULT_WATCHLIST,
            height=160,
        )
    with col2:
        min_conf = st.slider("Min Confidence", 0.0, 1.0, 0.0, 0.05,
                             help="Filter results below this confidence.")
        workers = st.slider("Parallel Workers", 1, 16, 4)
        categories = st.multiselect(
            "Indicator Categories",
            _ALL_CATEGORIES,
            default=_ALL_CATEGORIES,
        )

    tickers = [t.strip().upper() for t in raw.splitlines() if t.strip()]
    st.caption(f"{len(tickers)} tickers in watchlist")

    if st.button("Scan Watchlist", type="primary", disabled=not tickers):
        with st.spinner(f"Scanning {len(tickers)} tickers..."):
            _run_scan(tickers, min_conf, categories, workers)

    # ── Results ───────────────────────────────────────────────────────────────
    results = st.session_state.get(SCAN_RESULTS)
    if results is not None:
        _show_results(results)


def _run_scan(
    tickers: list[str],
    min_conf: float,
    categories: list[str],
    workers: int,
) -> None:
    try:
        from src.scanner import WatchlistScanner

        scanner = WatchlistScanner(
            categories=tuple(categories) if categories else None,
            min_confidence=min_conf,
            workers=workers,
        )
        results = scanner.scan(tickers)
        st.session_state[SCAN_RESULTS] = results
    except Exception as exc:
        st.error(f"Scan failed: {exc}")


def _show_results(results: list) -> None:
    if not results:
        st.info("No results match the confidence filter.")
        return

    st.subheader(f"Results ({len(results)} tickers)")

    rows = []
    for r in results:
        direction = getattr(r, "direction", "neutral")
        confidence = getattr(r, "confidence", 0.0)
        price = getattr(r, "current_price", None)
        top_factors = getattr(r, "top_factors", [])
        error = getattr(r, "error", None)

        rows.append({
            "Ticker": getattr(r, "ticker", ""),
            "Signal": _LABELS.get(direction, "HOLD"),
            "Confidence": confidence,
            "Price": f"${price:.2f}" if price else "—",
            "Top Factors": ", ".join(top_factors[:3]) if top_factors else "—",
            "Error": error or "",
        })

    df = pd.DataFrame(rows)

    # Color-code the Signal column via cell styling
    def _style_signal(val: str):
        colors = {"BUY": "#2ca02c", "SELL": "#d62728", "HOLD": "#7f7f7f"}
        c = colors.get(val, "#7f7f7f")
        return f"color: white; background-color: {c}; border-radius: 4px; padding: 2px 8px;"

    styled = df.style.applymap(_style_signal, subset=["Signal"])  # type: ignore[arg-type]
    styled = styled.format({"Confidence": "{:.1%}"})

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Summary counts
    col1, col2, col3 = st.columns(3)
    with col1:
        buys = sum(1 for r in rows if r["Signal"] == "BUY")
        st.metric("BUY signals", buys)
    with col2:
        sells = sum(1 for r in rows if r["Signal"] == "SELL")
        st.metric("SELL signals", sells)
    with col3:
        holds = sum(1 for r in rows if r["Signal"] == "HOLD")
        st.metric("HOLD / Neutral", holds)

    # CSV export
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(
        "Export CSV",
        csv_buf.getvalue().encode(),
        "scan_results.csv",
        "text/csv",
    )


_LABELS = {"bullish": "BUY", "bearish": "SELL", "neutral": "HOLD"}
