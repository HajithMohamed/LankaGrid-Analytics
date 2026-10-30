-- =============================================================================
-- Migration: 001_bootstrap.sql
-- Purpose  : Initialize migration tracking metadata and create the seven
--            segregated schemas for the Sri Lanka Electricity Grid Warehouse.
-- Target   : PostgreSQL 18
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version VARCHAR(255) CONSTRAINT pk_schema_migrations PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64) NOT NULL,
    execution_ms INTEGER
);

COMMENT ON TABLE public.schema_migrations IS
    'Audit ledger of sequentially applied forward SQL migrations and their SHA-256 checksums.';

-- Segregated Warehouse Schemas
CREATE SCHEMA IF NOT EXISTS raw;
COMMENT ON SCHEMA raw IS
    'Immutable source system registry, source file provenance metadata (URL, SHA-256, period), ingestion batches, and raw extracted record envelopes.';

CREATE SCHEMA IF NOT EXISTS staging;
COMMENT ON SCHEMA staging IS
    'Typed pre-warehouse landing tables preserving source lineage, original values, parsed values, and row validation states without silent drops.';

CREATE SCHEMA IF NOT EXISTS ref;
COMMENT ON SCHEMA ref IS
    'Controlled reference definitions: measurement units, unit conversions, reporting periods, verified entity/alias mappings, data-quality rules, and source precedence.';

CREATE SCHEMA IF NOT EXISTS dw;
COMMENT ON SCHEMA dw IS
    'Centralized Kimball Fact Constellation analytical warehouse: conformed dimensions (dim_*) and atomic/periodic fact tables (fact_*).';

CREATE SCHEMA IF NOT EXISTS mart;
COMMENT ON SCHEMA mart IS
    'Reusable analytical views (vw_*) and pre-aggregated materialized views (mv_*) enforcing grain-safe, non-double-counted reporting.';

CREATE SCHEMA IF NOT EXISTS audit;
COMMENT ON SCHEMA audit IS
    'ETL batch execution logs, row-level data-quality issue tracking, cross-source reconciliation cases, record lineage, and quality monitoring views.';

CREATE SCHEMA IF NOT EXISTS etl;
COMMENT ON SCHEMA etl IS
    'Database-side SQL and PL/pgSQL helper functions (fn_*), transactional ETL stored procedures (sp_*), trigger functions, and scheduler metadata.';
