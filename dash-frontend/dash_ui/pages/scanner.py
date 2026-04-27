"""Watchlist Scanner — bulk signal scoring with auto-refresh and CSV export."""
from __future__ import annotations

import io

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import Input, Output, State, callback, dcc, html, no_update

from dash_ui import api, components, theme

dash.register_page(__name__, path="/scanner", name="Scanner", order=2)

_DEFAULT_WATCHLIST = "AAPL\nMSFT\nNVDA\nTSLA\nGOOGL\nAMZN\nMETA"
_ALL_CATEGORIES = ["trend", "momentum", "volatility", "volume", "support", "fundamental", "news", "macro", "sector"]

layout = dbc.Container(
    [
        html.H4("Watchlist Scanner", className="mt-4 mb-3", style={"color": theme.TEXT}),

        # Input form
        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Watchlist (one ticker per line)", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Textarea(
                        id="scan-watchlist",
                        value=_DEFAULT_WATCHLIST,
                        style={
                            "width": "100%", "height": "120px",
                            "backgroundColor": "#161b22", "color": theme.TEXT,
                            "border": f"1px solid {theme.BORDER}", "borderRadius": "6px",
                            "padding": "8px", "fontSize": "13px", "fontFamily": "monospace",
                        },
                    ),
                ], md=4),
                dbc.Col([
                    dbc.Label("Min Confidence", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Slider(
                        id="scan-min-conf", min=0, max=1, step=0.05, value=0.0,
                        marks={i / 10: f"{i * 10}%" for i in range(0, 11, 2)},
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                    html.Br(),
                    dbc.Label("Parallel Workers", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="scan-workers", type="number", value=4, min=1, max=16, step=1),
                ], md=4),
                dbc.Col([
                    dbc.Label("Actions", style={"color": theme.MUTED, "fontSize": "12px"}),
                    html.Br(),
                    dbc.Button("Scan Now", id="scan-run-btn", color="success", n_clicks=0, className="me-2"),
                    dbc.Button("Export CSV", id="scan-export-btn", color="secondary", outline=True, n_clicks=0),
                    html.Hr(style={"borderColor": theme.BORDER}),
                    dbc.Switch(id="scan-auto-refresh", label="Auto-refresh (30s)", value=False),
                    dcc.Interval(id="scan-interval", interval=30_000, disabled=True),
                    dcc.Download(id="scan-download"),
                ], md=4),
            ], className="g-3"),
        ]), className="mb-4"),

        # Error area
        html.Div(id="scan-error"),

        # Summary KPIs
        html.Div(id="scan-summary-row", className="mb-3"),

        # Results table
        dcc.Loading(
            children=html.Div(id="scan-table-container"),
            type="default",
        ),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("scan-interval", "disabled"),
    Input("scan-auto-refresh", "value"),
)
def _toggle_interval(enabled: bool) -> bool:
    return not enabled


@callback(
    Output("scan-results-store", "data"),
    Output("scan-error", "children"),
    Output("scan-summary-row", "children"),
    Output("scan-table-container", "children"),
    Input("scan-run-btn", "n_clicks"),
    Input("scan-interval", "n_intervals"),
    State("scan-watchlist", "value"),
    State("scan-min-conf", "value"),
    State("scan-workers", "value"),
    prevent_initial_call=True,
)
def _run_scan(n_clicks, n_intervals, watchlist_text, min_conf, workers):
    tickers = [t.strip().upper() for t in (watchlist_text or "").splitlines() if t.strip()]
    if not tickers:
        return no_update, dbc.Alert("Enter at least one ticker.", color="warning"), no_update, no_update

    try:
        response = api.scan(tickers, min_confidence=min_conf or 0.0, workers=int(workers or 4))
    except Exception as exc:
        err = dbc.Alert([html.Strong("Scan failed: "), str(exc)], color="danger")
        return no_update, err, no_update, no_update

    results = response.get("results", [])
    buys = sum(1 for r in results if r.get("direction") == "bullish")
    sells = sum(1 for r in results if r.get("direction") == "bearish")
    holds = sum(1 for r in results if r.get("direction") == "neutral")

    summary = dbc.Row([
        dbc.Col(components.kpi_card("Total Scanned", str(len(results))), md=3, className="mb-2"),
        dbc.Col(components.kpi_card("BUY Signals", str(buys)), md=3, className="mb-2"),
        dbc.Col(components.kpi_card("SELL Signals", str(sells)), md=3, className="mb-2"),
        dbc.Col(components.kpi_card("HOLD", str(holds)), md=3, className="mb-2"),
    ], className="g-3")

    table = dbc.Card(dbc.CardBody(components.scan_results_table(results)))

    return results, None, summary, table


@callback(
    Output("scan-download", "data"),
    Input("scan-export-btn", "n_clicks"),
    State("scan-results-store", "data"),
    prevent_initial_call=True,
)
def _export_csv(n_clicks, results):
    if not results:
        return no_update
    rows = []
    for r in results:
        direction = r.get("direction", "neutral")
        rows.append({
            "Ticker": r.get("ticker", ""),
            "Direction": theme.DIRECTION_LABELS.get(direction, direction.upper()),
            "Confidence": round(r.get("confidence", 0) * 100, 1),
            "Price": r.get("current_price", 0),
            "Top Factors": " | ".join(r.get("top_factors", [])),
            "Error": r.get("error") or "",
        })
    df = pd.DataFrame(rows)
    return dcc.send_data_frame(df.to_csv, "scan_results.csv", index=False)
