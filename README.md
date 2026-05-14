# 🏭 Supply Chain Risk & Performance Analytics

> **End-to-end supply chain intelligence system** — tracking $7.7B in purchase orders across 120 global suppliers, 8 manufacturing plants, and 60 product lines to surface disruption risk, supplier performance, and inventory resilience.

---

## 📌 Project Overview

This project delivers a **production-grade supply chain analytics platform** built on a normalized star-schema data warehouse. It covers the full analytical lifecycle — from SQL data modeling and ETL to an interactive HTML dashboard — enabling procurement and operations teams to make faster, data-driven decisions.

**Domain:** Automotive / Manufacturing Supply Chain  
**Stack:** SQL · Python · HTML/CSS/JS · Data Visualization  
**Data Scope:** 2021–2024 · 3,000+ purchase orders · 120 suppliers · 8 global plants

---

## 📊 Key Business Impact

| Metric | Value |
|--------|-------|
| 💰 Total Purchase Order Value Analyzed | **$7.74 Billion** |
| 🚨 Total Disruption Financial Exposure | **$478.9 Million** |
| 📦 On-Time Delivery (OTD) Rate | **71.6%** |
| ⏱️ Average Delay (when delayed) | **15.7 days** |
| 🔬 Average Defect Rate | **4.00%** |
| 🏆 Average Supplier Composite Score | **83.5 / 100** |
| ⚠️ High-Risk Suppliers Identified | **22 of 120 (18.3%)** |
| 🔗 Sole-Source Dependency Suppliers | **44 (36.7%)** — critical concentration risk |
| 🛑 Critical Path Network Edges | **110 of 250 (44%)** |
| 🗓️ Average Disruption Duration | **47.1 days** |
| 📉 Inventory Shortage Risk Items | **6 of 160 SKUs monitored** |

---

## 🗂️ Data Architecture

Star-schema warehouse with **3 dimension tables** and **5 fact tables**:

```
dim_suppliers       → 120 suppliers across 5 continents, tiered & risk-banded
dim_products        → 60 products with criticality rating & BOM complexity
dim_plants          → 8 manufacturing plants with output & headcount

fact_purchase_orders    → 3,000 POs with delivery, delay, defect & cost tracking
fact_disruptions        → 200 disruption events across 9 disruption types
fact_supplier_scorecard → 1,920 quarterly KPI records (OTD, Quality, Cost, etc.)
fact_inventory_buffer   → 160 inventory positions with shortage risk flags
fact_supplier_network   → 250 supplier dependency edges with critical path mapping
```

---

## 🔍 Analytical Capabilities

### Supplier Performance
- Multi-dimensional scorecard tracking **OTD, Quality, Cost, Responsiveness, Sustainability**
- Quarterly trend analysis across 4 fiscal years (2021–2024)
- Incident frequency mapping to supplier risk bands

### Disruption Intelligence
- 9 disruption categories: Logistics Delay, Natural Disaster, Pandemic, Port Strike, Quality Recall, Supplier Bankruptcy, Raw Material Shortage, Cyber Attack, Geopolitical
- Financial loss quantification per event with resolution tracking
- Alternative supplier activation rate analysis (**50% activation rate** during disruptions)

### Inventory Risk
- Safety stock vs. reorder point gap analysis
- Days-of-stock coverage per plant × product combination
- Real-time shortage risk flagging

### Network & Concentration Risk
- Supplier dependency graph (Tier 1 → Tier 2 → Tier 3)
- Critical path identification across the sub-tier network
- Sole-source exposure across **36.7% of the supplier base**

---

## 🛠️ Technical Implementation

```sql
-- Normalized star schema with referential integrity & check constraints
-- Indexed on continent, tier, risk_band, fiscal_year, plant_id, product_id
-- Covers: DDL, DML, analytical queries, aggregation & window functions
```

- **SQL:** Full schema DDL with constraints, indexes, and analytical queries
- **Dashboard:** Interactive single-page HTML dashboard with live filters and KPI cards
- **Data:** Synthetic but statistically realistic dataset mirroring real automotive supply chain dynamics

---

## 📁 Repository Structure

```
├── supply_chain_queries.sql       # Full schema DDL + analytical SQL queries
├── supply_chain_dashboard.html    # Interactive analytics dashboard
├── dim_plants.csv                 # Plant dimension (8 global facilities)
├── dim_products.csv               # Product dimension (60 SKUs)
├── dim_suppliers.csv              # Supplier dimension (120 suppliers)
├── fact_purchase_orders.csv       # 3,000 purchase order records
├── fact_disruptions.csv           # 200 disruption events
├── fact_supplier_scorecard.csv    # 1,920 quarterly KPI records
├── fact_inventory_buffer.csv      # 160 inventory buffer positions
└── fact_supplier_network.csv      # 250 supplier dependency edges
```

---

## 🚀 Getting Started

**Run the SQL schema:**
```sql
-- Execute supply_chain_queries.sql in any SQL-compatible database
-- (PostgreSQL, MySQL, SQLite, SQL Server)
```

**View the dashboard:**
```bash
# Open directly in browser — no server required
open supply_chain_dashboard.html
```

**Explore the data:**
```python
import pandas as pd
po = pd.read_csv("fact_purchase_orders.csv")
print(po.groupby("fiscal_year")["total_value_usd"].sum())
```

---

## 💡 Business Questions Answered

- Which suppliers pose the **highest financial risk** if they fail?
- Where are the **sole-source dependencies** most concentrated by category and continent?
- Which plants face **inventory shortage exposure** within the next 30 days?
- How has **supplier OTD and quality** trended quarter-over-quarter?
- Which disruption types caused the **greatest financial losses**?
- What percentage of the network sits on a **critical supply path**?

---

## 👤 Author

**Rohit Bhowmick** — Data Analyst  
*SQL · Python · Tableau · Power BI*


[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](www.linkedin.com/in/rohit-bhowmick)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=flat&logo=github)](https://github.com/rohit-bhowmick2002)

---

*Built to demonstrate end-to-end data analytics competency: data modeling, SQL engineering, KPI design, risk quantification, and dashboard storytelling.*
