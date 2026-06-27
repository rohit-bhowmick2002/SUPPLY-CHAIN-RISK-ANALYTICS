"""
End-to-End Supply Chain Risk Pipeline
=====================================
Mirrors the fraud-detection workflow, re-themed for supply chain risk.
Steps:
  1. Load & clean (star schema: 3 dims + 5 facts)
  2. Feature engineering (join facts to dims, build supplier-risk signals)
  3. EDA + visualizations
  4. Anomaly detection (Isolation Forest)  -> unsupervised risk signal
  5. Classification (Random Forest)        -> predict LATE delivery
  6. Supplier / PO risk scoring + export (CSV / Excel)
  7. Persist models
Target: on_time_delivery == 'N'  (i.e. predict a LATE / failed delivery)
"""
import warnings, json, time, joblib, os
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (classification_report, confusion_matrix, roc_auc_score,
                             roc_curve, precision_recall_curve, average_precision_score,
                             precision_score, recall_score, f1_score)

sns.set_style("whitegrid")
P = {"blue":"#185FA5","green":"#3B6D11","red":"#A32D2D","amber":"#854F0B",
     "orange":"#d97706","teal":"#0E7490","grey":"#5a5a56"}
plt.rcParams.update({"figure.dpi":130,"savefig.dpi":150,"font.size":11,
                     "axes.titleweight":"bold","axes.titlesize":13,"figure.facecolor":"white"})
U="uploads/"; CHART="supplychain_project/charts/"; DATA="supplychain_project/data/"; MODEL="supplychain_project/models/"
metrics={}; t0=time.time()

# ================================================================== 1. LOAD & CLEAN
print("STEP 1  Loading star schema & cleaning ...")
plants   = pd.read_csv(U+"dim_plants.csv")
products = pd.read_csv(U+"dim_products.csv")
suppliers= pd.read_csv(U+"dim_suppliers.csv")
disrupt  = pd.read_csv(U+"fact_disruptions.csv")
inv      = pd.read_csv(U+"fact_inventory_buffer.csv")
po       = pd.read_csv(U+"fact_purchase_orders.csv")
network  = pd.read_csv(U+"fact_supplier_network.csv")
score    = pd.read_csv(U+"fact_supplier_scorecard.csv")
for d in [plants,products,suppliers,disrupt,inv,po,network,score]:
    d.drop_duplicates(inplace=True)
metrics["po_rows"]=len(po); metrics["supplier_rows"]=len(suppliers)
metrics["disruption_rows"]=len(disrupt)
metrics["total_disruption_loss"]=round(float(disrupt.financial_loss_usd.sum()),2)

# ================================================================== 2. FEATURE ENGINEERING
print("STEP 2  Feature engineering ...")
# supplier-level aggregates from scorecard (latest avg per supplier)
sc_agg = score.groupby("supplier_id").agg(
    otd=("otd_score","mean"), quality=("quality_score","mean"),
    cost=("cost_score","mean"), respons=("responsiveness_score","mean"),
    sustain=("sustainability_score","mean"), composite=("composite_score","mean"),
    incidents=("incidents_reported","sum")).reset_index()
# disruption history per supplier
dis_agg = disrupt.groupby("supplier_id").agg(
    n_disruptions=("disruption_id","count"),
    disruption_loss=("financial_loss_usd","sum"),
    avg_dis_duration=("duration_days","mean")).reset_index()
# network: in/out dependency counts + critical path
net_out = network.groupby("source_supplier_id").size().rename("n_downstream")
net_in  = network.groupby("target_supplier_id").size().rename("n_upstream")
net_crit= network[network.is_critical_path=="Y"].groupby("source_supplier_id").size().rename("n_critical_edges")

# enrich supplier dim
sup = suppliers.copy()
sup = sup.merge(sc_agg, on="supplier_id", how="left")
sup = sup.merge(dis_agg, on="supplier_id", how="left")
sup = sup.merge(net_out, left_on="supplier_id", right_index=True, how="left")
sup = sup.merge(net_in,  left_on="supplier_id", right_index=True, how="left")
sup = sup.merge(net_crit,left_on="supplier_id", right_index=True, how="left")
for c in ["n_disruptions","disruption_loss","avg_dis_duration","n_downstream","n_upstream","n_critical_edges","incidents"]:
    sup[c]=sup[c].fillna(0)
sup["is_sole_source_b"]=(sup.is_sole_source=="Y").astype(int)
sup["tier_num"]=sup.tier.str.extract(r"(\d)").astype(float)
sup["supplier_age"]=2025-sup.established_year

# ---- build PO-level modeling table (the main fact) ----
df = po.merge(sup[["supplier_id","tier_num","is_sole_source_b","lead_time_days",
                   "otd","quality","cost","respons","sustain","composite","incidents",
                   "n_disruptions","disruption_loss","avg_dis_duration",
                   "n_downstream","n_upstream","n_critical_edges","supplier_age",
                   "risk_band","category","continent"]], on="supplier_id", how="left")
df = df.merge(products[["product_id","criticality","unit_cost_usd","bom_components"]], on="product_id", how="left")
df = df.merge(plants[["plant_id","continent"]].rename(columns={"continent":"plant_continent"}), on="plant_id", how="left")

# target
df["is_late"]=(df.on_time_delivery=="N").astype(int)
metrics["late_rate"]=round(df.is_late.mean()*100,2)
metrics["n_late"]=int(df.is_late.sum())

# engineered PO features
df["order_value_per_unit"]=df.total_value_usd/(df.quantity_ordered+1)
df["high_value_order"]=(df.total_value_usd>df.total_value_usd.quantile(0.9)).astype(int)
df["crit_flag"]=df.criticality.isin(["High","Critical"]).astype(int)
df["lead_time_days"]=df.lead_time_days.fillna(df.lead_time_days.median())

NUM=["quantity_ordered","unit_price_usd","total_value_usd","defect_rate_pct","order_value_per_unit",
     "high_value_order","tier_num","is_sole_source_b","lead_time_days","otd","quality","cost",
     "respons","sustain","composite","incidents","n_disruptions","disruption_loss",
     "avg_dis_duration","n_downstream","n_upstream","n_critical_edges","supplier_age",
     "crit_flag","unit_cost_usd","bom_components"]
CAT=["status","risk_band","category","criticality"]
dfm = pd.get_dummies(df, columns=CAT, prefix=CAT)
FEATURES = NUM + [c for c in dfm.columns if any(c.startswith(p+"_") for p in CAT)]
FEATURES = [f for f in FEATURES if f in dfm.columns]
X = dfm[FEATURES].fillna(0); y = dfm["is_late"]

# ================================================================== 3. EDA CHARTS
print("STEP 3  EDA visualizations ...")
# 1 on-time vs late
fig,ax=plt.subplots(figsize=(6,4.2))
vc=df.is_late.value_counts().sort_index()
b=ax.bar(["On-Time","Late"],vc.values,color=[P["green"],P["red"]])
for bar,v in zip(b,vc.values): ax.text(bar.get_x()+bar.get_width()/2,v,f"{v:,}",ha="center",va="bottom",fontweight="bold")
ax.set_title("Delivery Outcome Distribution"); ax.set_ylabel("Purchase orders")
plt.tight_layout(); plt.savefig(CHART+"01_delivery_outcome.png"); plt.close()

# 2 late rate by supplier category
fig,ax=plt.subplots(figsize=(8,4.4))
lr=(df.groupby("category").is_late.mean()*100).sort_values(ascending=False)
b=ax.bar(lr.index,lr.values,color=P["amber"])
for bar,v in zip(b,lr.values): ax.text(bar.get_x()+bar.get_width()/2,v,f"{v:.0f}%",ha="center",va="bottom",fontsize=9)
ax.set_title("Late-Delivery Rate by Supplier Category"); ax.set_ylabel("Late %")
plt.xticks(rotation=25,ha="right"); plt.tight_layout(); plt.savefig(CHART+"02_late_by_category.png"); plt.close()

# 3 disruptions by type & severity
fig,ax=plt.subplots(figsize=(9,4.6))
pivot=disrupt.pivot_table(index="disruption_type",columns="severity",values="disruption_id",aggfunc="count",fill_value=0)
pivot=pivot.reindex(columns=[c for c in ["Low","Medium","High","Critical"] if c in pivot.columns])
pivot.plot(kind="bar",stacked=True,ax=ax,color=[P["green"],P["amber"],P["orange"],P["red"]][:pivot.shape[1]])
ax.set_title("Disruptions by Type & Severity"); ax.set_ylabel("Count"); ax.set_xlabel("")
plt.xticks(rotation=30,ha="right"); plt.legend(title="Severity"); plt.tight_layout()
plt.savefig(CHART+"03_disruptions_by_type.png"); plt.close()

# 4 financial loss by disruption type
fig,ax=plt.subplots(figsize=(8,4.4))
ll=(disrupt.groupby("disruption_type").financial_loss_usd.sum()/1e6).sort_values(ascending=True)
ax.barh(ll.index,ll.values,color=P["red"])
ax.set_title("Financial Loss by Disruption Type"); ax.set_xlabel("Loss (USD millions)")
plt.tight_layout(); plt.savefig(CHART+"04_loss_by_type.png"); plt.close()

# 5 correlation heatmap (key numeric)
fig,ax=plt.subplots(figsize=(9,7))
keyn=["delay_days","defect_rate_pct","total_value_usd","lead_time_days","otd","quality",
      "composite","incidents","n_disruptions","disruption_loss","is_late"]
keyn=[c for c in keyn if c in df.columns]
sns.heatmap(df[keyn].corr(),cmap="RdBu_r",center=0,annot=True,fmt=".2f",annot_kws={"size":7},ax=ax,cbar_kws={"shrink":.8})
ax.set_title("Feature Correlation Heatmap"); plt.tight_layout(); plt.savefig(CHART+"05_correlation_heatmap.png"); plt.close()

# 6 late deliveries over time (fiscal year)
fig,ax=plt.subplots(figsize=(8,4.2))
ts=df.groupby("fiscal_year").is_late.agg(["sum","count"])
ts["rate"]=ts["sum"]/ts["count"]*100
ax.bar(ts.index.astype(str),ts["sum"],color=P["blue"],label="Late count")
ax2=ax.twinx(); ax2.plot(ts.index.astype(str),ts["rate"],color=P["red"],marker="o",lw=2,label="Late %")
ax.set_title("Late Deliveries Over Time"); ax.set_ylabel("Late count"); ax2.set_ylabel("Late %")
ax.legend(loc="upper left"); ax2.legend(loc="upper right"); plt.tight_layout()
plt.savefig(CHART+"06_late_over_time.png"); plt.close()

# 7 supplier risk band distribution
fig,ax=plt.subplots(figsize=(6.5,4.2))
rb=sup.risk_band.value_counts().reindex(["Low","Medium","High"]).fillna(0)
b=ax.bar(rb.index,rb.values,color=[P["green"],P["amber"],P["red"]])
for bar,v in zip(b,rb.values): ax.text(bar.get_x()+bar.get_width()/2,v,f"{int(v)}",ha="center",va="bottom",fontweight="bold")
ax.set_title("Suppliers by Risk Band"); ax.set_ylabel("Suppliers")
plt.tight_layout(); plt.savefig(CHART+"07_supplier_risk_band.png"); plt.close()

# ================================================================== 4 & 5 MODELS
print("STEP 4  Train/test split & scaling ...")
X_tr,X_te,y_tr,y_te=train_test_split(X,y,test_size=0.25,stratify=y,random_state=42)
scaler=StandardScaler().fit(X_tr); X_tr_s,X_te_s=scaler.transform(X_tr),scaler.transform(X_te)

print("STEP 4a Isolation Forest (anomaly detection) ...")
iso=IsolationForest(n_estimators=200,contamination=float(y.mean()),random_state=42,n_jobs=-1).fit(X_tr_s)
iso_score=-iso.score_samples(X_te_s)
metrics["iso_auc"]=round(roc_auc_score(y_te,iso_score),4)

print("STEP 5a Random Forest classifier ...")
rf=RandomForestClassifier(n_estimators=300,max_depth=14,class_weight="balanced",random_state=42,n_jobs=-1).fit(X_tr_s,y_tr)
rf_proba=rf.predict_proba(X_te_s)[:,1]; rf_pred=rf.predict(X_te_s)
metrics["rf_auc"]=round(roc_auc_score(y_te,rf_proba),4)
metrics["rf_ap"]=round(average_precision_score(y_te,rf_proba),4)
metrics["rf_precision"]=round(precision_score(y_te,rf_pred),4)
metrics["rf_recall"]=round(recall_score(y_te,rf_pred),4)
metrics["rf_f1"]=round(f1_score(y_te,rf_pred),4)
print("\nRandom Forest report:\n",classification_report(y_te,rf_pred,digits=4))

# eval charts
fig,ax=plt.subplots(figsize=(5,4.2))
cm=confusion_matrix(y_te,rf_pred)
sns.heatmap(cm,annot=True,fmt="d",cmap="Blues",ax=ax,xticklabels=["On-Time","Late"],yticklabels=["On-Time","Late"])
ax.set_title("Random Forest — Confusion Matrix"); ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
plt.tight_layout(); plt.savefig(CHART+"08_confusion_matrix.png"); plt.close()

fig,ax=plt.subplots(figsize=(6,5))
for sc_,nm,col in [(rf_proba,"Random Forest",P["blue"]),(iso_score,"Isolation Forest",P["amber"])]:
    fpr,tpr,_=roc_curve(y_te,sc_); ax.plot(fpr,tpr,lw=2,color=col,label=f"{nm} (AUC={roc_auc_score(y_te,sc_):.3f})")
ax.plot([0,1],[0,1],"--",color="grey")
ax.set_title("ROC Curve — Model Comparison"); ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate"); ax.legend(loc="lower right")
plt.tight_layout(); plt.savefig(CHART+"09_roc_curve.png"); plt.close()

fig,ax=plt.subplots(figsize=(6,5))
pr,rc,_=precision_recall_curve(y_te,rf_proba); ax.plot(rc,pr,lw=2,color=P["green"],label=f"RF (AP={metrics['rf_ap']:.3f})")
ax.set_title("Precision-Recall Curve (Random Forest)"); ax.set_xlabel("Recall"); ax.set_ylabel("Precision"); ax.legend()
plt.tight_layout(); plt.savefig(CHART+"10_precision_recall.png"); plt.close()

fig,ax=plt.subplots(figsize=(7,5.2))
fi=pd.Series(rf.feature_importances_,index=FEATURES).sort_values().tail(14)
ax.barh(fi.index,fi.values,color=P["blue"]); ax.set_title("Top Feature Importances (Random Forest)"); ax.set_xlabel("Importance")
plt.tight_layout(); plt.savefig(CHART+"11_feature_importance.png"); plt.close()

# ================================================================== 6. RISK SCORING
print("STEP 6  Scoring all POs & exporting ...")
X_all_s=scaler.transform(X)
df["late_probability"]=rf.predict_proba(X_all_s)[:,1]
an=-iso.score_samples(X_all_s); df["anomaly_score"]=an
df["anomaly_score_norm"]=((an-an.min())/(an.max()-an.min())*100).round(2)
df["risk_score"]=(0.7*df.late_probability*100+0.3*df.anomaly_score_norm).round(2)
df["risk_level"]=pd.cut(df.risk_score,bins=[-1,25,50,75,101],labels=["Low","Medium","High","Critical"])
df["predicted_late"]=(df.late_probability>=0.5).astype(int)
metrics["high_risk_pos"]=int(df.risk_level.isin(["High","Critical"]).sum())
metrics["critical_pos"]=int((df.risk_level=="Critical").sum())

fig,ax=plt.subplots(figsize=(6.5,4.2))
rl=df.risk_level.value_counts().reindex(["Low","Medium","High","Critical"])
b=ax.bar(rl.index,rl.values,color=[P["green"],P["amber"],P["orange"],P["red"]])
for bar,v in zip(b,rl.values): ax.text(bar.get_x()+bar.get_width()/2,v,f"{int(v)}",ha="center",va="bottom",fontsize=9)
ax.set_title("Purchase Orders by Risk Level"); ax.set_ylabel("Count")
plt.tight_layout(); plt.savefig(CHART+"12_risk_level_distribution.png"); plt.close()

out=["po_id","supplier_id","product_id","plant_id","order_date","fiscal_year","status",
     "total_value_usd","delay_days","defect_rate_pct","late_probability","anomaly_score_norm",
     "risk_score","risk_level","predicted_late","is_late"]
df_sc=df[out].copy(); df_sc.to_csv(DATA+"scored_purchase_orders.csv",index=False)
df_sc.sort_values("risk_score",ascending=False).head(500).to_csv(DATA+"top_high_risk_pos.csv",index=False)

# supplier-level risk roll-up
sup_risk=df.groupby("supplier_id").agg(
    pos=("po_id","count"), avg_risk=("risk_score","mean"), late_rate=("is_late","mean"),
    total_value=("total_value_usd","sum")).round(2).reset_index()
sup_risk=sup_risk.merge(sup[["supplier_id","supplier_name","risk_band","tier","category","composite","n_disruptions"]],on="supplier_id",how="left")
sup_risk["late_rate"]=(sup_risk.late_rate*100).round(1)
sup_risk=sup_risk.sort_values("avg_risk",ascending=False)
sup_risk.to_csv(DATA+"supplier_risk_ranking.csv",index=False)

with pd.ExcelWriter(DATA+"supply_chain_analysis_report.xlsx",engine="openpyxl") as xl:
    pd.DataFrame([metrics]).T.rename(columns={0:"value"}).to_excel(xl,sheet_name="KPI_Summary")
    df.groupby("category").agg(pos=("po_id","count"),late=("is_late","sum"),
        late_pct=("is_late",lambda s:round(s.mean()*100,1)),value=("total_value_usd","sum")).to_excel(xl,sheet_name="By_Category")
    disrupt.groupby("disruption_type").agg(events=("disruption_id","count"),
        loss=("financial_loss_usd","sum")).round(0).to_excel(xl,sheet_name="Disruptions")
    sup_risk.head(40).to_excel(xl,sheet_name="Top_Risk_Suppliers",index=False)
    df_sc.sort_values("risk_score",ascending=False).head(200).to_excel(xl,sheet_name="Top_HighRisk_POs",index=False)
    pd.Series(rf.feature_importances_,index=FEATURES).sort_values(ascending=False).to_excel(xl,sheet_name="Feature_Importance")

# ================================================================== 7. PERSIST
joblib.dump(rf,MODEL+"random_forest_late.joblib")
joblib.dump(iso,MODEL+"isolation_forest.joblib")
joblib.dump(scaler,MODEL+"scaler.joblib")
json.dump({"features":FEATURES},open(MODEL+"features.json","w"),indent=2)
metrics["runtime_sec"]=round(time.time()-t0,1)
json.dump(metrics,open(DATA+"metrics.json","w"),indent=2)
print("\n=== METRICS ===\n",json.dumps(metrics,indent=2))
print("\nDONE.")
