-- ==============================================================================
-- Migration: 021_phase3_analytical_marts.sql
-- Description: Phase 3 Analytical Data Marts & Performance Materialized Views:
--              1. mart.mv_daily_dispatch_by_source (Aggregated sub-daily dispatch by technology)
--              2. mart.mv_monthly_weather_summary (Aggregated 5-year monthly weather indicators)
--              3. Unique indexes for REFRESH MATERIALIZED VIEW CONCURRENTLY
--              4. Stored procedure mart.sp_refresh_analytical_marts()
-- Applied By: Antigravity Phase 3 Architecture Closeout
-- Target Engine: PostgreSQL 18
-- Rollback: database/migrations/rollbacks/021_phase3_analytical_marts_rollback.sql
-- ==============================================================================

-- 1. Materialized View: Daily Dispatch by Energy Source
DROP MATERIALIZED VIEW IF EXISTS mart.mv_daily_dispatch_by_source CASCADE;

CREATE MATERIALIZED VIEW mart.mv_daily_dispatch_by_source AS
SELECT
    fdi.date_key,
    dd.calendar_date,
    dd.day_name,
    dd.is_weekend,
    fdi.energy_source_key,
    des.energy_source_code,
    des.energy_category,
    des.fuel_type,
    des.is_renewable,
    COUNT(fdi.dispatch_fact_id) AS interval_reading_count,
    ROUND(SUM(fdi.derived_energy_mwh), 2) AS daily_generation_mwh,
    ROUND(MAX(fdi.active_power_mw), 2) AS peak_dispatched_mw,
    ROUND(AVG(fdi.active_power_mw), 2) AS mean_dispatched_mw,
    CURRENT_TIMESTAMP AS refreshed_at
FROM dw.fact_dispatch_interval fdi
JOIN dw.dim_energy_source des ON fdi.energy_source_key = des.energy_source_key
JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
GROUP BY 
    fdi.date_key,
    dd.calendar_date,
    dd.day_name,
    dd.is_weekend,
    fdi.energy_source_key,
    des.energy_source_code,
    des.energy_category,
    des.fuel_type,
    des.is_renewable;

-- Unique index required for REFRESH MATERIALIZED VIEW CONCURRENTLY
CREATE UNIQUE INDEX idx_mv_daily_dispatch_grain 
ON mart.mv_daily_dispatch_by_source (date_key, energy_source_key);

CREATE INDEX idx_mv_daily_dispatch_date 
ON mart.mv_daily_dispatch_by_source (calendar_date);


-- 2. Materialized View: Monthly Weather Summary
DROP MATERIALIZED VIEW IF EXISTS mart.mv_monthly_weather_summary CASCADE;

CREATE MATERIALIZED VIEW mart.mv_monthly_weather_summary AS
SELECT
    dd.calendar_year,
    dd.month_number,
    dd.month_name,
    dd.sl_monsoon_season,
    fwd.weather_location_key,
    dwl.location_code,
    dwl.location_name,
    COUNT(DISTINCT dd.calendar_date) AS observed_days,
    -- Temperature Metrics
    ROUND(AVG(CASE WHEN dm.metric_code = 'AIR_TEMP_2M_C' THEN fwd.standardized_value END), 2) AS avg_temp_c,
    ROUND(MIN(CASE WHEN dm.metric_code = 'AIR_TEMP_2M_C' THEN fwd.standardized_value END), 2) AS min_temp_c,
    ROUND(MAX(CASE WHEN dm.metric_code = 'AIR_TEMP_2M_C' THEN fwd.standardized_value END), 2) AS max_temp_c,
    -- Precipitation Metrics
    ROUND(SUM(CASE WHEN dm.metric_code = 'PRECIPITATION_DAILY_MM' THEN fwd.standardized_value ELSE 0 END), 1) AS total_precipitation_mm,
    ROUND(MAX(CASE WHEN dm.metric_code = 'PRECIPITATION_DAILY_MM' THEN fwd.standardized_value ELSE 0 END), 2) AS max_single_day_rain_mm,
    -- Solar Irradiance Metrics
    ROUND(AVG(CASE WHEN dm.metric_code = 'SOLAR_IRRADIANCE_SW_DWN' THEN fwd.standardized_value END), 2) AS avg_solar_irradiance_mj_m2,
    ROUND(AVG(CASE WHEN dm.metric_code = 'SOLAR_IRRADIANCE_SW_DWN' THEN fwd.standardized_value END) / 3.6, 2) AS avg_peak_sun_hours_psh,
    -- Wind Speed Metrics
    ROUND(AVG(CASE WHEN dm.metric_code = 'WIND_SPEED_50M_MS' THEN fwd.standardized_value END), 2) AS avg_wind_speed_50m_ms,
    CURRENT_TIMESTAMP AS refreshed_at
FROM dw.fact_weather_daily fwd
JOIN dw.dim_weather_location dwl ON fwd.weather_location_key = dwl.weather_location_key
JOIN dw.dim_metric dm ON fwd.metric_key = dm.metric_key
JOIN dw.dim_date dd ON fwd.date_key = dd.date_key
WHERE fwd.is_missing = FALSE
GROUP BY 
    dd.calendar_year,
    dd.month_number,
    dd.month_name,
    dd.sl_monsoon_season,
    fwd.weather_location_key,
    dwl.location_code,
    dwl.location_name;

-- Unique index required for REFRESH MATERIALIZED VIEW CONCURRENTLY
CREATE UNIQUE INDEX idx_mv_monthly_weather_grain 
ON mart.mv_monthly_weather_summary (calendar_year, month_number, weather_location_key);


-- 3. Stored Procedure: Refresh Analytical Marts
CREATE OR REPLACE PROCEDURE mart.sp_refresh_analytical_marts()
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mart.mv_daily_dispatch_by_source;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mart.mv_monthly_weather_summary;
END;
$$;

-- Grant analytical access
GRANT SELECT ON mart.mv_daily_dispatch_by_source TO grid_analyst, grid_etl, grid_admin;
GRANT SELECT ON mart.mv_monthly_weather_summary TO grid_analyst, grid_etl, grid_admin;

