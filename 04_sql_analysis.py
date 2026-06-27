"""
SQL Analysis Layer (DuckDB) + Inventory Bottleneck Analysis
===========================================================
Closes resume gaps:
  - "analyzing supply-chain records in SQL and Pandas"  -> real SQL queries here
  - "inventory bottlenecks"                             -> dedicated inventory analysis + charts
Builds a queryable SQL database from all 8 CSVs, runs analytical queries,
and exports results + visualizations.
"""
import os, json
import duckdb, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style("whitegrid")
P={"blue":"#185FA5","green":"#3B6D11","red":"#A32D2D","amber":"#854F0B","orange":"#d97706","teal":"#0E7490"}
plt.rcParams.update({"figure.dpi":130,"savefig.dpi":150,"font.size":11,"axes.titleweight":"bold","figure.facecolor":"white"})
U="uploads/"; CHART="supplychain_project/charts/"; DATA="supplychain_project/data/"; SQL="supplychain_project/sql/"
os.makedirs(SQL, exist_ok=True)

# ------------------------------------------------ build SQL database
print("Building DuckDB database from CSVs ...")
con=duckdb.connect(DATA+"supply_chain.duckdb")
tables={
 "dim_plants":"dim_plants.csv","dim_products":"dim_products.csv","dim_suppliers":"dim_suppliers.csv",
 "fact_disruptions":"fact_disruptions.csv","fact_inventory_buffer":"fact_inventory_buffer.csv",
 "fact_purchase_orders":"fact_purchase_orders.csv","fact_supplier_network":"fact_supplier_network.csv",
 "fact_supplier_scorecard":"fact_supplier_scorecard.csv"}
for t,f in tables.items():
    con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT * FROM read_csv_auto('{U}{f}')")
print("Tables loaded:", [r[0] for r in con.execute("SHOW TABLES").fetchall()])

# ------------------------------------------------ analytical SQL queries
queries = {}

queries["q1_shipment_delays_by_supplier"] = """
SELECT s.supplier_name, s.category, s.tier,
       COUNT(*) AS total_orders,
       SUM(CASE WHEN po.on_time_delivery='N' THEN 1 ELSE 0 END) AS late_orders,
       ROUND(100.0*SUM(CASE WHEN po.on_time_delivery='N' THEN 1 ELSE 0 END)/COUNT(*),1) AS late_pct,
       ROUND(AVG(po.delay_days),1) AS avg_delay_days
FROM fact_purchase_orders po
JOIN dim_suppliers s ON po.supplier_id=s.supplier_id
GROUP BY 1,2,3
HAVING COUNT(*) >= 10
ORDER BY late_pct DESC
LIMIT 20;"""

queries["q2_supplier_risk_overview"] = """
SELECT s.risk_band,
       COUNT(DISTINCT s.supplier_id) AS suppliers,
       ROUND(AVG(sc.composite_score),1) AS avg_scorecard,
       SUM(d.disruptions) AS total_disruptions,
       ROUND(SUM(d.loss)/1e6,1) AS total_loss_musd
FROM dim_suppliers s
LEFT JOIN (SELECT supplier_id, AVG(composite_score) composite_score FROM fact_supplier_scorecard GROUP BY 1) sc
       ON s.supplier_id=sc.supplier_id
LEFT JOIN (SELECT supplier_id, COUNT(*) disruptions, SUM(financial_loss_usd) loss FROM fact_disruptions GROUP BY 1) d
       ON s.supplier_id=d.supplier_id
GROUP BY 1
ORDER BY CASE s.risk_band WHEN 'High' THEN 3 WHEN 'Medium' THEN 2 ELSE 1 END DESC;"""

queries["q3_inventory_bottlenecks"] = """
SELECT pl.plant_name, pr.product_name, pr.criticality,
       i.current_stock, i.reorder_point, i.safety_stock,
       ROUND(i.days_of_stock,1) AS days_of_stock,
       i.is_shortage_risk,
       ROUND(i.current_stock - i.reorder_point,0) AS stock_vs_reorder
FROM fact_inventory_buffer i
JOIN dim_plants pl  ON i.plant_id=pl.plant_id
JOIN dim_products pr ON i.product_id=pr.product_id
WHERE i.current_stock < i.reorder_point OR i.is_shortage_risk='Y'
ORDER BY days_of_stock ASC
LIMIT 25;"""

queries["q4_disruption_impact"] = """
SELECT disruption_type, severity,
       COUNT(*) AS events,
       ROUND(SUM(financial_loss_usd)/1e6,2) AS loss_musd,
       ROUND(AVG(duration_days),0) AS avg_duration_days,
       SUM(CASE WHEN is_resolved='Y' THEN 1 ELSE 0 END) AS resolved
FROM fact_disruptions
GROUP BY 1,2
ORDER BY loss_musd DESC
LIMIT 20;"""

queries["q5_plant_inventory_health"] = """
SELECT pl.plant_name, pl.country_name,
       COUNT(*) AS sku_lines,
       SUM(CASE WHEN i.is_shortage_risk='Y' THEN 1 ELSE 0 END) AS shortage_skus,
       SUM(CASE WHEN i.current_stock < i.reorder_point THEN 1 ELSE 0 END) AS below_reorder,
       ROUND(AVG(i.days_of_stock),1) AS avg_days_of_stock
FROM fact_inventory_buffer i
JOIN dim_plants pl ON i.plant_id=pl.plant_id
GROUP BY 1,2
ORDER BY below_reorder DESC, avg_days_of_stock ASC;"""

# run + save each query
with open(SQL+"analysis_queries.sql","w") as fh:
    results={}
    for name,q in queries.items():
        fh.write(f"-- {name}\n{q.strip()}\n\n")
        res=con.execute(q).fetchdf()
        res.to_csv(DATA+f"sql_{name}.csv", index=False)
        results[name]=res
        print(f"\n=== {name} ({len(res)} rows) ===")
        print(res.head(6).to_string(index=False))

# ------------------------------------------------ INVENTORY BOTTLENECK CHARTS
print("\nBuilding inventory bottleneck charts ...")
inv_full = con.execute("""
SELECT pl.plant_name, pr.criticality, i.current_stock, i.reorder_point,
       i.safety_stock, i.days_of_stock, i.is_shortage_risk
FROM fact_inventory_buffer i
JOIN dim_plants pl ON i.plant_id=pl.plant_id
JOIN dim_products pr ON i.product_id=pr.product_id""").fetchdf()

# 15 days-of-stock distribution with reorder threshold
fig,ax=plt.subplots(figsize=(7.5,4.4))
ax.hist(inv_full.days_of_stock, bins=30, color=P["teal"], alpha=.8)
med=inv_full.days_of_stock.median()
ax.axvline(med, ls="--", color=P["red"], label=f"Median {med:.0f} days")
ax.set_title("Inventory Days-of-Stock Distribution"); ax.set_xlabel("Days of stock"); ax.set_ylabel("SKU lines"); ax.legend()
plt.tight_layout(); plt.savefig(CHART+"15_inventory_days_of_stock.png"); plt.close()

# 16 below-reorder / shortage by plant
plant_health = con.execute("""
SELECT pl.plant_name,
       SUM(CASE WHEN i.current_stock < i.reorder_point THEN 1 ELSE 0 END) AS below_reorder,
       SUM(CASE WHEN i.is_shortage_risk='Y' THEN 1 ELSE 0 END) AS shortage_risk,
       COUNT(*) AS total_skus
FROM fact_inventory_buffer i JOIN dim_plants pl ON i.plant_id=pl.plant_id
GROUP BY 1 ORDER BY below_reorder DESC""").fetchdf()
fig,ax=plt.subplots(figsize=(8.5,4.6))
x=range(len(plant_health)); w=0.38
ax.bar([i-w/2 for i in x], plant_health.below_reorder, w, color=P["amber"], label="Below reorder point")
ax.bar([i+w/2 for i in x], plant_health.shortage_risk, w, color=P["red"], label="Flagged shortage risk")
ax.set_xticks(list(x)); ax.set_xticklabels(plant_health.plant_name, rotation=25, ha="right")
ax.set_title("Inventory Bottlenecks by Plant"); ax.set_ylabel("SKU lines"); ax.legend()
plt.tight_layout(); plt.savefig(CHART+"16_inventory_bottleneck_by_plant.png"); plt.close()

# 17 stock position scatter: current vs reorder, colored by shortage risk
fig,ax=plt.subplots(figsize=(7.5,4.8))
for flag,col,lbl in [("N",P["green"],"OK"),("Y",P["red"],"Shortage risk")]:
    sub=inv_full[inv_full.is_shortage_risk==flag]
    ax.scatter(sub.reorder_point, sub.current_stock, c=col, alpha=.6, s=28, label=lbl)
lim=max(inv_full.reorder_point.max(), inv_full.current_stock.max())
ax.plot([0,lim],[0,lim],"--",color="grey",alpha=.7,label="Stock = Reorder line")
ax.set_title("Stock Position vs Reorder Point"); ax.set_xlabel("Reorder point"); ax.set_ylabel("Current stock"); ax.legend()
plt.tight_layout(); plt.savefig(CHART+"17_stock_position_scatter.png"); plt.close()

# inventory KPIs
inv_kpi={
 "total_sku_lines":int(len(inv_full)),
 "below_reorder":int((inv_full.current_stock<inv_full.reorder_point).sum()),
 "shortage_risk_flagged":int((inv_full.is_shortage_risk=="Y").sum()),
 "median_days_of_stock":float(round(inv_full.days_of_stock.median(),1)),
 "min_days_of_stock":float(round(inv_full.days_of_stock.min(),1)),
 "critical_below_reorder":int(((inv_full.current_stock<inv_full.reorder_point)&(inv_full.criticality.isin(["High","Critical"]))).sum()),
}
json.dump(inv_kpi, open(DATA+"inventory_kpis.json","w"), indent=2)
print("\nInventory KPIs:", json.dumps(inv_kpi))
con.close()
print("\nDONE. SQL db, query results (sql_*.csv), inventory charts (15-17) written.")
