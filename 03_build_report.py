"""PDF report for supply chain risk project."""
import json, os
from fpdf import FPDF
m=json.load(open("supplychain_project/data/metrics.json"))
ar=json.load(open("supplychain_project/data/alert_rules.json"))
C="supplychain_project/charts/"; BLUE=(14,116,144); DARK=(22,32,44)
pdf=FPDF("P","mm","A4"); pdf.set_auto_page_break(True,15)
def header(t,s=""):
    pdf.set_fill_color(*BLUE); pdf.rect(0,0,210,30,"F"); pdf.set_xy(12,8); pdf.set_text_color(255,255,255)
    pdf.set_font("Helvetica","B",17); pdf.cell(0,8,t,ln=1)
    if s: pdf.set_x(12); pdf.set_font("Helvetica","",10); pdf.cell(0,6,s,ln=1)
    pdf.set_text_color(*DARK); pdf.ln(8)
def h2(t): pdf.ln(2); pdf.set_text_color(*BLUE); pdf.set_font("Helvetica","B",13); pdf.cell(0,8,t,ln=1); pdf.set_text_color(*DARK)
def body(t): pdf.set_font("Helvetica","",10.5); pdf.multi_cell(0,5.5,t); pdf.ln(1)
def chart(p,w=175): pdf.image(p,x=(210-w)/2,w=w); pdf.ln(3)

pdf.add_page(); header("Supply Chain Risk Analysis Report","End-to-end disruption & late-delivery risk scoring")
h2("Executive Summary")
body(f"This report documents an end-to-end supply-chain risk pipeline applied to a star-schema dataset of "
 f"{m['po_rows']:,} purchase orders, {m['supplier_rows']} suppliers and {m['disruption_rows']} disruption "
 f"events across 4 fiscal years. The pipeline cleans and joins the data, engineers supplier-risk and order "
 f"features, applies unsupervised anomaly detection (Isolation Forest) and supervised classification "
 f"(Random Forest) to predict late deliveries, then scores every purchase order with a composite risk "
 f"score and routes high-risk orders to a tiered escalation queue.\n\n"
 f"Across the portfolio, {m['n_late']} late deliveries were recorded ({m['late_rate']}% late rate), and "
 f"disruption events drove ${m['total_disruption_loss']:,.0f} in cumulative financial loss. The risk-scoring "
 f"layer flagged {m['high_risk_pos']} high/critical purchase orders for proactive intervention.")
h2("Key Performance Indicators")
rows=[("Purchase orders analyzed",f"{m['po_rows']:,}"),("Suppliers monitored",f"{m['supplier_rows']}"),
 ("Disruption events",f"{m['disruption_rows']}"),("Late deliveries",f"{m['n_late']} ({m['late_rate']}%)"),
 ("Total disruption loss",f"${m['total_disruption_loss']:,.0f}"),
 ("High / Critical risk POs",f"{m['high_risk_pos']}"),("Random Forest ROC-AUC",f"{m['rf_auc']}"),
 ("Isolation Forest ROC-AUC",f"{m['iso_auc']}"),("Pipeline runtime",f"{m['runtime_sec']} sec")]
pdf.set_font("Helvetica","",10.5)
for i,(a,b) in enumerate(rows):
    pdf.set_fill_color(240,242,246) if i%2==0 else pdf.set_fill_color(255,255,255)
    pdf.cell(120,8,"  "+a,fill=True); pdf.set_font("Helvetica","B",10.5); pdf.cell(60,8,b,fill=True,ln=1); pdf.set_font("Helvetica","",10.5)

pdf.add_page(); header("Exploratory Data Analysis")
h2("1. Delivery Outcomes & Category Risk"); chart(C+"01_delivery_outcome.png",140); chart(C+"02_late_by_category.png",165)
pdf.add_page(); header("Exploratory Data Analysis (cont.)")
h2("2. Disruptions & Financial Impact"); chart(C+"03_disruptions_by_type.png",170); chart(C+"04_loss_by_type.png",165)
pdf.add_page(); header("Exploratory Data Analysis (cont.)")
h2("3. Correlations, Trend & Supplier Risk"); chart(C+"05_correlation_heatmap.png",150); chart(C+"06_late_over_time.png",160)
pdf.add_page(); header("Exploratory Data Analysis (cont.)"); chart(C+"07_supplier_risk_band.png",140)

pdf.add_page(); header("Model Performance")
h2("4. Late-Delivery Prediction (Random Forest)")
body("Two complementary models are used: an Isolation Forest for unsupervised anomaly detection and a "
 "Random Forest classifier for supervised late-delivery prediction. IMPORTANT: in this synthetic dataset "
 "the late/on-time label is largely random with respect to pre-delivery features (post-hoc delay_days is "
 "excluded to avoid target leakage), so predictive power is modest (AUC ~0.53). On real operational data, "
 "supplier history, lead times and disruption signals carry genuine predictive value; the same pipeline, "
 "features and cost-based thresholds transfer directly.")
chart(C+"08_confusion_matrix.png",105); chart(C+"09_roc_curve.png",120)
pdf.add_page(); header("Model Performance (cont.)")
h2("5. Precision-Recall & Feature Importance"); chart(C+"10_precision_recall.png",120); chart(C+"11_feature_importance.png",165)

pdf.add_page(); header("Risk Scoring, Threshold Tuning & Alerting")
h2("6. Composite Risk Segmentation")
body("Every purchase order receives a composite risk score (0-100) blending the supervised late-probability "
 "(70%) and the normalized anomaly score (30%), mapped to four tiers driving KPI alerts and escalation.")
chart(C+"12_risk_level_distribution.png",150)
pdf.add_page(); header("Risk Scoring, Threshold Tuning & Alerting (cont.)")
rec=ar["at_recommended"]; ca=ar["cost_assumptions"]
h2("7. Cost-Based Intervention Threshold")
body(f"The intervention threshold is chosen to MINIMIZE expected cost. An unmitigated late delivery is "
 f"assigned a cost of ${ca['missed_late_FN_usd']:,.0f} (expedite freight, line-down risk), while an "
 f"unnecessary intervention costs ${ca['false_intervention_FP_usd']:,.0f}. The cost-minimizing threshold "
 f"is {ar['recommended_threshold']}, catching {rec['late_caught']} late orders (recall {rec['recall']}), "
 f"triggering {rec['interventions']} interventions, at an expected cost of ${rec['expected_cost_usd']:,.0f} "
 f"versus ${ar['baseline_cost_ignore']:,.0f} if late risk were ignored ({ar['cost_saving_vs_ignore_pct']}% reduction).")
chart(C+"13_cost_curve.png",165); chart(C+"14_metric_vs_threshold.png",165)
h2("KPI Alert Tiers")
pdf.set_font("Helvetica","",10)
for tier,desc in ar["kpi_alert_tiers"].items(): pdf.set_font("Helvetica","B",10); pdf.multi_cell(0,6,tier+":  "+desc); pdf.ln(0.3)
pdf.ln(2); h2("Power BI Deliverable")
body("A star-schema dataset (fact_purchase_orders_scored + fact_disruptions + dimension tables + KPI "
 "measures) is exported to the powerbi/ folder, ready to import into Power BI Desktop with documented "
 "relationships and suggested DAX measures (see powerbi/DATA_MODEL.md).")

# ---------- SQL + Inventory section ----------
ik_path="supplychain_project/data/inventory_kpis.json"
if os.path.exists(ik_path):
    ik=json.load(open(ik_path))
    pdf.add_page(); header("SQL Analysis & Inventory Bottlenecks")
    h2("8. SQL Analytical Layer")
    body("All joins and aggregations were also implemented in SQL (DuckDB) over a queryable database built "
     "from the 8 source files, mirroring a production SQL + Pandas workflow. Five analytical queries cover "
     "shipment delays by supplier, supplier risk overview, inventory bottlenecks, disruption impact, and "
     "plant inventory health (see sql/analysis_queries.sql and the sql_*.csv exports).")
    h2("9. Inventory Bottleneck Findings")
    body(f"Across {ik['total_sku_lines']} SKU lines, {ik['below_reorder']} are below their reorder point and "
     f"{ik['shortage_risk_flagged']} are flagged shortage-risk. Critically, {ik['critical_below_reorder']} "
     f"High/Critical-criticality items are understocked. The lowest cover is just {ik['min_days_of_stock']} "
     f"days of stock (median {ik['median_days_of_stock']} days), exposing line-down risk for key components.")
    chart(C+"16_inventory_bottleneck_by_plant.png",165)
    chart(C+"17_stock_position_scatter.png",150)
    pdf.add_page(); header("SQL Analysis & Inventory Bottlenecks (cont.)")
    chart(C+"15_inventory_days_of_stock.png",165)
    h2("Power BI DAX Deliverable")
    body("A complete set of production DAX measures (delivery, risk, supplier, disruption and inventory KPIs) "
     "is provided in powerbi/MEASURES.dax, alongside the star-schema CSVs and DATA_MODEL.md, so the .pbix can "
     "be assembled in Power BI Desktop in minutes with live KPI monitoring.")

pdf.output("supplychain_project/reports/Supply_Chain_Risk_Report.pdf")
print("PDF written.")
