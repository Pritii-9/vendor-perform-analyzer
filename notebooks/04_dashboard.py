"""
=============================================================
  VENDOR PERFORMANCE ANALYSIS — Phase 4: Interactive Dashboard
  Plotly Dash | Dark Premium Theme
=============================================================
"""

import sqlite3
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "vendor_analysis.db"

# ── Load Data ─────────────────────────────────────────────────────────────────
print("Loading data from SQLite...")
conn = sqlite3.connect(DB_PATH)
df   = pd.read_sql("SELECT * FROM vendor_summary",  conn)
mth  = pd.read_sql("SELECT * FROM monthly_trend",   conn)
conn.close()

# Clean
mth["period"] = pd.to_datetime(mth["year_month"], format="%Y-%m", errors="coerce")
mth = mth.dropna(subset=["period"]).sort_values("period")
df  = df.dropna(subset=["vendor_class"])

# ── Color Palette ─────────────────────────────────────────────────────────────
DARK_BG   = "#0f1117"
CARD_BG   = "#1a1d2e"
BORDER    = "#2a2d3e"
ACCENT1   = "#6c63ff"
ACCENT2   = "#f72585"
ACCENT3   = "#4cc9f0"
ACCENT4   = "#f8961e"
ACCENT5   = "#43aa8b"
TEXT      = "#e0e0e0"
MUTED     = "#8892a4"
PALETTE   = [ACCENT1, ACCENT2, ACCENT3, ACCENT4, ACCENT5,
             "#9b5de5", "#fee440", "#00bbf9", "#f15bb5"]

PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        font=dict(color=TEXT, family="Inter, sans-serif"),
        xaxis=dict(gridcolor=BORDER, linecolor=BORDER, zerolinecolor=BORDER),
        yaxis=dict(gridcolor=BORDER, linecolor=BORDER, zerolinecolor=BORDER),
        legend=dict(bgcolor=CARD_BG, bordercolor=BORDER),
        colorway=PALETTE,
    )
)

# ── KPI calculations ─────────────────────────────────────────────────────────
total_vendors  = len(df)
total_spend    = df["total_purchase_dollars"].sum()
total_orders   = df["total_orders"].sum()
avg_discount   = df["price_discount_pct"].median()
class_a_cnt    = (df["vendor_class"] == "A").sum()
avg_days_inv   = df["avg_days_to_invoice"].median()

# ── Helper: KPI Card ─────────────────────────────────────────────────────────
def kpi_card(title, value, icon, color, subtitle=""):
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Div([
                    html.Span(icon, style={"fontSize": "24px"}),
                ], style={
                    "width": "50px", "height": "50px",
                    "borderRadius": "12px", "display": "flex",
                    "alignItems": "center", "justifyContent": "center",
                    "background": f"linear-gradient(135deg, {color}33, {color}11)",
                    "border": f"1px solid {color}44",
                    "flexShrink": "0"
                }),
                html.Div([
                    html.P(title, style={"margin": 0, "fontSize": "11px",
                                         "color": MUTED, "fontWeight": "500",
                                         "textTransform": "uppercase",
                                         "letterSpacing": "0.5px"}),
                    html.H4(value, style={"margin": "4px 0 0 0",
                                          "color": color, "fontWeight": "700",
                                          "fontSize": "22px"}),
                    html.P(subtitle, style={"margin": 0, "fontSize": "10px",
                                            "color": MUTED}) if subtitle else html.Div(),
                ], style={"flex": 1})
            ], style={"display": "flex", "gap": "16px", "alignItems": "center"})
        ])
    ], style={
        "background": CARD_BG,
        "border": f"1px solid {BORDER}",
        "borderRadius": "16px",
        "boxShadow": f"0 4px 20px {color}22",
    })

# ── Charts ────────────────────────────────────────────────────────────────────
def fig_top_vendors(n=15):
    top = df.nlargest(n, "total_purchase_dollars").copy()
    top["label"] = top["VendorName"].str[:25]
    fig = go.Figure(go.Bar(
        y=top["label"],
        x=top["total_purchase_dollars"] / 1e6,
        orientation="h",
        marker=dict(
            color=top["total_purchase_dollars"] / 1e6,
            colorscale="Plasma",
            showscale=True,
            colorbar=dict(title="$M", thickness=10),
        ),
        text=[f"${v:.2f}M" for v in top["total_purchase_dollars"]/1e6],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Spend: $%{x:.2f}M<br>"
            "<extra></extra>"
        )
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE, height=450,
        title=dict(text=f"Top {n} Vendors by Purchase Spend", x=0.02, font=dict(size=14)),
        xaxis_title="Total Spend ($M)",
        margin=dict(l=10, r=60, t=45, b=10),
        yaxis=dict(autorange="reversed"),
    )
    return fig

def fig_vendor_class():
    class_spend = df.groupby("vendor_class")["total_purchase_dollars"].sum().reset_index()
    class_count = df["vendor_class"].value_counts().reset_index()
    class_count.columns = ["vendor_class", "count"]

    fig = make_subplots(rows=1, cols=2,
        specs=[[{"type":"pie"}, {"type":"bar"}]],
        subplot_titles=["Spend Share", "Vendor Count"])

    colors_ = [ACCENT1, ACCENT4, ACCENT2]
    fig.add_trace(go.Pie(
        labels=class_spend["vendor_class"],
        values=class_spend["total_purchase_dollars"],
        hole=0.55,
        marker=dict(colors=colors_, line=dict(color=DARK_BG, width=2)),
        textinfo="percent+label",
        hovertemplate="<b>Class %{label}</b><br>Spend: $%{value:,.0f}<br>%{percent}<extra></extra>",
    ), row=1, col=1)

    for i, row in class_count.iterrows():
        fig.add_trace(go.Bar(
            x=[row["vendor_class"]], y=[row["count"]],
            name=f"Class {row['vendor_class']}",
            marker_color=colors_[i],
            text=[row["count"]], textposition="outside",
            hovertemplate="<b>Class %{x}</b><br>Vendors: %{y}<extra></extra>",
        ), row=1, col=2)

    fig.update_layout(
        template=PLOTLY_TEMPLATE, height=380, showlegend=False,
        title=dict(text="ABC Vendor Classification", x=0.02, font=dict(size=14)),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig

def fig_monthly_trend():
    fig = make_subplots(rows=2, cols=1,
        shared_xaxes=True,
        subplot_titles=["Monthly Purchase Spend", "Active Vendors per Month"],
        vertical_spacing=0.12)

    fig.add_trace(go.Scatter(
        x=mth["period"], y=mth["total_spend"]/1e6,
        fill="tozeroy", fillcolor="rgba(108,99,255,0.13)",
        line=dict(color=ACCENT1, width=2.5),
        mode="lines+markers", marker=dict(size=5),
        name="Spend ($M)",
        hovertemplate="%{x|%b %Y}<br>Spend: $%{y:.2f}M<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=mth["period"], y=mth["active_vendors"],
        fill="tozeroy", fillcolor="rgba(76,201,240,0.13)",
        line=dict(color=ACCENT3, width=2.5),
        mode="lines+markers", marker=dict(size=5, symbol="square"),
        name="Active Vendors",
        hovertemplate="%{x|%b %Y}<br>Vendors: %{y}<extra></extra>",
    ), row=2, col=1)

    fig.update_layout(
        template=PLOTLY_TEMPLATE, height=420, showlegend=True,
        title=dict(text="Monthly Purchase Trend", x=0.02, font=dict(size=14)),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    fig.update_yaxes(title_text="Spend ($M)", row=1, col=1)
    fig.update_yaxes(title_text="Vendors", row=2, col=1)
    return fig

def fig_price_analysis():
    disc = df.dropna(subset=["price_discount_pct"])
    disc = disc[disc["price_discount_pct"].between(-50, 200)]

    fig = px.scatter(
        disc,
        x="total_purchase_dollars",
        y="price_discount_pct",
        color="vendor_class",
        size="total_orders",
        hover_name="VendorName",
        color_discrete_map={"A": ACCENT1, "B": ACCENT4, "C": ACCENT2},
        size_max=30,
        opacity=0.75,
        labels={
            "total_purchase_dollars": "Total Spend ($)",
            "price_discount_pct": "Price Discount %",
            "vendor_class": "Class"
        },
    )
    fig.add_hline(y=0, line_dash="dash", line_color=MUTED, opacity=0.5)
    fig.update_layout(
        template=PLOTLY_TEMPLATE, height=400,
        title=dict(text="Spend vs Price Discount per Vendor", x=0.02, font=dict(size=14)),
        margin=dict(l=10, r=10, t=45, b=10),
    )
    return fig

def fig_invoice_delay():
    inv = df.dropna(subset=["avg_days_to_invoice"])
    inv = inv[inv["avg_days_to_invoice"].between(-10, 200)]

    fig = go.Figure()
    class_colors = {"A": ACCENT1, "B": ACCENT4, "C": ACCENT2}
    for cls in ["A", "B", "C"]:
        subset = inv[inv["vendor_class"] == cls]["avg_days_to_invoice"]
        fig.add_trace(go.Box(
            y=subset, name=f"Class {cls}",
            marker_color=class_colors[cls],
            boxmean=True,
            jitter=0.3, pointpos=-1.5,
            hovertemplate=f"Class {cls}<br>%{{y:.1f}} days<extra></extra>",
        ))

    fig.update_layout(
        template=PLOTLY_TEMPLATE, height=380,
        title=dict(text="Invoice Delay Distribution by Vendor Class", x=0.02, font=dict(size=14)),
        yaxis_title="Avg Days to Invoice",
        margin=dict(l=10, r=10, t=45, b=10),
    )
    return fig

def fig_discount_histogram():
    disc = df.dropna(subset=["price_discount_pct"])
    disc = disc[disc["price_discount_pct"].between(-50, 200)]

    fig = go.Figure()
    class_colors = {"A": ACCENT1, "B": ACCENT4, "C": ACCENT2}
    for cls in ["A", "B", "C"]:
        subset = disc[disc["vendor_class"] == cls]["price_discount_pct"]
        fig.add_trace(go.Histogram(
            x=subset, name=f"Class {cls}",
            opacity=0.65,
            marker_color=class_colors[cls],
            nbinsx=30,
        ))

    fig.update_layout(
        barmode="overlay",
        template=PLOTLY_TEMPLATE, height=350,
        title=dict(text="Price Discount Distribution by Class", x=0.02, font=dict(size=14)),
        xaxis_title="Price Discount %",
        yaxis_title="Vendor Count",
        margin=dict(l=10, r=10, t=45, b=10),
    )
    return fig

# ── Helper: Card Style ───────────────────────────────────────────────────────
def _card_style():
    return {
        "background": CARD_BG,
        "borderRadius": "16px",
        "border": f"1px solid {BORDER}",
        "padding": "8px",
        "boxShadow": "0 4px 20px rgba(0,0,0,0.3)",
        "height": "100%",
    }

# ── Dash App ──────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
    ],
    title="Vendor Performance Analysis",
    suppress_callback_exceptions=True,
)

# ── Layout ────────────────────────────────────────────────────────────────────
app.layout = html.Div([

    # ── Header ──────────────────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.Div([
                html.Span("📦", style={"fontSize": "28px"}),
                html.Div([
                    html.H1("Vendor Performance Analysis",
                            style={"margin": 0, "fontSize": "24px",
                                   "fontWeight": "700", "color": TEXT}),
                    html.P("SQL · EDA · Hypothesis Testing · Dashboard",
                           style={"margin": 0, "fontSize": "12px", "color": MUTED}),
                ])
            ], style={"display": "flex", "gap": "14px", "alignItems": "center"}),

            html.Div([
                dbc.Select(
                    id="top-n-select",
                    options=[
                        {"label": "Top 10 Vendors", "value": 10},
                        {"label": "Top 15 Vendors", "value": 15},
                        {"label": "Top 20 Vendors", "value": 20},
                    ],
                    value=15,
                    style={"width": "160px", "background": CARD_BG,
                           "color": TEXT, "border": f"1px solid {BORDER}",
                           "borderRadius": "8px", "fontSize": "13px"}
                ),
            ], style={"display": "flex", "gap": "10px", "alignItems": "center"}),
        ], style={
            "display": "flex", "justifyContent": "space-between",
            "alignItems": "center", "maxWidth": "1600px",
            "margin": "0 auto", "padding": "0 24px"
        })
    ], style={
        "background": f"linear-gradient(135deg, {CARD_BG}, #0f1117)",
        "borderBottom": f"1px solid {BORDER}",
        "padding": "18px 0",
        "boxShadow": "0 4px 24px rgba(0,0,0,0.4)",
        "position": "sticky", "top": 0, "zIndex": 100,
    }),

    # ── Main Content ─────────────────────────────────────────────────────────
    html.Div([

        # KPI Row
        html.Div([
            dbc.Row([
                dbc.Col(kpi_card("Total Vendors",       f"{total_vendors:,}",       "🏢", ACCENT1), md=2),
                dbc.Col(kpi_card("Total Purchase Spend",f"${total_spend/1e6:.1f}M", "💰", ACCENT2), md=2),
                dbc.Col(kpi_card("Total PO Orders",     f"{total_orders:,}",        "📋", ACCENT3), md=2),
                dbc.Col(kpi_card("Avg Price Discount",  f"{avg_discount:.1f}%",     "🏷️", ACCENT4), md=2),
                dbc.Col(kpi_card("Class-A Vendors",     f"{class_a_cnt}",           "⭐", ACCENT5), md=2),
                dbc.Col(kpi_card("Avg Days to Invoice", f"{avg_days_inv:.0f}d",     "📅", "#9b5de5"), md=2),
            ], className="g-3"),
        ], style={"marginBottom": "24px"}),

        # Row 1: Top Vendors + Classification
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Graph(id="fig-top-vendors", config={"displayModeBar": False}),
                ], style=_card_style())
            ], md=7),
            dbc.Col([
                html.Div([
                    dcc.Graph(id="fig-vendor-class",
                              figure=fig_vendor_class(),
                              config={"displayModeBar": False}),
                ], style=_card_style())
            ], md=5),
        ], className="g-3 mb-3"),

        # Row 2: Monthly Trend + Price Analysis
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Graph(id="fig-monthly",
                              figure=fig_monthly_trend(),
                              config={"displayModeBar": False}),
                ], style=_card_style())
            ], md=7),
            dbc.Col([
                html.Div([
                    dcc.Graph(id="fig-price",
                              figure=fig_price_analysis(),
                              config={"displayModeBar": False}),
                ], style=_card_style())
            ], md=5),
        ], className="g-3 mb-3"),

        # Row 3: Invoice Delay + Discount Histogram
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Graph(id="fig-invoice",
                              figure=fig_invoice_delay(),
                              config={"displayModeBar": False}),
                ], style=_card_style())
            ], md=6),
            dbc.Col([
                html.Div([
                    dcc.Graph(id="fig-discount",
                              figure=fig_discount_histogram(),
                              config={"displayModeBar": False}),
                ], style=_card_style())
            ], md=6),
        ], className="g-3 mb-3"),

        # Footer
        html.Div([
            html.P(
                "Vendor Performance Analysis Project · Python + SQL + EDA + Hypothesis Testing",
                style={"textAlign": "center", "color": MUTED, "fontSize": "12px",
                       "margin": "32px 0 16px 0"}
            )
        ])

    ], style={
        "maxWidth": "1600px", "margin": "0 auto",
        "padding": "24px", "fontFamily": "Inter, sans-serif",
    })

], style={"background": DARK_BG, "minHeight": "100vh"})


# ── Callbacks ─────────────────────────────────────────────────────────────────
@app.callback(
    Output("fig-top-vendors", "figure"),
    Input("top-n-select", "value"),
)
def update_top_vendors(n):
    return fig_top_vendors(int(n))


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  VENDOR PERFORMANCE DASHBOARD")
    print("=" * 60)
    print(f"\n  Data loaded:")
    print(f"    Vendors : {total_vendors:,}")
    print(f"    Spend   : ${total_spend/1e6:.1f}M")
    print(f"    Months  : {len(mth)}")
    print("\n  🌐 Dashboard running at: http://127.0.0.1:8050")
    print("  Press Ctrl+C to stop\n")
    app.run(debug=False, port=8050, host="127.0.0.1")
