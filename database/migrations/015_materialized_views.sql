-- =============================================================================
-- Migration: 015_materialized_views.sql
-- Purpose  : Create pre-aggregated materialized views in mart with unique
--            indexes supporting REFRESH MATERIALIZED VIEW CONCURRENTLY.
-- Rollback : DROP MATERIALIZED VIEW IF EXISTS mart.mv_monthly_sales_summary,
--            mart.mv_annual_energy_mix,
--            mart.mv_monthly_generation_summary CASCADE;
-- =============================================================================

-- 1. Monthly Generation Summary Materialized View
CREATE MATERIALIZED VIEW mart.mv_monthly_generation_summary AS
SELECT
    d_start.calendar_year,
    d_start.month_number,
    d_start.year_month,
    fg.period_type_code,
    fg.generation_boundary,
    es.energy_source_code,
    es.energy_category,
    es.is_renewable,
    ss.source_code,
    COUNT(fg.generation_fact_id)::BIGINT AS observation_count,
    SUM(fg.generation_mwh) AS total_generation_mwh,
    MAX(fg.peak_generation_mw) AS peak_generation_mw
FROM dw.fact_generation_period fg
JOIN dw.dim_date d_start
  ON d_start.date_key = fg.period_start_date_key
JOIN dw.dim_energy_source es
  ON es.energy_source_key = fg.energy_source_key
JOIN dw.dim_source_system ss
  ON ss.source_system_key = fg.source_system_key
WHERE fg.is_current_revision = TRUE
  AND fg.period_type_code IN ('DAILY', 'MONTHLY')
GROUP BY
    d_start.calendar_year,
    d_start.month_number,
    d_start.year_month,
    fg.period_type_code,
    fg.generation_boundary,
    es.energy_source_code,
    es.energy_category,
    es.is_renewable,
    ss.source_code
WITH DATA;

CREATE UNIQUE INDEX uq_mv_monthly_generation_summary
    ON mart.mv_monthly_generation_summary (
        calendar_year,
        month_number,
        period_type_code,
        generation_boundary,
        energy_source_code,
        source_code
    );

-- 2. Annual Energy Mix Materialized View
CREATE MATERIALIZED VIEW mart.mv_annual_energy_mix AS
WITH grouped AS (
    SELECT
        d_start.calendar_year,
        fg.period_type_code,
        fg.generation_boundary,
        es.energy_source_code,
        es.energy_category,
        es.is_renewable,
        ss.source_code,
        SUM(fg.generation_mwh) AS source_generation_mwh
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
        fg.period_type_code,
        fg.generation_boundary,
        es.energy_source_code,
        es.energy_category,
        es.is_renewable,
        ss.source_code
)
SELECT
    g.calendar_year,
    g.period_type_code,
    g.generation_boundary,
    g.energy_source_code,
    g.energy_category,
    g.is_renewable,
    g.source_code,
    g.source_generation_mwh,
    SUM(g.source_generation_mwh) OVER (
        PARTITION BY g.calendar_year, g.period_type_code, g.generation_boundary, g.source_code
    ) AS total_system_generation_mwh,
    CASE
        WHEN SUM(g.source_generation_mwh) OVER (
            PARTITION BY g.calendar_year, g.period_type_code, g.generation_boundary, g.source_code
        ) > 0
        THEN ROUND(
            (g.source_generation_mwh / SUM(g.source_generation_mwh) OVER (
                PARTITION BY g.calendar_year, g.period_type_code, g.generation_boundary, g.source_code
            )) * 100.0,
            4
        )
        ELSE NULL
    END AS share_of_generation_pct
FROM grouped g
WITH DATA;

CREATE UNIQUE INDEX uq_mv_annual_energy_mix
    ON mart.mv_annual_energy_mix (
        calendar_year,
        period_type_code,
        generation_boundary,
        energy_source_code,
        source_code
    );

-- 3. Monthly Electricity Sales Summary Materialized View
CREATE MATERIALIZED VIEW mart.mv_monthly_sales_summary AS
SELECT
    d_start.calendar_year,
    d_start.month_number,
    d_start.year_month,
    fs.period_type_code,
    r.region_code,
    cs.sector_code,
    cs.tariff_group,
    ss.source_code,
    SUM(fs.energy_sold_mwh) AS total_energy_sold_mwh,
    MAX(fs.consumer_account_count) AS consumer_account_count,
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
    d_start.month_number,
    d_start.year_month,
    fs.period_type_code,
    r.region_code,
    cs.sector_code,
    cs.tariff_group,
    ss.source_code
WITH DATA;

CREATE UNIQUE INDEX uq_mv_monthly_sales_summary
    ON mart.mv_monthly_sales_summary (
        calendar_year,
        month_number,
        period_type_code,
        region_code,
        sector_code,
        source_code
    );
