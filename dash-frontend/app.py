"""Dash production trading dashboard entry point."""
from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_ui import theme

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
                        dbc.Nav(_nav_links(), navbar=True, className="ms-auto"),
                        id="navbar-collapse",
                        navbar=True,
                    ),
                ],
                fluid=True,
            ),
            dark=True,
            style={"backgroundColor": "#161b22", "borderBottom": f"1px solid {theme.BORDER}"},
        ),

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

if __name__ == "__main__":
    app.run(debug=True, port=8050)
