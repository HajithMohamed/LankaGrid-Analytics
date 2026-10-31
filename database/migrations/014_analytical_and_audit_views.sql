-- =============================================================================
-- Migration: 014_analytical_and_audit_views.sql
-- Purpose  : Create reusable analytical and governance views in audit and mart.
--            Strictly separates reporting granularities, boundaries, and
--            current revisions to prevent double counting.
-- Rollback : DROP VIEW IF EXISTS mart.vw_conflicting_source_metrics,
--            mart.vw_electricity_sales_summary,
--            mart.vw_historical_generation_trends,
--            mart.vw_generation_by_energy_source,
--            audit.data_quality_summary,
--            audit.vw_data_quality_summary CASCADE;
-- =============================================================================

-- 1. Data Quality Monitoring Summary Views
CREATE OR REPLACE VIEW audit.vw_data_quality_summary AS
SELECT
    dqi.etl_run_id,
    er.pipeline_name,
    dqi.staging_table_name,
    dqi.rule_code,
    dqr.rule_name,
    dqi.issue_classification,
    dqi.severity,
    dqi.issue_status,
    COUNT(*)::BIGINT AS issue_count,
    MIN(dqi.detected_at) AS first_detected_at,
    MAX(dqi.detected_at) AS last_detected_at
FROM audit.data_quality_issue dqi
JOIN ref.data_quality_rule dqr
  ON dqr.rule_code = dqi.rule_code
LEFT JOIN audit.etl_run er
  ON er.etl_run_id = dqi.etl_run_id
GROUP BY
    dqi.etl_run_id,
    er.pipeline_name,
    dqi.staging_table_name,
    dqi.rule_code,
    dqr.rule_name,
    dqi.issue_classification,
    dqi.severity,
    dqi.issue_status;

CREATE OR REPLACE VIEW audit.data_quality_summary AS
SELECT
    etl_run_id,
    pipeline_name,
    staging_table_name,
    rule_code,
    rule_name,
    issue_classification,
    severity,
    issue_status,
    issue_count,
    first_detected_at,
    last_detected_at
FROM audit.vw_data_quality_summary;

COMMENT ON VIEW audit.data_quality_summary IS
    'Aggregated data quality monitoring view grouped by ETL run, rule, issue classification, severity, and resolution status.';

-- 2. Generation by Energy Source View (Grain-Safe: Separates DAILY / MONTHLY / ANNUAL & GROSS / NET)
CREATE OR REPLACE VIEW mart.vw_generation_by_energy_source AS
SELECT
    d_start.calendar_year,
    d_start.quarter_number,
    d_start.month_number,
    d_start.year_month,
    fg.period_type_code,
    fg.generation_boundary,
    es.energy_source_code,
    es.energy_category,
    es.fuel_type,
    es.is_renewable,
    ss.source_code,
    COUNT(fg.generation_fact_id)::BIGINT AS record_count,
    SUM(fg.generation_mwh) AS total_generation_mwh,
    MAX(fg.peak_generation_mw) AS max_station_peak_mw
FROM dw.fact_generation_period fg
JOIN dw.dim_date d_start
  ON d_start.date_key = fg.period_start_date_key
JOIN dw.dim_energy_source es
  ON es.energy_source_key = fg.energy_source_key
JOIN dw.dim_source_system ss
  ON ss.source_system_key = fg.source_system_key
WHERE fg.is_current_revision = TRUE
GROUP BY
    d_start.calendar_year,
    d_start.quarter_number,
    d_start.month_number,
    d_start.year_month,
    fg.period_type_code,
    fg.generation_boundary,
    es.energy_source_code,
    es.energy_category,
    es.fuel_type,
    es.is_renewable,
    ss.source_code;

COMMENT ON VIEW mart.vw_generation_by_energy_source IS
    'Grain-safe generation summary over current revisions; keeps period_type_code, generation_boundary, and source_code explicit to prevent double counting.';

-- 3. Historical Annual Generation Trends with YoY Change
CREATE OR REPLACE VIEW mart.vw_historical_generation_trends AS
WITH annual_totals AS (
    SELECT
        d_start.calendar_year,
        fg.period_type_code,
        fg.generation_boundary,
        es.energy_source_code,
        es.energy_category,
        es.is_renewable,
        ss.source_code,
        SUM(fg.generation_mwh) AS generation_mwh
    FROM dw.fact_generation_period fg
    JOIN dw.dim_date d_start
      ON d_start.date_key = fg.period_start_date_key
    JOIN dw.dim_energy_source es
      ON es.energy_source_key = fg.energy_source_key
    JOIN dw.dim_source_system ss
      ON ss.source_system_key = fg.source_system_key
    WHERE fg.is_current_revision = TRUE
      AND fg.period_type_code = 'ANNUAL'
    GROUP BY
        d_start.calendar_year,
        fg.period_type_code,
        fg.generation_boundary,
        es.energy_source_code,
        es.energy_category,
        es.is_renewable,
        ss.source_code
)
SELECT
    at.calendar_year,
    at.period_type_code,
    at.generation_boundary,
    at.energy_source_code,
    at.energy_category,
    at.is_renewable,
    at.source_code,
    at.generation_mwh,
    LAG(at.generation_mwh) OVER (
        PARTITION BY at.period_type_code, at.generation_boundary, at.energy_source_code, at.source_code
        ORDER BY at.calendar_year
    ) AS prior_year_generation_mwh,
    etl.fn_calculate_yoy_change(
        at.generation_mwh,
        LAG(at.generation_mwh) OVER (
            PARTITION BY at.period_type_code, at.generation_boundary, at.energy_source_code, at.source_code
            ORDER BY at.calendar_year
        )
    ) AS yoy_change_pct
FROM annual_totals at;

COMMENT ON VIEW mart.vw_historical_generation_trends IS
    'Annual electricity generation trends and YoY percentage growth within matching energy source, boundary, and provider.';

-- 4. Electricity Sales Summary View
CREATE OR REPLACE VIEW mart.vw_electricity_sales_summary AS
SELECT
    d_start.calendar_year,
    d_start.quarter_number,
    d_start.month_number,
    d_start.year_month,
    fs.period_type_code,
    r.region_code,
    r.region_name,
    r.region_level,
    cs.sector_code,
    cs.sector_name,
    cs.tariff_group,
    ss.source_code,
    SUM(fs.energy_sold_mwh) AS total_energy_sold_mwh,
    MAX(fs.consumer_account_count) AS reported_consumer_accounts,
    SUM(fs.revenue_lkr) AS total_revenue_lkr
FROM dw.fact_electricity_sales fs
JOIN dw.dim_date d_start
  ON d_start.date_key = fs.period_start_date_key
JOIN dw.dim_region r
  ON r.region_key = fs.region_key
JOIN dw.dim_consumption_sector cs
  ON cs.sector_key = fs.sector_key
JOIN dw.dim_source_system ss
  ON ss.source_system_key = fs.source_system_key
WHERE fs.is_current_revision = TRUE
GROUP BY
    d_start.calendar_year,
    d_start.quarter_number,
    d_start.month_number,
    d_start.year_month,
    fs.period_type_code,
    r.region_code,
    r.region_name,
    r.region_level,
    cs.sector_code,
    cs.sector_name,
    cs.tariff_group,
    ss.source_code;

COMMENT ON VIEW mart.vw_electricity_sales_summary IS
    'Electricity sales summary keeping period_type_code and region_level explicit; consumer_account_count is semi-additive (not summed across time).';

-- 5. Conflicting Source Metrics & Reconciliation View
CREATE OR REPLACE VIEW mart.vw_conflicting_source_metrics AS
SELECT
    rc.reconciliation_id,
    rc.etl_run_id,
    rc.metric_code,
    dm.metric_name,
    dm.generation_boundary,
    rc.period_type_code,
    rc.period_start_date,
    rc.period_end_date,
    rc.entity_scope_code,
    rc.unit_code,
    rc.primary_source_code,
    rc.primary_value,
    rc.secondary_source_code,
    rc.secondary_value,
    rc.absolute_variance,
    rc.pct_variance,
    rc.reconciliation_status,
    rc.authoritative_source_chosen,
    rc.resolution_notes,
    rc.created_at
FROM audit.reconciliation_case rc
LEFT JOIN dw.dim_metric dm
  ON dm.metric_code = rc.metric_code;

COMMENT ON VIEW mart.vw_conflicting_source_metrics IS
    'Surfaces cross-source variance cases (e.g. CEB Statistical Digest vs PUCSL operational reports) along with authoritative source precedence.';
