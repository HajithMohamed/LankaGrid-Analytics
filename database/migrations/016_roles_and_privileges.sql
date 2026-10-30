-- =============================================================================
-- Migration: 016_roles_and_privileges.sql
-- Purpose  : Implement least-privilege database roles:
--            - grid_admin   : Schema owner and migration administrator
--            - grid_etl     : Controlled ETL loader (no DDL, no DELETE/TRUNCATE on facts)
--            - grid_analyst : Strictly read-only analytical consumer
--            Zero passwords are stored in SQL; login passwords are set via env.
-- Rollback : REVOKE privileges granted to grid_etl and grid_analyst.
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grid_admin') THEN
        CREATE ROLE grid_admin NOLOGIN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grid_etl') THEN
        CREATE ROLE grid_etl LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grid_analyst') THEN
        CREATE ROLE grid_analyst LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    END IF;
END;
$$;

-- Revoke broad public create privileges
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- ============================================================================
-- Role 1: grid_etl (Controlled Ingestion, Staging, Audit, and Fact UPSERTs)
-- ============================================================================
GRANT USAGE ON SCHEMA raw, staging, ref, dw, mart, audit, etl TO grid_etl;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA raw TO grid_etl;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA staging TO grid_etl;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA audit TO grid_etl;
GRANT SELECT ON ALL TABLES IN SCHEMA ref TO grid_etl;
GRANT SELECT, INSERT, UPDATE ON ref.plant_alias, ref.energy_source_mapping, ref.region_alias TO grid_etl;

-- Warehouse: grid_etl may SELECT dimensions and INSERT/UPDATE facts (for ON CONFLICT UPSERT & revision flags),
--            but is explicitly denied DELETE and TRUNCATE on dw.* and raw.*!
GRANT SELECT ON ALL TABLES IN SCHEMA dw TO grid_etl;
GRANT INSERT, UPDATE ON
    dw.fact_dispatch_interval,
    dw.fact_dispatch_interval_y2023,
    dw.fact_dispatch_interval_y2024,
    dw.fact_dispatch_interval_y2025,
    dw.fact_dispatch_interval_y2026,
    dw.fact_dispatch_interval_default,
    dw.fact_generation_period,
    dw.fact_capacity_period,
    dw.fact_electricity_sales,
    dw.fact_weather_daily,
    dw.fact_published_metric
TO grid_etl;

GRANT SELECT ON ALL TABLES IN SCHEMA mart TO grid_etl;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA raw, staging, ref, dw, audit TO grid_etl;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA etl TO grid_etl;
GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA etl TO grid_etl;

-- ============================================================================
-- Role 2: grid_analyst (Strictly Read-Only Analytics & Quality Monitoring)
-- ============================================================================
GRANT USAGE ON SCHEMA ref, dw, mart, audit TO grid_analyst;

GRANT SELECT ON ALL TABLES IN SCHEMA ref TO grid_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA dw TO grid_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO grid_analyst;
GRANT SELECT ON audit.vw_data_quality_summary, audit.data_quality_summary, audit.reconciliation_case TO grid_analyst;

-- Default privileges for future views/tables in analytical schemas
ALTER DEFAULT PRIVILEGES IN SCHEMA dw GRANT SELECT ON TABLES TO grid_analyst;
ALTER DEFAULT PRIVILEGES IN SCHEMA mart GRANT SELECT ON TABLES TO grid_analyst;
