"""
=============================================================
  VENDOR PERFORMANCE ANALYSIS — Phase 2: EDA & Visualizations
  Pandas | Matplotlib | Seaborn
=============================================================
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "vendor_analysis.db"
REPORTS  = BASE_DIR / "reports"
REPORTS.mkdir(exist_ok=True)

# ── Premium style ─────────────────────────────────────────────────────────────
DARK_BG   = "#0f1117"
CARD_BG   = "#1a1d2e"
ACCENT1   = "#6c63ff"   # purple
ACCENT2   = "#f72585"   # pink
ACCENT3   = "#4cc9f0"   # cyan
ACCENT4   = "#f8961e"   # orange
ACCENT5   = "#43aa8b"   # green
TEXT      = "#e0e0e0"
GRID      = "#2a2d3e"

PALETTE   = [ACCENT1, ACCENT2, ACCENT3, ACCENT4, ACCENT5,
             "#9b5de5", "#fee440", "#00bbf9", "#00f5d4", "#f15bb5"]

plt.rcParams.update({
    "figure.facecolor":  DARK_BG,
    "axes.facecolor":    CARD_BG,
    "axes.edgecolor":    GRID,
    "axes.labelcolor":   TEXT,
    "xtick.color":       TEXT,
    "ytick.color":       TEXT,
    "text.color":        TEXT,
    "grid.color":        GRID,
    "grid.linewidth":    0.6,
    "legend.facecolor":  CARD_BG,
    "legend.edgecolor":  GRID,
    "font.family":       "DejaVu Sans",
    "axes.spines.top":   False,
    "axes.spines.right": False,
})

def save_fig(name):
    path = REPORTS / name
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    print(f"   💾 Saved → {path.name}")

# ── Load data ─────────────────────────────────────────────────────────────────
print("=" * 60)
print("  VENDOR PERFORMANCE ANALYSIS — EDA")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
df   = pd.read_sql("SELECT * FROM vendor_summary",  conn)
mth  = pd.read_sql("SELECT * FROM monthly_trend",   conn)
conn.close()

print(f"\n✅ vendor_summary loaded: {df.shape}")
print(f"✅ monthly_trend  loaded: {mth.shape}")

# ── 1. Basic EDA ──────────────────────────────────────────────────────────────
print("\n── STEP 1: Basic EDA ─────────────────────────────────────────")
print(f"\n  Shape         : {df.shape}")
print(f"  Null counts   :\n{df.isnull().sum()[df.isnull().sum()>0].to_string()}")
print(f"\n  Numeric summary:\n{df.describe().round(2).to_string()}")

# ── 2. KPI Summary Card ───────────────────────────────────────────────────────
print("\n── STEP 2: KPI Summary ───────────────────────────────────────")

total_vendors  = len(df)
total_spend    = df["total_purchase_dollars"].sum()
total_orders   = df["total_orders"].sum()
avg_discount   = df["price_discount_pct"].median()
class_a_cnt    = (df["vendor_class"] == "A").sum()
avg_days_inv   = df["avg_days_to_invoice"].median()

kpis = [
    ("Total Vendors",       f"{total_vendors:,}",          ACCENT1),
    ("Total Purchase Spend",f"${total_spend/1e6:.1f}M",    ACCENT2),
    ("Total PO Orders",     f"{total_orders:,}",            ACCENT3),
    ("Avg Price Discount",  f"{avg_discount:.1f}%",         ACCENT4),
    ("Class-A Vendors",     f"{class_a_cnt}",               ACCENT5),
    ("Avg Days to Invoice", f"{avg_days_inv:.0f} days",     "#9b5de5"),
]

fig, axes = plt.subplots(1, 6, figsize=(22, 3.5))
fig.suptitle("Vendor Performance — Key Metrics", fontsize=16, fontweight="bold",
             color=TEXT, y=1.02)

for ax, (label, value, color) in zip(axes, kpis):
    ax.set_facecolor(CARD_BG)
    ax.axis("off")
    # Glow circle background
    circle = plt.Circle((0.5, 0.55), 0.38, color=color, alpha=0.12,
                         transform=ax.transAxes)
    ax.add_patch(circle)
    ax.text(0.5, 0.62, value, ha="center", va="center", fontsize=18,
            fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0.5, 0.25, label, ha="center", va="center", fontsize=9,
            color=TEXT, transform=ax.transAxes, wrap=True)
    for spine in ax.spines.values():
        spine.set_visible(False)

plt.tight_layout()
save_fig("00_kpi_summary.png")

# ── 3. Top 15 Vendors by Purchase Spend ──────────────────────────────────────
print("\n── STEP 3: Top 15 Vendors by Spend ──────────────────────────")
top15 = df.nlargest(15, "total_purchase_dollars").copy()
top15["label"] = top15["VendorName"].str[:22]

fig, ax = plt.subplots(figsize=(14, 7))
bars = ax.barh(
    top15["label"][::-1],
    top15["total_purchase_dollars"][::-1] / 1e6,
    color=[PALETTE[i % len(PALETTE)] for i in range(len(top15))],
    edgecolor="none",
    height=0.7,
)

# Value labels
for bar in bars:
    w = bar.get_width()
    ax.text(w + 0.02, bar.get_y() + bar.get_height() / 2,
            f"${w:.2f}M", va="center", ha="left", fontsize=9, color=TEXT)

ax.set_xlabel("Total Purchase Spend ($ Million)", fontsize=11)
ax.set_title("Top 15 Vendors by Purchase Spend", fontsize=15,
             fontweight="bold", pad=15)
ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:.1f}M"))
ax.grid(axis="x", alpha=0.4)
plt.tight_layout()
save_fig("01_top15_vendors_spend.png")

# ── 4. Vendor Classification (A/B/C) ─────────────────────────────────────────
print("\n── STEP 4: Vendor Classification ────────────────────────────")
class_data = df.groupby("vendor_class")["total_purchase_dollars"].sum()
class_cnt  = df["vendor_class"].value_counts()
class_colors = [ACCENT1, ACCENT4, ACCENT2]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Donut — spend share
wedges, _, autotexts = ax1.pie(
    class_data, labels=None, autopct="%1.1f%%",
    colors=class_colors, startangle=90,
    wedgeprops=dict(width=0.55, edgecolor=DARK_BG, linewidth=2),
    pctdistance=0.75
)
for t in autotexts:
    t.set_color(TEXT); t.set_fontsize(11)
ax1.set_facecolor(DARK_BG)
legend_labels = [f"Class {c} — ${v/1e6:.1f}M"
                 for c, v in zip(class_data.index, class_data.values)]
ax1.legend(wedges, legend_labels, loc="lower center",
           bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=9)
ax1.set_title("Spend Share by Vendor Class", fontsize=13, fontweight="bold")

# Bar — vendor count
bars2 = ax2.bar(class_cnt.index, class_cnt.values, color=class_colors,
                width=0.5, edgecolor="none")
for bar in bars2:
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
             str(int(bar.get_height())), ha="center", fontsize=12,
             fontweight="bold", color=TEXT)
ax2.set_xlabel("Vendor Class")
ax2.set_ylabel("Number of Vendors")
ax2.set_title("Vendor Count by Class (A/B/C)", fontsize=13, fontweight="bold")
ax2.grid(axis="y", alpha=0.4)

plt.suptitle("ABC Vendor Classification — Pareto Analysis",
             fontsize=15, fontweight="bold", y=1.02)
plt.tight_layout()
save_fig("02_vendor_classification.png")

# ── 5. Price Discount Analysis ────────────────────────────────────────────────
print("\n── STEP 5: Price Discount Analysis ──────────────────────────")
disc_df = df.dropna(subset=["price_discount_pct"])
disc_df = disc_df[disc_df["price_discount_pct"].between(-100, 200)]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# Histogram
ax1.hist(disc_df["price_discount_pct"], bins=40, color=ACCENT1,
         edgecolor=DARK_BG, alpha=0.85)
ax1.axvline(disc_df["price_discount_pct"].mean(), color=ACCENT2,
            linestyle="--", lw=2, label=f'Mean: {disc_df["price_discount_pct"].mean():.1f}%')
ax1.axvline(disc_df["price_discount_pct"].median(), color=ACCENT4,
            linestyle=":", lw=2, label=f'Median: {disc_df["price_discount_pct"].median():.1f}%')
ax1.set_xlabel("Price Discount %")
ax1.set_ylabel("Vendor Count")
ax1.set_title("Distribution of Price Discounts", fontsize=13, fontweight="bold")
ax1.legend()
ax1.grid(axis="y", alpha=0.4)

# Scatter — spend vs discount
sc = ax2.scatter(
    disc_df["total_purchase_dollars"] / 1e6,
    disc_df["price_discount_pct"],
    c=disc_df["total_orders"],
    cmap="plasma",
    alpha=0.7, s=50, edgecolors="none"
)
plt.colorbar(sc, ax=ax2, label="Total Orders")
ax2.axhline(0, color=ACCENT2, linestyle="--", lw=1)
ax2.set_xlabel("Total Purchase Spend ($M)")
ax2.set_ylabel("Price Discount %")
ax2.set_title("Spend vs Price Discount per Vendor", fontsize=13, fontweight="bold")
ax2.grid(alpha=0.3)

plt.suptitle("Vendor Price Discount Analysis", fontsize=15,
             fontweight="bold", y=1.02)
plt.tight_layout()
save_fig("03_price_discount_analysis.png")

# ── 6. Monthly Purchase Trend ─────────────────────────────────────────────────
print("\n── STEP 6: Monthly Purchase Trend ───────────────────────────")
mth = mth.dropna(subset=["year_month"])
mth["period"]     = pd.to_datetime(mth["year_month"], format="%Y-%m", errors="coerce")
mth               = mth.dropna(subset=["period"]).sort_values("period")
mth["total_spend_m"] = mth["total_spend"] / 1e6

fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

# Spend line
ax = axes[0]
ax.fill_between(mth["period"], mth["total_spend_m"],
                alpha=0.2, color=ACCENT1)
ax.plot(mth["period"], mth["total_spend_m"],
        color=ACCENT1, lw=2.5, marker="o", markersize=4)
ax.set_ylabel("Total Spend ($M)", fontsize=11)
ax.set_title("Monthly Purchase Spend", fontsize=13, fontweight="bold")
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"${x:.1f}M"))
ax.grid(axis="y", alpha=0.4)

# Active vendors line
ax2 = axes[1]
ax2.fill_between(mth["period"], mth["active_vendors"],
                 alpha=0.2, color=ACCENT3)
ax2.plot(mth["period"], mth["active_vendors"],
         color=ACCENT3, lw=2.5, marker="s", markersize=4)
ax2.set_ylabel("Active Vendors", fontsize=11)
ax2.set_xlabel("Month", fontsize=11)
ax2.set_title("Active Vendors per Month", fontsize=13, fontweight="bold")
ax2.grid(axis="y", alpha=0.4)

fig.suptitle("Monthly Purchase Trend Analysis", fontsize=16,
             fontweight="bold", y=1.01)
plt.tight_layout()
save_fig("04_monthly_trend.png")

# ── 7. Top Brands per Vendor ──────────────────────────────────────────────────
print("\n── STEP 7: Brands per Vendor ─────────────────────────────────")
fig, ax = plt.subplots(figsize=(12, 6))
top_brands = df.nlargest(20, "brands_supplied")[["VendorName", "brands_supplied"]]
top_brands["short_name"] = top_brands["VendorName"].str[:20]

bars = ax.bar(top_brands["short_name"], top_brands["brands_supplied"],
              color=[PALETTE[i % len(PALETTE)] for i in range(len(top_brands))],
              edgecolor="none")
for bar in bars:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
            str(int(bar.get_height())), ha="center", fontsize=8,
            fontweight="bold", color=TEXT)
ax.set_xlabel("Vendor")
ax.set_ylabel("Number of Brands Supplied")
ax.set_title("Top 20 Vendors by Brand Diversity", fontsize=14, fontweight="bold")
plt.xticks(rotation=45, ha="right", fontsize=8)
ax.grid(axis="y", alpha=0.4)
plt.tight_layout()
save_fig("05_brand_diversity.png")

# ── 8. Stores Served Distribution ────────────────────────────────────────────
print("\n── STEP 8: Stores Served Distribution ───────────────────────")
fig, ax = plt.subplots(figsize=(12, 5))
ax.hist(df["stores_served"].dropna(), bins=30, color=ACCENT5,
        edgecolor=DARK_BG, alpha=0.85)
ax.axvline(df["stores_served"].mean(), color=ACCENT2, linestyle="--",
           lw=2, label=f'Mean: {df["stores_served"].mean():.1f}')
ax.set_xlabel("Number of Stores Served")
ax.set_ylabel("Vendor Count")
ax.set_title("Distribution — Stores Served per Vendor", fontsize=14, fontweight="bold")
ax.legend()
ax.grid(axis="y", alpha=0.4)
plt.tight_layout()
save_fig("06_stores_served_distribution.png")

# ── 9. Correlation Heatmap ────────────────────────────────────────────────────
print("\n── STEP 9: Correlation Heatmap ──────────────────────────────")
num_cols = [
    "total_orders", "total_line_items", "total_qty_purchased",
    "total_purchase_dollars", "avg_actual_price_per_unit",
    "price_discount_pct", "stores_served", "brands_supplied",
    "avg_days_to_invoice", "avg_days_to_pay"
]
corr_df = df[num_cols].dropna()
corr    = corr_df.corr()

fig, ax = plt.subplots(figsize=(13, 10))
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(
    corr, mask=mask, annot=True, fmt=".2f", ax=ax,
    cmap=sns.diverging_palette(260, 10, as_cmap=True),
    linewidths=0.5, linecolor=DARK_BG,
    annot_kws={"size": 8}, center=0,
    cbar_kws={"shrink": 0.8}
)
ax.set_title("Feature Correlation Heatmap", fontsize=15, fontweight="bold", pad=15)
plt.tight_layout()
save_fig("07_correlation_heatmap.png")

# ── 10. Invoice Delay by Vendor Class ─────────────────────────────────────────
print("\n── STEP 10: Invoice Delay by Class ──────────────────────────")
inv_df = df.dropna(subset=["avg_days_to_invoice"])
inv_df = inv_df[inv_df["avg_days_to_invoice"].between(-10, 200)]

fig, ax = plt.subplots(figsize=(10, 6))
for i, cls in enumerate(["A", "B", "C"]):
    subset = inv_df[inv_df["vendor_class"] == cls]["avg_days_to_invoice"]
    ax.hist(subset, bins=30, alpha=0.65, color=class_colors[i],
            label=f"Class {cls} (n={len(subset)})", edgecolor="none")
ax.set_xlabel("Avg Days to Invoice")
ax.set_ylabel("Vendor Count")
ax.set_title("Invoice Delay Distribution by Vendor Class", fontsize=14, fontweight="bold")
ax.legend()
ax.grid(axis="y", alpha=0.4)
plt.tight_layout()
save_fig("08_invoice_delay_by_class.png")

# ── Done ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  EDA COMPLETE ✅")
print("=" * 60)
print(f"  Charts saved to: {REPORTS}")
charts = list(REPORTS.glob("*.png"))
for c in sorted(charts):
    print(f"  📊 {c.name}")
print(f"\n  Run next: python notebooks/03_hypothesis_testing.py")
