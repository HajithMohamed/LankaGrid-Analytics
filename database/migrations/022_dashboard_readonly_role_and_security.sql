-- ==============================================================================
-- Migration: 022_dashboard_readonly_role_and_security.sql
-- Description: Implement dedicated least-privilege read-only security hardening
--              for the GridLens Next.js Analytics Dashboard:
--              1. Ensure role 'grid_analyst' exists with restricted LOGIN privileges.
--              2. Apply session safeguards: default_transaction_read_only,
--                 statement_timeout = 5000ms, lock_timeout = 2000ms.
--              3. Grant strictly read-only SELECT permissions on dw, mart, ref,
--                 and audit schemas.
--              4. Explicitly deny and revoke all DDL and write (INSERT, UPDATE,
--                 DELETE, TRUNCATE, DROP, ALTER) operations.
-- Applied By: Antigravity Phase 5.1 Security Hardening
-- Target Engine: PostgreSQL 18
-- Rollback: database/migrations/rollbacks/022_dashboard_readonly_role_and_security_rollback.sql
-- ==============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grid_analyst') THEN
        CREATE ROLE grid_analyst LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    END IF;
END;
$$;

-- Configure strict execution constraints on the role
ALTER ROLE grid_analyst SET default_transaction_read_only = on;
ALTER ROLE grid_analyst SET statement_timeout = '5000'; -- 5-second maximum execution timeout
ALTER ROLE grid_analyst SET lock_timeout = '2000';       -- 2-second maximum lock wait
ALTER ROLE grid_analyst SET idle_in_transaction_session_timeout = '10000'; -- 10-second idle abort

-- Revoke all modifications on schemas
REVOKE ALL ON SCHEMA raw, staging, etl FROM grid_analyst;
REVOKE CREATE ON SCHEMA dw, mart, ref, audit, public FROM grid_analyst;

-- Grant schema navigation
GRANT USAGE ON SCHEMA dw, mart, ref, audit TO grid_analyst;

-- Grant SELECT-only on warehouse tables, analytical marts, reference catalogs, and audit logs
GRANT SELECT ON ALL TABLES IN SCHEMA dw TO grid_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO grid_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA ref TO grid_analyst;
GRANT SELECT ON ALL TABLES IN SCHEMA audit TO grid_analyst;

-- Ensure future tables/views in analytical schemas inherit SELECT-only privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA dw GRANT SELECT ON TABLES TO grid_analyst;
ALTER DEFAULT PRIVILEGES IN SCHEMA mart GRANT SELECT ON TABLES TO grid_analyst;
ALTER DEFAULT PRIVILEGES IN SCHEMA ref GRANT SELECT ON TABLES TO grid_analyst;
ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT SELECT ON TABLES TO grid_analyst;
