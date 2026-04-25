"""Shared UI components for the Streamlit dashboard."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from prediction_trading.prediction.predictor import Prediction
    from prediction_trading.trading.portfolio import Trade
except ImportError:
    Prediction = object  # type: ignore[misc,assignment]
    Trade = object       # type: ignore[misc,assignment]

# Dark broker color palette
_COLORS = {
    "bullish": "#00d25b",
    "bearish": "#ff4b4b",
    "neutral": "#8b949e",
}

_LABELS = {
    "bullish": "BUY",
    "bearish": "SELL",
    "neutral": "HOLD",
}

# Plotly dark chart template
_CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    font=dict(color="#c9d1d9", family="-apple-system, BlinkMacSystemFont, sans-serif"),
    xaxis=dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False),
    yaxis=dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False),
    margin=dict(l=0, r=0, t=36, b=0),
    hovermode="x unified",
)


def direction_badge(direction: str) -> str:
    cls = {"bullish": "badge-buy", "bearish": "badge-sell"}.get(direction, "badge-hold")
    label = _LABELS.get(direction, "HOLD")
    return f'<span class="{cls}">{label}</span>'


def metric_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_color: str = "auto",
) -> None:
    """Dark-themed metric card rendered as HTML."""
    if delta is not None:
        if delta_color == "auto":
            # Infer color from leading sign or prefix
            stripped = delta.lstrip("$+- ")
            if delta.lstrip(" ").startswith("+") or delta.lstrip(" ").startswith("▲"):
                cls = "pt-card-delta-pos"
            elif delta.lstrip(" ").startswith("-") or delta.lstrip(" ").startswith("▼"):
                cls = "pt-card-delta-neg"
            else:
                cls = "pt-card-delta-neutral"
        else:
            cls = {
                "positive": "pt-card-delta-pos",
                "negative": "pt-card-delta-neg",
                "neutral": "pt-card-delta-neutral",
            }.get(delta_color, "pt-card-delta-neutral")
        delta_html = f'<div class="{cls}">{delta}</div>'
    else:
        delta_html = ""

    st.markdown(
        f'<div class="pt-card">'
        f'<div class="pt-card-label">{label}</div>'
        f'<div class="pt-card-value">{value}</div>'
        f"{delta_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def confidence_badge(direction: str, confidence: float) -> None:
    color = _COLORS.get(direction, _COLORS["neutral"])
    label = _LABELS.get(direction, "HOLD")
    pct = int(confidence * 100)
    st.markdown(
        f'<div style="margin-bottom:8px">'
        f'<span class="{"badge-buy" if direction=="bullish" else "badge-sell" if direction=="bearish" else "badge-hold"}">'
        f'{label}</span> '
        f'<span style="font-size:1.4rem;font-weight:700;color:{color}">{pct}%</span>'
        f'<span style="color:#8b949e;font-size:0.85rem"> confidence</span>'
        f"</div>",
        unsafe_allow_html=True,
    )
    st.progress(confidence)


def prediction_card(prediction) -> None:
    """Render a compact dark card for a single Prediction result."""
    direction = getattr(prediction, "direction", "neutral")
    confidence = getattr(prediction, "confidence", 0.0)
    current_price = getattr(prediction, "current_price", None)
    price_target = getattr(prediction, "price_target", None)
    risk_level = getattr(prediction, "risk_level", "medium")
    color = _COLORS.get(direction, _COLORS["neutral"])
    badge_cls = {"bullish": "badge-buy", "bearish": "badge-sell"}.get(direction, "badge-hold")
    label = _LABELS.get(direction, "HOLD")
    pct = int(confidence * 100)

    st.markdown(
        f'<div class="pt-card" style="border-left:3px solid {color}">'
        f'<span class="{badge_cls}">{label}</span>'
        f'&nbsp;&nbsp;<span style="font-size:1.6rem;font-weight:800;color:{color}">{pct}%</span>'
        f'<span style="color:#8b949e;font-size:0.9rem"> confidence</span>'
        f"</div>",
        unsafe_allow_html=True,
    )
    st.progress(confidence)

    col1, col2, col3 = st.columns(3)
    if current_price is not None:
        with col1:
            metric_card("Current Price", f"${current_price:.2f}")
    if price_target is not None:
        change = ((price_target - current_price) / current_price * 100) if current_price else 0
        sign = "+" if change >= 0 else ""
        with col2:
            metric_card("Price Target", f"${price_target:.2f}", f"{sign}{change:.1f}%")
    with col3:
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
                        label_txt = f"▲ {f.name}" + (f" — {detail}" if detail else "")
                        st.markdown(
                            f'<div style="color:#00d25b;font-size:0.85rem;padding:2px 0">{label_txt}</div>',
                            unsafe_allow_html=True,
                        )
            with col_s:
                if bear:
                    st.markdown("**Bearish Factors**")
                    for f in bear[:5]:
                        detail = getattr(f, "detail", "")
                        label_txt = f"▼ {f.name}" + (f" — {detail}" if detail else "")
                        st.markdown(
                            f'<div style="color:#ff4b4b;font-size:0.85rem;padding:2px 0">{label_txt}</div>',
                            unsafe_allow_html=True,
                        )


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
    is_positive = values[-1] >= initial_capital if initial_capital else True
    line_color = "#00d25b" if is_positive else "#ff4b4b"
    fill_color = "rgba(0,210,91,0.1)" if is_positive else "rgba(255,75,75,0.1)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=values,
        mode="lines",
        name="Equity",
        line=dict(color=line_color, width=2),
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate="$%{y:,.2f}<extra></extra>",
    ))
    if initial_capital:
        fig.add_hline(
            y=initial_capital,
            line_dash="dash",
            line_color="#30363d",
            annotation_text="Initial",
            annotation_font_color="#8b949e",
        )
    layout = dict(**_CHART_LAYOUT)
    layout.update(
        title=dict(text=title, font=dict(size=13, color="#8b949e")),
        yaxis=dict(tickprefix="$", **_CHART_LAYOUT["yaxis"]),
        height=300,
    )
    fig.update_layout(**layout)
    st.plotly_chart(fig, use_container_width=True)


def candlestick_chart(
    ohlcv: pd.DataFrame,
    title: str = "Price",
    *,
    height: int = 420,
    entry_price: float | None = None,
    stop_price: float | None = None,
    target_price: float | None = None,
    buy_signals: list | None = None,
    sell_signals: list | None = None,
    show_volume: bool = True,
) -> None:
    """Full Plotly candlestick + volume chart in dark theme."""
    if ohlcv is None or ohlcv.empty:
        st.info("No price data available.")
        return

    tail = ohlcv.tail(120)

    rows = 2 if show_volume else 1
    row_heights = [0.75, 0.25] if show_volume else [1.0]
    from plotly.subplots import make_subplots
    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True,
        row_heights=row_heights, vertical_spacing=0.03,
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=tail.index,
        open=tail["Open"], high=tail["High"],
        low=tail["Low"], close=tail["Close"],
        increasing=dict(line=dict(color="#00d25b"), fillcolor="#00d25b"),
        decreasing=dict(line=dict(color="#ff4b4b"), fillcolor="#ff4b4b"),
        name="Price",
        showlegend=False,
    ), row=1, col=1)

    # SMA overlays
    for col_name, color, label in [
        ("SMA20", "#f0b429", "SMA20"),
        ("SMA50", "#58a6ff", "SMA50"),
    ]:
        if col_name in tail.columns:
            fig.add_trace(go.Scatter(
                x=tail.index, y=tail[col_name],
                mode="lines", line=dict(color=color, width=1.2),
                name=label, opacity=0.8,
            ), row=1, col=1)

    # Entry / stop / target lines
    if entry_price:
        fig.add_hline(y=entry_price, line_color="#58a6ff", line_dash="dot",
                      annotation_text=f"Entry ${entry_price:.2f}",
                      annotation_font_color="#58a6ff", row=1, col=1)
    if stop_price:
        fig.add_hline(y=stop_price, line_color="#ff4b4b", line_dash="dash",
                      annotation_text=f"Stop ${stop_price:.2f}",
                      annotation_font_color="#ff4b4b", row=1, col=1)
    if target_price:
        fig.add_hline(y=target_price, line_color="#00d25b", line_dash="dash",
                      annotation_text=f"Target ${target_price:.2f}",
                      annotation_font_color="#00d25b", row=1, col=1)

    # Buy/sell markers
    if buy_signals:
        dates_b, prices_b = zip(*buy_signals)
        fig.add_trace(go.Scatter(
            x=list(dates_b), y=list(prices_b),
            mode="markers",
            marker=dict(symbol="triangle-up", size=10, color="#00d25b"),
            name="Buy", showlegend=True,
        ), row=1, col=1)
    if sell_signals:
        dates_s, prices_s = zip(*sell_signals)
        fig.add_trace(go.Scatter(
            x=list(dates_s), y=list(prices_s),
            mode="markers",
            marker=dict(symbol="triangle-down", size=10, color="#ff4b4b"),
            name="Sell", showlegend=True,
        ), row=1, col=1)

    # Volume bars
    if show_volume and "Volume" in tail.columns:
        vol_colors = [
            "#00d25b" if c >= o else "#ff4b4b"
            for c, o in zip(tail["Close"], tail["Open"])
        ]
        fig.add_trace(go.Bar(
            x=tail.index, y=tail["Volume"],
            marker_color=vol_colors, name="Volume",
            showlegend=False, opacity=0.7,
        ), row=2, col=1)

    layout = dict(**_CHART_LAYOUT)
    layout.update(
        title=dict(text=title, font=dict(size=13, color="#8b949e")),
        height=height,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02, x=0, font=dict(size=11)),
    )
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor="#21262d", linecolor="#30363d")
    fig.update_yaxes(gridcolor="#21262d", linecolor="#30363d")
    st.plotly_chart(fig, use_container_width=True)


def trade_log_table(trades: list) -> None:
    if not trades:
        st.info("No trades recorded.")
        return

    rows = []
    for t in trades:
        pnl = getattr(t, "pnl", 0)
        rows.append({
            "Ticker": getattr(t, "ticker", ""),
            "Side": getattr(t, "side", "").upper(),
            "Qty": getattr(t, "quantity", 0),
            "Entry": f"${getattr(t, 'entry_price', 0):.2f}",
            "Exit": f"${getattr(t, 'exit_price', 0):.2f}",
            "P&L": f"${pnl:+.2f}",
            "Return %": f"{getattr(t, 'return_pct', 0) * 100:+.2f}%",
            "Result": "✅ Win" if getattr(t, "is_win", False) else "❌ Loss",
            "Reason": getattr(t, "reason", ""),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
