"""Live Dashboard — polls /trading/status every 10s."""
from __future__ import annotations

import datetime

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dash_table, dcc, html

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

        # Detail tabs: positions, trades, risk
        dbc.Tabs([
            dbc.Tab(label="Open Positions", tab_id="pos"),
            dbc.Tab(label="Recent Trades", tab_id="trades"),
            dbc.Tab(label="Risk", tab_id="risk"),
        ], id="dash-detail-tabs", active_tab="pos", className="mt-2 mb-2"),
        html.Div(id="dash-detail-content"),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("equity-history-store", "data"),
    Output("dash-api-banner", "children"),
    Output("dash-kpi-row", "children"),
    Output("dash-detail-content", "children"),
    Input("dash-interval", "n_intervals"),
    Input("dash-detail-tabs", "active_tab"),
    State("equity-history-store", "data"),
)
def _poll_status(n: int, active_tab: str, history: list) -> tuple:
    try:
        status = api.trading_status()
    except Exception as exc:
        banner = dbc.Alert(
            [html.Strong("API Offline — "), f"Cannot reach {api.API_BASE}. Start the API with: make api-dev"],
            color="danger", className="mb-3",
        )
        return history, banner, _empty_kpi_row(), html.Div()

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

    # Detail tab content
    detail_content = _build_detail_tab(active_tab or "pos", status)

    return new_history, banner, kpi_row, detail_content


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
    Input("current-theme-store", "data"),
)
def _update_equity_chart(history: list, current_theme: str) -> object:
    layout = theme.get_plotly_layout(current_theme or "dark")
    return components.equity_line_chart(history or [], height=300, plotly_layout=layout)


def _build_detail_tab(active_tab: str, status: dict) -> html.Div:
    if active_tab == "pos":
        return _positions_table(status.get("positions", []))
    if active_tab == "trades":
        return _trades_table(status.get("recent_trades", []))
    return _risk_tab(status)


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


def _positions_table(positions: list) -> html.Div:
    if not positions:
        return html.P("No open positions.", style={"color": theme.MUTED, "fontSize": "14px", "padding": "12px 0"})
    rows = [{"Ticker": p["ticker"], "Side": str(p["side"]).upper(),
             "Qty": p["quantity"],
             "Entry": f"${p['entry_price']:.2f}",
             "Stop": f"${p['stop_loss']:.2f}",
             "Target": f"${p['take_profit']:.2f}",
             "Unreal. P&L": "—"} for p in positions]
    return dash_table.DataTable(
        data=rows,
        columns=[{"name": c, "id": c} for c in
                 ["Ticker", "Side", "Qty", "Entry", "Stop", "Target", "Unreal. P&L"]],
        style_table={"overflowX": "auto"},
        style_header=_TABLE_STYLE_HEADER,
        style_cell=_TABLE_STYLE_CELL,
    )


def _trades_table(trades: list) -> html.Div:
    if not trades:
        return html.P("No recent trades.", style={"color": theme.MUTED, "fontSize": "14px", "padding": "12px 0"})
    rows = [{"Ticker": t["ticker"], "Side": str(t["side"]).upper(),
             "Qty": t["quantity"],
             "Entry": f"${t['entry_price']:.2f}",
             "Exit": f"${t['exit_price']:.2f}",
             "P&L": f"${t['pnl']:+,.2f}",
             "Return %": f"{t['return_pct']:+.2f}%",
             "Exit Time": t.get("exit_time", "")[:19],
             "Reason": t.get("reason", "")} for t in trades]
    return dash_table.DataTable(
        data=rows,
        columns=[{"name": c, "id": c} for c in
                 ["Ticker", "Side", "Qty", "Entry", "Exit", "P&L", "Return %", "Exit Time", "Reason"]],
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_header=_TABLE_STYLE_HEADER,
        style_cell=_TABLE_STYLE_CELL,
        style_data_conditional=[
            {"if": {"filter_query": '{P&L} contains "+"', "column_id": "P&L"},
             "color": theme.GREEN},
            {"if": {"filter_query": '{P&L} contains "-"', "column_id": "P&L"},
             "color": theme.RED},
        ],
    )


def _risk_tab(status: dict) -> html.Div:
    trades = status.get("recent_trades", [])
    cycle_count = status.get("cycle_count", 0)
    n = len(trades)

    if n == 0:
        return html.Div([
            dbc.Row([
                dbc.Col(components.kpi_card("Win Rate", "—"), md=3, className="mb-3"),
                dbc.Col(components.kpi_card("Profit Factor", "—"), md=3, className="mb-3"),
                dbc.Col(components.kpi_card("Total Trades", "0"), md=3, className="mb-3"),
                dbc.Col(components.kpi_card("Cycles", str(cycle_count)), md=3, className="mb-3"),
            ], className="g-3"),
            html.P("Max Drawdown: — (requires live session equity curve)",
                   style={"color": theme.MUTED, "fontSize": "12px"}),
        ])

    wins = [t for t in trades if t.get("pnl", 0) > 0]
    losses = [t for t in trades if t.get("pnl", 0) <= 0]
    win_rate = len(wins) / n * 100
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    pf = gross_win / gross_loss if gross_loss > 0 else None

    return html.Div([
        dbc.Row([
            dbc.Col(components.kpi_card("Win Rate", f"{win_rate:.1f}%",
                                        delta_positive=win_rate >= 50), md=3, className="mb-3"),
            dbc.Col(components.kpi_card("Profit Factor",
                                        f"{pf:.2f}" if pf else "—",
                                        delta_positive=pf is not None and pf >= 1), md=3, className="mb-3"),
            dbc.Col(components.kpi_card("Total Trades", str(n)), md=3, className="mb-3"),
            dbc.Col(components.kpi_card("Cycles", str(cycle_count)), md=3, className="mb-3"),
        ], className="g-3"),
        html.P("Max Drawdown: — (equity curve not in /trading/status)",
               style={"color": theme.MUTED, "fontSize": "12px"}),
    ])
