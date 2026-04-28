"""Color palette and Plotly layout defaults matching the existing dark theme."""

# Core palette (matches frontend/ui/theme.py)
BG = "#0f1318"
CARD_BG = "#1c2128"
BORDER = "#3d444d"
BORDER_LIGHT = "#2d333b"
GREEN = "#26d96a"
RED = "#ff6464"
TEXT = "#e8edf3"
MUTED = "#b0b8c4"
BLUE = "#58a6ff"
YELLOW = "#f0b429"
PURPLE = "#c084fc"

DIRECTION_COLORS = {"bullish": GREEN, "bearish": RED, "neutral": MUTED}
DIRECTION_LABELS = {"bullish": "BUY", "bearish": "SELL", "neutral": "HOLD"}
DIRECTION_BADGE_BG = {"bullish": "#0d3a1f", "bearish": "#3a0d0d", "neutral": "#2a2a2a"}

PLOTLY_DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    font=dict(color="#c9d1d9", family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size=12),
    xaxis=dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False, showgrid=True),
    yaxis=dict(gridcolor="#21262d", linecolor="#30363d", zeroline=False, showgrid=True),
    margin=dict(l=50, r=20, t=40, b=40),
    hovermode="x unified",
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#30363d"),
)

PLOTLY_LIGHT_LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8f9fa",
    font=dict(color="#212529", family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size=12),
    xaxis=dict(gridcolor="#dee2e6", linecolor="#ced4da", zeroline=False, showgrid=True),
    yaxis=dict(gridcolor="#dee2e6", linecolor="#ced4da", zeroline=False, showgrid=True),
    margin=dict(l=50, r=20, t=40, b=40),
    hovermode="x unified",
    legend=dict(bgcolor="rgba(255,255,255,0)", bordercolor="#ced4da"),
)


def get_plotly_layout(theme_name: str) -> dict:
    return PLOTLY_LIGHT_LAYOUT if theme_name == "light" else PLOTLY_DARK_LAYOUT


CUSTOM_CSS = """
:root {
    --theme-bg: #0f1318;
    --theme-card-bg: #1c2128;
    --theme-border: #3d444d;
    --theme-border-light: #2d333b;
    --theme-text: #e8edf3;
    --theme-muted: #b0b8c4;
    --theme-input-bg: #161b22;
    --theme-navbar-bg: #161b22;
    --theme-table-header-bg: #161b22;
    --theme-row-hover: #21262d;
}
[data-bs-theme="dark"] {
    --theme-bg: #0f1318;
    --theme-card-bg: #1c2128;
    --theme-border: #3d444d;
    --theme-border-light: #2d333b;
    --theme-text: #e8edf3;
    --theme-muted: #b0b8c4;
    --theme-input-bg: #161b22;
    --theme-navbar-bg: #161b22;
    --theme-table-header-bg: #161b22;
    --theme-row-hover: #21262d;
}
[data-bs-theme="light"] {
    --theme-bg: #f0f2f5;
    --theme-card-bg: #ffffff;
    --theme-border: #ced4da;
    --theme-border-light: #dee2e6;
    --theme-text: #212529;
    --theme-muted: #6c757d;
    --theme-input-bg: #ffffff;
    --theme-navbar-bg: #ffffff;
    --theme-table-header-bg: #f8f9fa;
    --theme-row-hover: #f1f3f5;
}
@media (prefers-color-scheme: light) {
    :root:not([data-bs-theme="dark"]):not([data-bs-theme="light"]) {
        --theme-bg: #f0f2f5;
        --theme-card-bg: #ffffff;
        --theme-border: #ced4da;
        --theme-border-light: #dee2e6;
        --theme-text: #212529;
        --theme-muted: #6c757d;
        --theme-input-bg: #ffffff;
        --theme-navbar-bg: #ffffff;
        --theme-table-header-bg: #f8f9fa;
        --theme-row-hover: #f1f3f5;
    }
}
body {
    background-color: var(--theme-bg) !important;
    color: var(--theme-text) !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.navbar {
    background-color: var(--theme-navbar-bg) !important;
    border-bottom: 1px solid var(--theme-border) !important;
}
.navbar-brand, .nav-link {
    color: var(--theme-text) !important;
}
.nav-link:hover {
    color: #26d96a !important;
}
.card {
    background-color: var(--theme-card-bg) !important;
    border: 1px solid var(--theme-border) !important;
    border-radius: 8px !important;
}
.card-body {
    color: var(--theme-text) !important;
}
.dash-table-container .dash-spreadsheet-container {
    background-color: var(--theme-card-bg) !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
    background-color: var(--theme-table-header-bg) !important;
    color: var(--theme-muted) !important;
    border-bottom: 1px solid var(--theme-border) !important;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {
    background-color: var(--theme-card-bg) !important;
    color: var(--theme-text) !important;
    border-bottom: 1px solid var(--theme-border-light) !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner tr:hover td {
    background-color: var(--theme-row-hover) !important;
}
.form-control, .form-select {
    background-color: var(--theme-input-bg) !important;
    border-color: var(--theme-border) !important;
    color: var(--theme-text) !important;
}
.form-control:focus, .form-select:focus {
    border-color: #26d96a !important;
    box-shadow: 0 0 0 0.2rem rgba(38, 217, 106, 0.15) !important;
}
.btn-success {
    background-color: #26d96a !important;
    border-color: #26d96a !important;
    color: #000 !important;
    font-weight: 600;
}
.btn-success:hover {
    background-color: #1fad56 !important;
    border-color: #1fad56 !important;
}
.btn-danger {
    background-color: #ff6464 !important;
    border-color: #ff6464 !important;
    color: #fff !important;
    font-weight: 600;
}
.Select-control {
    background-color: var(--theme-input-bg) !important;
    border-color: var(--theme-border) !important;
}
.Select-menu-outer {
    background-color: var(--theme-input-bg) !important;
    border-color: var(--theme-border) !important;
}
.Select-option {
    background-color: var(--theme-input-bg) !important;
    color: var(--theme-text) !important;
}
.Select-option:hover, .Select-option.is-focused {
    background-color: var(--theme-row-hover) !important;
}
.kpi-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--theme-muted);
    margin-bottom: 4px;
}
.kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--theme-text);
    line-height: 1.1;
}
.kpi-delta {
    font-size: 12px;
    margin-top: 4px;
}
.direction-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.5px;
}
"""
