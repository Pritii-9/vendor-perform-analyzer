# -*- coding: utf-8 -*-
"""
=============================================================
  VENDOR PERFORMANCE ANALYSIS - Phase 1: SQL Setup
  Load CSVs -> SQLite DB -> SQL Aggregations -> Save Table
=============================================================
"""

import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import sqlite3
import pandas as pd
import os
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
DB_PATH    = BASE_DIR / "vendor_analysis.db"
REPORTS    = BASE_DIR / "reports"
REPORTS.mkdir(exist_ok=True)

print("=" * 60)
print("  VENDOR PERFORMANCE ANALYSIS — SQL SETUP")
print("=" * 60)

# ── 1. Load CSVs ──────────────────────────────────────────────────────────────
def load_csv(name, parse_dates=None):
    path = DATA_DIR / name
    print(f"\n📂 Loading {name}  ({path.stat().st_size / 1e6:.1f} MB)...")
    df = pd.read_csv(path, parse_dates=parse_dates, low_memory=False)
    print(f"   ✅ {df.shape[0]:,} rows × {df.shape[1]} columns")
    return df

print("\n── STEP 1: Loading Datasets ──────────────────────────────────")

begin_inv       = load_csv("begin_inventory.csv")
end_inv         = load_csv("end_inventory.csv")
purchase_prices = load_csv("purchase_prices.csv")
purchases       = load_csv("purchases.csv",       parse_dates=["PODate", "ReceivingDate", "InvoiceDate", "PayDate"])
vendor_invoice  = load_csv("vendor_invoice.csv",  parse_dates=["InvoiceDate", "PODate", "PayDate"])

# Sales is very large — load a sample for EDA performance
print(f"\n📂 Loading sales.csv  (large file — sampling 1M rows)...")
sales = pd.read_csv(DATA_DIR / "sales.csv", low_memory=False, nrows=1_000_000)
print(f"   ✅ {sales.shape[0]:,} rows × {sales.shape[1]} columns (sample)")

# ── 2. Preview schemas ────────────────────────────────────────────────────────
print("\n── STEP 2: Schema Preview ────────────────────────────────────")
for name, df in [
    ("begin_inventory",  begin_inv),
    ("end_inventory",    end_inv),
    ("purchase_prices",  purchase_prices),
    ("purchases",        purchases),
    ("vendor_invoice",   vendor_invoice),
    ("sales",            sales),
]:
    print(f"\n  [{name}]  {df.shape}")
    print(f"  Columns: {list(df.columns)}")

# ── 3. Write to SQLite ────────────────────────────────────────────────────────
print("\n── STEP 3: Writing to SQLite ─────────────────────────────────")

conn = sqlite3.connect(DB_PATH)

tables = {
    "begin_inventory":  begin_inv,
    "end_inventory":    end_inv,
    "purchase_prices":  purchase_prices,
    "purchases":        purchases,
    "vendor_invoice":   vendor_invoice,
    "sales":            sales,
}

for tbl, df in tables.items():
    print(f"   ↳ Writing {tbl}...", end=" ")
    df.to_sql(tbl, conn, if_exists="replace", index=False, chunksize=10_000)
    print("done")

print(f"\n   ✅ SQLite DB created at: {DB_PATH}")

# ── 4. SQL Cleaning & Aggregations ───────────────────────────────────────────
print("\n── STEP 4: SQL Aggregations ──────────────────────────────────")

SQL_VENDOR_SUMMARY = """
SELECT
    p.VendorNumber,
    p.VendorName,
    COUNT(DISTINCT p.PONumber)                             AS total_orders,
    COUNT(p.InventoryId)                                   AS total_line_items,
    SUM(p.Quantity)                                        AS total_qty_purchased,
    ROUND(SUM(p.Dollars), 2)                               AS total_purchase_dollars,
    ROUND(AVG(p.Dollars / NULLIF(p.Quantity, 0)), 4)       AS avg_actual_price_per_unit,
    ROUND(AVG(pp.PurchasePrice), 4)                        AS avg_list_price_per_unit,
    ROUND(
        (AVG(pp.PurchasePrice) - AVG(p.Dollars / NULLIF(p.Quantity, 0)))
        / NULLIF(AVG(pp.PurchasePrice), 0) * 100, 2
    )                                                      AS price_discount_pct,
    COUNT(DISTINCT p.Store)                                AS stores_served,
    COUNT(DISTINCT p.Brand)                                AS brands_supplied,
    ROUND(
        AVG(
            julianday(p.InvoiceDate) - julianday(p.PODate)
        ), 1
    )                                                      AS avg_days_to_invoice,
    ROUND(
        AVG(
            julianday(p.PayDate) - julianday(p.InvoiceDate)
        ), 1
    )                                                      AS avg_days_to_pay
FROM purchases p
LEFT JOIN purchase_prices pp
    ON p.VendorNumber = pp.VendorNumber
    AND p.Brand       = pp.Brand
    AND p.Description = pp.Description
GROUP BY p.VendorNumber, p.VendorName
HAVING total_purchase_dollars > 0
ORDER BY total_purchase_dollars DESC;
"""

print("   Running vendor summary query...")
vendor_summary = pd.read_sql_query(SQL_VENDOR_SUMMARY, conn)
print(f"   ✅ vendor_summary: {vendor_summary.shape}")

# ── 5. Classify Vendors (A/B/C by spend) ─────────────────────────────────────
vendor_summary = vendor_summary.sort_values("total_purchase_dollars", ascending=False)
vendor_summary["cumulative_pct"] = (
    vendor_summary["total_purchase_dollars"].cumsum()
    / vendor_summary["total_purchase_dollars"].sum() * 100
)

def classify_vendor(row):
    if row["cumulative_pct"] <= 80:
        return "A"   # Top 80% of spend
    elif row["cumulative_pct"] <= 95:
        return "B"   # Next 15%
    else:
        return "C"   # Bottom 5%

vendor_summary["vendor_class"] = vendor_summary.apply(classify_vendor, axis=1)
print(f"\n   Vendor Classification:")
print(vendor_summary["vendor_class"].value_counts().to_string())

# ── 6. Gross Margin per Vendor ────────────────────────────────────────────────
SQL_SALES_VENDOR = """
SELECT
    s.VendorNo                                              AS VendorNumber,
    s.VendorName,
    ROUND(SUM(s.SalesDollars), 2)                           AS total_sales_dollars,
    SUM(s.SalesQuantity)                                    AS total_sales_qty,
    COUNT(s.InventoryId)                                    AS sales_line_items
FROM sales s
GROUP BY s.VendorNo, s.VendorName
ORDER BY total_sales_dollars DESC;
"""

print("\n   Running vendor sales query...")
try:
    vendor_sales = pd.read_sql_query(SQL_SALES_VENDOR, conn)
    print(f"   ✅ vendor_sales: {vendor_sales.shape}")

    # Merge with vendor_summary to compute gross margin
    vendor_full = vendor_summary.merge(
        vendor_sales[["VendorNumber", "total_sales_dollars"]],
        on="VendorNumber",
        how="left"
    )
    vendor_full["gross_margin_dollars"] = (
        vendor_full["total_sales_dollars"] - vendor_full["total_purchase_dollars"]
    )
    vendor_full["gross_margin_pct"] = (
        vendor_full["gross_margin_dollars"]
        / vendor_full["total_sales_dollars"].replace(0, pd.NA) * 100
    ).round(2)
except Exception as e:
    print(f"   ⚠️  Could not compute gross margin: {e}")
    vendor_full = vendor_summary.copy()
    vendor_full["total_sales_dollars"]   = None
    vendor_full["gross_margin_dollars"]  = None
    vendor_full["gross_margin_pct"]      = None

# ── 7. Monthly Purchase Trend ─────────────────────────────────────────────────
SQL_MONTHLY = """
SELECT
    strftime('%Y-%m', PODate)     AS year_month,
    SUM(Quantity)                 AS total_qty,
    ROUND(SUM(Dollars), 2)        AS total_spend,
    COUNT(DISTINCT VendorNumber)  AS active_vendors,
    COUNT(DISTINCT PONumber)      AS total_orders
FROM purchases
WHERE PODate IS NOT NULL
GROUP BY year_month
ORDER BY year_month;
"""
print("\n   Running monthly trend query...")
monthly_trend = pd.read_sql_query(SQL_MONTHLY, conn)
print(f"   ✅ monthly_trend: {monthly_trend.shape}")

# ── 8. Save aggregated tables back to DB ─────────────────────────────────────
print("\n── STEP 5: Saving Aggregated Tables ─────────────────────────")
vendor_full.to_sql("vendor_summary",  conn, if_exists="replace", index=False)
monthly_trend.to_sql("monthly_trend", conn, if_exists="replace", index=False)
print("   ✅ vendor_summary  → SQLite")
print("   ✅ monthly_trend   → SQLite")

# Also export to CSV for easy access
vendor_full.to_csv(REPORTS / "vendor_summary.csv", index=False)
monthly_trend.to_csv(REPORTS / "monthly_trend.csv", index=False)
print("   ✅ Exported CSVs to reports/")

conn.close()

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  SQL SETUP COMPLETE ✅")
print("=" * 60)
print(f"\n  DB path     : {DB_PATH}")
print(f"  Vendors     : {len(vendor_full):,}")
print(f"  Total spend : ${vendor_full['total_purchase_dollars'].sum():,.0f}")
print(f"  Months      : {len(monthly_trend)}")
print(f"\n  Run next: python notebooks/02_eda_analysis.py")
