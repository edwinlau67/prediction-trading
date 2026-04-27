"""Trading Control — start/monitor AutoTrader, live metrics via 10s polling."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html, no_update

from dash_ui import api, components, theme

dash.register_page(__name__, path="/trading", name="Trading", order=3)

_INTERVAL = 10_000

layout = dbc.Container(
    [
        dcc.Interval(id="trade-interval", interval=_INTERVAL, n_intervals=0),
        dcc.Store(id="trade-ui-state", storage_type="session", data={"started_here": False}),

        html.H4("Trading Control", className="mt-4 mb-3", style={"color": theme.TEXT}),

        # Status banner
        html.Div(id="trade-status-banner", className="mb-3"),

        # Live metrics
        html.Div(id="trade-kpi-row", className="mb-4"),

        # Start form + stop button
        html.Div(id="trade-control-panel"),

        # Stop limitation notice (always visible for transparency)
        dbc.Alert(
            [
                html.Strong("Note: "),
                "Stopping the AutoTrader requires restarting the API server. "
                "The Stop button below resets this UI view only. "
                "Run ", html.Code("make api-dev"), " to restart.",
            ],
            color="warning", className="mt-3",
        ),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("trade-status-banner", "children"),
    Output("trade-kpi-row", "children"),
    Output("trade-control-panel", "children"),
    Input("trade-interval", "n_intervals"),
    State("trade-ui-state", "data"),
)
def _poll_trading(n: int, ui_state: dict):
    try:
        status = api.trading_status()
    except Exception as exc:
        banner = dbc.Alert([html.Strong("API Offline — "), str(exc)], color="danger")
        return banner, _empty_kpi_row(), _start_form()

    running = status.get("running", False)
    equity = status.get("equity")
    cash = status.get("cash")
    open_pos = status.get("open_positions", 0)
    tickers = status.get("tickers", [])

    if running:
        banner = dbc.Alert(
            [html.Strong("AutoTrader Running — "), f"{len(tickers)} ticker(s): {', '.join(tickers)}"],
            color="success",
        )
    else:
        banner = dbc.Alert("AutoTrader is stopped.", color="secondary")

    equity_str = f"${equity:,.2f}" if equity is not None else "—"
    cash_str = f"${cash:,.2f}" if cash is not None else "—"
    kpi_row = dbc.Row([
        dbc.Col(components.kpi_card("Portfolio Equity", equity_str), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Cash", cash_str), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Open Positions", str(open_pos)), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Status", "Live" if running else "Stopped"), md=3, className="mb-3"),
    ], className="g-3")

    control = _stop_button() if running else _start_form()
    return banner, kpi_row, control


def _empty_kpi_row():
    return dbc.Row([
        dbc.Col(components.kpi_card("Portfolio Equity", "—"), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Cash", "—"), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Open Positions", "—"), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Status", "Offline"), md=3, className="mb-3"),
    ], className="g-3")


def _start_form():
    return dbc.Card(dbc.CardBody([
        html.H6("Start AutoTrader", style={"color": theme.TEXT, "marginBottom": "16px"}),
        dbc.Row([
            dbc.Col([
                dbc.Label("Tickers (one per line)", style={"color": theme.MUTED, "fontSize": "12px"}),
                dcc.Textarea(
                    id="trade-tickers",
                    value="AAPL\nMSFT\nNVDA",
                    style={
                        "width": "100%", "height": "100px",
                        "backgroundColor": "#161b22", "color": theme.TEXT,
                        "border": f"1px solid {theme.BORDER}", "borderRadius": "6px",
                        "padding": "8px", "fontSize": "13px", "fontFamily": "monospace",
                    },
                ),
            ], md=4),
            dbc.Col([
                dbc.Label("Initial Capital ($)", style={"color": theme.MUTED, "fontSize": "12px"}),
                dbc.Input(id="trade-capital", type="number", value=10_000, min=1_000, step=1_000),
                html.Br(),
                dbc.Switch(id="trade-dry-run", label="Dry Run (paper trading)", value=True),
                dbc.Switch(id="trade-market-hours", label="Enforce Market Hours", value=False),
            ], md=4),
            dbc.Col([
                dbc.Label("Launch", style={"color": theme.MUTED, "fontSize": "12px"}),
                html.Br(),
                dbc.Button("Start AutoTrader", id="trade-start-btn", color="success", n_clicks=0),
                html.Div(id="trade-start-error", className="mt-2"),
            ], md=4),
        ], className="g-3"),
    ]))


def _stop_button():
    return dbc.Card(dbc.CardBody([
        html.P("AutoTrader is currently running. Use the button below to reset the UI view.", style={"color": theme.MUTED}),
        dbc.Button("Reset UI View", id="trade-stop-btn", color="danger", outline=True, n_clicks=0),
    ]))


@callback(
    Output("trade-start-error", "children"),
    Input("trade-start-btn", "n_clicks"),
    State("trade-tickers", "value"),
    State("trade-capital", "value"),
    State("trade-dry-run", "value"),
    State("trade-market-hours", "value"),
    prevent_initial_call=True,
)
def _start_trader(n_clicks, tickers_text, capital, dry_run, market_hours):
    tickers = [t.strip().upper() for t in (tickers_text or "").splitlines() if t.strip()]
    if not tickers:
        return dbc.Alert("Enter at least one ticker.", color="warning")
    try:
        api.trading_start(tickers, float(capital or 10_000), dry_run=dry_run, enforce_market_hours=market_hours)
        return dbc.Alert("AutoTrader started successfully. Dashboard will update shortly.", color="success")
    except Exception as exc:
        return dbc.Alert([html.Strong("Failed: "), str(exc)], color="danger")
