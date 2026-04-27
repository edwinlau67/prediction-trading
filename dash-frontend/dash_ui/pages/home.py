"""Live Dashboard — polls /trading/status every 10s."""
from __future__ import annotations

import datetime

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from dash_ui import api, components, theme

dash.register_page(__name__, path="/", name="Dashboard", order=0)

_INTERVAL = 10_000  # ms

layout = dbc.Container(
    [
        dcc.Interval(id="dash-interval", interval=_INTERVAL, n_intervals=0),
        dcc.Store(id="equity-history-store", storage_type="memory", data=[]),

        html.H4("Live Dashboard", className="mt-4 mb-3", style={"color": theme.TEXT}),

        # API status banner
        html.Div(id="dash-api-banner"),

        # KPI cards row
        html.Div(id="dash-kpi-row", className="mb-4"),

        # Equity chart
        dbc.Card(dbc.CardBody([
            dcc.Graph(id="dash-equity-chart", config={"displayModeBar": False}),
        ]), className="mb-4"),

        # Positions + info
        dbc.Row([
            dbc.Col([
                html.H6("Portfolio Status", style={"color": theme.MUTED}),
                html.Div(id="dash-status-detail"),
            ], md=12),
        ]),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("equity-history-store", "data"),
    Output("dash-api-banner", "children"),
    Output("dash-kpi-row", "children"),
    Input("dash-interval", "n_intervals"),
    State("equity-history-store", "data"),
)
def _poll_status(n: int, history: list) -> tuple:
    try:
        status = api.trading_status()
    except Exception as exc:
        banner = dbc.Alert(
            [html.Strong("API Offline — "), f"Cannot reach {api.API_BASE}. Start the API with: make api-dev"],
            color="danger", className="mb-3",
        )
        return history, banner, _empty_kpi_row()

    equity = status.get("equity")
    cash = status.get("cash")
    running = status.get("running", False)
    open_pos = status.get("open_positions", 0)
    tickers = status.get("tickers", [])

    # Accumulate equity history (keep last 360 = 1 h at 10s)
    new_history = list(history or [])
    if equity is not None:
        new_history.append({"ts": datetime.datetime.now().isoformat(), "equity": equity})
    if len(new_history) > 360:
        new_history = new_history[-360:]

    # Banner
    if running:
        banner = dbc.Alert(
            [html.Strong("AutoTrader Running — "), f"{len(tickers)} ticker(s): {', '.join(tickers)}"],
            color="success", className="mb-3",
        )
    else:
        banner = dbc.Alert("AutoTrader is not running. Start it on the Trading page.", color="secondary", className="mb-3")

    # KPI cards
    equity_str = f"${equity:,.2f}" if equity is not None else "—"
    cash_str = f"${cash:,.2f}" if cash is not None else "—"

    delta_equity = None
    delta_positive = None
    if len(new_history) >= 2:
        first = new_history[0]["equity"]
        last = new_history[-1]["equity"]
        diff = last - first
        delta_equity = f"{'+' if diff >= 0 else ''}{diff:,.2f} since session start"
        delta_positive = diff >= 0

    kpi_row = dbc.Row([
        dbc.Col(components.kpi_card("Portfolio Equity", equity_str, delta_equity, delta_positive), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Cash Available", cash_str), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Open Positions", str(open_pos)), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Status", "Live" if running else "Stopped"), md=3, className="mb-3"),
    ], className="g-3")

    return new_history, banner, kpi_row


def _empty_kpi_row():
    return dbc.Row([
        dbc.Col(components.kpi_card("Portfolio Equity", "—"), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Cash Available", "—"), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Open Positions", "—"), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Status", "Offline"), md=3, className="mb-3"),
    ], className="g-3")


@callback(
    Output("dash-equity-chart", "figure"),
    Input("equity-history-store", "data"),
)
def _update_equity_chart(history: list) -> object:
    return components.equity_line_chart(history or [], height=300)


@callback(
    Output("dash-status-detail", "children"),
    Input("dash-interval", "n_intervals"),
)
def _status_detail(n: int) -> object:
    try:
        status = api.trading_status()
    except Exception:
        return html.P("API offline.", style={"color": theme.MUTED})

    tickers = status.get("tickers", [])
    running = status.get("running", False)

    if not running:
        return html.P(
            "No active trading session. Navigate to the Trading page to start the AutoTrader.",
            style={"color": theme.MUTED, "fontSize": "14px"},
        )

    return html.Div([
        html.P(f"Trading {len(tickers)} ticker(s): {', '.join(tickers)}", style={"fontSize": "14px"}),
        html.P(
            "Open positions and trade log details are available on the Trading page.",
            style={"color": theme.MUTED, "fontSize": "12px"},
        ),
    ])
