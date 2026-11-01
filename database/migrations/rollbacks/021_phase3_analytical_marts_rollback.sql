-- ==============================================================================
-- Rollback: 021_phase3_analytical_marts_rollback.sql
-- Description: Teardown Phase 3 Materialized Views and Refresh Procedure
-- Applied By: Antigravity Rollback Handler
-- ==============================================================================

DROP PROCEDURE IF EXISTS mart.sp_refresh_analytical_marts();
DROP MATERIALIZED VIEW IF EXISTS mart.mv_monthly_weather_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mart.mv_daily_dispatch_by_source CASCADE;

