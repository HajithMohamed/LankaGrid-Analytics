-- =============================================================================
-- Rollback Script: rollback_all_phase1.sql
-- Purpose        : Cleanly tear down Phase 1 warehouse objects in reverse
--                  dependency order for clean-room migration testing.
-- WARNING        : Never run on production data without full backup.
-- =============================================================================

DROP SCHEMA IF EXISTS mart CASCADE;
DROP SCHEMA IF EXISTS etl CASCADE;
DROP SCHEMA IF EXISTS staging CASCADE;
DROP SCHEMA IF EXISTS dw CASCADE;
DROP SCHEMA IF EXISTS audit CASCADE;
DROP SCHEMA IF EXISTS ref CASCADE;
DROP SCHEMA IF EXISTS raw CASCADE;
DROP TABLE IF EXISTS public.schema_migrations CASCADE;
