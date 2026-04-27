"""Backtest page — historical bar-by-bar backtesting."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dash_table, dcc, html

from dash_ui import api, components, theme

dash.register_page(__name__, path="/backtest", name="Backtest", order=5)

layout = dbc.Container(
    [
        dcc.Store(id="bt-store", storage_type="session", data={}),
        html.H4("Backtest", className="mt-4 mb-3", style={"color": theme.TEXT}),

        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Ticker", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="bt-ticker", placeholder="AAPL", type="text",
                              style={"textTransform": "uppercase"}),
                ], md=2),
                dbc.Col([
                    dbc.Label("Start Date", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="bt-start", type="date", value="2023-01-01"),
                ], md=2),
                dbc.Col([
                    dbc.Label("End Date", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="bt-end", type="date", value="2024-12-31"),
                ], md=2),
                dbc.Col([
                    dbc.Label("Initial Capital ($)", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="bt-capital", type="number", value=10000, min=1000, step=1000),
                ], md=2),
                dbc.Col([
                    dbc.Label("Commission ($)", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="bt-commission", type="number", value=1.0, min=0, step=0.5),
                ], md=2),
                dbc.Col([
                    dbc.Label(" ", style={"display": "block", "fontSize": "12px"}),
                    dbc.Button("Run Backtest", id="bt-run-btn", color="success", n_clicks=0,
                               className="w-100"),
                ], md=2),
            ], className="g-3"),
        ]), className="mb-4"),

        html.Div(id="bt-error"),
        dcc.Loading(html.Div(id="bt-results"), type="default"),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("bt-store", "data"),
    Output("bt-results", "children"),
    Output("bt-error", "children"),
    Input("bt-run-btn", "n_clicks"),
    State("bt-ticker", "value"),
    State("bt-start", "value"),
    State("bt-end", "value"),
    State("bt-capital", "value"),
    State("bt-commission", "value"),
    prevent_initial_call=True,
)
def _run_backtest(n_clicks, ticker, start, end, capital, commission):
    if not ticker or not start or not end:
        return {}, html.Div(), dbc.Alert("Please fill in all required fields.", color="warning")

    try:
        result = api.backtest(
            ticker=ticker.upper(),
            start=start,
            end=end,
            initial_capital=float(capital or 10000),
            commission=float(commission or 1.0),
        )
    except Exception as exc:
        return {}, html.Div(), dbc.Alert(f"Backtest failed: {exc}", color="danger")

    return result, _build_results(result), html.Div()


def _build_results(result: dict) -> html.Div:
    stats = result.get("stats", {})
    trades = result.get("trades", [])
    equity_curve = result.get("equity_curve", [])
    ohlcv = result.get("ohlcv", [])

    initial = stats.get("initial_capital", 10000)
    final = stats.get("final_equity", initial)
    ret = stats.get("return_pct", 0)
    drawdown = stats.get("max_drawdown_pct", 0)
    win_rate = stats.get("win_rate_pct", 0)
    profit_factor = stats.get("profit_factor")
    n_trades = stats.get("trades", 0)
    avg_win = stats.get("avg_win", 0)
    avg_loss = stats.get("avg_loss", 0)

    kpi_row = dbc.Row([
        dbc.Col(components.kpi_card("Total Return", f"{ret:+.2f}%",
                                    delta_positive=ret >= 0), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Max Drawdown", f"{drawdown:.2f}%",
                                    delta_positive=False), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Win Rate", f"{win_rate:.1f}%",
                                    delta_positive=win_rate >= 50), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Profit Factor",
                                    f"{profit_factor:.2f}" if profit_factor else "—",
                                    delta_positive=profit_factor is not None and profit_factor >= 1), md=3, className="mb-3"),
    ], className="g-3 mb-3")

    kpi_row2 = dbc.Row([
        dbc.Col(components.kpi_card("Total Trades", str(n_trades)), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Avg Win", f"${avg_win:,.2f}",
                                    delta_positive=avg_win >= 0), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Avg Loss", f"${avg_loss:,.2f}",
                                    delta_positive=False), md=3, className="mb-3"),
        dbc.Col(components.kpi_card("Final Equity", f"${final:,.2f}",
                                    delta_positive=final >= initial), md=3, className="mb-3"),
    ], className="g-3 mb-4")

    # Equity curve tab
    equity_fig = components.equity_line_chart(equity_curve, height=360, initial_capital=initial)

    # Candlestick + trades tab
    candle_fig = _build_candle_with_trades(ohlcv, trades)

    # Trade log tab
    trade_table = _build_trade_table(trades)

    results_tabs = dbc.Card(dbc.CardBody([
        dbc.Tabs([
            dbc.Tab(
                dcc.Graph(figure=equity_fig, config={"displayModeBar": False}),
                label="Equity Curve", tab_id="bt-tab-equity",
            ),
            dbc.Tab(
                dcc.Graph(figure=candle_fig, config={"displayModeBar": False}),
                label="Candlestick + Trades", tab_id="bt-tab-candle",
            ),
            dbc.Tab(
                html.Div(trade_table, style={"maxHeight": "500px", "overflowY": "auto"}),
                label="Trade Log", tab_id="bt-tab-trades",
            ),
        ], active_tab="bt-tab-equity"),
    ]))

    return html.Div([kpi_row, kpi_row2, results_tabs])


def _build_candle_with_trades(ohlcv: list[dict], trades: list[dict]) -> go.Figure:
    fig = components.candlestick_chart(ohlcv, height=420)

    buys = [t for t in trades if str(t.get("side", "")).lower() == "long"]
    sells = [t for t in trades if str(t.get("side", "")).lower() != "long"]

    if buys:
        fig.add_trace(go.Scatter(
            x=[t["entry_time"][:10] for t in buys],
            y=[t["entry_price"] for t in buys],
            mode="markers",
            marker=dict(symbol="triangle-up", size=12, color=theme.GREEN, line=dict(color="#000", width=1)),
            name="Buy",
            hovertemplate="Buy @ $%{y:.2f}<extra></extra>",
        ), row=1, col=1)

    if sells:
        fig.add_trace(go.Scatter(
            x=[t["exit_time"][:10] for t in sells],
            y=[t["exit_price"] for t in sells],
            mode="markers",
            marker=dict(symbol="triangle-down", size=12, color=theme.RED, line=dict(color="#000", width=1)),
            name="Sell",
            hovertemplate="Sell @ $%{y:.2f}<extra></extra>",
        ), row=1, col=1)

    return fig


def _build_trade_table(trades: list[dict]) -> dash_table.DataTable:
    rows = []
    for t in trades:
        pnl = t.get("pnl", 0)
        rows.append({
            "Ticker": t.get("ticker", ""),
            "Side": str(t.get("side", "")).upper(),
            "Qty": t.get("quantity", 0),
            "Entry": f"${t.get('entry_price', 0):.2f}",
            "Exit": f"${t.get('exit_price', 0):.2f}",
            "P&L": f"${pnl:+,.2f}",
            "Return %": f"{t.get('return_pct', 0):+.2f}%",
            "Result": "Win" if t.get("is_win") else "Loss",
            "Reason": t.get("reason", ""),
        })

    return dash_table.DataTable(
        data=rows,
        columns=[{"name": c, "id": c} for c in
                 ["Ticker", "Side", "Qty", "Entry", "Exit", "P&L", "Return %", "Result", "Reason"]],
        sort_action="native",
        page_size=25,
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
            {"if": {"filter_query": '{Result} = "Win"', "column_id": "Result"},
             "color": theme.GREEN, "fontWeight": "700"},
            {"if": {"filter_query": '{Result} = "Loss"', "column_id": "Result"},
             "color": theme.RED, "fontWeight": "700"},
        ],
    )
