"""Shared UI components for the Streamlit dashboard."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from src.prediction.predictor import Prediction
    from src.trading.portfolio import Trade
except ImportError:
    Prediction = object  # type: ignore[misc,assignment]
    Trade = object       # type: ignore[misc,assignment]

_COLORS = {
    "bullish": "#2ca02c",
    "bearish": "#d62728",
    "neutral": "#7f7f7f",
}

_LABELS = {
    "bullish": "BUY",
    "bearish": "SELL",
    "neutral": "HOLD",
}


def direction_badge(direction: str) -> str:
    color = _COLORS.get(direction, _COLORS["neutral"])
    label = _LABELS.get(direction, "HOLD")
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:4px;font-weight:bold;font-size:0.85em">{label}</span>'
    )


def metric_card(label: str, value: str, delta: str | None = None) -> None:
    st.metric(label=label, value=value, delta=delta)


def confidence_badge(direction: str, confidence: float) -> None:
    color = _COLORS.get(direction, _COLORS["neutral"])
    label = _LABELS.get(direction, "HOLD")
    pct = int(confidence * 100)
    st.markdown(
        f'<div style="margin-bottom:6px">'
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:4px;font-weight:bold">{label}</span> '
        f'<span style="font-size:1.1em;font-weight:bold">{pct}%</span> confidence'
        f"</div>",
        unsafe_allow_html=True,
    )
    st.progress(confidence)


def prediction_card(prediction) -> None:
    """Render a compact card for a single Prediction result."""
    direction = getattr(prediction, "direction", "neutral")
    confidence = getattr(prediction, "confidence", 0.0)
    current_price = getattr(prediction, "current_price", None)
    price_target = getattr(prediction, "price_target", None)
    risk_level = getattr(prediction, "risk_level", "medium")

    confidence_badge(direction, confidence)

    cols = st.columns(3)
    if current_price is not None:
        with cols[0]:
            metric_card("Current Price", f"${current_price:.2f}")
    if price_target is not None:
        change = ((price_target - current_price) / current_price * 100) if current_price else 0
        with cols[1]:
            metric_card("Price Target", f"${price_target:.2f}", f"{change:+.1f}%")
    with cols[2]:
        metric_card("Risk Level", risk_level.title())

    factors = getattr(prediction, "factors", [])
    if factors:
        bull = [f for f in factors if getattr(f, "direction", "") == "bullish"]
        bear = [f for f in factors if getattr(f, "direction", "") == "bearish"]

        if bull or bear:
            col_b, col_s = st.columns(2)
            with col_b:
                if bull:
                    st.markdown("**Bullish Factors**")
                    for f in bull[:5]:
                        detail = getattr(f, "detail", "")
                        label = f"- {f.name}" + (f" — {detail}" if detail else "")
                        st.markdown(f'<span style="color:#2ca02c">{label}</span>',
                                    unsafe_allow_html=True)
            with col_s:
                if bear:
                    st.markdown("**Bearish Factors**")
                    for f in bear[:5]:
                        detail = getattr(f, "detail", "")
                        label = f"- {f.name}" + (f" — {detail}" if detail else "")
                        st.markdown(f'<span style="color:#d62728">{label}</span>',
                                    unsafe_allow_html=True)


def equity_chart(
    equity_curve: list[tuple[datetime, float]],
    initial_capital: float = 0.0,
    title: str = "Equity Curve",
) -> None:
    if not equity_curve:
        st.info("No equity data available.")
        return

    dates = [row[0] for row in equity_curve]
    values = [row[1] for row in equity_curve]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values,
        mode="lines",
        name="Equity",
        line=dict(color="#1f77b4", width=2),
        fill="tozeroy",
        fillcolor="rgba(31,119,180,0.1)",
    ))
    if initial_capital:
        fig.add_hline(
            y=initial_capital,
            line_dash="dash",
            line_color="gray",
            annotation_text="Initial Capital",
        )
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        hovermode="x unified",
        margin=dict(l=0, r=0, t=40, b=0),
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)


def trade_log_table(trades: list) -> None:
    if not trades:
        st.info("No trades recorded.")
        return

    rows = []
    for t in trades:
        rows.append({
            "Ticker": getattr(t, "ticker", ""),
            "Side": getattr(t, "side", ""),
            "Qty": getattr(t, "quantity", 0),
            "Entry": f"${getattr(t, 'entry_price', 0):.2f}",
            "Exit": f"${getattr(t, 'exit_price', 0):.2f}",
            "P&L": f"${getattr(t, 'pnl', 0):+.2f}",
            "Return %": f"{getattr(t, 'return_pct', 0) * 100:+.2f}%",
            "Result": "Win" if getattr(t, "is_win", False) else "Loss",
            "Reason": getattr(t, "reason", ""),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
