-- ==============================================================================
-- Migration: 023_phase6_warehouse_freshness_and_maintenance.sql
-- Description: Phase 6.2 Scheduled Refresh Reliability, Calendar & Partition
--              Auto-Extension, Safe Materialized Mart Refresh, and Read-Only
--              Provenance Metadata Access:
--              1. Update mart.sp_refresh_analytical_marts(p_concurrent BOOLEAN DEFAULT FALSE)
--                 so procedural CALL mart.sp_refresh_analytical_marts() succeeds
--                 reliably without CONCURRENTLY transaction-block errors.
--              2. Create etl.sp_ensure_calendar_and_partitions(p_start_year, p_end_year)
--                 to idempotently extend dw.dim_date and yearly partitions on
--                 dw.fact_dispatch_interval through 2030.
--              3. Grant read-only SELECT on raw.source_system, raw.source_document,
--                 and raw.ingestion_batch to grid_analyst for freshness monitoring.
-- Target Engine: PostgreSQL 18 / Supabase Managed PostgreSQL
-- Rollback: database/migrations/rollbacks/023_phase6_warehouse_freshness_and_maintenance_rollback.sql
-- ==============================================================================

-- 1. Update mart.sp_refresh_analytical_marts to support non-concurrent procedural invocation
DROP PROCEDURE IF EXISTS mart.sp_refresh_analytical_marts();

CREATE OR REPLACE PROCEDURE mart.sp_refresh_analytical_marts(
    IN p_concurrent BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_concurrent THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mart.mv_daily_dispatch_by_source;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mart.mv_monthly_weather_summary;
    ELSE
        REFRESH MATERIALIZED VIEW mart.mv_daily_dispatch_by_source;
        REFRESH MATERIALIZED VIEW mart.mv_monthly_weather_summary;
    END IF;
END;
$$;

COMMENT ON PROCEDURE mart.sp_refresh_analytical_marts(BOOLEAN) IS
    'Refreshes Phase 3 analytical materialized views (mv_daily_dispatch_by_source, mv_monthly_weather_summary). Defaults to non-concurrent refresh for safe invocation inside stored procedure and ETL transaction boundaries.';


-- 2. Idempotent Calendar & Partition Extension Procedure
CREATE OR REPLACE PROCEDURE etl.sp_ensure_calendar_and_partitions(
    IN p_start_year INTEGER DEFAULT 2019,
    IN p_end_year INTEGER DEFAULT 2030
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_year INTEGER;
    v_part_name TEXT;
    v_from_key INTEGER;
    v_to_key INTEGER;
BEGIN
    IF p_start_year > p_end_year THEN
        RAISE EXCEPTION 'p_start_year (%) cannot be greater than p_end_year (%)', p_start_year, p_end_year;
    END IF;

    -- 2a. Extend dw.dim_date idempotently across [p_start_year .. p_end_year]
    INSERT INTO dw.dim_date (
        date_key,
        calendar_date,
        day_of_month,
        day_of_year,
        day_of_week_iso,
        day_name,
        is_weekend,
        week_of_year_iso,
        month_number,
        month_name,
        year_month,
        quarter_number,
        quarter_name,
        calendar_year,
        sl_monsoon_season
    )
    SELECT
        (EXTRACT(YEAR FROM d)::INTEGER * 10000)
            + (EXTRACT(MONTH FROM d)::INTEGER * 100)
            + EXTRACT(DAY FROM d)::INTEGER AS date_key,
        d::DATE AS calendar_date,
        EXTRACT(DAY FROM d)::SMALLINT AS day_of_month,
        EXTRACT(DOY FROM d)::SMALLINT AS day_of_year,
        EXTRACT(ISODOW FROM d)::SMALLINT AS day_of_week_iso,
        TO_CHAR(d, 'FMDay') AS day_name,
        (EXTRACT(ISODOW FROM d) IN (6, 7)) AS is_weekend,
        EXTRACT(WEEK FROM d)::SMALLINT AS week_of_year_iso,
        EXTRACT(MONTH FROM d)::SMALLINT AS month_number,
        TO_CHAR(d, 'FMMonth') AS month_name,
        TO_CHAR(d, 'YYYY-MM') AS year_month,
        EXTRACT(QUARTER FROM d)::SMALLINT AS quarter_number,
        'Q' || EXTRACT(QUARTER FROM d)::TEXT AS quarter_name,
        EXTRACT(YEAR FROM d)::SMALLINT AS calendar_year,
        CASE
            WHEN EXTRACT(MONTH FROM d) IN (12, 1, 2) THEN 'NORTHEAST_MONSOON'
            WHEN EXTRACT(MONTH FROM d) IN (3, 4) THEN 'FIRST_INTER_MONSOON'
            WHEN EXTRACT(MONTH FROM d) IN (5, 6, 7, 8, 9) THEN 'SOUTHWEST_MONSOON'
            ELSE 'SECOND_INTER_MONSOON'
        END AS sl_monsoon_season
    FROM generate_series(
        MAKE_DATE(p_start_year, 1, 1)::TIMESTAMP,
        MAKE_DATE(p_end_year, 12, 31)::TIMESTAMP,
        INTERVAL '1 day'
    ) AS gs(d)
    ON CONFLICT (date_key) DO NOTHING;

    -- 2b. Ensure yearly partitions exist on dw.fact_dispatch_interval
    FOR v_year IN p_start_year..p_end_year LOOP
        v_part_name := format('fact_dispatch_interval_y%s', v_year);
        v_from_key := v_year * 10000 + 101;
        v_to_key := (v_year + 1) * 10000 + 101;

        IF to_regclass('dw.' || v_part_name) IS NULL THEN
            BEGIN
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS dw.%I PARTITION OF dw.fact_dispatch_interval FOR VALUES FROM (%s) TO (%s);',
                    v_part_name,
                    v_from_key,
                    v_to_key
                );
            EXCEPTION
                WHEN duplicate_table OR invalid_object_definition THEN
                    -- If default partition already holds rows or partition was created concurrently,
                    -- rows remain safely routable via dw.fact_dispatch_interval_default.
                    NULL;
            END;
        END IF;
    END LOOP;
END;
$$;

COMMENT ON PROCEDURE etl.sp_ensure_calendar_and_partitions(INTEGER, INTEGER) IS
    'Idempotently populates dw.dim_date and creates yearly dw.fact_dispatch_interval partitions for the requested year range.';

-- Execute calendar and partition extension through 2030
CALL etl.sp_ensure_calendar_and_partitions(2019, 2030);


-- 3. Grant least-privilege read-only provenance access for dashboard freshness monitoring
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grid_analyst') THEN
        GRANT USAGE ON SCHEMA raw TO grid_analyst;
        GRANT SELECT ON raw.source_system, raw.source_document, raw.ingestion_batch TO grid_analyst;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grid_etl') THEN
        GRANT EXECUTE ON PROCEDURE mart.sp_refresh_analytical_marts(BOOLEAN) TO grid_etl;
        GRANT EXECUTE ON PROCEDURE etl.sp_ensure_calendar_and_partitions(INTEGER, INTEGER) TO grid_etl;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grid_admin') THEN
        GRANT EXECUTE ON PROCEDURE mart.sp_refresh_analytical_marts(BOOLEAN) TO grid_admin;
        GRANT EXECUTE ON PROCEDURE etl.sp_ensure_calendar_and_partitions(INTEGER, INTEGER) TO grid_admin;
    END IF;
END;
$$;

