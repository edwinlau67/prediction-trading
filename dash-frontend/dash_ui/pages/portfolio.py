"""Portfolio Builder — ETF/stock correlation, sector exposure, diversification analysis."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html

from dash_ui import api, components, theme

dash.register_page(__name__, path="/portfolio", name="Portfolio Builder", order=7)

_DEFAULT_TICKERS = "SPY\nQQQ\nXLK\nBND\nGLD"

layout = dbc.Container(
    [
        html.H4("Portfolio Builder", className="mt-4 mb-3", style={"color": theme.TEXT}),
        html.Div(id="pb-api-banner"),

        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Tickers (one per line)", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dcc.Textarea(
                        id="pb-tickers",
                        value=_DEFAULT_TICKERS,
                        style={
                            "width": "100%", "height": "120px",
                            "backgroundColor": "#161b22", "color": theme.TEXT,
                            "border": f"1px solid {theme.BORDER}", "borderRadius": "6px",
                            "padding": "8px", "fontFamily": "monospace", "fontSize": "13px",
                        },
                    ),
                ], md=6),
                dbc.Col([
                    dbc.Label("Lookback Days", style={"color": theme.MUTED, "fontSize": "12px"}),
                    dbc.Input(id="pb-lookback", type="number", value=252, min=30, max=1260, step=21),
                    html.Br(),
                    dbc.Button("Analyze Portfolio", id="pb-run-btn", color="success",
                               n_clicks=0, className="mt-2"),
                ], md=6),
            ], className="g-3"),
        ]), className="mb-4"),

        html.Div(id="pb-error"),
        dcc.Loading(html.Div(id="pb-results"), type="default"),
    ],
    fluid=True,
    style={"padding": "0 24px"},
)


@callback(
    Output("pb-results", "children"),
    Output("pb-error", "children"),
    Output("pb-api-banner", "children"),
    Input("pb-run-btn", "n_clicks"),
    State("pb-tickers", "value"),
    State("pb-lookback", "value"),
    prevent_initial_call=True,
)
def _run_analysis(n_clicks, tickers_text, lookback):
    tickers = [t.strip().upper() for t in (tickers_text or "").splitlines() if t.strip()]
    if not tickers:
        return html.Div(), dbc.Alert("Enter at least one ticker.", color="warning"), html.Div()

    try:
        result = api.portfolio_analyze(tickers, lookback_days=int(lookback or 252))
    except Exception as exc:
        banner = dbc.Alert(
            [html.Strong("API Error — "), str(exc)],
            color="danger", className="mb-3",
        )
        return html.Div(), html.Div(), banner

    return _build_results(result), html.Div(), html.Div()


def _build_results(result: dict) -> html.Div:
    etf_infos = result.get("etf_infos", [])
    score = result.get("diversification_score", 0.0)
    corr = result.get("correlation_matrix", {})
    sector_exp = result.get("sector_exposure", {})
    recs = result.get("recommendations", [])
    tickers = result.get("tickers", [])

    # ETF/Stock info cards
    info_cards = []
    for info in etf_infos:
        is_etf = info.get("is_etf", False)
        badge_color = theme.BLUE if is_etf else theme.PURPLE
        badge_label = "ETF" if is_etf else "Stock"
        exp = info.get("expense_ratio")
        exp_str = f"{exp:.2f}%" if exp is not None else "—"
        info_cards.append(dbc.Col(dbc.Card(dbc.CardBody([
            html.Div([
                html.Span(info.get("ticker", ""), style={"fontWeight": "700", "fontSize": "16px"}),
                html.Span(badge_label, style={
                    "backgroundColor": badge_color, "color": "#fff",
                    "borderRadius": "10px", "padding": "2px 8px",
                    "fontSize": "11px", "marginLeft": "8px", "fontWeight": "600",
                }),
            ]),
            html.Div(info.get("name", ""), style={"color": theme.TEXT, "fontSize": "13px", "marginTop": "4px"}),
            html.Div(info.get("category", ""), style={"color": theme.MUTED, "fontSize": "12px"}),
            html.Div(f"Expense: {exp_str}", style={"color": theme.MUTED, "fontSize": "12px"}),
        ])), md=3, className="mb-3"))

    # Diversification score card
    if score >= 0.5:
        score_color = theme.GREEN
    elif score >= 0.25:
        score_color = theme.YELLOW
    else:
        score_color = theme.RED

    score_card = dbc.Col(
        components.kpi_card("Diversification Score", f"{score:.2f}",
                            delta="Higher = lower avg pairwise correlation",
                            delta_positive=score >= 0.5),
        md=4, className="mb-4",
    )

    # Correlation heatmap
    corr_chart = html.Div()
    if corr and tickers:
        matrix = [[corr.get(col, {}).get(row, 0.0) for col in tickers] for row in tickers]
        heatmap_fig = go.Figure(go.Heatmap(
            z=matrix,
            x=tickers,
            y=tickers,
            colorscale=[[0, theme.RED], [0.5, "#21262d"], [1, theme.GREEN]],
            zmid=0.5,
            zmin=-1, zmax=1,
            text=[[f"{v:.2f}" for v in row] for row in matrix],
            texttemplate="%{text}",
            hovertemplate="%{y} / %{x}: %{z:.3f}<extra></extra>",
        ))
        layout_cfg = dict(theme.PLOTLY_DARK_LAYOUT)
        layout_cfg.update(height=400, title="Correlation Matrix", margin=dict(l=80, r=20, t=50, b=60))
        heatmap_fig.update_layout(**layout_cfg)
        corr_chart = dbc.Card(dbc.CardBody(
            dcc.Graph(figure=heatmap_fig, config={"displayModeBar": False})
        ), className="mb-4")

    # Sector exposure bar chart
    sector_chart = html.Div()
    if sector_exp:
        sectors = list(sector_exp.keys())
        weights = [v * 100 for v in sector_exp.values()]
        sector_fig = go.Figure(go.Bar(
            x=sectors, y=weights,
            marker_color=theme.BLUE,
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        ))
        layout_cfg = dict(theme.PLOTLY_DARK_LAYOUT)
        layout_cfg.update(
            height=300, title="Sector Exposure (Equal-Weighted)",
            yaxis=dict(**theme.PLOTLY_DARK_LAYOUT["yaxis"], ticksuffix="%"),
        )
        sector_fig.update_layout(**layout_cfg)
        sector_chart = dbc.Card(dbc.CardBody(
            dcc.Graph(figure=sector_fig, config={"displayModeBar": False})
        ), className="mb-4")

    # Recommendations
    rec_items = []
    for rec in recs:
        low = rec.lower()
        if any(w in low for w in ("high correlation", "low diversification", "caution")):
            color = "warning"
        elif any(w in low for w in ("good", "excellent")):
            color = "success"
        else:
            color = "info"
        rec_items.append(dbc.Alert(rec, color=color, className="mb-2"))

    return html.Div([
        dbc.Row(info_cards, className="mb-2"),
        dbc.Row([score_card], className="mb-4"),
        corr_chart,
        sector_chart,
        html.H6("Recommendations", style={"color": theme.MUTED, "marginBottom": "12px"}),
        html.Div(rec_items),
    ])
