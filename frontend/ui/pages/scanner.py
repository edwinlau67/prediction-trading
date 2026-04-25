"""Scanner page — parallel watchlist screening."""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from ui.state import SCAN_RESULTS, WATCHLIST_TICKERS

_ALL_CATEGORIES = ["trend", "momentum", "volatility", "volume", "support", "fundamental"]
_LABELS = {"bullish": "BUY", "bearish": "SELL", "neutral": "HOLD"}


def render() -> None:
    st.markdown("## 🔍 Scanner")

    # ── Inputs ────────────────────────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        # Default to saved watchlist
        saved = st.session_state.get(WATCHLIST_TICKERS, [])
        default_wl = "\n".join(saved) if saved else "AAPL\nMSFT\nNVDA\nTSLA\nGOOGL\nAMZN\nMETA"
        raw = st.text_area(
            "Watchlist (one ticker per line)",
            value=default_wl,
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

    if st.button("▶ Scan Watchlist", type="primary", disabled=not tickers):
        with st.spinner(f"Scanning {len(tickers)} tickers in parallel..."):
            _run_scan(tickers, min_conf, categories, workers)

    # ── Results ───────────────────────────────────────────────────────────────
    results = st.session_state.get(SCAN_RESULTS)
    if results is not None:
        _show_results(results)


def _run_scan(tickers, min_conf, categories, workers) -> None:
    try:
        from prediction_trading.scanner import WatchlistScanner

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

    buys = sum(1 for r in results if getattr(r, "direction", "") == "bullish")
    sells = sum(1 for r in results if getattr(r, "direction", "") == "bearish")
    holds = len(results) - buys - sells

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="pt-card"><div class="pt-card-label">Total Scanned</div>'
            f'<div class="pt-card-value">{len(results)}</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="pt-card" style="border-left:3px solid #00d25b">'
            f'<div class="pt-card-label">BUY Signals</div>'
            f'<div class="pt-card-value" style="color:#00d25b">{buys}</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="pt-card" style="border-left:3px solid #ff4b4b">'
            f'<div class="pt-card-label">SELL Signals</div>'
            f'<div class="pt-card-value" style="color:#ff4b4b">{sells}</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f'<div class="pt-card"><div class="pt-card-label">HOLD / Neutral</div>'
            f'<div class="pt-card-value" style="color:#8b949e">{holds}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown(f"#### Results ({len(results)} tickers)")
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

    def _style_signal(val: str):
        colors = {"BUY": "#00d25b", "SELL": "#ff4b4b", "HOLD": "#8b949e"}
        c = colors.get(val, "#8b949e")
        bg = {"BUY": "rgba(0,210,91,0.15)", "SELL": "rgba(255,75,75,0.15)"}.get(val, "transparent")
        return f"color: {c}; background-color: {bg}; font-weight: 600;"

    styled = df.style.applymap(_style_signal, subset=["Signal"])  # type: ignore[arg-type]
    styled = styled.format({"Confidence": "{:.1%}"})
    st.dataframe(styled, use_container_width=True, hide_index=True)

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(
        "⬇ Export CSV",
        csv_buf.getvalue().encode(),
        "scan_results.csv",
        "text/csv",
    )
