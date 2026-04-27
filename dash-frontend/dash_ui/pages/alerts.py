"""Alerts page — price/confidence threshold management with localStorage persistence."""
from __future__ import annotations

import datetime

import dash
import dash_bootstrap_components as dbc
import yfinance as yf
from dash import ALL, Input, Output, State, callback, ctx, dcc, html

from dash_ui import theme

dash.register_page(__name__, path="/alerts", name="Alerts", order=6)

_ALERT_TYPES = ["Price above", "Price below", "Confidence ≥", "Daily P&L ≥", "Daily P&L ≤"]

_TYPE_COLORS = {
    "Price above": theme.GREEN, "Confidence ≥": theme.GREEN, "Daily P&L ≥": theme.GREEN,
    "Price below": theme.RED, "Daily P&L ≤": theme.RED,
}

layout = dbc.Container(
    [
        dcc.Store(id="alerts-store", storage_type="local",
                  data={"active": [], "triggered": []}),
        html.H4("Alerts Manager", className="mt-4 mb-3", style={"color": theme.TEXT}),

        dbc.Tabs([
            dbc.Tab(label="Active Alerts", tab_id="active"),
            dbc.Tab(label="Create Alert", tab_id="create"),
            dbc.Tab(label="Triggered Log", tab_id="log"),
        ], id="alerts-tabs", active_tab="active", className="mb-3"),

        html.Div(id="alerts-tab-content"),
        html.Div(id="alerts-create-msg"),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("alerts-tab-content", "children"),
    Input("alerts-tabs", "active_tab"),
    Input("alerts-store", "data"),
)
def _render_tab(active_tab: str, store: dict) -> object:
    store = store or {"active": [], "triggered": []}

    if active_tab == "active":
        return _render_active(store["active"])
    if active_tab == "create":
        return _render_create_form()
    return _render_log(store["triggered"])


def _render_active(alerts: list) -> html.Div:
    if not alerts:
        return html.Div([
            html.P("No active alerts.", style={"color": theme.MUTED, "fontSize": "14px"}),
            dbc.Button("Check Alerts Now", id="check-alerts-btn", color="secondary",
                       size="sm", className="me-2"),
        ])

    cards = []
    for i, alert in enumerate(alerts):
        color = _TYPE_COLORS.get(alert.get("type", ""), theme.MUTED)
        cards.append(dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([
                html.Span(alert.get("ticker", ""), style={"fontWeight": "700", "fontSize": "15px"}),
                html.Span(f"  {alert.get('type', '')}  {alert.get('value', '')}",
                          style={"color": color, "fontSize": "14px", "marginLeft": "8px"}),
                html.Div(f"Created: {alert.get('created', '')[:19]}",
                         style={"color": theme.MUTED, "fontSize": "12px", "marginTop": "4px"}),
            ]),
            dbc.Col(
                dbc.Button("✕", id={"type": "del-alert-btn", "index": i},
                           color="secondary", size="sm", className="float-end"),
                md=1,
            ),
        ])), className="mb-2"))

    return html.Div([
        html.Div(cards),
        html.Div(className="mt-3", children=[
            dbc.Button("Check Alerts Now", id="check-alerts-btn", color="secondary",
                       size="sm", className="me-2"),
            html.Div(id="check-alerts-msg", style={"display": "inline-block", "marginLeft": "8px"}),
        ]),
    ])


def _render_create_form() -> html.Div:
    return html.Div([
        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Ticker", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="create-ticker", placeholder="AAPL", type="text",
                              style={"textTransform": "uppercase"}),
                ], md=3),
                dbc.Col([
                    dbc.Label("Trigger Type", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Dropdown(
                        id="create-type",
                        options=[{"label": t, "value": t} for t in _ALERT_TYPES],
                        value="Price above",
                        clearable=False,
                    ),
                ], md=4),
                dbc.Col([
                    dbc.Label("Value", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="create-value", type="number", placeholder="0.00"),
                ], md=3),
                dbc.Col([
                    dbc.Label(" ", style={"display": "block", "fontSize": "12px"}),
                    dbc.Button("Create Alert", id="create-alert-btn", color="success",
                               n_clicks=0, className="w-100"),
                ], md=2),
            ], className="g-3"),
        ])),
    ])


def _render_log(triggered: list) -> html.Div:
    if not triggered:
        return html.P("No alerts triggered yet.", style={"color": theme.MUTED, "fontSize": "14px"})

    rows = []
    for t in reversed(triggered[-50:]):
        color = _TYPE_COLORS.get(t.get("type", ""), theme.MUTED)
        rows.append(html.Tr([
            html.Td(t.get("ticker", ""), style={"fontWeight": "700"}),
            html.Td(t.get("fired_at", "")[:19], style={"color": theme.MUTED, "fontSize": "12px"}),
            html.Td(t.get("type", ""), style={"color": color}),
            html.Td(str(t.get("threshold", ""))),
            html.Td(str(t.get("actual", ""))),
        ]))

    return html.Div([
        html.Table([
            html.Thead(html.Tr([
                html.Th("Ticker"), html.Th("Fired At"), html.Th("Type"),
                html.Th("Threshold"), html.Th("Actual"),
            ], style={"color": theme.MUTED, "fontSize": "11px"})),
            html.Tbody(rows),
        ], style={"width": "100%", "borderCollapse": "collapse", "fontSize": "13px"}),
        html.Div(className="mt-3", children=[
            dbc.Button("Clear Log", id="clear-log-btn", color="danger", size="sm", n_clicks=0),
        ]),
    ])


@callback(
    Output("alerts-store", "data", allow_duplicate=True),
    Output("alerts-create-msg", "children"),
    Input("create-alert-btn", "n_clicks"),
    State("create-ticker", "value"),
    State("create-type", "value"),
    State("create-value", "value"),
    State("alerts-store", "data"),
    prevent_initial_call=True,
)
def _create_alert(n_clicks, ticker, alert_type, value, store):
    store = store or {"active": [], "triggered": []}
    if not ticker or value is None:
        return store, dbc.Alert("Ticker and value are required.", color="warning", duration=3000)

    new_alert = {
        "ticker": ticker.upper(),
        "type": alert_type,
        "value": float(value),
        "created": datetime.datetime.now().isoformat(),
    }
    store["active"] = list(store.get("active", [])) + [new_alert]
    msg = dbc.Alert(
        f"Alert created: {ticker.upper()} {alert_type} {value}",
        color="success", duration=3000,
    )
    return store, msg


@callback(
    Output("alerts-store", "data", allow_duplicate=True),
    Input({"type": "del-alert-btn", "index": ALL}, "n_clicks"),
    State("alerts-store", "data"),
    prevent_initial_call=True,
)
def _delete_alert(del_clicks, store):
    store = store or {"active": [], "triggered": []}
    triggered_id = ctx.triggered_id
    if triggered_id is None or not any(c for c in (del_clicks or []) if c):
        return store

    idx = triggered_id.get("index", -1)
    active = list(store.get("active", []))
    if 0 <= idx < len(active):
        active.pop(idx)
    store["active"] = active
    return store


@callback(
    Output("alerts-store", "data", allow_duplicate=True),
    Output("check-alerts-msg", "children"),
    Input("check-alerts-btn", "n_clicks"),
    State("alerts-store", "data"),
    prevent_initial_call=True,
)
def _check_alerts(n_clicks, store):
    store = store or {"active": [], "triggered": []}
    active = list(store.get("active", []))
    triggered = list(store.get("triggered", []))

    still_active = []
    fired_count = 0

    for alert in active:
        alert_type = alert.get("type", "")
        threshold = alert.get("value", 0)
        ticker = alert.get("ticker", "")

        fired = False
        actual = None

        if alert_type in ("Price above", "Price below") and ticker:
            try:
                price = yf.Ticker(ticker).fast_info.last_price
                actual = price
                if alert_type == "Price above" and price >= threshold:
                    fired = True
                elif alert_type == "Price below" and price <= threshold:
                    fired = True
            except Exception:
                pass

        if fired:
            triggered.append({
                **alert,
                "fired_at": datetime.datetime.now().isoformat(),
                "threshold": threshold,
                "actual": round(actual, 4) if actual is not None else None,
            })
            fired_count += 1
        else:
            still_active.append(alert)

    store["active"] = still_active
    store["triggered"] = triggered[-50:]

    msg = dbc.Alert(
        f"Checked alerts: {fired_count} fired." if fired_count else "All alerts checked — none triggered.",
        color="success" if fired_count else "secondary",
        duration=3000,
    )
    return store, msg


@callback(
    Output("alerts-store", "data", allow_duplicate=True),
    Input("clear-log-btn", "n_clicks"),
    State("alerts-store", "data"),
    prevent_initial_call=True,
)
def _clear_log(n_clicks, store):
    store = store or {"active": [], "triggered": []}
    store["triggered"] = []
    return store
