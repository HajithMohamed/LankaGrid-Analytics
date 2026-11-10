-- ==============================================================================
-- Rollback: 023_phase6_warehouse_freshness_and_maintenance_rollback.sql
-- Purpose : Revert Phase 6.2 maintenance procedures and provenance grants.
-- ==============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grid_analyst') THEN
        REVOKE SELECT ON raw.source_system, raw.source_document, raw.ingestion_batch FROM grid_analyst;
        REVOKE USAGE ON SCHEMA raw FROM grid_analyst;
    END IF;
END;
$$;

DROP PROCEDURE IF EXISTS etl.sp_ensure_calendar_and_partitions(INTEGER, INTEGER);
DROP PROCEDURE IF EXISTS mart.sp_refresh_analytical_marts(BOOLEAN);

CREATE OR REPLACE PROCEDURE mart.sp_refresh_analytical_marts()
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mart.mv_daily_dispatch_by_source;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mart.mv_monthly_weather_summary;
END;
$$;

