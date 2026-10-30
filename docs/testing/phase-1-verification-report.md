# Phase 1 Database Verification Report

**Execution Date**: 2026-10-29 (Sri Lanka Standard Time, `UTC+05:30`)  
**Target Engine**: PostgreSQL `18.6` on Docker (`postgres:18-alpine`, container `sl_grid_warehouse_db`, mapped to `127.0.0.1:5433`)  
**Git Branch**: `feature/phase-1-warehouse-database` (branched from `development`)  
**Verification Scripts**: [verify_database.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/verify_database.py), [phase1_sql_assertions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/tests/phase1_sql_assertions.sql), and `pytest` (`33` automated tests)

---

## 1. TDD Red → Green Execution Log & Issue Resolutions

All Phase 0 and Phase 1 deliverables were developed under strict **Red → Green → Refactor** discipline:

1. **Red Baseline 1 (Phase 0 Foundation Contracts)**:
   - Initial `pytest` execution failed during collection (`7 errors: ModuleNotFoundError` for `src.common.config`, `src.common.db`, `src.ingestion.*`, `src.preprocessing.*`, `src.validation.*`, `scripts.migrate`).
   - Initial PostgreSQL 18 container startup failed when mounting `/var/lib/postgresql/data` due to PostgreSQL 18's `pg_ctlcluster` volume layout (`18/docker`). Fixed in [docker-compose.yml](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docker-compose.yml) by mounting `postgres_data:/var/lib/postgresql`.
   - First Green run on `test_migrations.py` caught a transaction-nesting bug (`AssertionError: assert '001_bootstrap' in []` because `autocommit=False` wrapped `with conn.transaction():` in a savepoint that rolled back on connection close). Fixed in [migrate.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/migrate.py) by opening runner connections with `autocommit=True` so each migration commits atomically at top level (`19 passed`).
2. **Red Baseline 2 (Phase 1 Warehouse Specifications)**:
   - Authored 5 new test modules ([test_seed_definitions.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/unit/test_seed_definitions.py), [test_phase1_schema_and_constraints.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_schema_and_constraints.py), [test_phase1_seeding.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_seeding.py), [test_phase1_advanced_objects.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_advanced_objects.py), [test_phase1_etl_transactions.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_etl_transactions.py)) and confirmed Red failures prior to migrations `002`–`017`.
   - Implemented migrations `002`–`017`, [seed_reference.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/seed_reference.py), and [batch_loader.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/etl/batch_loader.py). First Green pass achieved `31 passed, 2 failed`:
     - *Failure 1*: Synthetic invalid unit string `'FAKE_JOULES_PER_FORTNIGHT'` (25 chars) hit `VARCHAR(24)` truncation before `ForeignKeyViolation`. Shortened test fixture token to `'FAKE_UNIT_XYZ'` (13 chars) so the FK constraint itself is directly exercised.
     - *Failure 2*: Fixture cleanup in `test_procedures_views_mvs_reconciliation_and_no_double_counting` deleted `audit.etl_run` by `etl_run_id` rather than `source_document_id`. Updated cleanup `DELETE` to filter by `source_document_id`.
   - Re-ran full suite: **`33 passed, 0 failed`**.

---

## 2. Clean-Database Migration & Idempotent Seeding Verification

Executed via `.\.venv\Scripts\python.exe scripts/verify_database.py` (exit code `0`):

- **PostgreSQL Engine**: `18.6`
- **Clean Database Migration Apply (`001`–`017`)**: `17` migrations applied cleanly from empty schema state.
- **Immediate Re-Run Idempotency**: `0` pending migrations applied; all 17 SHA-256 checksums verified in `public.schema_migrations`.
- **Dual-Pass Reference Seeding (`seed_counts_pass_2_identical: true`)**:

| Schema.Table | Pass 1 Rows | Pass 2 Rows | Verification Status |
|---|---:|---:|---|
| `raw.source_system` | 3 | 3 | Identical (`CEB`, `PUCSL`, `NASA_POWER`) |
| `ref.unit` | 17 | 17 | Identical |
| `ref.unit_conversion` | 9 | 9 | Identical |
| `ref.reporting_period_type` | 6 | 6 | Identical |
| `ref.energy_source_mapping` | 5 | 5 | Identical (`VERIFIED` with evidence) |
| `ref.plant_alias` | 5 | 5 | Identical (`VERIFIED` with evidence) |
| `ref.region_alias` | 3 | 3 | Identical (`VERIFIED` with evidence) |
| `ref.metric_mapping` | 7 | 7 | Identical |
| `ref.data_quality_rule` | 13 | 13 | All 13 DQ classifications covered |
| `ref.source_precedence` | 7 | 7 | Identical |
| `dw.dim_date` | 2,922 | 2,922 | `2019-01-01` through `2026-12-31` |
| `dw.dim_interval` | 120 | 120 | `96` x 15-min + `24` x 60-min SLST TOU slots |
| `dw.dim_source_system` | 3 | 3 | Identical |
| `dw.dim_energy_source` | 9 | 9 | Identical |
| `dw.dim_region` | 14 | 14 | `LK` + 9 ISO provinces + 4 CEB divisions |
| `dw.dim_consumption_sector` | 9 | 9 | Identical |
| `dw.dim_power_plant` | 32 | 32 | Verified stations + reported aggregate categories |
| `dw.dim_weather_location` | 6 | 6 | Verified Sri Lanka energy zones |
| `dw.dim_metric` | 14 | 14 | Canonical metrics & additivity rules |
| `dw.fact_dispatch_interval` | **0** | **0** | **Zero fabricated measurements** |
| `dw.fact_generation_period` | **0** | **0** | **Zero fabricated measurements** |
| `dw.fact_capacity_period` | **0** | **0** | **Zero fabricated measurements** |
| `dw.fact_electricity_sales` | **0** | **0** | **Zero fabricated measurements** |
| `dw.fact_weather_daily` | **0** | **0** | **Zero fabricated measurements** |
| `dw.fact_published_metric` | **0** | **0** | **Zero fabricated measurements** |

---

## 3. Exact PostgreSQL Catalog Inventory (`sl_grid_warehouse`)

Verified across the 7 warehouse schemas (`raw`, `staging`, `ref`, `dw`, `mart`, `audit`, `etl`) plus `public.schema_migrations`:

- **Total Warehouse Relations**: **`53`**
  - `38` regular base tables (`4` in `raw`, `9` in `ref`, `4` in `audit`, `9` dimensions + `5` non-partitioned facts in `dw`, `6` in `staging`, `1` in `etl`) + `public.schema_migrations` = `39` regular tables (`40` including partitioned parent)
  - `1` range-partitioned parent fact table (`dw.fact_dispatch_interval`)
  - `5` child range partitions (`fact_dispatch_interval_y2023`, `_y2024`, `_y2025`, `_y2026`, `_default`)
  - `6` analytical & audit views (`audit.data_quality_summary`, `audit.vw_data_quality_summary`, `mart.vw_generation_by_energy_source`, `mart.vw_historical_generation_trends`, `mart.vw_electricity_sales_summary`, `mart.vw_conflicting_source_metrics`)
  - `3` materialized views (`mart.mv_monthly_generation_summary`, `mart.mv_annual_energy_mix`, `mart.mv_monthly_sales_summary`)
- **Total `etl` Routines**: **`16`** (`9` functions + `7` stored procedures)
- **Total User Triggers**: **`13`** (`9` `updated_at` triggers, `3` alias/mapping evidence triggers, `1` DQ resolution trigger)
- **Total Indexes**: **`134`** (including B-Tree PK/FK/grain indexes, partial unique SCD2 index, `UNIQUE NULLS NOT DISTINCT` index, concurrent MV refresh unique indexes, and BRIN indexes on append-heavy/time-series tables)

---

## 4. Actual Automated Test Suite & Static Analysis Output

### `.\.venv\Scripts\pytest.exe -v --cov=src --cov=scripts`
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-8.4.2, pluggy-1.7.0
collected 33 items

tests/data_quality/test_quality_gates.py::test_quality_gate_quarantine_evaluation PASSED [  3%]
tests/integration/test_db_connection.py::test_db_connection_failure_handling PASSED [  6%]
tests/integration/test_db_connection.py::test_db_connection_success PASSED [  9%]
tests/integration/test_db_connection.py::test_db_version_check PASSED    [ 12%]
tests/integration/test_migrations.py::test_migration_runner_discovery PASSED [ 15%]
tests/integration/test_migrations.py::test_migration_application_and_idempotency PASSED [ 18%]
tests/integration/test_phase1_advanced_objects.py::test_plpgsql_functions_contracts PASSED [ 21%]
tests/integration/test_phase1_advanced_objects.py::test_triggers_guard_alias_evidence_and_dq_resolution PASSED [ 24%]
tests/integration/test_phase1_advanced_objects.py::test_procedures_views_mvs_reconciliation_and_no_double_counting PASSED [ 27%]
tests/integration/test_phase1_advanced_objects.py::test_least_privilege_database_roles PASSED [ 30%]
tests/integration/test_phase1_etl_transactions.py::test_transactional_batch_commit_idempotency_and_rollback PASSED [ 33%]
tests/integration/test_phase1_schema_and_constraints.py::test_migration_sequence_001_to_017 PASSED [ 36%]
tests/integration/test_phase1_schema_and_constraints.py::test_all_seven_schemas_and_core_tables_exist PASSED [ 39%]
tests/integration/test_phase1_schema_and_constraints.py::test_negative_and_impossible_measurements_rejected PASSED [ 42%]
tests/integration/test_phase1_schema_and_constraints.py::test_missing_weather_sentinel_preserved_as_null_and_duplicate_prevented PASSED [ 45%]
tests/integration/test_phase1_schema_and_constraints.py::test_dispatch_partition_pruning_via_explain PASSED [ 48%]
tests/integration/test_phase1_seeding.py::test_reference_seeding_idempotency_and_zero_fabricated_facts PASSED [ 51%]
tests/unit/test_config.py::test_database_config_defaults PASSED          [ 54%]
tests/unit/test_config.py::test_database_config_masks_password PASSED    [ 57%]
tests/unit/test_config.py::test_app_config_paths PASSED                  [ 60%]
tests/unit/test_manifest.py::test_manifest_validation_success PASSED     [ 63%]
tests/unit/test_manifest.py::test_manifest_validation_rejects_missing_fields PASSED [ 66%]
tests/unit/test_manifest.py::test_official_manifest_validity PASSED      [ 69%]
tests/unit/test_parsers.py::test_load_csv_parser PASSED                  [ 72%]
tests/unit/test_parsers.py::test_load_dispatch_15min_json PASSED         [ 75%]
tests/unit/test_preprocessing.py::test_missing_values_detection_and_null_preservation PASSED [ 78%]
tests/unit/test_preprocessing.py::test_duplicate_record_detection PASSED [ 81%]
tests/unit/test_preprocessing.py::test_physical_outlier_detection PASSED [ 84%]
tests/unit/test_preprocessing.py::test_canonical_station_name_standardization PASSED [ 87%]
tests/unit/test_preprocessing.py::test_timestamp_parsing_with_colombo_timezone PASSED [ 90%]
tests/unit/test_seed_definitions.py::test_calendar_date_generation_bounds PASSED [ 93%]
tests/unit/test_seed_definitions.py::test_time_interval_generation_96_slots_and_tou_blocks PASSED [ 96%]
tests/unit/test_seed_definitions.py::test_reference_definitions_completeness_and_sri_lanka_bounds PASSED [100%]

============================= 33 passed in 6.72s ==============================
```

### Static Linting & Strict Type Checking
- `.\.venv\Scripts\ruff.exe check src scripts tests` → **`All checks passed!`**
- `.\.venv\Scripts\mypy.exe src scripts` → **`Success: no issues found in 18 source files`**

---

## 5. Representative `EXPLAIN (ANALYZE, BUFFERS)` Execution Plans

Captured inside a rolled-back benchmark transaction (`2,880` synthetic 15-minute Victoria Hydro dispatch observations in `sl_grid_warehouse_test`; `0` rows persisted after `conn.rollback()`):

### Query 1: Partition-Pruned 15-Minute TOU Dispatch Aggregation (`2024-01-01` to `2024-01-15`)
```text
GroupAggregate  (cost=20.14..20.18 rows=1 width=77) (actual time=1.519..1.634 rows=3.00 loops=1)
  Group Key: di.tariff_time_block
  Buffers: shared hit=925
  InitPlan 1
    ->  Index Scan using uq_dim_power_plant_current on dim_power_plant  (cost=0.14..8.16 rows=1 width=4) (actual time=0.010..0.011 rows=1.00 loops=1)
          Index Cond: ((plant_code)::text = 'VICTORIA'::text)
          Index Searches: 1
          Buffers: shared hit=2
  ->  Sort  (cost=11.98..11.99 rows=1 width=37) (actual time=1.378..1.431 rows=1440.00 loops=1)
        Sort Key: di.tariff_time_block
        Sort Method: quicksort  Memory: 99kB
        Buffers: shared hit=925
        ->  Hash Join  (cost=8.31..11.97 rows=1 width=37) (actual time=0.979..1.098 rows=1440.00 loops=1)
              Hash Cond: (di.interval_key = fd.interval_key)
              Buffers: shared hit=922
              ->  Seq Scan on dim_interval di  (cost=0.00..3.20 rows=120 width=9) (actual time=0.008..0.016 rows=120.00 loops=1)
                    Buffers: shared hit=2
              ->  Hash  (cost=8.30..8.30 rows=1 width=36) (actual time=0.960..0.960 rows=1440.00 loops=1)
                    Buckets: 2048 (originally 1024)  Batches: 1 (originally 1)  Memory Usage: 84kB
                    Buffers: shared hit=920
                    ->  Index Scan using fact_dispatch_interval_y2024_plant_key_date_key_idx on fact_dispatch_interval_y2024 fd  (cost=0.28..8.30 rows=1 width=36) (actual time=0.029..0.741 rows=1440.00 loops=1)
                          Index Cond: ((plant_key = (InitPlan 1).col1) AND (date_key >= 20240101) AND (date_key <= 20240115))
                          Filter: is_current_revision
                          Index Searches: 1
                          Buffers: shared hit=920
Planning Time: 2.541 ms
Execution Time: 1.770 ms
```
**Observed Behavior**: PostgreSQL 18 pruned `fact_dispatch_interval_y2023`, `_y2025`, `_y2026`, and `_default` completely, performing a single `Index Scan` (`Index Searches: 1`) on `fact_dispatch_interval_y2024` in **`1.770 ms`**.

---

## 6. Phase 1 Acceptance Criteria Sign-Off

| # | Acceptance Criterion | Status | Verification Evidence |
|---|---|---|---|
| 1 | PostgreSQL starts successfully | **MET** | `sl_grid_warehouse_db` (`PostgreSQL 18.6`) running and `Healthy` via Docker Compose. |
| 2 | All schema migrations execute on a clean database | **MET** | `001`–`017` applied from empty state (`migrations_applied_clean_db: 17`, re-run: `0`). |
| 3 | All intended tables and relationships exist | **MET** | `53` warehouse relations (`40` tables, `5` partitions, `6` views, `3` MVs) + PK/FK/UK/CHECK verified. |
| 4 | Reference seeding executes correctly | **MET** | [seed_reference.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/seed_reference.py) populates all 10 reference & conformed dimension groups. |
| 5 | Seeding is idempotent | **MET** | Dual-pass seed check confirmed identical counts (`seed_counts_pass_2_identical: true`). |
| 6 | Advanced database objects have working tests | **MET** | Functions, procedures, triggers, views, concurrent MVs, partitions, and roles tested in [test_phase1_advanced_objects.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_advanced_objects.py). |
| 7 | Transaction rollback has been verified | **MET** | [test_phase1_etl_transactions.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_etl_transactions.py) verifies `0` partial fact rows on failure while preserving `ROLLED_BACK` audit row. |
| 8 | Data-quality auditing works | **MET** | All 13 DQ classifications, 4 lifecycle statuses, and resolution trigger verified. |
| 9 | Source provenance is preserved | **MET** | Every staging and fact table enforces FKs to `raw.source_document`, `raw.extracted_record`, and `audit.etl_run`. |
| 10 | Database roles are correctly restricted | **MET** | `grid_analyst` blocked from `INSERT`/`UPDATE`/`DELETE` on `dw.fact_*` and blocked from `raw`/`staging`. |
| 11 | Relevant SQL integration tests pass | **MET** | `33 passed in 6.72s` + [phase1_sql_assertions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/tests/phase1_sql_assertions.sql) passed. |
| 12 | No source measurements are fabricated | **MET** | All 6 `dw.fact_*` tables contain **`0` rows** in `sl_grid_warehouse`; `manifest.json` honestly marks files `catalogued_pending_download`. |
| 13 | All database diagrams and data dictionaries are complete | **MET** | `40` tables / `514` columns documented in [data-dictionary.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/database/data-dictionary.md) + ERDs in [erd-fact-constellation.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/database/erd-fact-constellation.md). |
| 14 | Real-source loading path is defined and ready for Phase 2 | **MET** | End-to-end `raw` → `staging` → `etl.sp_validate_*` → `etl.sp_load_*` / [batch_loader.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/etl/batch_loader.py) → `dw` → `mart` path verified. |

