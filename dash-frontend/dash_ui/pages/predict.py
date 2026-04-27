"""Prediction page — user-triggered via button, results stored cross-page."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html, no_update

from dash_ui import api, components, theme

dash.register_page(__name__, path="/predict", name="Predict", order=1)

_ALL_CATEGORIES = ["trend", "momentum", "volatility", "volume", "support", "fundamental", "news", "macro", "sector"]
_TIMEFRAMES = ["1d", "1w", "1m", "3m", "6m", "1y", "2y", "5y"]
_CLAUDE_MODELS = [
    {"label": "claude-sonnet-4-6", "value": "claude-sonnet-4-6"},
    {"label": "claude-opus-4-7", "value": "claude-opus-4-7"},
    {"label": "claude-haiku-4-5-20251001", "value": "claude-haiku-4-5-20251001"},
]

_TIMING_COLORS = {
    "BUY_NOW": theme.GREEN, "BUY_ON_DIP": theme.BLUE, "BUY_ON_BREAKOUT": theme.BLUE,
    "SELL_NOW": theme.RED, "SELL_TRAILING": theme.YELLOW,
    "HOLD": theme.MUTED, "WAIT": theme.MUTED,
}

layout = dbc.Container(
    [
        html.H4("Stock Prediction", className="mt-4 mb-3", style={"color": theme.TEXT}),

        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Ticker Symbol", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="pred-ticker", placeholder="e.g. AAPL", type="text",
                              debounce=False, style={"textTransform": "uppercase"}),
                ], md=2),
                dbc.Col([
                    dbc.Label("Timeframe", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Dropdown(
                        id="pred-timeframe",
                        options=[{"label": t, "value": t} for t in _TIMEFRAMES],
                        value="1w", clearable=False,
                    ),
                ], md=2),
                dbc.Col([
                    dbc.Label("Enable AI (Claude)", style={"color": theme.MUTED, "fontSize": "12px"}),
                    html.Br(),
                    dbc.Switch(id="pred-ai-toggle", value=False, label="AI Analysis"),
                ], md=2),
                dbc.Col([
                    dbc.Label("Claude Model", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Dropdown(id="pred-ai-model", options=_CLAUDE_MODELS,
                                 value="claude-sonnet-4-6", clearable=False),
                ], md=3),
                dbc.Col([
                    dbc.Label("4H Confluence", style={"color": theme.MUTED, "fontSize": "12px"}),
                    html.Br(),
                    dbc.Switch(id="pred-4h-toggle", value=False, label="Enable 4H"),
                ], md=1),
                dbc.Col([
                    dbc.Label("Run", style={"color": theme.MUTED, "fontSize": "12px"}),
                    html.Br(),
                    dbc.Button("Run Prediction", id="pred-run-btn", color="success", n_clicks=0),
                ], md=2),
            ], className="g-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Indicator Categories", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Dropdown(
                        id="pred-categories",
                        options=[{"label": c.title(), "value": c} for c in _ALL_CATEGORIES],
                        value=_ALL_CATEGORIES, multi=True,
                    ),
                ], md=12),
            ], className="g-3 mt-1"),
        ]), className="mb-4"),

        html.Div(id="pred-error"),
        dcc.Loading(id="pred-loading", type="default", children=html.Div(id="pred-results")),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("predict-result-store", "data"),
    Output("pred-error", "children"),
    Output("pred-results", "children"),
    Input("pred-run-btn", "n_clicks"),
    State("pred-ticker", "value"),
    State("pred-timeframe", "value"),
    State("pred-ai-toggle", "value"),
    State("pred-4h-toggle", "value"),
    State("pred-categories", "value"),
    State("pred-ai-model", "value"),
    prevent_initial_call=True,
)
def _run_prediction(n_clicks, ticker, timeframe, enable_ai, use_4h, categories, ai_model):
    if not ticker:
        return no_update, dbc.Alert("Please enter a ticker symbol.", color="warning"), no_update

    ticker = ticker.strip().upper()
    try:
        result = api.predict(ticker, timeframe, enable_ai, categories or None, use_4h=use_4h)
    except Exception as exc:
        err = dbc.Alert([html.Strong("Prediction failed: "), str(exc)], color="danger")
        return no_update, err, no_update

    # Fetch macro context for market index table (non-blocking)
    try:
        macro = api.predict_macro()
        result["macro"] = macro
    except Exception:
        result["macro"] = {}

    results_ui = _build_results(result)
    return result, None, results_ui


def _build_results(result: dict) -> object:
    direction = result.get("direction", "neutral")
    confidence = result.get("confidence", 0.0)
    ticker = result.get("ticker", "")
    price = result.get("current_price", 0.0)
    target = result.get("price_target")
    risk = result.get("risk_level", "medium")
    factors = result.get("factors", [])
    meta = result.get("meta", {})
    narrative = meta.get("ai_narrative") or meta.get("narrative")
    timing = result.get("timing")
    ohlcv = result.get("ohlcv", [])
    macro = result.get("macro", {})

    price_change_pct = None
    if target and price:
        price_change_pct = (target - price) / price * 100

    # Build signal tab content
    signal_content = [
        dbc.Row([
            dbc.Col([
                dbc.Card(dbc.CardBody([
                    html.H5(ticker, style={"color": theme.TEXT, "marginBottom": "12px"}),
                    html.Div(components.direction_badge(direction), className="mb-3"),
                    html.Div([
                        html.Span("Confidence: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                        html.Span(f"{confidence * 100:.1f}%",
                                  style={"color": theme.TEXT, "fontWeight": "600"}),
                    ], className="mb-2"),
                    html.Div([
                        html.Span("Current Price: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                        html.Span(f"${price:.2f}", style={"color": theme.TEXT, "fontWeight": "600"}),
                    ], className="mb-2"),
                    *([html.Div([
                        html.Span("Price Target: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                        html.Span(
                            f"${target:.2f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.1f}%)",
                            style={"color": theme.GREEN if price_change_pct >= 0 else theme.RED,
                                   "fontWeight": "600"},
                        ),
                    ], className="mb-2")] if target and price_change_pct is not None else []),
                    html.Div([
                        html.Span("Risk Level: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                        html.Span(risk.title(), style={"color": theme.YELLOW, "fontWeight": "600"}),
                    ], className="mb-2"),
                ]), className="h-100"),
            ], md=4),
            dbc.Col([
                dcc.Graph(figure=components.confidence_gauge(direction, confidence),
                          config={"displayModeBar": False}),
            ], md=8),
        ], className="g-3"),
    ]

    # Timing Recommendation card
    if timing:
        signal_content.append(_build_timing_card(timing))

    # Market Index Overview table
    indexes = macro.get("indexes", [])
    if indexes:
        signal_content.append(_build_index_table(indexes))

    factors_tab = dcc.Graph(
        figure=components.factor_bar_chart(factors),
        config={"displayModeBar": False},
    )

    tabs = [
        dbc.Tab(html.Div(signal_content), label="Signal", tab_id="sig"),
        dbc.Tab(factors_tab, label=f"Factors ({len(factors)})", tab_id="fac"),
    ]

    if narrative:
        tabs.append(dbc.Tab(
            dbc.Card(dbc.CardBody(html.Pre(
                narrative,
                style={"color": theme.TEXT, "fontSize": "13px", "whiteSpace": "pre-wrap", "margin": 0},
            ))),
            label="AI Narrative", tab_id="ai",
        ))

    if ohlcv:
        entry = timing.get("entry_price") if timing else None
        stop = timing.get("stop_loss") if timing else None
        tp = timing.get("take_profit") if timing else None
        candle_fig = components.candlestick_chart(ohlcv, height=420, entry=entry, stop=stop, target=tp)
        tabs.append(dbc.Tab(
            dcc.Graph(figure=candle_fig, config={"displayModeBar": False}),
            label="Candlestick", tab_id="candle",
        ))

    return dbc.Tabs(tabs, active_tab="sig", className="mt-2")


def _build_timing_card(timing: dict) -> dbc.Card:
    action = timing.get("action", "WAIT")
    reason = timing.get("reason", "")
    entry = timing.get("entry_price")
    stop = timing.get("stop_loss")
    tp = timing.get("take_profit")
    color = _TIMING_COLORS.get(action, theme.MUTED)

    kpis = []
    if entry:
        kpis.append(dbc.Col(components.kpi_card("Entry", f"${entry:.2f}"), md=4))
    if stop:
        kpis.append(dbc.Col(components.kpi_card("Stop Loss", f"${stop:.2f}",
                                                  delta_positive=False), md=4))
    if tp:
        kpis.append(dbc.Col(components.kpi_card("Take Profit", f"${tp:.2f}",
                                                  delta_positive=True), md=4))

    return dbc.Card(dbc.CardBody([
        html.Div([
            html.Span("Timing Recommendation",
                      style={"color": theme.MUTED, "fontSize": "11px",
                             "textTransform": "uppercase", "letterSpacing": "0.6px"}),
            html.Br(),
            html.Span(action, style={"color": color, "fontWeight": "700", "fontSize": "18px"}),
            html.Span(f"  {reason}", style={"color": theme.TEXT, "fontSize": "13px"}),
        ], className="mb-3"),
        dbc.Row(kpis, className="g-3") if kpis else html.Div(),
    ]), style={"borderLeft": f"3px solid {color}"}, className="mt-3 mb-3")


def _build_index_table(indexes: list[dict]) -> html.Div:
    rows = []
    for idx in indexes:
        c1d = idx.get("change_1d_pct")
        c5d = idx.get("change_5d_pct")
        c30d = idx.get("change_30d_pct")
        price = idx.get("price")
        rows.append({
            "Index": idx.get("name") or idx.get("symbol", ""),
            "Price": f"${price:.2f}" if price else "—",
            "1D %": f"{c1d:+.2f}%" if c1d is not None else "—",
            "5D %": f"{c5d:+.2f}%" if c5d is not None else "—",
            "30D %": f"{c30d:+.2f}%" if c30d is not None else "—",
            "Trend": "Above SMA50" if idx.get("above_sma50") else ("Below SMA50" if idx.get("above_sma50") is False else "—"),
        })

    return html.Div([
        html.H6("Market Index Overview",
                style={"color": theme.MUTED, "fontSize": "12px",
                       "textTransform": "uppercase", "letterSpacing": "0.6px", "marginTop": "16px"}),
        dash_table.DataTable(
            data=rows,
            columns=[{"name": c, "id": c} for c in ["Index", "Price", "1D %", "5D %", "30D %", "Trend"]],
            style_table={"overflowX": "auto"},
            style_header={
                "backgroundColor": "#161b22", "color": theme.MUTED,
                "fontWeight": "600", "fontSize": "11px",
                "textTransform": "uppercase", "border": f"1px solid {theme.BORDER}",
            },
            style_cell={
                "backgroundColor": theme.CARD_BG, "color": theme.TEXT,
                "border": f"1px solid {theme.BORDER_LIGHT}",
                "padding": "8px 12px", "fontSize": "13px",
            },
            style_data_conditional=[
                {"if": {"filter_query": '{1D %} contains "+"', "column_id": "1D %"},
                 "color": theme.GREEN},
                {"if": {"filter_query": '{1D %} contains "-"', "column_id": "1D %"},
                 "color": theme.RED},
                {"if": {"filter_query": '{5D %} contains "+"', "column_id": "5D %"},
                 "color": theme.GREEN},
                {"if": {"filter_query": '{5D %} contains "-"', "column_id": "5D %"},
                 "color": theme.RED},
                {"if": {"filter_query": '{30D %} contains "+"', "column_id": "30D %"},
                 "color": theme.GREEN},
                {"if": {"filter_query": '{30D %} contains "-"', "column_id": "30D %"},
                 "color": theme.RED},
            ],
        ),
    ], className="mt-3")
