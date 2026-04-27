"""Reusable Dash component factories."""
from __future__ import annotations

import plotly.graph_objects as go
from dash import dash_table, html
import dash_bootstrap_components as dbc

from dash_ui import theme


def kpi_card(title: str, value: str, delta: str | None = None, delta_positive: bool | None = None) -> dbc.Card:
    delta_color = theme.MUTED
    if delta is not None and delta_positive is not None:
        delta_color = theme.GREEN if delta_positive else theme.RED

    children = [
        html.Div(title, className="kpi-label"),
        html.Div(value, className="kpi-value"),
    ]
    if delta is not None:
        children.append(html.Div(delta, className="kpi-delta", style={"color": delta_color}))

    return dbc.Card(dbc.CardBody(children), className="h-100")


def direction_badge(direction: str) -> html.Span:
    label = theme.DIRECTION_LABELS.get(direction, direction.upper())
    color = theme.DIRECTION_COLORS.get(direction, theme.MUTED)
    bg = theme.DIRECTION_BADGE_BG.get(direction, "#2a2a2a")
    return html.Span(
        label,
        className="direction-badge",
        style={"color": color, "backgroundColor": bg, "border": f"1px solid {color}"},
    )


def factor_bar_chart(factors: list[dict], height: int = 380) -> go.Figure:
    if not factors:
        fig = go.Figure()
        fig.update_layout(**theme.PLOTLY_DARK_LAYOUT, height=height, title="No factors available")
        return fig

    sorted_factors = sorted(factors, key=lambda f: abs(f.get("points", 0)), reverse=True)[:15]
    labels = [f"{f['name']} [{f['category']}]" for f in sorted_factors]
    points = [f.get("points", 0) for f in sorted_factors]
    directions = [f.get("direction", "neutral") for f in sorted_factors]
    colors = [theme.DIRECTION_COLORS.get(d, theme.MUTED) for d in directions]
    hover = [f.get("detail", "") for f in sorted_factors]

    fig = go.Figure(go.Bar(
        x=points,
        y=labels,
        orientation="h",
        marker_color=colors,
        hovertext=hover,
        hovertemplate="%{y}<br>Points: %{x}<br>%{hovertext}<extra></extra>",
    ))
    layout = dict(theme.PLOTLY_DARK_LAYOUT)
    layout.update(
        height=height,
        title="Signal Factors",
        xaxis=dict(**theme.PLOTLY_DARK_LAYOUT["xaxis"], title="Points (+ bullish / − bearish)"),
        yaxis=dict(**theme.PLOTLY_DARK_LAYOUT["yaxis"], autorange="reversed"),
    )
    fig.update_layout(**layout)
    return fig


def confidence_gauge(direction: str, confidence: float, height: int = 220) -> go.Figure:
    color = theme.DIRECTION_COLORS.get(direction, theme.MUTED)
    label = theme.DIRECTION_LABELS.get(direction, direction.upper())
    pct = round(confidence * 100, 1)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={"suffix": "%", "font": {"size": 28, "color": theme.TEXT}},
        title={"text": label, "font": {"size": 16, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": theme.MUTED},
            "bar": {"color": color},
            "bgcolor": "#21262d",
            "bordercolor": theme.BORDER,
            "threshold": {
                "line": {"color": theme.YELLOW, "width": 2},
                "thickness": 0.75,
                "value": 40,
            },
            "steps": [
                {"range": [0, 40], "color": "#3a1a1a"},
                {"range": [40, 60], "color": "#21262d"},
                {"range": [60, 100], "color": "#0d3a1f"},
            ],
        },
    ))
    layout = dict(theme.PLOTLY_DARK_LAYOUT)
    layout.update(height=height, margin=dict(l=20, r=20, t=60, b=20))
    fig.update_layout(**layout)
    return fig


def equity_line_chart(equity_points: list[dict], height: int = 300, initial_capital: float | None = None) -> go.Figure:
    if not equity_points:
        fig = go.Figure()
        fig.update_layout(**theme.PLOTLY_DARK_LAYOUT, height=height, title="No equity data yet")
        return fig

    xs = [p["ts"] for p in equity_points]
    ys = [p["equity"] for p in equity_points]
    baseline = initial_capital or ys[0]
    fill_color = theme.GREEN if ys[-1] >= baseline else theme.RED
    line_color = fill_color

    traces = []
    if initial_capital:
        traces.append(go.Scatter(
            x=[xs[0], xs[-1]], y=[initial_capital, initial_capital],
            mode="lines", line=dict(color=theme.MUTED, dash="dash", width=1),
            name="Initial Capital", showlegend=True,
        ))
    traces.append(go.Scatter(
        x=xs, y=ys,
        mode="lines",
        fill="tozeroy",
        fillcolor=f"rgba{tuple(int(fill_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.15,)}",
        line=dict(color=line_color, width=2),
        name="Equity",
        hovertemplate="$%{y:,.2f}<extra></extra>",
    ))

    fig = go.Figure(traces)
    layout = dict(theme.PLOTLY_DARK_LAYOUT)
    layout.update(height=height, title="Equity Curve", yaxis=dict(**theme.PLOTLY_DARK_LAYOUT["yaxis"], tickprefix="$"))
    fig.update_layout(**layout)
    return fig


def candlestick_chart(
    ohlcv: list[dict],
    height: int = 420,
    entry: float | None = None,
    stop: float | None = None,
    target: float | None = None,
) -> go.Figure:
    if not ohlcv:
        fig = go.Figure()
        fig.update_layout(**theme.PLOTLY_DARK_LAYOUT, height=height)
        return fig

    dates = [r["date"] for r in ohlcv]
    opens = [r["open"] for r in ohlcv]
    highs = [r["high"] for r in ohlcv]
    lows = [r["low"] for r in ohlcv]
    closes = [r["close"] for r in ohlcv]
    vols = [r.get("volume", 0) for r in ohlcv]

    from plotly.subplots import make_subplots
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.02)

    fig.add_trace(go.Candlestick(
        x=dates, open=opens, high=highs, low=lows, close=closes,
        increasing_line_color=theme.GREEN, decreasing_line_color=theme.RED,
        name="Price",
    ), row=1, col=1)

    vol_colors = [theme.GREEN if c >= o else theme.RED for c, o in zip(closes, opens)]
    fig.add_trace(go.Bar(x=dates, y=vols, marker_color=vol_colors, name="Volume", opacity=0.6), row=2, col=1)

    for level, label, color, dash in [
        (entry, "Entry", theme.BLUE, "dash"),
        (stop, "Stop", theme.RED, "dot"),
        (target, "Target", theme.GREEN, "dot"),
    ]:
        if level:
            fig.add_hline(y=level, line_dash=dash, line_color=color, annotation_text=f"{label}: ${level:.2f}",
                          annotation_position="right", row=1, col=1)

    layout = dict(theme.PLOTLY_DARK_LAYOUT)
    layout.update(height=height, showlegend=False, xaxis_rangeslider_visible=False)
    fig.update_layout(**layout)
    fig.update_yaxes(tickprefix="$", row=1, col=1)
    return fig


def scan_results_table(results: list[dict]) -> dash_table.DataTable:
    rows = []
    for r in results:
        direction = r.get("direction", "neutral")
        rows.append({
            "Ticker": r.get("ticker", ""),
            "Direction": theme.DIRECTION_LABELS.get(direction, direction.upper()),
            "Confidence": f"{r.get('confidence', 0) * 100:.1f}%",
            "Price": f"${r.get('current_price', 0):.2f}",
            "Top Factors": ", ".join(r.get("top_factors", [])[:3]),
            "Error": r.get("error") or "",
        })

    return dash_table.DataTable(
        data=rows,
        columns=[{"name": c, "id": c} for c in ["Ticker", "Direction", "Confidence", "Price", "Top Factors", "Error"]],
        sort_action="native",
        filter_action="native",
        page_size=20,
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "#161b22",
            "color": theme.MUTED,
            "fontWeight": "600",
            "fontSize": "11px",
            "textTransform": "uppercase",
            "letterSpacing": "0.5px",
            "border": f"1px solid {theme.BORDER}",
        },
        style_cell={
            "backgroundColor": theme.CARD_BG,
            "color": theme.TEXT,
            "border": f"1px solid {theme.BORDER_LIGHT}",
            "padding": "10px 14px",
            "fontSize": "13px",
            "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        },
        style_data_conditional=[
            {
                "if": {"filter_query": '{Direction} = "BUY"', "column_id": "Direction"},
                "color": theme.GREEN, "fontWeight": "700",
            },
            {
                "if": {"filter_query": '{Direction} = "SELL"', "column_id": "Direction"},
                "color": theme.RED, "fontWeight": "700",
            },
            {
                "if": {"filter_query": '{Direction} = "HOLD"', "column_id": "Direction"},
                "color": theme.MUTED, "fontWeight": "700",
            },
            {
                "if": {"filter_query": '{Error} != ""', "column_id": "Error"},
                "color": theme.YELLOW,
            },
        ],
    )
