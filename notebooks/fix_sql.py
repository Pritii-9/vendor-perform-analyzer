"""Quick fix: Run just the monthly trend + save aggregations"""
import sqlite3, pandas as pd
from pathlib import Path

DB_PATH = Path('vendor_analysis.db')
REPORTS = Path('reports')
REPORTS.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)

print("Re-running vendor_summary...")
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
    ROUND(AVG(julianday(p.InvoiceDate) - julianday(p.PODate)), 1) AS avg_days_to_invoice,
    ROUND(AVG(julianday(p.PayDate) - julianday(p.InvoiceDate)), 1) AS avg_days_to_pay
FROM purchases p
LEFT JOIN purchase_prices pp
    ON p.VendorNumber = pp.VendorNumber
    AND p.Brand = pp.Brand
    AND p.Description = pp.Description
GROUP BY p.VendorNumber, p.VendorName
HAVING total_purchase_dollars > 0
ORDER BY total_purchase_dollars DESC;
"""
vs = pd.read_sql_query(SQL_VENDOR_SUMMARY, conn)
vs = vs.sort_values('total_purchase_dollars', ascending=False)
vs['cumulative_pct'] = vs['total_purchase_dollars'].cumsum() / vs['total_purchase_dollars'].sum() * 100
vs['vendor_class'] = vs['cumulative_pct'].apply(lambda x: 'A' if x <= 80 else ('B' if x <= 95 else 'C'))
print(f"  vendor_summary: {vs.shape}")
print(vs['vendor_class'].value_counts().to_string())

print("\nRunning sales aggregation...")
SQL_SALES = """
SELECT s.VendorNo AS VendorNumber, s.VendorName,
    ROUND(SUM(s.SalesDollars), 2) AS total_sales_dollars,
    SUM(s.SalesQuantity) AS total_sales_qty
FROM sales s GROUP BY s.VendorNo, s.VendorName ORDER BY total_sales_dollars DESC;
"""
vsal = pd.read_sql_query(SQL_SALES, conn)
print(f"  vendor_sales: {vsal.shape}")

vf = vs.merge(vsal[['VendorNumber', 'total_sales_dollars']], on='VendorNumber', how='left')
vf['gross_margin_dollars'] = vf['total_sales_dollars'] - vf['total_purchase_dollars']
vf['gross_margin_pct'] = (
    vf['gross_margin_dollars'] / vf['total_sales_dollars'].replace(0, None) * 100
).round(2)

print("\nRunning monthly trend...")
SQL_MTH = """
SELECT
    strftime('%Y-%m', PODate) AS year_month,
    SUM(Quantity) AS total_qty,
    ROUND(SUM(Dollars), 2) AS total_spend,
    COUNT(DISTINCT VendorNumber) AS active_vendors,
    COUNT(DISTINCT PONumber) AS total_orders
FROM purchases
WHERE PODate IS NOT NULL
GROUP BY year_month
ORDER BY year_month;
"""
mth = pd.read_sql_query(SQL_MTH, conn)
print(f"  monthly_trend: {mth.shape}")
print(mth.head())

print("\nSaving to DB and CSV...")
vf.to_sql('vendor_summary', conn, if_exists='replace', index=False)
mth.to_sql('monthly_trend', conn, if_exists='replace', index=False)
vf.to_csv(REPORTS / 'vendor_summary.csv', index=False)
mth.to_csv(REPORTS / 'monthly_trend.csv', index=False)
conn.close()

print("\n[DONE] SQL Setup Complete!")
print(f"  Vendors     : {len(vf)}")
print(f"  Total spend : ${vf['total_purchase_dollars'].sum():,.0f}")
print(f"  Months      : {len(mth)}")
