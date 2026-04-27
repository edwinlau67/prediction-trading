"""Trading Control — start/monitor AutoTrader, live metrics via 10s polling."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html, no_update

from dash_ui import api, components, theme

dash.register_page(__name__, path="/trading", name="Trading", order=3)

_INTERVAL = 10_000

layout = dbc.Container(
    [
        dcc.Interval(id="trade-interval", interval=_INTERVAL, n_intervals=0),
        dcc.Store(id="trade-ui-state", storage_type="session", data={"started_here": False}),

        html.H4("Trading Control", className="mt-4 mb-3", style={"color": theme.TEXT}),

        html.Div(id="trade-status-banner", className="mb-3"),
        html.Div(id="trade-kpi-row", className="mb-4"),
        html.Div(id="trade-control-panel"),

        dbc.Alert(
            [html.Strong("Note: "), "Stopping requires restarting the API server. "
             "Run ", html.Code("make api-dev"), " to restart."],
            color="warning", className="mt-3",
        ),

        # Positions and last-cycle panels (always in DOM, populated by poll)
        html.Div(id="trade-positions", className="mt-4"),
        html.Div(id="trade-last-cycle", className="mt-4"),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("trade-status-banner", "children"),
    Output("trade-kpi-row", "children"),
    Output("trade-control-panel", "children"),
    Output("trade-positions", "children"),
    Output("trade-last-cycle", "children"),
    Input("trade-interval", "n_intervals"),
    State("trade-ui-state", "data"),
)
def _poll_trading(n: int, ui_state: dict):
    try:
        status = api.trading_status()
    except Exception as exc:
        banner = dbc.Alert([html.Strong("API Offline — "), str(exc)], color="danger")
        return banner, _empty_kpi_row(), _start_form(), html.Div(), html.Div()

    running = status.get("running", False)
    equity = status.get("equity")
    cash = status.get("cash")
    open_pos = status.get("open_positions", 0)
    tickers = status.get("tickers", [])
    cycle_count = status.get("cycle_count", 0)

    if running:
        banner = dbc.Alert(
            [html.Strong("AutoTrader Running — "),
             f"{len(tickers)} ticker(s): {', '.join(tickers)}  |  Cycles: {cycle_count}"],
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

    positions_div = _build_positions_table(status.get("positions", []))
    cycle_div = _build_last_cycle(status.get("last_cycle"))

    return banner, kpi_row, control, positions_div, cycle_div


def _empty_kpi_row():
    return dbc.Row([
        dbc.Col(components.kpi_card("Portfolio Equity", "—"), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Cash", "—"), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Open Positions", "—"), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Status", "Offline"), md=3, className="mb-3"),
    ], className="g-3")


_TABLE_STYLE_HEADER = {
    "backgroundColor": "#161b22", "color": theme.MUTED,
    "fontWeight": "600", "fontSize": "11px",
    "textTransform": "uppercase", "border": f"1px solid {theme.BORDER}",
}
_TABLE_STYLE_CELL = {
    "backgroundColor": theme.CARD_BG, "color": theme.TEXT,
    "border": f"1px solid {theme.BORDER_LIGHT}",
    "padding": "8px 12px", "fontSize": "13px",
}


def _build_positions_table(positions: list) -> html.Div:
    if not positions:
        return html.Div()
    rows = [{"Ticker": p["ticker"], "Side": str(p["side"]).upper(), "Qty": p["quantity"],
             "Entry": f"${p['entry_price']:.2f}", "Stop": f"${p['stop_loss']:.2f}",
             "Target": f"${p['take_profit']:.2f}"} for p in positions]
    return html.Div([
        html.H6("Open Positions", style={"color": theme.MUTED, "fontSize": "12px",
                                          "textTransform": "uppercase"}),
        dash_table.DataTable(
            data=rows,
            columns=[{"name": c, "id": c} for c in
                     ["Ticker", "Side", "Qty", "Entry", "Stop", "Target"]],
            style_table={"overflowX": "auto"},
            style_header=_TABLE_STYLE_HEADER,
            style_cell=_TABLE_STYLE_CELL,
        ),
    ])


def _build_last_cycle(last_cycle: dict | None) -> html.Div:
    if not last_cycle:
        return html.Div()

    started = last_cycle.get("started_at", "")[:19]
    finished = last_cycle.get("finished_at", "")[:19]
    actions = last_cycle.get("actions", [])
    errors = last_cycle.get("errors", [])

    action_rows = []
    for a in actions:
        conf = a.get("confidence")
        action_rows.append({
            "Ticker": a.get("ticker", ""),
            "Action": str(a.get("action", "")).upper(),
            "Direction": str(a.get("direction") or "—"),
            "Confidence": f"{conf * 100:.1f}%" if conf is not None else "—",
            "Price": f"${a['price']:.2f}" if a.get("price") else "—",
            "Reason": a.get("reason", ""),
        })

    action_table = dash_table.DataTable(
        data=action_rows,
        columns=[{"name": c, "id": c} for c in
                 ["Ticker", "Action", "Direction", "Confidence", "Price", "Reason"]],
        style_table={"overflowX": "auto"},
        style_header=_TABLE_STYLE_HEADER,
        style_cell=_TABLE_STYLE_CELL,
        style_data_conditional=[
            {"if": {"filter_query": '{Action} = "OPEN"', "column_id": "Action"},
             "color": theme.GREEN, "fontWeight": "700"},
            {"if": {"filter_query": '{Action} = "CLOSE"', "column_id": "Action"},
             "color": theme.YELLOW, "fontWeight": "700"},
            {"if": {"filter_query": '{Action} = "ERROR"', "column_id": "Action"},
             "color": theme.RED, "fontWeight": "700"},
        ],
    )

    error_section = html.Div()
    if errors:
        error_section = dbc.Card(dbc.CardBody(
            html.Pre("\n".join(errors), style={"color": theme.RED, "fontSize": "12px", "margin": 0})
        ), className="mt-2")

    return html.Div([
        html.H6(f"Last Cycle  {started} → {finished}",
                style={"color": theme.MUTED, "fontSize": "12px", "textTransform": "uppercase",
                       "marginBottom": "8px"}),
        action_table,
        error_section,
    ])


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
                dbc.Label("Cycle Interval (seconds)", style={"color": theme.MUTED, "fontSize": "12px"}),
                dcc.Slider(
                    id="trade-cycle-interval",
                    min=60, max=3600, step=60, value=300,
                    marks={60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "1h"},
                ),
                dbc.Label("State File Path (optional)", style={"color": theme.MUTED, "fontSize": "12px", "marginTop": "12px"}),
                dbc.Input(id="trade-state-path", type="text",
                          placeholder="results/live/portfolio_state.json"),
                html.Br(),
                dbc.Button("Start AutoTrader", id="trade-start-btn", color="success", n_clicks=0),
                html.Div(id="trade-start-error", className="mt-2"),
            ], md=4),
        ], className="g-3"),
    ]))


def _stop_button():
    return dbc.Card(dbc.CardBody([
        html.P("AutoTrader is running. Use the button below to reset the UI view.",
               style={"color": theme.MUTED}),
        dbc.Button("Reset UI View", id="trade-stop-btn", color="danger", outline=True, n_clicks=0),
    ]))


@callback(
    Output("trade-start-error", "children"),
    Input("trade-start-btn", "n_clicks"),
    State("trade-tickers", "value"),
    State("trade-capital", "value"),
    State("trade-dry-run", "value"),
    State("trade-market-hours", "value"),
    State("trade-cycle-interval", "value"),
    State("trade-state-path", "value"),
    prevent_initial_call=True,
)
def _start_trader(n_clicks, tickers_text, capital, dry_run, market_hours, interval, state_path):
    tickers = [t.strip().upper() for t in (tickers_text or "").splitlines() if t.strip()]
    if not tickers:
        return dbc.Alert("Enter at least one ticker.", color="warning")
    try:
        api.trading_start(
            tickers,
            float(capital or 10_000),
            dry_run=dry_run,
            enforce_market_hours=market_hours,
            interval_seconds=int(interval or 300),
            state_path=state_path or None,
        )
        return dbc.Alert("AutoTrader started. Dashboard will update shortly.", color="success")
    except Exception as exc:
        return dbc.Alert([html.Strong("Failed: "), str(exc)], color="danger")
