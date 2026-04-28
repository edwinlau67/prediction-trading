"""Reusable Dash component factories."""
from __future__ import annotations

import plotly.graph_objects as go
from dash import dash_table, html
import dash_bootstrap_components as dbc

from dash_ui import theme


def status_bar(config_data: dict | None, api_online: bool) -> dbc.Container:
    """Compact status bar shown between navbar and page content on every page."""
    _label_style = {
        "fontSize": "10px", "textTransform": "uppercase",
        "letterSpacing": "0.5px", "color": "var(--theme-muted)", "marginRight": "4px",
    }
    _badge_style = {"fontSize": "11px"}
    _bar_style = {
        "backgroundColor": "var(--theme-card-bg)",
        "borderBottom": "1px solid var(--theme-border)",
        "padding": "5px 24px",
    }

    if not api_online or not config_data:
        return dbc.Container(
            dbc.Row([
                dbc.Col(
                    dbc.Badge(
                        [html.I(className="bi bi-exclamation-triangle-fill me-1"), "API Offline"],
                        color="danger", style=_badge_style,
                    ),
                    width="auto",
                ),
            ], className="align-items-center g-1"),
            fluid=True, style=_bar_style,
        )

    data_cfg   = config_data.get("data", {})
    ai_cfg     = config_data.get("ai", {})
    broker_cfg = config_data.get("broker", {})
    trader_cfg = config_data.get("trader", {})

    data_source   = data_cfg.get("source", "yfinance")
    data_interval = data_cfg.get("interval", "1d")
    ai_enabled    = ai_cfg.get("enabled", False)
    ai_model      = ai_cfg.get("model", "—")
    model_label   = ai_model if ai_enabled else "Rule-based"
    broker_type   = broker_cfg.get("type", "paper")
    paper_trading = broker_cfg.get("paper_trading", True)
    broker_label  = "Paper" if (broker_type == "paper" or paper_trading) else "Alpaca"
    broker_color  = "secondary" if broker_label == "Paper" else "warning"
    dry_run       = trader_cfg.get("dry_run", True)
    live_dot_color = "#6c757d" if dry_run else "#26d96a"

    def _item(label: str, badge_content, color: str) -> dbc.Col:
        return dbc.Col(
            html.Span([
                html.Span(label, style=_label_style),
                dbc.Badge(badge_content, color=color, style=_badge_style, className="me-3"),
            ]),
            width="auto",
        )

    cols = [
        _item("Data", data_source, "primary"),
        _item("Feed", data_interval, "info"),
        _item("Model", model_label, "success" if ai_enabled else "secondary"),
        dbc.Col(
            html.Span([
                html.Span("Broker", style=_label_style),
                dbc.Badge(
                    [html.Span("● ", style={"color": live_dot_color, "fontSize": "9px"}), broker_label],
                    color=broker_color, style=_badge_style,
                ),
            ]),
            width="auto",
        ),
    ]

    return dbc.Container(
        dbc.Row(cols, className="align-items-center g-1"),
        fluid=True, style=_bar_style,
    )


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


def factor_bar_chart(factors: list[dict], height: int = 380, plotly_layout: dict | None = None) -> go.Figure:
    base_layout = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    if not factors:
        fig = go.Figure()
        fig.update_layout(**base_layout, height=height, title="No factors available")
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
    layout = dict(base_layout)
    layout.update(
        height=height,
        title="Signal Factors",
        xaxis=dict(**base_layout["xaxis"], title="Points (+ bullish / − bearish)"),
        yaxis=dict(**base_layout["yaxis"], autorange="reversed"),
    )
    fig.update_layout(**layout)
    return fig


def confidence_gauge(direction: str, confidence: float, height: int = 220, plotly_layout: dict | None = None) -> go.Figure:
    base_layout = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    color = theme.DIRECTION_COLORS.get(direction, theme.MUTED)
    label = theme.DIRECTION_LABELS.get(direction, direction.upper())
    pct = round(confidence * 100, 1)
    is_light = base_layout.get("template") == "plotly_white"
    gauge_bg = "#e9ecef" if is_light else "#21262d"
    step_lo   = "#f8d7da" if is_light else "#3a1a1a"
    step_mid  = "#e9ecef" if is_light else "#21262d"
    step_hi   = "#d1e7dd" if is_light else "#0d3a1f"
    num_color = "#212529" if is_light else theme.TEXT

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={"suffix": "%", "font": {"size": 28, "color": num_color}},
        title={"text": label, "font": {"size": 16, "color": color}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": theme.MUTED},
            "bar": {"color": color},
            "bgcolor": gauge_bg,
            "bordercolor": theme.BORDER,
            "threshold": {
                "line": {"color": theme.YELLOW, "width": 2},
                "thickness": 0.75,
                "value": 40,
            },
            "steps": [
                {"range": [0, 40], "color": step_lo},
                {"range": [40, 60], "color": step_mid},
                {"range": [60, 100], "color": step_hi},
            ],
        },
    ))
    layout = dict(base_layout)
    layout.update(height=height, margin=dict(l=20, r=20, t=60, b=20))
    fig.update_layout(**layout)
    return fig


def equity_line_chart(equity_points: list[dict], height: int = 300, initial_capital: float | None = None, plotly_layout: dict | None = None) -> go.Figure:
    base_layout = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    if not equity_points:
        fig = go.Figure()
        fig.update_layout(**base_layout, height=height, title="No equity data yet")
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
    layout = dict(base_layout)
    layout.update(height=height, title="Equity Curve", yaxis=dict(**base_layout["yaxis"], tickprefix="$"))
    fig.update_layout(**layout)
    return fig


def candlestick_chart(
    ohlcv: list[dict],
    height: int = 420,
    entry: float | None = None,
    stop: float | None = None,
    target: float | None = None,
    plotly_layout: dict | None = None,
) -> go.Figure:
    base_layout = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    if not ohlcv:
        fig = go.Figure()
        fig.update_layout(**base_layout, height=height)
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

    layout = dict(base_layout)
    layout.update(height=height, showlegend=False, xaxis_rangeslider_visible=False)
    fig.update_layout(**layout)
    fig.update_yaxes(tickprefix="$", row=1, col=1)
    return fig


def analysis_chart(
    ohlcv: list[dict],
    indicators: dict,
    levels: dict,
    timing: dict | None = None,
    height: int = 1200,
    plotly_layout: dict | None = None,
) -> go.Figure:
    from plotly.subplots import make_subplots
    base_layout = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT

    if not ohlcv:
        fig = go.Figure()
        fig.update_layout(**base_layout, height=height)
        return fig

    dates = [r["date"] for r in ohlcv]
    opens = [r["open"] for r in ohlcv]
    highs = [r["high"] for r in ohlcv]
    lows = [r["low"] for r in ohlcv]
    closes = [r["close"] for r in ohlcv]
    vols = [r.get("volume", 0) for r in ohlcv]

    fig = make_subplots(
        rows=7, cols=1,
        shared_xaxes=True,
        row_heights=[3, 1, 1.5, 1, 1, 1, 1],
        vertical_spacing=0.012,
        subplot_titles=("", "Volume", "MACD", "RSI", "Stochastic", "OBV", "ATR"),
    )

    # ── Row 1: Candlestick ─────────────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=dates, open=opens, high=highs, low=lows, close=closes,
        increasing_line_color=theme.GREEN, decreasing_line_color=theme.RED,
        name="OHLC", showlegend=False,
    ), row=1, col=1)

    # Bollinger Bands (fill between upper/lower)
    bb_upper = indicators.get("bb_upper", [])
    bb_lower = indicators.get("bb_lower", [])
    bb_mid = indicators.get("bb_mid", [])
    if any(v is not None for v in bb_upper):
        fig.add_trace(go.Scatter(
            x=dates, y=bb_upper,
            line=dict(color="rgba(88,166,255,0.35)", width=1),
            name="BB Upper", showlegend=False, hoverinfo="skip",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=bb_lower,
            line=dict(color="rgba(88,166,255,0.35)", width=1),
            fill="tonexty", fillcolor="rgba(88,166,255,0.06)",
            name="BB Lower", showlegend=False, hoverinfo="skip",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=bb_mid,
            line=dict(color="rgba(88,166,255,0.5)", width=1, dash="dot"),
            name="BB Mid", showlegend=False, hoverinfo="skip",
        ), row=1, col=1)

    # Moving averages
    for key, label, color, width in [
        ("sma20", "SMA20", theme.YELLOW, 1),
        ("sma50", "SMA50", theme.PURPLE, 1.2),
        ("sma200", "SMA200", theme.RED, 1.5),
        ("ema20", "EMA20", "#ff9f40", 1),
    ]:
        vals = indicators.get(key, [])
        if any(v is not None for v in vals):
            fig.add_trace(go.Scatter(
                x=dates, y=vals, line=dict(color=color, width=width),
                name=label, showlegend=False,
                hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>",
            ), row=1, col=1)

    # Fibonacci levels
    _fib_colors = [
        ("0.0%",   "rgba(255,100,100,0.55)"),
        ("23.6%",  "rgba(255,165,0,0.55)"),
        ("38.2%",  "rgba(240,200,40,0.55)"),
        ("50.0%",  "rgba(150,150,255,0.55)"),
        ("61.8%",  "rgba(40,200,100,0.55)"),
        ("78.6%",  "rgba(100,200,255,0.55)"),
        ("100.0%", "rgba(100,255,200,0.55)"),
    ]
    if levels.get("fibonacci"):
        fib_lvls = levels["fibonacci"].get("levels", {})
        color_map = dict(_fib_colors)
        for lvl_name, lvl_price in fib_lvls.items():
            c = color_map.get(lvl_name, "rgba(200,200,200,0.3)")
            fig.add_hline(
                y=lvl_price, line_dash="dash", line_color=c, line_width=1,
                annotation_text=f"Fib {lvl_name}",
                annotation_font_size=9,
                annotation_position="right",
                row=1, col=1,
            )

    # Pivot levels
    if levels.get("pivots"):
        pvt = levels["pivots"]
        for name, val, color in [
            ("PP", pvt.get("pp"), theme.MUTED),
            ("R1", pvt.get("r1"), "#4dff88"),
            ("R2", pvt.get("r2"), "#26d96a"),
            ("S1", pvt.get("s1"), "#ff9999"),
            ("S2", pvt.get("s2"), theme.RED),
        ]:
            if val:
                fig.add_hline(
                    y=val, line_dash="dot", line_color=color, line_width=1,
                    annotation_text=name, annotation_font_size=9,
                    annotation_position="left",
                    row=1, col=1,
                )

    # Entry / stop / take-profit
    if timing:
        for level, label, color, dash in [
            (timing.get("entry_price"), "Entry", theme.BLUE, "dash"),
            (timing.get("stop_loss"),   "Stop",  theme.RED,  "dot"),
            (timing.get("take_profit"), "Target", theme.GREEN, "dot"),
        ]:
            if level:
                fig.add_hline(
                    y=level, line_dash=dash, line_color=color, line_width=2,
                    annotation_text=f"{label}: ${level:.2f}",
                    annotation_font_size=10,
                    annotation_position="right",
                    row=1, col=1,
                )

    # ── Row 2: Volume ─────────────────────────────────────────────────────────
    vol_colors = [theme.GREEN if c >= o else theme.RED for c, o in zip(closes, opens)]
    fig.add_trace(go.Bar(
        x=dates, y=vols, marker_color=vol_colors, name="Volume",
        opacity=0.7, showlegend=False,
        hovertemplate="Vol: %{y:,.0f}<extra></extra>",
    ), row=2, col=1)
    # Volume spikes
    spikes = indicators.get("volume_spike", [])
    if spikes:
        sdates = [d for d, s in zip(dates, spikes) if s]
        svols  = [v for v, s in zip(vols,  spikes) if s]
        if sdates:
            fig.add_trace(go.Scatter(
                x=sdates, y=svols, mode="markers",
                marker=dict(color=theme.YELLOW, size=9, symbol="star"),
                name="Spike", showlegend=False,
                hovertemplate="Spike: %{y:,.0f}<extra></extra>",
            ), row=2, col=1)

    # ── Row 3: MACD ───────────────────────────────────────────────────────────
    macd      = indicators.get("macd", [])
    macd_sig  = indicators.get("macd_signal", [])
    macd_hist = indicators.get("macd_hist", [])
    if any(v is not None for v in macd):
        hist_colors = [theme.GREEN if (v or 0) >= 0 else theme.RED for v in macd_hist]
        fig.add_trace(go.Bar(
            x=dates, y=macd_hist, marker_color=hist_colors, name="Hist",
            opacity=0.7, showlegend=False,
            hovertemplate="Hist: %{y:.4f}<extra></extra>",
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=macd, line=dict(color=theme.BLUE, width=1.5),
            name="MACD", showlegend=False,
            hovertemplate="MACD: %{y:.4f}<extra></extra>",
        ), row=3, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=macd_sig, line=dict(color=theme.YELLOW, width=1.5),
            name="Signal", showlegend=False,
            hovertemplate="Signal: %{y:.4f}<extra></extra>",
        ), row=3, col=1)
        fig.add_hline(y=0, line_color=theme.MUTED, line_width=0.5, row=3, col=1)

    # ── Row 4: RSI ────────────────────────────────────────────────────────────
    rsi = indicators.get("rsi", [])
    if any(v is not None for v in rsi):
        fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255,100,100,0.08)", line_width=0, row=4, col=1)
        fig.add_hrect(y0=0,  y1=30,  fillcolor="rgba(38,217,106,0.08)",  line_width=0, row=4, col=1)
        fig.add_hline(y=70, line_color=theme.RED,   line_width=0.7, line_dash="dash", row=4, col=1)
        fig.add_hline(y=30, line_color=theme.GREEN, line_width=0.7, line_dash="dash", row=4, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=rsi, line=dict(color=theme.BLUE, width=1.5),
            name="RSI", showlegend=False,
            hovertemplate="RSI: %{y:.1f}<extra></extra>",
        ), row=4, col=1)

    # ── Row 5: Stochastic ─────────────────────────────────────────────────────
    stoch_k = indicators.get("stoch_k", [])
    stoch_d = indicators.get("stoch_d", [])
    if any(v is not None for v in stoch_k):
        fig.add_hrect(y0=80, y1=100, fillcolor="rgba(255,100,100,0.08)", line_width=0, row=5, col=1)
        fig.add_hrect(y0=0,  y1=20,  fillcolor="rgba(38,217,106,0.08)",  line_width=0, row=5, col=1)
        fig.add_hline(y=80, line_color=theme.RED,   line_width=0.7, line_dash="dash", row=5, col=1)
        fig.add_hline(y=20, line_color=theme.GREEN, line_width=0.7, line_dash="dash", row=5, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=stoch_k, line=dict(color=theme.BLUE, width=1.5),
            name="%K", showlegend=False,
            hovertemplate="%%K: %{y:.1f}<extra></extra>",
        ), row=5, col=1)
        fig.add_trace(go.Scatter(
            x=dates, y=stoch_d, line=dict(color=theme.YELLOW, width=1.5),
            name="%D", showlegend=False,
            hovertemplate="%%D: %{y:.1f}<extra></extra>",
        ), row=5, col=1)

    # ── Row 6: OBV ────────────────────────────────────────────────────────────
    obv = indicators.get("obv", [])
    if any(v is not None for v in obv):
        valid = [v for v in obv if v is not None]
        obv_color = theme.GREEN if valid[-1] >= valid[0] else theme.RED
        fig.add_trace(go.Scatter(
            x=dates, y=obv, line=dict(color=obv_color, width=1.5),
            name="OBV", showlegend=False,
            hovertemplate="OBV: %{y:,.0f}<extra></extra>",
        ), row=6, col=1)

    # ── Row 7: ATR ────────────────────────────────────────────────────────────
    atr = indicators.get("atr", [])
    if any(v is not None for v in atr):
        valid_atr = [v for v in atr if v is not None]
        atr_mean = sum(valid_atr) / len(valid_atr) if valid_atr else None
        fig.add_trace(go.Scatter(
            x=dates, y=atr, line=dict(color=theme.PURPLE, width=1.5),
            name="ATR", showlegend=False,
            hovertemplate="ATR: %{y:.4f}<extra></extra>",
        ), row=7, col=1)
        if atr_mean:
            fig.add_hline(
                y=atr_mean, line_color=theme.MUTED, line_dash="dash", line_width=0.7,
                row=7, col=1,
            )

    # ── Layout ────────────────────────────────────────────────────────────────
    lbase = {k: v for k, v in base_layout.items() if k not in ("xaxis", "yaxis")}
    lbase.update(
        height=height,
        hovermode="x unified",
        showlegend=False,
        margin=dict(l=60, r=90, t=30, b=40),
    )
    fig.update_layout(**lbase)
    fig.update_layout(xaxis_rangeslider_visible=False)
    # Global axis styles
    ax_x = {k: v for k, v in base_layout["xaxis"].items() if k != "rangeslider"}
    fig.update_xaxes(**ax_x)
    fig.update_yaxes(**base_layout["yaxis"])
    # Per-row y-axis
    fig.update_yaxes(tickprefix="$", row=1, col=1)
    fig.update_yaxes(range=[0, 100], fixedrange=True, row=4, col=1)
    fig.update_yaxes(range=[0, 100], fixedrange=True, row=5, col=1)
    # Subplot title font
    for ann in fig.layout.annotations:
        ann.font.size = 10
        ann.font.color = theme.MUTED
    return fig


def fundamentals_chart(fundamentals: dict, ticker: str = "", plotly_layout: dict | None = None) -> go.Figure:
    from plotly.subplots import make_subplots
    base_layout = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT

    if not fundamentals:
        fig = go.Figure()
        fig.update_layout(**base_layout, height=380, title="No fundamental data available")
        return fig

    val_items = [
        ("P/E (TTM)",   fundamentals.get("trailingPE"),                   25, 40),
        ("P/E (Fwd)",   fundamentals.get("forwardPE"),                     20, 35),
        ("P/B",         fundamentals.get("priceToBook"),                    3,  6),
        ("P/S",         fundamentals.get("priceToSalesTrailing12Months"),   5, 10),
        ("EV/EBITDA",   fundamentals.get("enterpriseToEbitda"),            15, 25),
        ("PEG",         fundamentals.get("pegRatio"),                       1.5, 3),
        ("D/E",         fundamentals.get("debtToEquity"),                   1,  2),
        ("Short Ratio", fundamentals.get("shortRatio"),                     3,  6),
    ]
    qual_items = [
        ("Rev Growth %",  fundamentals.get("revenueGrowth")),
        ("EPS Growth %",  fundamentals.get("earningsGrowth")),
        ("Profit Margin", fundamentals.get("profitMargins")),
        ("Op. Margin",    fundamentals.get("operatingMargins")),
        ("ROE",           fundamentals.get("returnOnEquity")),
        ("Curr Ratio",    fundamentals.get("currentRatio")),
        ("Div Yield",     fundamentals.get("dividendYield")),
    ]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Valuation Ratios", "Quality Metrics"),
        horizontal_spacing=0.12,
    )

    val_labels, val_values, val_colors = [], [], []
    for label, val, fair, exp in val_items:
        if val is None:
            continue
        val_labels.append(label)
        val_values.append(round(val, 2))
        val_colors.append(
            theme.GREEN if val <= fair else (theme.YELLOW if val <= exp else theme.RED)
        )

    if val_labels:
        fig.add_trace(go.Bar(
            x=val_values, y=val_labels, orientation="h",
            marker_color=val_colors, showlegend=False,
            hovertemplate="%{y}: %{x:.2f}<extra></extra>",
        ), row=1, col=1)

    qual_labels, qual_values, qual_colors = [], [], []
    for label, val in qual_items:
        if val is None:
            continue
        pct = round(val * 100, 2)
        qual_labels.append(label)
        qual_values.append(pct)
        qual_colors.append(theme.GREEN if pct >= 0 else theme.RED)

    if qual_labels:
        fig.add_trace(go.Bar(
            x=qual_values, y=qual_labels, orientation="h",
            marker_color=qual_colors, showlegend=False,
            hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
        ), row=1, col=2)

    fbase = {k: v for k, v in base_layout.items() if k not in ("xaxis", "yaxis")}
    fbase.update(height=380, title=f"{ticker} Fundamentals" if ticker else "Fundamentals")
    fig.update_layout(**fbase)
    fig.update_xaxes(**base_layout["xaxis"])
    fig.update_yaxes(**base_layout["yaxis"])
    fig.update_xaxes(title_text="Ratio", row=1, col=1)
    fig.update_xaxes(title_text="%", row=1, col=2)
    for ann in fig.layout.annotations:
        ann.font.size = 11
        ann.font.color = theme.MUTED
    return fig


def index_performance_chart(indexes: list[dict], plotly_layout: dict | None = None) -> go.Figure:
    base_layout = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    if not indexes:
        fig = go.Figure()
        fig.update_layout(**base_layout, height=320, title="No market data available")
        return fig

    _colors = {
        "SPY": theme.BLUE, "^GSPC": theme.BLUE,
        "QQQ": theme.PURPLE, "^IXIC": theme.PURPLE,
        "DIA": theme.YELLOW, "^DJI": theme.YELLOW,
        "^VIX": theme.RED, "VIX": theme.RED,
        "IWM": "#ff9f40", "^RUT": "#ff9f40",
    }
    periods = ["1D %", "5D %", "30D %"]
    period_keys = ["change_1d_pct", "change_5d_pct", "change_30d_pct"]

    fig = go.Figure()
    for idx in indexes:
        sym = idx.get("symbol", "")
        name = idx.get("name") or sym
        color = _colors.get(sym, theme.MUTED)
        values = [idx.get(k) for k in period_keys]
        fig.add_trace(go.Bar(
            name=name, x=periods, y=values,
            marker_color=color,
            hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:+.2f}}%<extra></extra>",
        ))

    layout = dict(base_layout)
    layout.update(
        height=350,
        title="Index Performance",
        barmode="group",
        yaxis=dict(**base_layout["yaxis"], title="% Change", ticksuffix="%"),
    )
    fig.update_layout(**layout)
    fig.add_hline(y=0, line_color=theme.MUTED, line_width=0.6)
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
