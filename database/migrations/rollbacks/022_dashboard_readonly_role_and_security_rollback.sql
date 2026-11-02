-- ==============================================================================
-- Rollback: 022_dashboard_readonly_role_and_security_rollback.sql
-- Description: Teardown Phase 5.1 dashboard read-only privileges and settings
-- Applied By: Antigravity Rollback Handler
-- ==============================================================================

ALTER ROLE grid_analyst RESET default_transaction_read_only;
ALTER ROLE grid_analyst RESET statement_timeout;
ALTER ROLE grid_analyst RESET lock_timeout;
ALTER ROLE grid_analyst RESET idle_in_transaction_session_timeout;

REVOKE SELECT ON ALL TABLES IN SCHEMA audit FROM grid_analyst;
REVOKE SELECT ON ALL TABLES IN SCHEMA ref FROM grid_analyst;
REVOKE SELECT ON ALL TABLES IN SCHEMA mart FROM grid_analyst;
REVOKE SELECT ON ALL TABLES IN SCHEMA dw FROM grid_analyst;

REVOKE USAGE ON SCHEMA dw, mart, ref, audit FROM grid_analyst;
