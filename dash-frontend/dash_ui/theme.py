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

CUSTOM_CSS = f"""
body {{
    background-color: {BG} !important;
    color: {TEXT} !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}}
.navbar {{
    background-color: #161b22 !important;
    border-bottom: 1px solid {BORDER} !important;
}}
.navbar-brand, .nav-link {{
    color: {TEXT} !important;
}}
.nav-link:hover {{
    color: {GREEN} !important;
}}
.card {{
    background-color: {CARD_BG} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
}}
.card-body {{
    color: {TEXT} !important;
}}
.dash-table-container .dash-spreadsheet-container {{
    background-color: {CARD_BG} !important;
}}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {{
    background-color: #161b22 !important;
    color: {MUTED} !important;
    border-bottom: 1px solid {BORDER} !important;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td {{
    background-color: {CARD_BG} !important;
    color: {TEXT} !important;
    border-bottom: 1px solid {BORDER_LIGHT} !important;
}}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner tr:hover td {{
    background-color: #21262d !important;
}}
.form-control, .form-select {{
    background-color: #161b22 !important;
    border-color: {BORDER} !important;
    color: {TEXT} !important;
}}
.form-control:focus, .form-select:focus {{
    border-color: {GREEN} !important;
    box-shadow: 0 0 0 0.2rem rgba(38, 217, 106, 0.15) !important;
}}
.btn-success {{
    background-color: {GREEN} !important;
    border-color: {GREEN} !important;
    color: #000 !important;
    font-weight: 600;
}}
.btn-success:hover {{
    background-color: #1fad56 !important;
    border-color: #1fad56 !important;
}}
.btn-danger {{
    background-color: {RED} !important;
    border-color: {RED} !important;
    color: #fff !important;
    font-weight: 600;
}}
.Select-control {{
    background-color: #161b22 !important;
    border-color: {BORDER} !important;
}}
.Select-menu-outer {{
    background-color: #161b22 !important;
    border-color: {BORDER} !important;
}}
.Select-option {{
    background-color: #161b22 !important;
    color: {TEXT} !important;
}}
.Select-option:hover, .Select-option.is-focused {{
    background-color: #21262d !important;
}}
.kpi-label {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: {MUTED};
    margin-bottom: 4px;
}}
.kpi-value {{
    font-size: 28px;
    font-weight: 700;
    color: {TEXT};
    line-height: 1.1;
}}
.kpi-delta {{
    font-size: 12px;
    margin-top: 4px;
}}
.direction-badge {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.5px;
}}
"""
