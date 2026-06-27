"""Threshold tuning (cost-based) + Power BI star-schema export + dashboard data."""
import warnings,json,os; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import precision_score,recall_score,f1_score,confusion_matrix
P={"blue":"#185FA5","green":"#3B6D11","red":"#A32D2D","amber":"#854F0B","orange":"#d97706"}
plt.rcParams.update({"figure.dpi":130,"savefig.dpi":150,"font.size":11,"axes.titleweight":"bold","figure.facecolor":"white"})
CHART="supplychain_project/charts/"; DATA="supplychain_project/data/"; PBI="supplychain_project/powerbi/"; U="uploads/"
os.makedirs(PBI,exist_ok=True)

# cost model: expediting a late PO (FN missed) vs. unnecessary intervention (FP)
COST_FN=12000.0  # avg cost of an unmitigated late delivery (line-down, expedite freight)
COST_FP=600.0    # cost of proactively intervening on an order that would've been fine
df=pd.read_csv(DATA+"scored_purchase_orders.csv")
y=df.is_late.values; p=df.late_probability.values
ths=np.linspace(0.05,0.95,91); rows=[]
for t in ths:
    pred=(p>=t).astype(int)
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    rows.append({"threshold":round(float(t),3),"tp":int(tp),"fp":int(fp),"fn":int(fn),"tn":int(tn),
        "interventions":int(tp+fp),"precision":round(precision_score(y,pred,zero_division=0),4),
        "recall":round(recall_score(y,pred,zero_division=0),4),"f1":round(f1_score(y,pred,zero_division=0),4),
        "expected_cost":round(float(fn*COST_FN+fp*COST_FP),2)})
sweep=pd.DataFrame(rows); sweep.to_csv(DATA+"threshold_sweep.csv",index=False)
best=sweep.loc[sweep.expected_cost.idxmin()]; bf1=sweep.loc[sweep.f1.idxmax()]
cost_ignore=int(y.sum())*COST_FN
print(f"Optimal threshold {best.threshold}: cost ${best.expected_cost:,.0f}, recall {best.recall}, interventions {int(best.interventions)}")

# charts
fig,ax=plt.subplots(figsize=(7.5,4.4))
ax.plot(sweep.threshold,sweep.expected_cost,color=P["red"],lw=2)
ax.axvline(best.threshold,ls="--",color=P["green"],label=f"Optimal t={best.threshold} (${best.expected_cost:,.0f})")
ax.scatter([best.threshold],[best.expected_cost],color=P["green"],s=60,zorder=5)
ax.set_title("Expected Cost vs Intervention Threshold"); ax.set_xlabel("Late-probability threshold"); ax.set_ylabel("Expected cost ($)"); ax.legend()
plt.tight_layout(); plt.savefig(CHART+"13_cost_curve.png"); plt.close()

fig,ax=plt.subplots(figsize=(7.5,4.4))
ax.plot(sweep.threshold,sweep.precision,label="Precision",color=P["blue"],lw=2)
ax.plot(sweep.threshold,sweep.recall,label="Recall",color=P["green"],lw=2)
ax.plot(sweep.threshold,sweep.f1,label="F1",color=P["amber"],lw=2)
ax.axvline(best.threshold,ls="--",color="grey",alpha=.7)
ax.set_title("Precision / Recall / F1 vs Threshold"); ax.set_xlabel("Threshold"); ax.set_ylabel("Score"); ax.legend()
plt.tight_layout(); plt.savefig(CHART+"14_metric_vs_threshold.png"); plt.close()

alert={"cost_assumptions":{"missed_late_FN_usd":COST_FN,"false_intervention_FP_usd":COST_FP},
  "recommended_threshold":float(best.threshold),
  "at_recommended":{"recall":float(best.recall),"precision":float(best.precision),"f1":float(best.f1),
     "interventions":int(best.interventions),"expected_cost_usd":float(best.expected_cost),
     "late_caught":int(best.tp),"late_missed":int(best.fn),"false_interventions":int(best.fp)},
  "max_f1_threshold":float(bf1.threshold),"baseline_cost_ignore":float(cost_ignore),
  "cost_saving_vs_ignore_pct":round((1-best.expected_cost/max(cost_ignore,1))*100,1),
  "kpi_alert_tiers":{"CRITICAL":"risk>=75 -> escalate to procurement lead + activate backup supplier",
     "HIGH":"risk 50-75 -> expedite review, contact supplier (SLA 24h)",
     "MEDIUM":"risk 25-50 -> monitor weekly",
     "LOW":"risk<25 -> standard processing"}}
json.dump(alert,open(DATA+"alert_rules.json","w"),indent=2)

# ---------- POWER BI star schema ----------
print("Building Power BI dataset ...")
plants=pd.read_csv(U+"dim_plants.csv"); products=pd.read_csv(U+"dim_products.csv"); suppliers=pd.read_csv(U+"dim_suppliers.csv")
disrupt=pd.read_csv(U+"fact_disruptions.csv")
sup_rank=pd.read_csv(DATA+"supplier_risk_ranking.csv")
fact=df.copy(); fact.insert(0,"po_key",range(1,len(fact)+1))
fact.to_csv(PBI+"fact_purchase_orders_scored.csv",index=False)
plants.to_csv(PBI+"dim_plants.csv",index=False)
products.to_csv(PBI+"dim_products.csv",index=False)
suppliers.merge(sup_rank[["supplier_id","avg_risk","late_rate"]],on="supplier_id",how="left").to_csv(PBI+"dim_suppliers.csv",index=False)
disrupt.to_csv(PBI+"fact_disruptions.csv",index=False)
dim_risk=pd.DataFrame({"risk_level_key":["Low","Medium","High","Critical"],"risk_order":[1,2,3,4],
  "score_min":[0,25,50,75],"score_max":[25,50,75,100],
  "action":["Standard processing","Monitor weekly","Expedite review (SLA 24h)","Escalate + activate backup"],
  "sla_hours":[None,168,24,4]})
dim_risk.to_csv(PBI+"dim_risk_level.csv",index=False)
m=json.load(open(DATA+"metrics.json"))
kpi=pd.DataFrame([
 {"metric":"Total Purchase Orders","value":m["po_rows"]},
 {"metric":"Late Deliveries","value":m["n_late"]},
 {"metric":"Late Rate %","value":m["late_rate"]},
 {"metric":"Suppliers Monitored","value":m["supplier_rows"]},
 {"metric":"Disruption Events","value":m["disruption_rows"]},
 {"metric":"Total Disruption Loss USD","value":m["total_disruption_loss"]},
 {"metric":"High+Critical Risk POs","value":m["high_risk_pos"]},
 {"metric":"Model ROC AUC","value":m["rf_auc"]},
 {"metric":"Recommended Threshold","value":float(best.threshold)}])
kpi.to_csv(PBI+"kpi_measures.csv",index=False)
open(PBI+"DATA_MODEL.md","w").write(f"""# Power BI Data Model (Star Schema) — Supply Chain Risk

Import these CSVs into Power BI Desktop (Get Data > Text/CSV) and build relationships.

## Tables
- **fact_purchase_orders_scored** (grain: 1 row / PO, with late_probability + risk_score) — central fact
- **fact_disruptions** (grain: 1 row / disruption event)
- **dim_suppliers** / **dim_products** / **dim_plants** — descriptive dimensions
- **dim_risk_level** — risk tiers, SLA, escalation action
- **kpi_measures** — pre-computed KPI card values

## Relationships
| From (fact) | To (dim) | Cardinality |
|---|---|---|
| fact_purchase_orders_scored[supplier_id] | dim_suppliers[supplier_id] | Many-to-One |
| fact_purchase_orders_scored[product_id]  | dim_products[product_id]   | Many-to-One |
| fact_purchase_orders_scored[plant_id]    | dim_plants[plant_id]       | Many-to-One |
| fact_purchase_orders_scored[risk_level]  | dim_risk_level[risk_level_key] | Many-to-One |
| fact_disruptions[supplier_id]            | dim_suppliers[supplier_id] | Many-to-One |

## Suggested DAX
```
Late Orders = SUM(fact_purchase_orders_scored[is_late])
Late Rate % = DIVIDE([Late Orders], COUNTROWS(fact_purchase_orders_scored)) * 100
High Risk POs = CALCULATE(COUNTROWS(fact_purchase_orders_scored), fact_purchase_orders_scored[risk_score] >= 50)
Total PO Value = SUM(fact_purchase_orders_scored[total_value_usd])
Disruption Loss = SUM(fact_disruptions[financial_loss_usd])
Recommended Threshold = {best.threshold}
```

## Suggested visuals
1. KPI cards: Late Rate %, High Risk POs, Disruption Loss, Total PO Value
2. Bar: Late Rate % by dim_suppliers[category]
3. Stacked bar: disruptions by type & severity
4. Map: suppliers by dim_suppliers[country_name] colored by risk_band
5. Table: top suppliers by avg_risk with conditional formatting
6. Line: Late Rate % over fiscal_year
""")

# ---------- dashboard data ----------
sup_rank2=sup_rank.head(12)[["supplier_name","category","tier","avg_risk","late_rate","n_disruptions"]]
dd={"kpi":{"total_pos":int(m["po_rows"]),"n_late":int(m["n_late"]),"late_rate":m["late_rate"],
   "suppliers":int(m["supplier_rows"]),"disruptions":int(m["disruption_rows"]),
   "disruption_loss":m["total_disruption_loss"],"high_risk":int(m["high_risk_pos"]),
   "rf_auc":m["rf_auc"],"rf_recall":m["rf_recall"],"rf_precision":m["rf_precision"],"iso_auc":m["iso_auc"]},
 "cat":list((df.merge(suppliers[["supplier_id","category"]],on="supplier_id",how="left").groupby("category").is_late.mean()*100).round(1).index),
 "cat_late":[float(x) for x in (df.merge(suppliers[["supplier_id","category"]],on="supplier_id",how="left").groupby("category").is_late.mean()*100).round(1).values],
 "risk_labels":["Low","Medium","High","Critical"],
 "risk_values":[int(df.risk_level.value_counts().get(k,0)) for k in ["Low","Medium","High","Critical"]],
 "dis_types":list(disrupt.groupby("disruption_type").financial_loss_usd.sum().sort_values(ascending=False).index),
 "dis_loss":[round(float(x)/1e6,1) for x in disrupt.groupby("disruption_type").financial_loss_usd.sum().sort_values(ascending=False).values],
 "years":[int(x) for x in df.groupby("fiscal_year").is_late.mean().index],
 "year_rate":[round(float(x)*100,1) for x in df.groupby("fiscal_year").is_late.mean().values],
 "top_suppliers":sup_rank2.round(1).to_dict(orient="records"),
 "thresh":{"th":[round(float(x),2) for x in sweep.threshold[::2]],"cost":[float(x) for x in sweep.expected_cost[::2]],
    "optimal":float(best.threshold),"recall":float(best.recall),"interventions":int(best.interventions),
    "saving":round((1-best.expected_cost/max(cost_ignore,1))*100,1)}}
json.dump(dd,open(DATA+"dashboard_data.json","w"),indent=2)
print("Done. PBI + dashboard data + alert rules written.")
