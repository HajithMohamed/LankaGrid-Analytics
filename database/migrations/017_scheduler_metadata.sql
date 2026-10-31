-- =============================================================================
-- Migration: 017_scheduler_metadata.sql
-- Purpose  : Create optional scheduler job registry and pg_cron detection
--            helper supporting external schedulers or pg_cron without MySQL
--            CREATE EVENT syntax.
-- Rollback : DROP FUNCTION IF EXISTS etl.fn_detect_pg_cron_available CASCADE;
--            DROP TABLE IF EXISTS etl.scheduled_job_registry CASCADE;
-- =============================================================================

CREATE TABLE etl.scheduled_job_registry (
    job_code VARCHAR(64)
        CONSTRAINT pk_etl_scheduled_job_registry PRIMARY KEY,
    job_name VARCHAR(128) NOT NULL,
    cron_schedule VARCHAR(64) NOT NULL,
    sql_command TEXT NOT NULL,
    execution_mechanism VARCHAR(32) NOT NULL DEFAULT 'EXTERNAL_OR_PG_CRON'
        CONSTRAINT ck_etl_sched_mechanism
        CHECK (execution_mechanism IN ('EXTERNAL_OR_PG_CRON', 'MANUAL_ONLY', 'PG_CRON')),
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    last_manual_or_scheduled_run TIMESTAMPTZ,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE etl.scheduled_job_registry IS
    'Declarative catalogue of recurring maintenance jobs (e.g. concurrent MV refresh) kept optional in Phase 1.';

INSERT INTO etl.scheduled_job_registry (
    job_code,
    job_name,
    cron_schedule,
    sql_command,
    execution_mechanism,
    is_enabled,
    description
) VALUES (
    'REFRESH_MART_MVS_DAILY',
    'Daily Concurrent Refresh of Mart Materialized Views',
    '30 2 * * *',
    'CALL etl.sp_refresh_mart_views(TRUE);',
    'EXTERNAL_OR_PG_CRON',
    FALSE,
    'Refreshes mart.mv_monthly_generation_summary, mart.mv_annual_energy_mix, and mart.mv_monthly_sales_summary after daily ETL completion.'
)
ON CONFLICT (job_code) DO NOTHING;

CREATE OR REPLACE FUNCTION etl.fn_detect_pg_cron_available()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM pg_available_extensions
        WHERE name = 'pg_cron'
    );
$$;

COMMENT ON FUNCTION etl.fn_detect_pg_cron_available() IS
    'Checks whether the optional pg_cron extension is installed on the host PostgreSQL 18 image.';
