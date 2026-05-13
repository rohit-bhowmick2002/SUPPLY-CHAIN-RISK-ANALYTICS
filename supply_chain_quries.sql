
-- ============================================================
-- DROP ORDER (reverse FK dependency)
-- ============================================================
DROP TABLE IF EXISTS fact_supplier_network;
DROP TABLE IF EXISTS fact_inventory_buffer;
DROP TABLE IF EXISTS fact_disruptions;
DROP TABLE IF EXISTS fact_supplier_scorecard;
DROP TABLE IF EXISTS fact_purchase_orders;
DROP TABLE IF EXISTS dim_plants;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_suppliers;


-- ============================================================
-- TABLE 1: dim_suppliers
-- ============================================================
CREATE TABLE dim_suppliers (
    supplier_id          VARCHAR(10)   NOT NULL,
    supplier_name        VARCHAR(120)  NOT NULL,
    country_code         CHAR(2)       NOT NULL,
    country_name         VARCHAR(60)   NOT NULL,
    continent            VARCHAR(20)   NOT NULL,
    category             VARCHAR(40)   NOT NULL,
    tier                 VARCHAR(10)   NOT NULL,
    established_year     SMALLINT      NOT NULL,
    annual_capacity_usd  DECIMAL(18,2) NOT NULL,
    lead_time_days       SMALLINT      NOT NULL,
    min_order_qty        INTEGER       NOT NULL,
    risk_band            VARCHAR(10)   NOT NULL,
    is_sole_source       CHAR(1)       NOT NULL DEFAULT 'N',
    certifications       VARCHAR(60),
    CONSTRAINT pk_dim_suppliers PRIMARY KEY (supplier_id),
    CONSTRAINT chk_supplier_tier CHECK (tier IN ('Tier 1','Tier 2','Tier 3')),
    CONSTRAINT chk_supplier_risk CHECK (risk_band IN ('Low','Medium','High')),
    CONSTRAINT chk_sole_source   CHECK (is_sole_source IN ('Y','N'))
);
CREATE INDEX idx_sup_continent ON dim_suppliers(continent);
CREATE INDEX idx_sup_tier      ON dim_suppliers(tier);
CREATE INDEX idx_sup_risk      ON dim_suppliers(risk_band);
CREATE INDEX idx_sup_category  ON dim_suppliers(category);

select * from dim_suppliers;

-- ============================================================
-- TABLE 2: dim_products
-- ============================================================
CREATE TABLE dim_products (
    product_id       VARCHAR(10)   NOT NULL,
    product_name     VARCHAR(100)  NOT NULL,
    product_category VARCHAR(60)   NOT NULL,
    criticality      VARCHAR(10)   NOT NULL,
    bom_components   SMALLINT      NOT NULL,
    unit_cost_usd    DECIMAL(12,2) NOT NULL,
    CONSTRAINT pk_dim_products PRIMARY KEY (product_id),
    CONSTRAINT chk_criticality CHECK (criticality IN ('Critical','High','Medium','Low'))
);

select * from dim_products;

-- ============================================================
-- TABLE 3: dim_plants
-- ============================================================
CREATE TABLE dim_plants (
    plant_id          VARCHAR(10)   NOT NULL,
    plant_name        VARCHAR(80)   NOT NULL,
    country_code      CHAR(2)       NOT NULL,
    country_name      VARCHAR(60)   NOT NULL,
    continent         VARCHAR(20)   NOT NULL,
    headcount         INTEGER       NOT NULL,
    annual_output_usd DECIMAL(18,2) NOT NULL,
    CONSTRAINT pk_dim_plants PRIMARY KEY (plant_id)
);

select * from dim_plants;

-- ============================================================
-- TABLE 4: fact_purchase_orders
-- ============================================================
CREATE TABLE fact_purchase_orders (
    po_id                VARCHAR(12)   NOT NULL,
    supplier_id          VARCHAR(10)   NOT NULL,
    product_id           VARCHAR(10)   NOT NULL,
    plant_id             VARCHAR(10)   NOT NULL,
    order_date           DATE          NOT NULL,
    fiscal_year          SMALLINT      NOT NULL,
    fiscal_month         SMALLINT      NOT NULL,
    scheduled_delivery   DATE          NOT NULL,
    actual_delivery      DATE,
    delay_days           SMALLINT      NOT NULL DEFAULT 0,
    quantity_ordered     INTEGER       NOT NULL,
    unit_price_usd       DECIMAL(12,2) NOT NULL,
    total_value_usd      DECIMAL(18,2) NOT NULL,
    status               VARCHAR(20)   NOT NULL,
    defect_rate_pct      DECIMAL(5,2)  NOT NULL DEFAULT 0,
    on_time_delivery     CHAR(1)       NOT NULL DEFAULT 'Y',
    CONSTRAINT pk_fact_po        PRIMARY KEY (po_id),
    CONSTRAINT fk_po_supplier    FOREIGN KEY (supplier_id) REFERENCES dim_suppliers(supplier_id),
    CONSTRAINT fk_po_product     FOREIGN KEY (product_id)  REFERENCES dim_products(product_id),
    CONSTRAINT fk_po_plant       FOREIGN KEY (plant_id)    REFERENCES dim_plants(plant_id),
    CONSTRAINT chk_po_status     CHECK (status IN ('Delivered','Delayed','Cancelled','In Transit','Partial')),
    CONSTRAINT chk_otd           CHECK (on_time_delivery IN ('Y','N')),
    CONSTRAINT chk_defect        CHECK (defect_rate_pct >= 0 AND defect_rate_pct <= 100)
);
CREATE INDEX idx_po_supplier ON fact_purchase_orders(supplier_id);
CREATE INDEX idx_po_plant    ON fact_purchase_orders(plant_id);
CREATE INDEX idx_po_year     ON fact_purchase_orders(fiscal_year);
CREATE INDEX idx_po_status   ON fact_purchase_orders(status);
CREATE INDEX idx_po_otd      ON fact_purchase_orders(on_time_delivery);

select * from fact_purchase_orders;

-- ============================================================
-- TABLE 5: fact_supplier_scorecard
-- ============================================================
CREATE TABLE fact_supplier_scorecard (
    score_id               VARCHAR(12)  NOT NULL,
    supplier_id            VARCHAR(10)  NOT NULL,
    fiscal_year            SMALLINT     NOT NULL,
    quarter                SMALLINT     NOT NULL,
    otd_score              DECIMAL(5,2) NOT NULL,
    quality_score          DECIMAL(5,2) NOT NULL,
    cost_score             DECIMAL(5,2) NOT NULL,
    responsiveness_score   DECIMAL(5,2) NOT NULL,
    sustainability_score   DECIMAL(5,2) NOT NULL,
    composite_score        DECIMAL(5,2) NOT NULL,
    incidents_reported     SMALLINT     NOT NULL DEFAULT 0,
    CONSTRAINT pk_scorecard      PRIMARY KEY (score_id),
    CONSTRAINT uq_scorecard      UNIQUE (supplier_id, fiscal_year, quarter),
    CONSTRAINT fk_scorecard_sup  FOREIGN KEY (supplier_id) REFERENCES dim_suppliers(supplier_id),
    CONSTRAINT chk_quarter       CHECK (quarter BETWEEN 1 AND 4),
    CONSTRAINT chk_scores        CHECK (otd_score BETWEEN 0 AND 100 AND quality_score BETWEEN 0 AND 100)
);
CREATE INDEX idx_sc_supplier ON fact_supplier_scorecard(supplier_id);
CREATE INDEX idx_sc_year     ON fact_supplier_scorecard(fiscal_year);

select * from fact_supplier_scorecard;

-- ============================================================
-- TABLE 6: fact_disruptions
-- ============================================================
CREATE TABLE fact_disruptions (
    disruption_id                  VARCHAR(10)   NOT NULL,
    supplier_id                    VARCHAR(10)   NOT NULL,
    disruption_type                VARCHAR(40)   NOT NULL,
    severity                       VARCHAR(10)   NOT NULL,
    start_date                     DATE          NOT NULL,
    end_date                       DATE,
    duration_days                  SMALLINT      NOT NULL,
    fiscal_year                    SMALLINT      NOT NULL,
    fiscal_month                   SMALLINT      NOT NULL,
    financial_loss_usd             DECIMAL(18,2) NOT NULL DEFAULT 0,
    is_resolved                    CHAR(1)       NOT NULL DEFAULT 'N',
    alternative_supplier_activated CHAR(1)       NOT NULL DEFAULT 'N',
    CONSTRAINT pk_disruptions      PRIMARY KEY (disruption_id),
    CONSTRAINT fk_disruption_sup   FOREIGN KEY (supplier_id) REFERENCES dim_suppliers(supplier_id),
    CONSTRAINT chk_severity        CHECK (severity IN ('Low','Medium','High','Critical')),
    CONSTRAINT chk_resolved        CHECK (is_resolved IN ('Y','N')),
    CONSTRAINT chk_alt_sup         CHECK (alternative_supplier_activated IN ('Y','N'))
);
CREATE INDEX idx_dis_supplier ON fact_disruptions(supplier_id);
CREATE INDEX idx_dis_severity ON fact_disruptions(severity);
CREATE INDEX idx_dis_year     ON fact_disruptions(fiscal_year);
CREATE INDEX idx_dis_type     ON fact_disruptions(disruption_type);

select * from fact_disruptions;

-- ============================================================
-- TABLE 7: fact_inventory_buffer
-- ============================================================
CREATE TABLE fact_inventory_buffer (
    inventory_id      VARCHAR(10)  NOT NULL,
    plant_id          VARCHAR(10)  NOT NULL,
    product_id        VARCHAR(10)  NOT NULL,
    current_stock     INTEGER      NOT NULL DEFAULT 0,
    reorder_point     INTEGER      NOT NULL,
    safety_stock      INTEGER      NOT NULL,
    days_of_stock     DECIMAL(6,1) NOT NULL,
    is_shortage_risk  CHAR(1)      NOT NULL DEFAULT 'N',
    fiscal_year       SMALLINT     NOT NULL,
    CONSTRAINT pk_inventory       PRIMARY KEY (inventory_id),
    CONSTRAINT uq_inventory       UNIQUE (plant_id, product_id, fiscal_year),
    CONSTRAINT fk_inv_plant       FOREIGN KEY (plant_id)   REFERENCES dim_plants(plant_id),
    CONSTRAINT fk_inv_product     FOREIGN KEY (product_id) REFERENCES dim_products(product_id),
    CONSTRAINT chk_shortage_risk  CHECK (is_shortage_risk IN ('Y','N')),
    CONSTRAINT chk_stock          CHECK (current_stock >= 0),
    CONSTRAINT chk_days_of_stock  CHECK (days_of_stock >= 0)
);
CREATE INDEX idx_inv_plant   ON fact_inventory_buffer(plant_id);
CREATE INDEX idx_inv_product ON fact_inventory_buffer(product_id);
CREATE INDEX idx_inv_risk    ON fact_inventory_buffer(is_shortage_risk);

select * from fact_inventory_buffer;

-- ============================================================
-- TABLE 8: fact_supplier_network (directed graph edges)
-- ============================================================
CREATE TABLE fact_supplier_network (
    edge_id              VARCHAR(10)   NOT NULL,
    source_supplier_id   VARCHAR(10)   NOT NULL,
    target_supplier_id   VARCHAR(10)   NOT NULL,
    dependency_type      VARCHAR(30)   NOT NULL,
    annual_flow_usd      DECIMAL(18,2) NOT NULL,
    is_critical_path     CHAR(1)       NOT NULL DEFAULT 'N',
    CONSTRAINT pk_network        PRIMARY KEY (edge_id),
    CONSTRAINT fk_net_source     FOREIGN KEY (source_supplier_id) REFERENCES dim_suppliers(supplier_id),
    CONSTRAINT fk_net_target     FOREIGN KEY (target_supplier_id) REFERENCES dim_suppliers(supplier_id),
    CONSTRAINT chk_net_no_self   CHECK (source_supplier_id <> target_supplier_id),
    CONSTRAINT chk_critical_path CHECK (is_critical_path IN ('Y','N'))
);
CREATE INDEX idx_net_source ON fact_supplier_network(source_supplier_id);
CREATE INDEX idx_net_target ON fact_supplier_network(target_supplier_id);
CREATE INDEX idx_net_crit   ON fact_supplier_network(is_critical_path);

select * from fact_supplier_network;

-- ============================================================
-- SECTION 1: SUPPLIER PERFORMANCE & RANKING
-- ============================================================

-- 1.1 Overall supplier scorecard ranking with performance tier
SELECT s.supplier_id, s.supplier_name, s.continent, s.tier, s.category,
       ROUND(AVG(sc.composite_score),2)      AS avg_composite,
       ROUND(AVG(sc.otd_score),2)            AS avg_otd,
       ROUND(AVG(sc.quality_score),2)        AS avg_quality,
       ROUND(AVG(sc.cost_score),2)           AS avg_cost,
       SUM(sc.incidents_reported)            AS total_incidents,
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
GROUP BY s.supplier_id, s.supplier_name, s.continent, s.tier, s.category
ORDER BY avg_composite DESC;


-- 1.2 On-time delivery rate and defect rate by supplier & year
SELECT s.supplier_name, s.continent, s.tier, po.fiscal_year,
       COUNT(*)                                                      AS total_orders,
       COUNT(*) FILTER (WHERE po.on_time_delivery='Y')              AS on_time,
       ROUND(COUNT(*) FILTER (WHERE po.on_time_delivery='Y')
             * 100.0 / COUNT(*), 1)                                 AS otd_pct,
       ROUND(AVG(po.defect_rate_pct), 2)                            AS avg_defect_pct,
       ROUND(SUM(po.total_value_usd)/1e6, 2)                        AS spend_usd_m,
       COUNT(*) FILTER (WHERE po.status='Delayed')                  AS delayed_orders
FROM fact_purchase_orders po
JOIN dim_suppliers s ON po.supplier_id = s.supplier_id
GROUP BY s.supplier_name, s.continent, s.tier, po.fiscal_year
ORDER BY otd_pct ASC;


-- 1.3 Quarter-over-quarter composite score change (trend detection)
SELECT supplier_id, fiscal_year, quarter, composite_score,
       LAG(composite_score) OVER (PARTITION BY supplier_id ORDER BY fiscal_year, quarter) AS prev_qtr,
       ROUND(composite_score
           - LAG(composite_score) OVER (PARTITION BY supplier_id ORDER BY fiscal_year, quarter), 2) AS qoq_change,
       CASE
           WHEN composite_score
               - LAG(composite_score) OVER (PARTITION BY supplier_id ORDER BY fiscal_year, quarter) < -5
           THEN 'Declining Fast'
           WHEN composite_score
               - LAG(composite_score) OVER (PARTITION BY supplier_id ORDER BY fiscal_year, quarter) < 0
           THEN 'Slight Decline'
           WHEN composite_score
               - LAG(composite_score) OVER (PARTITION BY supplier_id ORDER BY fiscal_year, quarter) > 5
           THEN 'Improving Fast'
           ELSE 'Stable'
       END AS trend
FROM fact_supplier_scorecard
ORDER BY supplier_id, fiscal_year, quarter;


-- 1.4 Top 5 suppliers per continent by spend (RANK + PARTITION)
WITH ranked AS (
    SELECT s.supplier_name, s.continent, s.tier, s.category,
           ROUND(SUM(po.total_value_usd)/1e6, 2) AS spend_usd_m,
           RANK() OVER (PARTITION BY s.continent ORDER BY SUM(po.total_value_usd) DESC) AS rank_in_continent
    FROM fact_purchase_orders po
    JOIN dim_suppliers s ON po.supplier_id = s.supplier_id
    GROUP BY s.supplier_name, s.continent, s.tier, s.category
)
SELECT * FROM ranked WHERE rank_in_continent <= 5
ORDER BY continent, rank_in_continent;


-- ============================================================
-- SECTION 2: BOTTLENECK & NETWORK ANALYSIS
-- ============================================================

-- 2.1 Node in-degree: suppliers with most downstream dependencies (bottlenecks)
SELECT s.supplier_id, s.supplier_name, s.continent, s.tier, s.risk_band,
       COUNT(n.edge_id)                      AS times_depended_on,
       COUNT(*) FILTER (WHERE n.is_critical_path='Y') AS critical_path_count,
       ROUND(SUM(n.annual_flow_usd)/1e6,2)   AS total_inflow_usd_m
FROM dim_suppliers s
JOIN fact_supplier_network n ON s.supplier_id = n.target_supplier_id
GROUP BY s.supplier_id, s.supplier_name, s.continent, s.tier, s.risk_band
ORDER BY times_depended_on DESC
LIMIT 20;


-- 2.2 Supplier betweenness proxy: appears as BOTH source and target (hub nodes)
WITH out_flow AS (
    SELECT source_supplier_id AS supplier_id, COUNT(*) AS outgoing, SUM(annual_flow_usd) AS out_usd
    FROM fact_supplier_network GROUP BY source_supplier_id
),
in_flow AS (
    SELECT target_supplier_id AS supplier_id, COUNT(*) AS incoming, SUM(annual_flow_usd) AS in_usd
    FROM fact_supplier_network GROUP BY target_supplier_id
)
SELECT s.supplier_id, s.supplier_name, s.continent, s.tier, s.risk_band,
       COALESCE(o.outgoing,0)                AS outgoing_links,
       COALESCE(i.incoming,0)                AS incoming_links,
       COALESCE(o.outgoing,0)+COALESCE(i.incoming,0) AS total_degree,
       ROUND((COALESCE(o.out_usd,0)+COALESCE(i.in_usd,0))/1e6,2) AS total_flow_usd_m
FROM dim_suppliers s
LEFT JOIN out_flow o ON s.supplier_id = o.supplier_id
LEFT JOIN in_flow  i ON s.supplier_id = i.supplier_id
ORDER BY total_degree DESC
LIMIT 15;


-- 2.3 Sole-source suppliers with high risk band — critical single points of failure
SELECT s.supplier_id, s.supplier_name, s.continent, s.country_name,
       s.tier, s.category, s.risk_band, s.lead_time_days,
       COUNT(po.po_id)                              AS total_orders,
       ROUND(SUM(po.total_value_usd)/1e6,2)         AS spend_usd_m,
       ROUND(AVG(po.defect_rate_pct),2)             AS avg_defect_pct,
       COUNT(d.disruption_id)                       AS past_disruptions,
       'SINGLE POINT OF FAILURE'                    AS risk_label
FROM dim_suppliers s
JOIN fact_purchase_orders po ON s.supplier_id = po.supplier_id
LEFT JOIN fact_disruptions d ON s.supplier_id = d.supplier_id
WHERE s.is_sole_source = 'Y'
  AND s.risk_band IN ('Medium','High')
GROUP BY s.supplier_id, s.supplier_name, s.continent, s.country_name,
         s.tier, s.category, s.risk_band, s.lead_time_days
ORDER BY spend_usd_m DESC;


-- 2.4 Recursive CTE: multi-hop supply chain dependency traversal
WITH RECURSIVE chain AS (
    SELECT source_supplier_id AS root,
           source_supplier_id AS node,
           target_supplier_id AS next_node,
           dependency_type, annual_flow_usd, is_critical_path,
           1 AS hop,
           CAST(source_supplier_id AS VARCHAR(500)) AS path
    FROM fact_supplier_network
    WHERE is_critical_path = 'Y'

    UNION ALL

    SELECT c.root, c.next_node, n.target_supplier_id,
           n.dependency_type, n.annual_flow_usd, n.is_critical_path,
           c.hop + 1,
           c.path || ' -> ' || n.target_supplier_id
    FROM chain c
    JOIN fact_supplier_network n ON c.next_node = n.source_supplier_id
    WHERE c.hop < 4
      AND c.path NOT LIKE '%' || n.target_supplier_id || '%'
)
SELECT root, hop, path, next_node AS end_node, dependency_type,
       ROUND(annual_flow_usd/1e6,2) AS flow_usd_m
FROM chain
ORDER BY root, hop;


-- ============================================================
-- SECTION 3: DISRUPTION RISK ANALYSIS
-- ============================================================

-- 3.1 Financial loss by disruption type and severity
SELECT disruption_type, severity,
       COUNT(*)                               AS event_count,
       ROUND(AVG(duration_days),1)            AS avg_duration_days,
       ROUND(SUM(financial_loss_usd)/1e6,2)  AS total_loss_usd_m,
       ROUND(AVG(financial_loss_usd),0)       AS avg_loss_per_event,
       COUNT(*) FILTER (WHERE is_resolved='N') AS unresolved,
       COUNT(*) FILTER (WHERE alternative_supplier_activated='Y') AS alt_sup_used
FROM fact_disruptions
GROUP BY disruption_type, severity
ORDER BY total_loss_usd_m DESC;


-- 3.2 Suppliers with repeated disruptions (chronic risk)
SELECT s.supplier_id, s.supplier_name, s.continent, s.tier, s.risk_band,
       COUNT(d.disruption_id)               AS total_disruptions,
       COUNT(*) FILTER (WHERE d.severity IN ('High','Critical')) AS critical_events,
       ROUND(SUM(d.financial_loss_usd)/1e6,2) AS total_loss_usd_m,
       ROUND(AVG(d.duration_days),1)         AS avg_disruption_days,
       COUNT(*) FILTER (WHERE d.is_resolved='N') AS open_disruptions,
       MIN(d.start_date)                    AS first_incident,
       MAX(d.start_date)                    AS latest_incident
FROM dim_suppliers s
JOIN fact_disruptions d ON s.supplier_id = d.supplier_id
GROUP BY s.supplier_id, s.supplier_name, s.continent, s.tier, s.risk_band
HAVING COUNT(d.disruption_id) > 2
ORDER BY total_disruptions DESC, total_loss_usd_m DESC;


-- 3.3 Geographic concentration risk — spend and disruptions by continent
SELECT s.continent,
       COUNT(DISTINCT s.supplier_id)        AS supplier_count,
       ROUND(SUM(po.total_value_usd)/1e6,2) AS total_spend_usd_m,
       ROUND(SUM(po.total_value_usd)
             / SUM(SUM(po.total_value_usd)) OVER() * 100, 1) AS spend_share_pct,
       COUNT(d.disruption_id)               AS disruption_events,
       ROUND(SUM(d.financial_loss_usd)/1e6,2) AS disruption_loss_usd_m,
       ROUND(AVG(s.lead_time_days),1)       AS avg_lead_time_days
FROM dim_suppliers s
LEFT JOIN fact_purchase_orders po ON s.supplier_id = po.supplier_id
LEFT JOIN fact_disruptions d ON s.supplier_id = d.supplier_id
GROUP BY s.continent
ORDER BY total_spend_usd_m DESC;


-- 3.4 Disruption heatmap: month × disruption type frequency
SELECT fiscal_month,
       COUNT(*) FILTER (WHERE disruption_type='Natural Disaster')     AS natural_disaster,
       COUNT(*) FILTER (WHERE disruption_type='Port Strike')          AS port_strike,
       COUNT(*) FILTER (WHERE disruption_type='Geopolitical')         AS geopolitical,
       COUNT(*) FILTER (WHERE disruption_type='Logistics Delay')      AS logistics_delay,
       COUNT(*) FILTER (WHERE disruption_type='Raw Material Shortage') AS raw_material,
       COUNT(*) FILTER (WHERE disruption_type='Pandemic')             AS pandemic,
       COUNT(*) FILTER (WHERE disruption_type='Cyber Attack')         AS cyber_attack,
       COUNT(*)                                                        AS total
FROM fact_disruptions
GROUP BY fiscal_month
ORDER BY fiscal_month;


-- ============================================================
-- SECTION 4: INVENTORY & SHORTAGE RISK
-- ============================================================

-- 4.1 Plants at shortage risk by product criticality
SELECT pl.plant_name, pl.continent, pr.product_category, pr.criticality,
       COUNT(*) FILTER (WHERE i.is_shortage_risk='Y') AS shortage_items,
       COUNT(*)                                        AS total_items,
       ROUND(COUNT(*) FILTER (WHERE i.is_shortage_risk='Y')
             * 100.0 / COUNT(*), 1)                   AS shortage_pct,
       ROUND(AVG(i.days_of_stock),1)                  AS avg_days_of_stock,
       MIN(i.days_of_stock)                            AS min_days_of_stock
FROM fact_inventory_buffer i
JOIN dim_plants pl ON i.plant_id = pl.plant_id
JOIN dim_products pr ON i.product_id = pr.product_id
GROUP BY pl.plant_name, pl.continent, pr.product_category, pr.criticality
ORDER BY shortage_pct DESC;


-- 4.2 Below-reorder-point items needing immediate replenishment
SELECT pl.plant_name, pr.product_name, pr.criticality,
       i.current_stock, i.reorder_point, i.safety_stock,
       i.current_stock - i.safety_stock  AS buffer_above_safety,
       i.days_of_stock,
       s.supplier_name, s.lead_time_days,
       CASE
           WHEN i.current_stock < i.safety_stock    THEN 'CRITICAL — below safety stock'
           WHEN i.current_stock < i.reorder_point   THEN 'WARNING — below reorder point'
           ELSE 'OK'
       END AS replenishment_status
FROM fact_inventory_buffer i
JOIN dim_plants pl ON i.plant_id = pl.plant_id
JOIN dim_products pr ON i.product_id = pr.product_id
LEFT JOIN fact_purchase_orders po ON pr.product_id = po.product_id AND po.status='Delivered'
LEFT JOIN dim_suppliers s ON po.supplier_id = s.supplier_id
WHERE i.current_stock < i.reorder_point
ORDER BY pr.criticality, i.days_of_stock ASC;


-- 4.3 Days-of-stock distribution by plant (NTILE quartile segmentation)
SELECT plant_id, product_id, days_of_stock,
       NTILE(4) OVER (PARTITION BY plant_id ORDER BY days_of_stock) AS stock_quartile,
       PERCENT_RANK() OVER (PARTITION BY plant_id ORDER BY days_of_stock) AS pct_rank
FROM fact_inventory_buffer
ORDER BY plant_id, days_of_stock;


-- ============================================================
-- SECTION 5: ADVANCED ANALYTICS
-- ============================================================

-- 5.1 Supplier risk matrix: spend vs composite score (quadrant analysis)
WITH metrics AS (
    SELECT s.supplier_id, s.supplier_name, s.continent, s.tier, s.risk_band,
           ROUND(SUM(po.total_value_usd)/1e6,2)      AS spend_usd_m,
           ROUND(AVG(sc.composite_score),2)           AS avg_score,
           ROUND(AVG(po.defect_rate_pct),2)           AS avg_defect,
           COUNT(d.disruption_id)                     AS disruptions
    FROM dim_suppliers s
    JOIN fact_purchase_orders po ON s.supplier_id = po.supplier_id
    JOIN fact_supplier_scorecard sc ON s.supplier_id = sc.supplier_id
    LEFT JOIN fact_disruptions d ON s.supplier_id = d.supplier_id
    GROUP BY s.supplier_id, s.supplier_name, s.continent, s.tier, s.risk_band
),
thresholds AS (
    SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY spend_usd_m) AS med_spend,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY avg_score)   AS med_score
    FROM metrics
)
SELECT m.*, t.med_spend, t.med_score,
    CASE
        WHEN m.spend_usd_m >= t.med_spend AND m.avg_score >= t.med_score THEN 'Strategic Partner   (High Spend, High Score)'
        WHEN m.spend_usd_m >= t.med_spend AND m.avg_score <  t.med_score THEN 'URGENT FIX          (High Spend, Low Score)'
        WHEN m.spend_usd_m <  t.med_spend AND m.avg_score >= t.med_score THEN 'Develop Further     (Low Spend, High Score)'
        ELSE                                                                   'Monitor / Exit      (Low Spend, Low Score)'
    END AS quadrant
FROM metrics m, thresholds t
ORDER BY quadrant, spend_usd_m DESC;


-- 5.2 Z-score anomaly detection on delivery delays
WITH stats AS (
    SELECT supplier_id,
           AVG(delay_days)    AS mean_delay,
           STDDEV(delay_days) AS std_delay
    FROM fact_purchase_orders
    WHERE status = 'Delayed'
    GROUP BY supplier_id
)
SELECT po.po_id, po.supplier_id, s.supplier_name, s.continent,
       po.order_date, po.delay_days,
       ROUND(st.mean_delay,1)  AS supplier_avg_delay,
       ROUND((po.delay_days - st.mean_delay) / NULLIF(st.std_delay,0), 2) AS z_score,
       po.total_value_usd
FROM fact_purchase_orders po
JOIN stats st ON po.supplier_id = st.supplier_id
JOIN dim_suppliers s ON po.supplier_id = s.supplier_id
WHERE ABS((po.delay_days - st.mean_delay) / NULLIF(st.std_delay,0)) > 2
ORDER BY ABS((po.delay_days - st.mean_delay) / NULLIF(st.std_delay,0)) DESC;


-- 5.3 Rolling 4-quarter average OTD score per supplier
SELECT supplier_id, fiscal_year, quarter, otd_score,
       ROUND(AVG(otd_score) OVER (
           PARTITION BY supplier_id
           ORDER BY fiscal_year, quarter
           ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
       ),2) AS rolling_4q_otd,
       ROUND(otd_score - AVG(otd_score) OVER (
           PARTITION BY supplier_id
           ORDER BY fiscal_year, quarter
           ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
       ),2) AS deviation
FROM fact_supplier_scorecard
ORDER BY supplier_id, fiscal_year, quarter;


-- 5.4 Monte Carlo-style: expected annual loss from disruption probability
WITH disruption_rate AS (
    SELECT s.supplier_id, s.supplier_name, s.continent, s.risk_band,
           COUNT(d.disruption_id)                        AS event_count,
           ROUND(AVG(d.financial_loss_usd),0)            AS avg_loss_per_event,
           ROUND(COUNT(d.disruption_id)/4.0,2)           AS events_per_year,
           ROUND(COUNT(d.disruption_id)/4.0
                 * AVG(d.financial_loss_usd),0)          AS expected_annual_loss
    FROM dim_suppliers s
    LEFT JOIN fact_disruptions d ON s.supplier_id = d.supplier_id
    GROUP BY s.supplier_id, s.supplier_name, s.continent, s.risk_band
)
SELECT *, NTILE(5) OVER (ORDER BY expected_annual_loss DESC) AS loss_quintile
FROM disruption_rate
WHERE event_count > 0
ORDER BY expected_annual_loss DESC;


-- 5.5 Lead time volatility — coefficient of variation per supplier
SELECT s.supplier_id, s.supplier_name, s.continent, s.tier,
       s.lead_time_days                          AS contracted_lead_time,
       ROUND(AVG(po.delay_days),1)               AS avg_actual_delay,
       ROUND(STDDEV(po.delay_days),1)            AS delay_stddev,
       ROUND(STDDEV(po.delay_days)
             / NULLIF(AVG(po.delay_days),0)*100, 1) AS delay_cv_pct,
       ROUND(AVG(s.lead_time_days + po.delay_days),1) AS effective_lead_time,
       COUNT(po.po_id)                           AS sample_orders
FROM dim_suppliers s
JOIN fact_purchase_orders po ON s.supplier_id = po.supplier_id
WHERE po.delay_days > 0
GROUP BY s.supplier_id, s.supplier_name, s.continent, s.tier, s.lead_time_days
HAVING COUNT(po.po_id) >= 5
ORDER BY delay_cv_pct DESC;


-- ============================================================
-- END OF QUERY FILE
-- ============================================================
