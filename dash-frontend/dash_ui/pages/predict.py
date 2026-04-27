"""Prediction page — user-triggered via button, results stored cross-page."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update

from dash_ui import api, components, theme

dash.register_page(__name__, path="/predict", name="Predict", order=1)

_ALL_CATEGORIES = ["trend", "momentum", "volatility", "volume", "support", "fundamental", "news", "macro", "sector"]
_TIMEFRAMES = ["1d", "1w", "1m", "3m", "6m", "1y", "2y", "5y"]

layout = dbc.Container(
    [
        html.H4("Stock Prediction", className="mt-4 mb-3", style={"color": theme.TEXT}),

        # Input form
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
                        value="1w",
                        clearable=False,
                    ),
                ], md=2),
                dbc.Col([
                    dbc.Label("Enable AI (Claude)", style={"color": theme.MUTED, "fontSize": "12px"}),
                    html.Br(),
                    dbc.Switch(id="pred-ai-toggle", value=False, label="AI Analysis"),
                ], md=2),
                dbc.Col([
                    dbc.Label("4H Confluence", style={"color": theme.MUTED, "fontSize": "12px"}),
                    html.Br(),
                    dbc.Switch(id="pred-4h-toggle", value=False, label="Enable 4H"),
                ], md=2),
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
                        value=_ALL_CATEGORIES,
                        multi=True,
                    ),
                ], md=12),
            ], className="g-3 mt-1"),
        ]), className="mb-4"),

        # Error area
        html.Div(id="pred-error"),

        # Results
        dcc.Loading(
            id="pred-loading",
            type="default",
            children=html.Div(id="pred-results"),
        ),
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
    prevent_initial_call=True,
)
def _run_prediction(n_clicks, ticker, timeframe, enable_ai, use_4h, categories):
    if not ticker:
        return no_update, dbc.Alert("Please enter a ticker symbol.", color="warning"), no_update

    ticker = ticker.strip().upper()
    try:
        result = api.predict(ticker, timeframe, enable_ai, categories or None, use_4h=use_4h)
    except Exception as exc:
        err = dbc.Alert([html.Strong("Prediction failed: "), str(exc)], color="danger")
        return no_update, err, no_update

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

    price_change_pct = None
    if target and price:
        price_change_pct = (target - price) / price * 100

    signal_tab = dbc.Row([
        dbc.Col([
            dbc.Card(dbc.CardBody([
                html.H5(ticker, style={"color": theme.TEXT, "marginBottom": "12px"}),
                html.Div(components.direction_badge(direction), className="mb-3"),
                html.Div([
                    html.Span("Confidence: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                    html.Span(f"{confidence * 100:.1f}%", style={"color": theme.TEXT, "fontWeight": "600"}),
                ], className="mb-2"),
                html.Div([
                    html.Span("Current Price: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                    html.Span(f"${price:.2f}", style={"color": theme.TEXT, "fontWeight": "600"}),
                ], className="mb-2"),
                *([html.Div([
                    html.Span("Price Target: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                    html.Span(
                        f"${target:.2f} ({'+' if price_change_pct >= 0 else ''}{price_change_pct:.1f}%)",
                        style={"color": theme.GREEN if price_change_pct >= 0 else theme.RED, "fontWeight": "600"},
                    ),
                ], className="mb-2")] if target and price_change_pct is not None else []),
                html.Div([
                    html.Span("Risk Level: ", style={"color": theme.MUTED, "fontSize": "13px"}),
                    html.Span(risk.title(), style={"color": theme.YELLOW, "fontWeight": "600"}),
                ], className="mb-2"),
            ]), className="h-100"),
        ], md=4),
        dbc.Col([
            dcc.Graph(
                figure=components.confidence_gauge(direction, confidence),
                config={"displayModeBar": False},
            ),
        ], md=8),
    ], className="g-3")

    factors_tab = dcc.Graph(
        figure=components.factor_bar_chart(factors),
        config={"displayModeBar": False},
    )

    tabs = [
        dbc.Tab(signal_tab, label="Signal", tab_id="sig"),
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

    return dbc.Tabs(tabs, active_tab="sig", className="mt-2")
