# Test Strategy & TDD Verification Protocol

## 1. Governance & Test-Driven Development (TDD) Lifecycle

All warehouse schema migrations, PL/pgSQL database routines, ETL batch loaders, and Python validation modules follow strict **Red → Green → Refactor** governance ([testing.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.agents/rules/testing.md)):

1. **Red (Failing Specification First)**: Author deterministic unit, integration, or SQL assertion tests specifying the exact contract (constraint violation, function edge case, transaction rollback, role restriction, or idempotency invariant) and confirm failure before writing implementation code.
2. **Green (Minimal Correct Implementation)**: Implement the numbered SQL migration (`database/migrations/001`–`017`) or Python module (`src/`, `scripts/`) required to satisfy the specification.
3. **Refactor & Static Verification**: Enforce clean modular boundaries, strict static typing (`mypy src scripts`), and zero lint defects (`ruff check src scripts tests`) while keeping 100% of tests green.

---

## 2. Database Isolation & Zero-Fabrication Safeguards

| Database / Layer | Target Instance | Purpose & Data Hygiene Rule |
|---|---|---|
| **Primary Warehouse DB** | `sl_grid_warehouse` | Receives sequential migrations (`001`–`017`) and verified static reference seeds ([seed_reference.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/seed_reference.py)). **All 6 `dw.fact_*` tables remain at `0` rows** until authentic CEB, PUCSL, and NASA POWER files are downloaded in Phase 2. |
| **Isolated QA Test DB** | `sl_grid_warehouse_test` | Initialized automatically by [init-db.sh](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/init-db.sh) and session fixture `migrated_test_db` in [conftest.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/conftest.py). Synthetic records carry `acquisition_status = 'SYNTHETIC_FIXTURE'` and are rolled back or deleted in `finally` blocks. |

---

## 3. Four-Layer Test Architecture

### Layer 1: Offline Unit Tests (`tests/unit/`)
Zero network or PostgreSQL dependencies; sub-second execution:
- [test_config.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/unit/test_config.py): Environment configuration parsing and credential masking in `DatabaseConfig` ([config.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/common/config.py)).
- [test_manifest.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/unit/test_manifest.py): Provenance manifest schema validation and `catalogued_pending_download` vs `verified` SHA-256 enforcement ([manifest_validator.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/ingestion/manifest_validator.py)).
- [test_parsers.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/unit/test_parsers.py): CSV and 15-minute JSON fixture parsing ([parsers.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/ingestion/parsers.py)).
- [test_preprocessing.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/unit/test_preprocessing.py): Lecture 6 missing-value `NULL` preservation (never `0`), exact/fuzzy duplicate detection, physical nameplate outlier detection, canonical plant standardization, and `Asia/Colombo` (`UTC+05:30`) timestamp normalization ([cleaning.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/preprocessing/cleaning.py)).
- [test_seed_definitions.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/unit/test_seed_definitions.py): Validates deterministic 2019–2026 calendar generation, 96 x 15-minute + 24 hourly TOU interval slots, Sri Lanka bounding-box coordinates (`5.8°N–10.0°N`, `79.4°E–82.0°E`), and all 13 DQ classifications.

### Layer 2: Data Quality Gate Tests (`tests/data_quality/`)
- [test_quality_gates.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/data_quality/test_quality_gates.py): Verifies quarantine routing of negative generation, missing timestamps, and over-capacity outliers while passing valid observations ([quality_gates.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/validation/quality_gates.py)).

### Layer 3: Live PostgreSQL 18 Integration Tests (`tests/integration/`)
Executed against `sl_grid_warehouse_test` running on Docker (`postgres:18-alpine`):
- [test_db_connection.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_db_connection.py) & [test_migrations.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_migrations.py): Connection pooling, PostgreSQL 18 server verification, migration ordering, SHA-256 drift detection, and idempotency.
- [test_phase1_schema_and_constraints.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_schema_and_constraints.py): Verifies all 7 schemas, PK/FK/UNIQUE/CHECK rejection of negative MW/MWh, invalid units, daily period date mismatches, dependable > installed capacity, NASA `-999` missing-sentinel `NULL` enforcement, and `EXPLAIN` partition pruning on `dw.fact_dispatch_interval`.
- [test_phase1_seeding.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_seeding.py): Executes [seed_reference.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/seed_reference.py) twice back-to-back, asserting identical row counts and `0` rows across all 6 `dw.fact_*` tables.
- [test_phase1_advanced_objects.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_advanced_objects.py): Tests PL/pgSQL functions (`fn_convert_unit`, `fn_validate_reporting_period`, `fn_normalize_interval_15min`, `fn_calculate_yoy_change`), triggers (`trg_validate_plant_alias_evidence`, `trg_audit_dq_issue_resolution`), stored procedures, concurrent materialized view refresh (`sp_refresh_mart_views(TRUE)`), cross-source reconciliation (`sp_record_reconciliation_case`), no double-counting across revisions or published summaries, and `SET ROLE grid_analyst` read-only enforcement.
- [test_phase1_etl_transactions.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_etl_transactions.py): Tests [batch_loader.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/etl/batch_loader.py) atomic commit, idempotent batch re-execution, full fact rollback on failure (`0` partial rows), and survival of `ROLLED_BACK` audit evidence in `audit.etl_run`.

### Layer 4: SQL Catalog & End-to-End Verification Runner
- [phase1_sql_assertions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/tests/phase1_sql_assertions.sql) & [verify_database.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/verify_database.py): Clean-room teardown + migration apply (`001`–`017`), dual-pass seed check, catalog object count assertions, privilege matrix audit, and `EXPLAIN (ANALYZE, BUFFERS)` execution plans.

---

## 4. Test Execution Commands

```powershell
# Run full unit, data-quality, and PostgreSQL 18 integration test suite with coverage
.\.venv\Scripts\pytest.exe -v --cov=src --cov=scripts

# Run clean-room database verification, SQL assertions, and EXPLAIN (ANALYZE, BUFFERS)
.\.venv\Scripts\python.exe scripts/verify_database.py

# Run static linting and strict type verification
.\.venv\Scripts\ruff.exe check src scripts tests
.\.venv\Scripts\mypy.exe src scripts
```

