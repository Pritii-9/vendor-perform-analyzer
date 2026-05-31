"""
=============================================================
  VENDOR PERFORMANCE ANALYSIS — Phase 3: Hypothesis Testing
  t-tests | ANOVA | Confidence Intervals | Chi-Square
=============================================================
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "vendor_analysis.db"
REPORTS  = BASE_DIR / "reports"
REPORTS.mkdir(exist_ok=True)

DARK_BG  = "#0f1117"
CARD_BG  = "#1a1d2e"
ACCENT1  = "#6c63ff"
ACCENT2  = "#f72585"
ACCENT3  = "#4cc9f0"
ACCENT4  = "#f8961e"
ACCENT5  = "#43aa8b"
TEXT     = "#e0e0e0"
GRID     = "#2a2d3e"

plt.rcParams.update({
    "figure.facecolor": DARK_BG, "axes.facecolor": CARD_BG,
    "axes.edgecolor":   GRID,    "axes.labelcolor": TEXT,
    "xtick.color":      TEXT,    "ytick.color":     TEXT,
    "text.color":       TEXT,    "grid.color":      GRID,
    "grid.linewidth":   0.6,     "legend.facecolor": CARD_BG,
    "legend.edgecolor": GRID,    "font.family":     "DejaVu Sans",
    "axes.spines.top":  False,   "axes.spines.right": False,
})

def save_fig(name):
    path = REPORTS / name
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=DARK_BG)
    plt.close()
    print(f"   💾 Saved → {path.name}")

def print_test(title, stat, p, df_=None, alpha=0.05):
    print(f"\n  {'─'*50}")
    print(f"  {title}")
    print(f"  {'─'*50}")
    if df_ is not None:
        print(f"  Statistic : {stat:.4f}   df={df_}")
    else:
        print(f"  Statistic : {stat:.4f}")
    print(f"  p-value   : {p:.6f}")
    print(f"  α         : {alpha}")
    conclusion = "✅ REJECT H₀" if p < alpha else "❌ FAIL TO REJECT H₀"
    print(f"  Conclusion: {conclusion}  (p {'<' if p < alpha else '>='} α)")

# ── Load data ─────────────────────────────────────────────────────────────────
print("=" * 60)
print("  VENDOR PERFORMANCE ANALYSIS — HYPOTHESIS TESTING")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)
df   = pd.read_sql("SELECT * FROM vendor_summary", conn)
conn.close()

df = df.dropna(subset=["vendor_class"])
classA = df[df["vendor_class"] == "A"]
classB = df[df["vendor_class"] == "B"]
classC = df[df["vendor_class"] == "C"]

print(f"\n✅ Data loaded: {df.shape}  |  A={len(classA)}, B={len(classB)}, C={len(classC)}")

results = []   # Store test results for summary chart

# ══════════════════════════════════════════════════════════════════
# TEST 1: t-test — Class A vs Class B avg purchase price per unit
# ══════════════════════════════════════════════════════════════════
print("\n\n━━ TEST 1: Independent t-test ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  H₀: Avg actual price/unit for Class A = Class B")
print("  H₁: Class A vendors have significantly different pricing than Class B")

a_price = classA["avg_actual_price_per_unit"].dropna()
b_price = classB["avg_actual_price_per_unit"].dropna()

t_stat, p_t = stats.ttest_ind(a_price, b_price, equal_var=False)
print_test("Independent t-test: Class A vs Class B Price/Unit", t_stat, p_t)
results.append(("T-Test\nA vs B Price", p_t, t_stat))

# Confidence Intervals
def ci_95(series):
    mean = series.mean()
    se   = stats.sem(series)
    h    = se * stats.t.ppf(0.975, len(series) - 1)
    return mean - h, mean, mean + h

ci_a = ci_95(a_price)
ci_b = ci_95(b_price)

print(f"\n  Class A  95% CI: [{ci_a[0]:.4f}, {ci_a[2]:.4f}]  mean={ci_a[1]:.4f}")
print(f"  Class B  95% CI: [{ci_b[0]:.4f}, {ci_b[2]:.4f}]  mean={ci_b[1]:.4f}")

# ── Visualize Test 1 ──────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# KDE plot
ax = axes[0]
a_price.plot.kde(ax=ax, color=ACCENT1, lw=2.5, label=f"Class A (n={len(a_price)})")
b_price.plot.kde(ax=ax, color=ACCENT2, lw=2.5, label=f"Class B (n={len(b_price)})")
ax.axvline(a_price.mean(), color=ACCENT1, linestyle="--", alpha=0.6)
ax.axvline(b_price.mean(), color=ACCENT2, linestyle="--", alpha=0.6)
ax.set_xlabel("Avg Price Per Unit ($)")
ax.set_title("Price Distribution: Class A vs Class B", fontsize=12, fontweight="bold")
ax.legend()
ax.grid(axis="y", alpha=0.3)

# CI chart
ax2 = axes[1]
classes = ["Class A", "Class B"]
means   = [ci_a[1], ci_b[1]]
lows    = [ci_a[1] - ci_a[0], ci_b[1] - ci_b[0]]
highs   = [ci_a[2] - ci_a[1], ci_b[2] - ci_b[1]]
colors  = [ACCENT1, ACCENT2]

for i, (cls, mean, lo, hi, col) in enumerate(zip(classes, means, lows, highs, colors)):
    ax2.bar(i, mean, color=col, alpha=0.75, width=0.4)
    ax2.errorbar(i, mean, yerr=[[lo], [hi]], fmt="none",
                 color=TEXT, capsize=8, capthick=2, lw=2)
    ax2.text(i, mean + hi + 0.002, f"${mean:.3f}", ha="center",
             fontsize=11, fontweight="bold", color=col)

ax2.set_xticks([0, 1])
ax2.set_xticklabels(classes)
ax2.set_ylabel("Avg Price Per Unit ($)")
ax2.set_title(f"95% Confidence Intervals\n(p={p_t:.4f}  {'Significant ✓' if p_t < 0.05 else 'Not Significant'})",
              fontsize=12, fontweight="bold")
ax2.grid(axis="y", alpha=0.3)

plt.suptitle("Test 1: Class A vs B Pricing — Independent t-test",
             fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
save_fig("09_test1_ttest_pricing.png")

# ══════════════════════════════════════════════════════════════════
# TEST 2: One-Way ANOVA — Purchase dollars across A/B/C
# ══════════════════════════════════════════════════════════════════
print("\n\n━━ TEST 2: One-Way ANOVA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  H₀: Mean purchase spend is equal across Class A, B, C")
print("  H₁: At least one class has a significantly different mean spend")

spend_a = classA["total_purchase_dollars"].dropna()
spend_b = classB["total_purchase_dollars"].dropna()
spend_c = classC["total_purchase_dollars"].dropna()

f_stat, p_anova = stats.f_oneway(spend_a, spend_b, spend_c)
print_test("One-Way ANOVA: Spend across A/B/C classes", f_stat, p_anova)
results.append(("ANOVA\nSpend A/B/C", p_anova, f_stat))

# Post-hoc Tukey-like pairwise (manual)
pairs = [("A vs B", spend_a, spend_b), ("A vs C", spend_a, spend_c),
         ("B vs C", spend_b, spend_c)]
print("\n  Pairwise t-tests (Bonferroni corrected α=0.017):")
for label, g1, g2 in pairs:
    t, p = stats.ttest_ind(g1, g2, equal_var=False)
    sig  = "✅ Sig" if p < 0.017 else "❌ NS"
    print(f"    {label}: t={t:.3f}, p={p:.6f}  {sig}")

# Visualize ANOVA
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Violin plot
ax = axes[0]
parts = ax.violinplot(
    [spend_a/1e6, spend_b/1e6, spend_c/1e6],
    positions=[1, 2, 3], showmedians=True, showmeans=True
)
colors_ = [ACCENT1, ACCENT4, ACCENT2]
for i, (pc, col) in enumerate(zip(parts["bodies"], colors_)):
    pc.set_facecolor(col); pc.set_alpha(0.6)
parts["cmedians"].set_color(TEXT)
parts["cmeans"].set_color(TEXT)
ax.set_xticks([1, 2, 3])
ax.set_xticklabels(["Class A", "Class B", "Class C"])
ax.set_ylabel("Purchase Spend ($M)")
ax.set_title("Spend Distribution by Vendor Class", fontsize=12, fontweight="bold")
ax.grid(axis="y", alpha=0.3)

# Box plot
ax2 = axes[1]
data_box = pd.DataFrame({
    "Spend_M": pd.concat([spend_a/1e6, spend_b/1e6, spend_c/1e6], ignore_index=True),
    "Class": (["A"] * len(spend_a)) + (["B"] * len(spend_b)) + (["C"] * len(spend_c))
})

sns.boxplot(data=data_box, x="Class", y="Spend_M", ax=ax2,
            palette={"A": ACCENT1, "B": ACCENT4, "C": ACCENT2},
            linewidth=1.5)
ax2.set_ylabel("Purchase Spend ($M)")
ax2.set_title(f"Box Plot — ANOVA F={f_stat:.2f}, p={p_anova:.4f}",
              fontsize=12, fontweight="bold")
ax2.grid(axis="y", alpha=0.3)

plt.suptitle("Test 2: One-Way ANOVA — Purchase Spend across Classes",
             fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
save_fig("10_test2_anova_spend.png")

# ══════════════════════════════════════════════════════════════════
# TEST 3: Confidence Intervals — Avg Days to Invoice
# ══════════════════════════════════════════════════════════════════
print("\n\n━━ TEST 3: Confidence Intervals — Invoice Delay ━━━━━━━━━━━━")
inv_df = df.dropna(subset=["avg_days_to_invoice"])
inv_df = inv_df[inv_df["avg_days_to_invoice"].between(-10, 200)]

ci_by_class = {}
for cls in ["A", "B", "C"]:
    subset = inv_df[inv_df["vendor_class"] == cls]["avg_days_to_invoice"]
    ci_by_class[cls] = ci_95(subset)
    lo, mean, hi = ci_by_class[cls]
    print(f"  Class {cls}: mean={mean:.2f}d  95% CI=[{lo:.2f}, {hi:.2f}]  n={len(subset)}")

fig, ax = plt.subplots(figsize=(10, 6))
cls_list = list(ci_by_class.keys())
colors_  = [ACCENT1, ACCENT4, ACCENT2]
for i, (cls, col) in enumerate(zip(cls_list, colors_)):
    lo, mean, hi = ci_by_class[cls]
    ax.barh(i, mean, color=col, alpha=0.75, height=0.5)
    ax.errorbar(mean, i, xerr=[[mean-lo], [hi-mean]],
                fmt="none", color=TEXT, capsize=8, capthick=2, lw=2)
    ax.text(hi + 0.3, i, f"{mean:.1f} days", va="center",
            fontsize=11, fontweight="bold", color=col)

ax.set_yticks(range(len(cls_list)))
ax.set_yticklabels([f"Class {c}" for c in cls_list], fontsize=12)
ax.set_xlabel("Avg Days to Invoice")
ax.set_title("95% Confidence Intervals — Avg Days to Invoice by Vendor Class",
             fontsize=13, fontweight="bold")
ax.grid(axis="x", alpha=0.4)
plt.tight_layout()
save_fig("11_test3_ci_invoice_delay.png")
results.append(("CI\nInvoice Delay", None, None))

# ══════════════════════════════════════════════════════════════════
# TEST 4: Chi-Square — Vendor Class vs High Invoice Delay Flag
# ══════════════════════════════════════════════════════════════════
print("\n\n━━ TEST 4: Chi-Square Test ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  H₀: Vendor class is independent of invoice delay severity")
print("  H₁: There is a significant association between class and delay")

median_delay   = inv_df["avg_days_to_invoice"].median()
inv_df         = inv_df.copy()
inv_df["high_delay"] = (inv_df["avg_days_to_invoice"] > median_delay).astype(int)
contingency    = pd.crosstab(inv_df["vendor_class"], inv_df["high_delay"])
contingency.columns = ["Low Delay", "High Delay"]
print(f"\n  Contingency Table:\n{contingency.to_string()}")

chi2, p_chi, dof, expected = stats.chi2_contingency(contingency)
print_test("Chi-Square: Vendor Class vs Invoice Delay", chi2, p_chi, dof)
results.append(("Chi-Square\nClass × Delay", p_chi, chi2))

# Visualize Chi-Square
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Stacked bar
ax = axes[0]
contingency_pct = contingency.div(contingency.sum(axis=1), axis=0) * 100
contingency_pct.plot(
    kind="bar", stacked=True, ax=ax,
    color=[ACCENT5, ACCENT2], edgecolor="none", width=0.5
)
ax.set_xlabel("Vendor Class")
ax.set_ylabel("Percentage of Vendors")
ax.set_title("Invoice Delay by Vendor Class (Stacked)", fontsize=12, fontweight="bold")
ax.legend(["Low Delay", "High Delay"])
plt.setp(ax.xaxis.get_majorticklabels(), rotation=0)
ax.grid(axis="y", alpha=0.3)

# Heatmap of contingency table
ax2 = axes[1]
sns.heatmap(contingency, annot=True, fmt="d", ax=ax2,
            cmap="RdPu", linewidths=0.5, linecolor=DARK_BG,
            cbar_kws={"shrink": 0.8})
ax2.set_title(f"Contingency Table\n(χ²={chi2:.2f}, p={p_chi:.4f})",
              fontsize=12, fontweight="bold")
ax2.set_xlabel("Invoice Delay Severity")
ax2.set_ylabel("Vendor Class")

plt.suptitle("Test 4: Chi-Square — Vendor Class vs Invoice Delay",
             fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
save_fig("12_test4_chisquare_delay.png")

# ══════════════════════════════════════════════════════════════════
# TEST 5: Correlation — Spend vs Price Discount
# ══════════════════════════════════════════════════════════════════
print("\n\n━━ TEST 5: Pearson Correlation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("  H₀: No linear correlation between spend and price discount")
print("  H₁: There is a significant linear correlation")

corr_df = df.dropna(subset=["total_purchase_dollars", "price_discount_pct"])
corr_df = corr_df[corr_df["price_discount_pct"].between(-100, 200)]

r, p_corr = stats.pearsonr(
    corr_df["total_purchase_dollars"],
    corr_df["price_discount_pct"]
)
print_test("Pearson Correlation: Spend vs Price Discount", r, p_corr)
print(f"  r = {r:.4f}  (effect: {'strong' if abs(r)>0.5 else 'moderate' if abs(r)>0.3 else 'weak'})")
results.append(("Pearson Corr\nSpend×Discount", p_corr, r))

# ── Summary Results Chart ─────────────────────────────────────────
print("\n── Summary Results Chart ─────────────────────────────────────")
fig, ax = plt.subplots(figsize=(12, 6))

test_labels = [r[0] for r in results if r[1] is not None]
p_values    = [r[1] for r in results if r[1] is not None]
colors_     = [ACCENT5 if p < 0.05 else ACCENT2 for p in p_values]

bars = ax.bar(test_labels, p_values, color=colors_, edgecolor="none", width=0.5)
ax.axhline(0.05, color=ACCENT4, linestyle="--", lw=2,
           label="α = 0.05 threshold")
for bar, p in zip(bars, p_values):
    ax.text(bar.get_x() + bar.get_width()/2,
            bar.get_height() + max(p_values) * 0.02,
            f"{p:.4f}", ha="center", fontsize=9, fontweight="bold",
            color=TEXT)

sig_patch  = mpatches.Patch(color=ACCENT5, label="Significant (p < 0.05)")
nsig_patch = mpatches.Patch(color=ACCENT2, label="Not Significant")
ax.legend(handles=[sig_patch, nsig_patch, plt.Line2D([0],[0], color=ACCENT4,
          linestyle="--", label="α=0.05")])
ax.set_ylabel("p-value")
ax.set_title("Hypothesis Testing Summary — p-values", fontsize=14, fontweight="bold")
ax.grid(axis="y", alpha=0.3)
plt.tight_layout()
save_fig("13_hypothesis_summary.png")

# ── Done ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  HYPOTHESIS TESTING COMPLETE ✅")
print("=" * 60)
print(f"\n  All results saved to: {REPORTS}")
print(f"\n  Run next: python notebooks/04_dashboard.py")
