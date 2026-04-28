"""Dash production trading dashboard entry point."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html

from dash_ui import api, components, theme

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="dash_ui/pages",
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Trading Dashboard",
    update_title=None,
)
server = app.server  # WSGI entry point for gunicorn


def _nav_links() -> list:
    return [
        dbc.NavItem(dbc.NavLink(page["name"], href=page["relative_path"], active="exact"))
        for page in sorted(dash.page_registry.values(), key=lambda p: p.get("order", 99))
    ]


app.layout = html.Div(
    [
        # Global stores (cross-page state)
        dcc.Store(id="scan-results-store", storage_type="session", data=[]),
        dcc.Store(id="predict-result-store", storage_type="session", data={}),
        dcc.Store(id="app-config-store", storage_type="session", data=None),
        dcc.Store(id="theme-store", storage_type="local", data="auto"),
        dcc.Store(id="current-theme-store", storage_type="memory", data="dark"),
        dcc.Interval(id="config-load-interval", interval=999_999_999, n_intervals=0, max_intervals=1),

        # Navbar
        dbc.Navbar(
            dbc.Container(
                [
                    dbc.NavbarBrand(
                        [html.I(className="bi bi-graph-up-arrow me-2"), "Trading Dashboard"],
                        href="/",
                        style={"color": theme.GREEN, "fontWeight": "700", "fontSize": "16px"},
                    ),
                    dbc.NavbarToggler(id="navbar-toggler"),
                    dbc.Collapse(
                        dbc.Nav(
                            _nav_links() + [
                                dbc.NavItem(
                                    dbc.ButtonGroup(
                                        [
                                            dbc.Button(
                                                html.I(className="bi bi-circle-half"),
                                                id="theme-auto-btn", size="sm",
                                                color="secondary", outline=True, title="Auto (system)",
                                            ),
                                            dbc.Button(
                                                html.I(className="bi bi-moon-stars-fill"),
                                                id="theme-dark-btn", size="sm",
                                                color="secondary", outline=True, title="Dark",
                                            ),
                                            dbc.Button(
                                                html.I(className="bi bi-sun-fill"),
                                                id="theme-light-btn", size="sm",
                                                color="secondary", outline=True, title="Light",
                                            ),
                                        ],
                                        className="ms-3",
                                    ),
                                ),
                            ],
                            navbar=True, className="ms-auto",
                        ),
                        id="navbar-collapse",
                        navbar=True,
                    ),
                ],
                fluid=True,
            ),
            dark=True,
            style={"backgroundColor": "#161b22", "borderBottom": f"1px solid {theme.BORDER}"},
        ),

        # Global status bar (populated by callback on load)
        html.Div(id="global-status-bar"),

        # Page content
        dash.page_container,
    ],
    style={"backgroundColor": theme.BG, "minHeight": "100vh"},
)

# Inject custom CSS
app.index_string = app.index_string.replace(
    "</head>",
    f"<style>{theme.CUSTOM_CSS}</style></head>",
)


# ── Theme toggle (clientside — runs in browser, no round-trip) ───────────────
app.clientside_callback(
    """
    function(auto_n, dark_n, light_n, stored) {
        var ctx = window.dash_clientside.callback_context;
        var pref = stored || "auto";
        if (ctx.triggered && ctx.triggered.length > 0) {
            var tid = ctx.triggered[0].prop_id;
            if (tid.indexOf("theme-auto-btn")  >= 0) pref = "auto";
            if (tid.indexOf("theme-dark-btn")  >= 0) pref = "dark";
            if (tid.indexOf("theme-light-btn") >= 0) pref = "light";
        }
        var resolved;
        if (pref === "auto") {
            resolved = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
            document.documentElement.removeAttribute("data-bs-theme");
        } else {
            resolved = pref;
            document.documentElement.setAttribute("data-bs-theme", pref);
        }
        return [pref, resolved, pref === "auto", pref === "dark", pref === "light"];
    }
    """,
    Output("theme-store", "data"),
    Output("current-theme-store", "data"),
    Output("theme-auto-btn", "active"),
    Output("theme-dark-btn", "active"),
    Output("theme-light-btn", "active"),
    Input("theme-auto-btn", "n_clicks"),
    Input("theme-dark-btn", "n_clicks"),
    Input("theme-light-btn", "n_clicks"),
    Input("theme-store", "data"),
)


# ── Load config once on startup and render the status bar ────────────────────
@app.callback(
    Output("app-config-store", "data"),
    Output("global-status-bar", "children"),
    Input("config-load-interval", "n_intervals"),
)
def _load_global_config(_n):
    try:
        cfg = api.get_config()
        return cfg, components.status_bar(cfg, api_online=True)
    except Exception:
        return None, components.status_bar(None, api_online=False)


if __name__ == "__main__":
    app.run(debug=True, port=8050)
