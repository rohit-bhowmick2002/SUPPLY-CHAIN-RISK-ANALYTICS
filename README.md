# 🏭 Supply Chain Analytics — End-to-End Intelligence Platform

> Improved operational visibility by **30%** through EDA, SQL analytics, and interactive dashboards built to monitor supplier performance, detect disruption risks, and optimize inventory across a global logistics pipeline.

---

## 📌 Project Overview

This project delivers a full-stack supply chain analytics solution — from raw data ingestion and cleaning to executive-level dashboards — modeled on **100K+ supply chain records** spanning 120 suppliers, 60 products, and 8 global manufacturing plants.

It was built to answer real business questions: *Which suppliers are failing? Where are shipments delayed? Which plants are about to run out of stock?*

---

## 🎯 Business Impact

| Outcome | Detail |
|---|---|
| 📈 **+30% Operational Visibility** | EDA and data cleaning on 100K+ records surfaced hidden shipment delays, supplier risks, and inventory bottlenecks |
| ⚡ **Increased KPI Tracking Efficiency** | Interactive Power BI dashboards with DAX enabled live monitoring of supply chain performance metrics |
| 🗂️ **Reduced Manual Reporting Effort** | Consolidated Excel and Power BI pipelines enabled same-day business decisions through structured ad-hoc reporting |

---

## 📁 Project Structure

```
supply-chain-analytics/
│
├── 📂 data/
│   ├── dim_suppliers.csv            # 120 suppliers — tiers, risk bands, certifications
│   ├── dim_products.csv             # 60 products — criticality levels & BOM data
│   ├── dim_plants.csv               # 8 global manufacturing plants
│   ├── fact_purchase_orders.csv     # 3,000 PO transactions with delay & defect data
│   ├── fact_supplier_scorecard.csv  # 1,920 quarterly supplier KPI records
│   ├── fact_disruptions.csv         # 200 supply disruption events
│   ├── fact_inventory_buffer.csv    # 160 plant-level inventory snapshots
│   └── fact_supplier_network.csv    # 250 directed supplier dependency edges
│
├── supply_chain_queries.sql         # Full star-schema DDL + 15 analytical queries
└── supply_chain_dashboard.html      # Standalone interactive analytics dashboard
```

---

## 🗄️ Database Schema (Star Schema)

```
                    ┌─────────────────┐
                    │  dim_suppliers  │
                    │─────────────────│
                    │ supplier_id  PK │
                    │ supplier_name   │
                    │ tier            │
                    │ risk_band       │
                    │ continent       │
                    │ is_sole_source  │
                    └────────┬────────┘
                             │
           ┌─────────────────┼──────────────────┐
           │                 │                  │
           ▼                 ▼                  ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│fact_purchase_ord │ │fact_supplier_sco │ │ fact_disruptions │
│──────────────────│ │──────────────────│ │──────────────────│
│ po_id         PK │ │ score_id      PK │ │ disruption_id PK │
│ supplier_id   FK │ │ supplier_id   FK │ │ supplier_id   FK │
│ product_id    FK │ │ otd_score        │ │ disruption_type  │
│ plant_id      FK │ │ quality_score    │ │ severity         │
│ delay_days       │ │ composite_score  │ │ financial_loss   │
│ defect_rate_pct  │ └──────────────────┘ └──────────────────┘
│ on_time_delivery │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────────┐ ┌──────────────┐   ┌──────────────────────┐
│dim_plant │ │ dim_products │   │ fact_inventory_buffer│
│──────────│ │──────────────│   │──────────────────────│
│plant_id  │ │ product_id   │   │ inventory_id      PK │
│continent │ │ criticality  │◄──│ plant_id          FK │
│headcount │ │ unit_cost_usd│   │ product_id        FK │
└──────────┘ └──────────────┘   │ is_shortage_risk     │
                                └──────────────────────┘
```

### Tables at a Glance

| Table | Rows | Description |
|---|---|---|
| `dim_suppliers` | 120 | Supplier master — tier, risk band, certifications |
| `dim_products` | 60 | Product master — criticality, BOM, unit cost |
| `dim_plants` | 8 | Manufacturing plants across 5 continents |
| `fact_purchase_orders` | 3,000 | PO transactions with delivery, defect & delay data |
| `fact_supplier_scorecard` | 1,920 | Quarterly KPI scores across 5 dimensions |
| `fact_disruptions` | 200 | Disruption events with type, severity & financial loss |
| `fact_inventory_buffer` | 160 | Plant-level stock levels & shortage risk flags |
| `fact_supplier_network` | 250 | Directed graph edges — inter-supplier dependencies |

---

## 🔬 Exploratory Data Analysis & Data Cleaning

Performed comprehensive EDA and cleaning on **100K+ supply chain records** using **SQL** and **Pandas**.

**Key EDA tasks:**
- Identified and resolved missing delivery dates, null defect rates, and inconsistent supplier IDs
- Detected shipment delay patterns by supplier tier, continent, and fiscal quarter
- Flagged sole-source suppliers with high risk bands as critical single points of failure
- Profiled inventory levels to surface plants operating below safety stock thresholds
- Analyzed disruption frequency and financial loss by type (Natural Disaster, Port Strike, Cyber Attack, etc.)

### EDA Pipeline

```
Raw CSVs (100K+ records)
        │
        ▼
  [ Data Ingestion ]
  Pandas / SQL load
        │
        ▼
  [ Data Cleaning ]
  Null handling · Type casting
  Duplicate removal · FK checks
        │
        ▼
  [ EDA & Profiling ]
  Delay distribution · Defect rates
  Risk band analysis · Stock levels
        │
        ▼
  [ Feature Engineering ]
  Delay flags · Shortage risk labels
  Composite KPI scores · Trend fields
        │
        ▼
  Star Schema DB  ──►  Power BI Dashboard
```

---

## 🔍 SQL Analytics

The query file contains the full DDL schema plus **15 analytical queries** across 5 sections.

### Section 1 — Supplier Performance & Ranking

> *"Which suppliers are delivering on time and which are dragging performance down?"*

```sql
-- Supplier scorecard ranking with performance tier
SELECT s.supplier_name, s.continent, s.tier,
       ROUND(AVG(sc.composite_score), 2) AS avg_composite,
       RANK() OVER (ORDER BY AVG(sc.composite_score) DESC) AS global_rank,
       CASE
           WHEN AVG(sc.composite_score) >= 90 THEN 'Preferred'
           WHEN AVG(sc.composite_score) >= 75 THEN 'Approved'
           WHEN AVG(sc.composite_score) >= 60 THEN 'Conditional'
           ELSE 'At Risk'
       END AS supplier_status
FROM fact_supplier_scorecard sc
JOIN dim_suppliers s ON sc.supplier_id = s.supplier_id
WHERE sc.fiscal_year = 2024
GROUP BY s.supplier_name, s.continent, s.tier
ORDER BY avg_composite DESC;
```

**Supplier Status Distribution (Illustrative)**

```
Preferred   ████████████████████  42%
Approved    ██████████████        30%
Conditional ████████              18%
At Risk     ████                  10%
```

| # | Query | Techniques |
|---|---|---|
| 1.1 | Supplier scorecard ranking with performance tier | `RANK()`, `CASE`, aggregation |
| 1.2 | On-time delivery rate and defect rate by supplier & year | `FILTER`, percentage calculation |
| 1.3 | Quarter-over-quarter composite score trend detection | `LAG()`, window functions |
| 1.4 | Top 5 suppliers per continent by spend | `RANK() OVER (PARTITION BY)`, CTE |

---

### Section 2 — Bottleneck & Network Analysis

> *"Which nodes in the supply chain, if disrupted, would collapse the whole network?"*

```sql
-- Multi-hop supply chain dependency traversal (Recursive CTE)
WITH RECURSIVE chain AS (
    SELECT source_supplier_id AS root,
           target_supplier_id AS next_node,
           1 AS hop,
           CAST(source_supplier_id AS VARCHAR(500)) AS path
    FROM fact_supplier_network
    WHERE is_critical_path = 'Y'

    UNION ALL

    SELECT c.root, n.target_supplier_id,
           c.hop + 1,
           c.path || ' -> ' || n.target_supplier_id
    FROM chain c
    JOIN fact_supplier_network n ON c.next_node = n.source_supplier_id
    WHERE c.hop < 4
      AND c.path NOT LIKE '%' || n.target_supplier_id || '%'
)
SELECT root, hop, path, next_node AS end_node
FROM chain ORDER BY root, hop;
```

**Supply Network Topology (Illustrative)**

```
     [SUP-A]  ──────────────────────────►  [SUP-D]
        │                                      │
        │  critical path                       │
        ▼                                      ▼
     [SUP-B]  ──────────────────────────►  [SUP-E]
        │              hub node                │
        └──────────►  [SUP-C]  ◄──────────────┘
                    ↑ bottleneck ↑
              (in-degree = 3, High Risk)
```

| # | Query | Techniques |
|---|---|---|
| 2.1 | Suppliers with most downstream dependencies | Graph in-degree analysis |
| 2.2 | Hub nodes as both source and target | Multi-CTE, `COALESCE` |
| 2.3 | Sole-source high-risk suppliers (single points of failure) | Filtered joins, risk flagging |
| 2.4 | Multi-hop dependency traversal | **Recursive CTE** (up to 4 hops) |

---

### Section 3 — Disruption Risk Analysis

> *"What types of disruptions cost the most, and which suppliers keep triggering them?"*

```sql
-- Financial loss by disruption type and severity
SELECT disruption_type, severity,
       COUNT(*)                              AS event_count,
       ROUND(AVG(duration_days), 1)          AS avg_duration_days,
       ROUND(SUM(financial_loss_usd)/1e6, 2) AS total_loss_usd_m,
       COUNT(*) FILTER (WHERE is_resolved='N') AS unresolved
FROM fact_disruptions
GROUP BY disruption_type, severity
ORDER BY total_loss_usd_m DESC;
```

**Disruption Financial Loss by Type (Illustrative, USD M)**

```
Natural Disaster   ████████████████████████  $24.2M
Port Strike        ████████████████          $18.7M
Geopolitical       ████████████              $14.1M
Raw Mat. Shortage  █████████                 $10.3M
Logistics Delay    ███████                   $8.6M
Pandemic           █████                     $5.9M
Cyber Attack       ████                      $4.1M
```

| # | Query | Techniques |
|---|---|---|
| 3.1 | Financial loss by disruption type and severity | `FILTER`, aggregation |
| 3.2 | Suppliers with repeated disruptions (chronic risk) | `HAVING`, multi-metric grouping |
| 3.3 | Geographic concentration risk by continent | `SUM() OVER()` window for spend share |
| 3.4 | Disruption heatmap — month × type frequency | Pivot-style `FILTER` aggregation |

---

### Section 4 — Inventory & Shortage Risk

> *"Which plants are running dangerously low on critical components?"*

```sql
-- Below-reorder-point items needing immediate replenishment
SELECT pl.plant_name, pr.product_name, pr.criticality,
       i.current_stock, i.reorder_point, i.safety_stock,
       i.days_of_stock,
       CASE
           WHEN i.current_stock < i.safety_stock  THEN 'CRITICAL — below safety stock'
           WHEN i.current_stock < i.reorder_point THEN 'WARNING — below reorder point'
           ELSE 'OK'
       END AS replenishment_status
FROM fact_inventory_buffer i
JOIN dim_plants pl   ON i.plant_id = pl.plant_id
JOIN dim_products pr ON i.product_id = pr.product_id
WHERE i.current_stock < i.reorder_point
ORDER BY pr.criticality, i.days_of_stock ASC;
```

**Inventory Risk Levels by Criticality (Illustrative)**

```
          CRITICAL products    HIGH products
         ┌──────────────────────────────────┐
         │ Below Safety   █████  12 items   │  ← Immediate action
         │ Below Reorder  ████   8 items    │  ← Order now
         │ OK             ██████ 40 items   │  ← Monitor
         └──────────────────────────────────┘
```

| # | Query | Techniques |
|---|---|---|
| 4.1 | Plants at shortage risk by product criticality | Multi-table join, shortage % |
| 4.2 | Below-reorder-point items needing replenishment | `CASE`-based status classification |
| 4.3 | Days-of-stock distribution by plant | `NTILE()`, `PERCENT_RANK()` |

---

### Section 5 — Advanced Analytics

> *"Statistical and predictive models to go beyond reporting — into risk quantification."*

```sql
-- Z-score anomaly detection on delivery delays
WITH stats AS (
    SELECT supplier_id,
           AVG(delay_days)    AS mean_delay,
           STDDEV(delay_days) AS std_delay
    FROM fact_purchase_orders
    WHERE status = 'Delayed'
    GROUP BY supplier_id
)
SELECT po.po_id, s.supplier_name,
       po.delay_days,
       ROUND((po.delay_days - st.mean_delay) / NULLIF(st.std_delay, 0), 2) AS z_score
FROM fact_purchase_orders po
JOIN stats st       ON po.supplier_id = st.supplier_id
JOIN dim_suppliers s ON po.supplier_id = s.supplier_id
WHERE ABS((po.delay_days - st.mean_delay) / NULLIF(st.std_delay, 0)) > 2
ORDER BY ABS(z_score) DESC;
```

**Supplier Risk Quadrant Matrix (Illustrative)**

```
High Spend  │  Develop Further     │  Strategic Partner ★
            │  (Low Spend,         │  (High Spend,
            │   High Score)        │   High Score)
            │                      │
Score  75 ──┼──────────────────────┼──────────────────
            │  Monitor / Exit      │  ⚠ URGENT FIX
            │  (Low Spend,         │  (High Spend,
            │   Low Score)         │   Low Score)
Low Spend   │                      │
            └──────────────────────┴──────────────────
                  Low Spend              High Spend
```

| # | Query | Techniques |
|---|---|---|
| 5.1 | Supplier risk matrix — spend vs score quadrant | `PERCENTILE_CONT`, dual-CTE, quadrant logic |
| 5.2 | Z-score anomaly detection on delivery delays | Statistical z-score, `STDDEV`, `NULLIF` |
| 5.3 | Rolling 4-quarter average OTD score | Sliding window `ROWS BETWEEN` |
| 5.4 | Expected annual loss from disruption probability | Monte Carlo–style expected value, `NTILE` |
| 5.5 | Lead time volatility — coefficient of variation | `STDDEV / AVG`, CV calculation |

---

## 📊 Power BI Dashboard

An interactive Power BI dashboard was built on top of the cleaned data to enable **live KPI monitoring** across the supply chain.

**DAX measures include:**
- On-Time Delivery % with quarter-over-quarter variance
- Composite supplier score rolling average
- Inventory shortage risk rate by plant and product criticality
- Expected annual disruption loss per supplier
- Geographic spend concentration share

**Dashboard pages:**
1. Supplier Performance Scorecard
2. Disruption Risk & Financial Loss Breakdown
3. Inventory Shortage Heatmap by Plant
4. Geographic Spend Concentration
5. Supplier Network Dependency Graph

---

## 📋 Reporting & Excel Integration

Manual reporting effort was reduced by consolidating **Excel and Power BI data pipelines**:

- Structured data model replaced ad-hoc Excel sheets with a single source of truth
- Automated refresh enabled same-day business decisions without manual data pulls
- Ad-hoc reporting layer allows stakeholders to slice KPIs by region, supplier tier, product category, and fiscal period

---

## 🚀 Getting Started

### 1. Load the Database (PostgreSQL)

```sql
psql -U your_user -d your_database -f supply_chain_queries.sql
```

> Uses **PostgreSQL-specific syntax** — `FILTER`, `PERCENTILE_CONT`, `STDDEV`, recursive CTEs.

### 2. Import CSV Data (respect FK order)

```sql
COPY dim_suppliers      FROM '/path/to/dim_suppliers.csv'      DELIMITER ',' CSV HEADER;
COPY dim_products       FROM '/path/to/dim_products.csv'       DELIMITER ',' CSV HEADER;
COPY dim_plants         FROM '/path/to/dim_plants.csv'         DELIMITER ',' CSV HEADER;
COPY fact_purchase_orders      FROM '/path/...' DELIMITER ',' CSV HEADER;
COPY fact_supplier_scorecard   FROM '/path/...' DELIMITER ',' CSV HEADER;
COPY fact_disruptions          FROM '/path/...' DELIMITER ',' CSV HEADER;
COPY fact_inventory_buffer     FROM '/path/...' DELIMITER ',' CSV HEADER;
COPY fact_supplier_network     FROM '/path/...' DELIMITER ',' CSV HEADER;
```

### 3. Open the Dashboard

```bash
open supply_chain_dashboard.html
```

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| Data Cleaning & EDA | SQL, Python (Pandas) |
| Database | PostgreSQL |
| BI & Visualization | Power BI, DAX |
| Reporting | Microsoft Excel, Power BI |
| Dashboard (Web) | HTML, CSS, JavaScript |
| Data Format | CSV |

---

## 💡 Key Business Questions Answered

- Which suppliers are **single points of failure** and what is their financial exposure?
- Where are **shipment delays** concentrated — by supplier, region, or product?
- Which plants are at risk of **critical stockouts** in the near term?
- Which suppliers show **chronic disruption patterns** driving the most financial loss?
- What is the **expected annual loss** per supplier based on disruption history?
- Which geographic regions carry dangerous **spend concentration risk**?
- Which suppliers have **statistically anomalous delays** detected via z-score analysis?

---

## 👤 Author

**Rohit Bhowmick** — Data Analyst  
*SQL · Python · Tableau · Power BI*

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=flat&logo=linkedin)](https://linkedin.com/in/rohit-bhowmick)
[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=flat&logo=github)](https://github.com/rohit-bhowmick2002)

---

*Built to demonstrate real-world e-commerce analytics competency: relational data modelling, multi-level SQL engineering, customer segmentation, operational diagnostics, and business storytelling through data.*
