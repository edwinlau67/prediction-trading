"""ML Analytics — visualises signal factor data from scan/predict sessions."""
from __future__ import annotations

from collections import Counter

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from dash_ui import theme

dash.register_page(__name__, path="/analytics", name="Analytics", order=4)

layout = dbc.Container(
    [
        dcc.Interval(id="analytics-interval", interval=30_000, n_intervals=0),

        html.H4("ML Signal Analytics", className="mt-4 mb-3", style={"color": theme.TEXT}),

        dbc.Alert(
            "Analytics are computed from scan and prediction results in your current session. "
            "Run a scan on the Scanner page or a prediction on the Predict page to populate the charts.",
            color="info", className="mb-3",
        ),

        # Filters
        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Min Confidence Filter", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Slider(
                        id="analytics-min-conf", min=0, max=1, step=0.05, value=0.0,
                        marks={i / 10: f"{i * 10}%" for i in range(0, 11, 2)},
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                ], md=6),
                dbc.Col([
                    dbc.Label("Direction Filter", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Checklist(
                        id="analytics-dir-filter",
                        options=[
                            {"label": " BUY", "value": "bullish"},
                            {"label": " SELL", "value": "bearish"},
                            {"label": " HOLD", "value": "neutral"},
                        ],
                        value=["bullish", "bearish", "neutral"],
                        inline=True,
                        inputStyle={"marginRight": "4px"},
                        labelStyle={"marginRight": "16px", "color": theme.TEXT},
                    ),
                ], md=6),
            ], className="g-3"),
        ]), className="mb-4"),

        # Charts in tabs
        dbc.Tabs([
            dbc.Tab(
                dcc.Graph(id="analytics-confidence-hist", config={"displayModeBar": False}),
                label="Confidence Distribution", tab_id="conf",
            ),
            dbc.Tab(
                dcc.Graph(id="analytics-direction-pie", config={"displayModeBar": False}),
                label="Direction Breakdown", tab_id="dir",
            ),
            dbc.Tab(
                dcc.Graph(id="analytics-factor-freq", config={"displayModeBar": False}),
                label="Factor Frequency", tab_id="freq",
            ),
            dbc.Tab(
                dcc.Graph(id="analytics-category-heatmap", config={"displayModeBar": False}),
                label="Category Heatmap", tab_id="heat",
            ),
            dbc.Tab(
                dcc.Graph(id="analytics-ticker-scatter", config={"displayModeBar": False}),
                label="Ticker Confidence", tab_id="scatter",
            ),
        ], active_tab="conf", className="mt-2"),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


def _get_filtered(scan_results, predict_result, min_conf, dir_filter):
    items = list(scan_results or [])
    if predict_result and isinstance(predict_result, dict) and predict_result.get("ticker"):
        pr = predict_result
        items.append({
            "ticker": pr.get("ticker"),
            "direction": pr.get("direction", "neutral"),
            "confidence": pr.get("confidence", 0.0),
            "top_factors": [f.get("name", "") for f in pr.get("factors", [])[:5]],
            "factors": pr.get("factors", []),
            "current_price": pr.get("current_price", 0.0),
        })
    return [
        r for r in items
        if r.get("confidence", 0) >= min_conf
        and r.get("direction") in (dir_filter or ["bullish", "bearish", "neutral"])
    ]


@callback(
    Output("analytics-confidence-hist", "figure"),
    Output("analytics-direction-pie", "figure"),
    Output("analytics-factor-freq", "figure"),
    Output("analytics-category-heatmap", "figure"),
    Output("analytics-ticker-scatter", "figure"),
    Input("analytics-interval", "n_intervals"),
    Input("analytics-min-conf", "value"),
    Input("analytics-dir-filter", "value"),
    Input("current-theme-store", "data"),
    State("scan-results-store", "data"),
    State("predict-result-store", "data"),
)
def _update_charts(n, min_conf, dir_filter, current_theme, scan_results, predict_result):
    items = _get_filtered(scan_results, predict_result, min_conf or 0.0, dir_filter)
    layout = theme.get_plotly_layout(current_theme or "dark")

    return (
        _confidence_histogram(items, layout),
        _direction_pie(items, layout),
        _factor_frequency(items, layout),
        _category_heatmap(items, layout),
        _ticker_scatter(items, layout),
    )


def _empty_fig(msg: str, plotly_layout: dict | None = None) -> go.Figure:
    base = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    fig = go.Figure()
    fig.update_layout(
        **base,
        annotations=[dict(text=msg, x=0.5, y=0.5, showarrow=False, font=dict(color=theme.MUTED, size=14))],
    )
    return fig


def _confidence_histogram(items: list, plotly_layout: dict | None = None) -> go.Figure:
    base = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    if not items:
        return _empty_fig("No data. Run a scan or prediction first.", base)

    traces = []
    for direction, label, color in [
        ("bullish", "BUY", theme.GREEN),
        ("bearish", "SELL", theme.RED),
        ("neutral", "HOLD", theme.MUTED),
    ]:
        vals = [r["confidence"] for r in items if r.get("direction") == direction]
        if vals:
            traces.append(go.Histogram(
                x=vals, name=label, nbinsx=20,
                marker_color=color, opacity=0.75,
                hovertemplate=f"{label}: %{{x:.2f}} confidence, count: %{{y}}<extra></extra>",
            ))

    fig = go.Figure(traces)
    layout = dict(base)
    layout.update(
        title="Confidence Distribution by Direction",
        xaxis=dict(**base["xaxis"], title="Confidence Score", range=[0, 1]),
        yaxis=dict(**base["yaxis"], title="Count"),
        barmode="overlay",
        height=380,
    )
    fig.update_layout(**layout)
    return fig


def _direction_pie(items: list, plotly_layout: dict | None = None) -> go.Figure:
    base = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    if not items:
        return _empty_fig("No data. Run a scan or prediction first.", base)

    counts = Counter(r.get("direction", "neutral") for r in items)
    labels = ["BUY", "SELL", "HOLD"]
    values = [counts.get("bullish", 0), counts.get("bearish", 0), counts.get("neutral", 0)]
    colors = [theme.GREEN, theme.RED, theme.MUTED]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors, line=dict(color=theme.BORDER, width=2)),
        hole=0.4,
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    layout = dict(base)
    layout.update(title="Signal Direction Breakdown", height=380)
    fig.update_layout(**layout)
    return fig


_BULLISH_KEYWORDS = {"above", "oversold", "golden", "bullish", "rising", "beat", "strong", "positive", "low", "breakout", "buy"}


def _factor_frequency(items: list, plotly_layout: dict | None = None) -> go.Figure:
    base = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    if not items:
        return _empty_fig("No data. Run a scan or prediction first.", base)

    counter: Counter = Counter()
    for r in items:
        for name in r.get("top_factors", []):
            if name:
                counter[name] += 1

    if not counter:
        return _empty_fig("No factor data available.", base)

    top = counter.most_common(20)
    names = [t[0] for t in top]
    counts = [t[1] for t in top]
    colors = [
        theme.GREEN if any(kw in n.lower() for kw in _BULLISH_KEYWORDS) else theme.RED
        for n in names
    ]

    fig = go.Figure(go.Bar(
        x=counts, y=names, orientation="h",
        marker_color=colors,
        hovertemplate="%{y}: %{x} occurrences<extra></extra>",
    ))
    layout = dict(base)
    layout.update(
        title="Top 20 Most Frequent Factors",
        xaxis=dict(**base["xaxis"], title="Occurrences"),
        yaxis=dict(**base["yaxis"], autorange="reversed"),
        height=max(380, len(names) * 22 + 80),
    )
    fig.update_layout(**layout)
    return fig


_CATEGORIES = ["trend", "momentum", "volatility", "volume", "support", "fundamental", "news", "macro", "sector"]


def _category_heatmap(items: list, plotly_layout: dict | None = None) -> go.Figure:
    base = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    detailed = [r for r in items if r.get("factors")]
    if not detailed:
        return _empty_fig(
            "Category heatmap requires full factor data.\nIndividual predictions (Predict page) include this.\nScan factors shown here if backend returns them.",
            base,
        )

    tickers = [r["ticker"] for r in detailed]
    matrix = []
    for cat in _CATEGORIES:
        row = []
        for r in detailed:
            net = sum(
                (f.get("points", 0) if f.get("direction") == "bullish" else -f.get("points", 0))
                for f in r.get("factors", [])
                if f.get("category") == cat
            )
            row.append(net)
        matrix.append(row)

    is_light = base.get("template") == "plotly_white"
    heatmap_mid = "#e9ecef" if is_light else "#21262d"
    text_color = "#212529" if is_light else theme.TEXT

    fig = go.Figure(go.Heatmap(
        z=matrix,
        x=tickers,
        y=_CATEGORIES,
        colorscale=[[0, theme.RED], [0.5, heatmap_mid], [1, theme.GREEN]],
        zmid=0,
        hovertemplate="Ticker: %{x}<br>Category: %{y}<br>Net Points: %{z}<extra></extra>",
        colorbar=dict(title="Net Points", tickfont=dict(color=text_color)),
    ))
    layout = dict(base)
    layout.update(title="Signal Category Heatmap (Net Points)", height=420)
    fig.update_layout(**layout)
    return fig


def _ticker_scatter(items: list, plotly_layout: dict | None = None) -> go.Figure:
    base = plotly_layout if plotly_layout is not None else theme.PLOTLY_DARK_LAYOUT
    if not items:
        return _empty_fig("No data. Run a scan or prediction first.", base)

    tickers = [r.get("ticker", "") for r in items]
    confidences = [r.get("confidence", 0.0) for r in items]
    directions = [r.get("direction", "neutral") for r in items]
    colors = [theme.DIRECTION_COLORS.get(d, theme.MUTED) for d in directions]
    labels = [theme.DIRECTION_LABELS.get(d, d.upper()) for d in directions]
    sizes = [max(10, c * 40) for c in confidences]

    fig = go.Figure(go.Scatter(
        x=tickers, y=confidences,
        mode="markers+text",
        text=labels,
        textposition="top center",
        marker=dict(color=colors, size=sizes, line=dict(color=theme.BORDER, width=1)),
        hovertemplate="%{x}: %{y:.1%} confidence<extra></extra>",
    ))
    layout = dict(base)
    layout.update(
        title="Ticker Confidence Overview",
        yaxis=dict(**base["yaxis"], title="Confidence", range=[0, 1.1], tickformat=".0%"),
        height=380,
    )
    fig.update_layout(**layout)
    return fig
