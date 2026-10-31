-- =============================================================================
-- Migration Rollback: 018_real_data_etl_procedures_rollback.sql
-- Purpose  : Tear down procedures added in migration 018.
-- =============================================================================

DROP PROCEDURE IF EXISTS etl.sp_load_electricity_sales(BIGINT, BIGINT, INTEGER, INTEGER);
DROP PROCEDURE IF EXISTS etl.sp_validate_staged_sales(BIGINT, BIGINT, INTEGER, INTEGER);
DROP PROCEDURE IF EXISTS etl.sp_load_weather_daily(BIGINT, BIGINT, INTEGER, INTEGER);
DROP PROCEDURE IF EXISTS etl.sp_validate_staged_weather(BIGINT, BIGINT, INTEGER, INTEGER);
DROP PROCEDURE IF EXISTS etl.sp_load_dispatch_interval(BIGINT, BIGINT, INTEGER, INTEGER);
DROP PROCEDURE IF EXISTS etl.sp_validate_staged_dispatch(BIGINT, BIGINT, INTEGER, INTEGER);
