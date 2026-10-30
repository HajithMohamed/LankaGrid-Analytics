# Database Role & Least-Privilege Access Matrix

Implemented in [016_roles_and_privileges.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/016_roles_and_privileges.sql) and credential-bound from environment variables via `MigrationRunner.configure_role_passwords_from_env()` in [migrate.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/migrate.py). **Zero passwords or secrets exist in SQL files or Git.**

---

## 1. Role Definitions

| Role | Intended Consumer | Login Credential Env Vars | Capabilities Summary |
|---|---|---|---|
| `grid_admin` | Migration runner (`scripts/migrate.py`) & DBA maintenance | `POSTGRES_USER`, `POSTGRES_PASSWORD` | Full schema DDL ownership, migration application, role administration. |
| `grid_etl` | Automated ingestion, staging, validation, and fact loading jobs | `POSTGRES_ETL_USER`, `POSTGRES_ETL_PASSWORD` | `SELECT/INSERT/UPDATE` on `raw`, `staging`, `audit`, `dw.fact_*`, and alias mapping tables in `ref`; `EXECUTE` on `etl.*`. **Explicitly denied `DELETE`, `TRUNCATE`, and `DROP` on warehouse facts and raw provenance.** |
| `grid_analyst` | BI queries, academic 24-query analytical workloads, QA readers | `POSTGRES_ANALYST_USER`, `POSTGRES_ANALYST_PASSWORD` | **Strictly read-only (`SELECT` only)** on `dw.*`, `mart.*`, `ref.*`, `audit.data_quality_summary`, and `audit.reconciliation_case`. Zero write access across the entire database. |

---

## 2. Schema-by-Schema Privilege Matrix

| Schema / Object Group | `grid_admin` | `grid_etl` | `grid_analyst` |
|---|---|---|---|
| `raw.*` (Provenance Registry) | `ALL` (Owner) | `SELECT, INSERT, UPDATE` | *None* |
| `staging.stg_*` | `ALL` (Owner) | `SELECT, INSERT, UPDATE` | *None* |
| `ref.*` (Controlled Definitions) | `ALL` (Owner) | `SELECT` (`+ INSERT, UPDATE` on alias/mapping tables) | `SELECT` |
| `dw.dim_*` (Conformed Dimensions) | `ALL` (Owner) | `SELECT` | `SELECT` |
| `dw.fact_*` (Warehouse Facts & Partitions) | `ALL` (Owner) | `SELECT, INSERT, UPDATE` *(No `DELETE`/`TRUNCATE`)* | `SELECT` |
| `mart.vw_*` & `mart.mv_*` | `ALL` (Owner) | `SELECT` | `SELECT` |
| `audit.etl_run` / `data_quality_issue` / `record_lineage` | `ALL` (Owner) | `SELECT, INSERT, UPDATE` | *None* |
| `audit.data_quality_summary` & `reconciliation_case` | `ALL` (Owner) | `SELECT, INSERT, UPDATE` | `SELECT` |
| `etl.fn_*` & `etl.sp_*` | `ALL` (Owner) | `EXECUTE` | *None* |

---

## 3. Verification Evidence
Verified by `test_least_privilege_database_roles` in [test_phase1_advanced_objects.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_advanced_objects.py):
- `grid_analyst` succeeds on `SELECT` from `dw.dim_energy_source`, `mart.vw_generation_by_energy_source`, and `mart.mv_monthly_generation_summary`, and raises `psycopg.errors.InsufficientPrivilege` on `DELETE FROM dw.dim_energy_source` and `DELETE FROM dw.fact_generation_period`.
- `grid_etl` raises `psycopg.errors.InsufficientPrivilege` when attempting `DROP TABLE dw.fact_capacity_period`.

