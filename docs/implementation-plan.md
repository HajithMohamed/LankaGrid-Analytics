# Phase 1 Implementation Plan — PostgreSQL Data Warehouse Design, Advanced Objects, Reference Seeding & Verification

## 1. Pre-Implementation Audit & Baseline Findings

### 1.1 Git & Repository Audit
- **Baseline Commit**: `b26282e` (`chore(foundation): initialize repository structure, quality gates, and docker environment`), present identically on `main`, `development`, and `chore/phase-0-foundation`.
- **Feature Branch**: `feature/phase-1-warehouse-database` branched cleanly from `development`.
- **Phase 0 Deliverable State**:
  - Phase 0 established governance rules (`.agents/rules/`, `.agents/skills/`), `docker-compose.yml` (`postgres:18-alpine`), `pyproject.toml`, source inventory (`docs/data_sources/source-inventory.md`), and Red-phase TDD test suites (`tests/unit/`, `tests/integration/`, `tests/data_quality/`).
  - Phase 0 left implementation modules (`src/common/`, `src/ingestion/`, `src/preprocessing/`, `src/validation/`, `scripts/migrate.py`, `database/migrations/001_bootstrap.sql`) to be completed under TDD.
  - **Raw Source Data Audit**: `data/raw/` currently contains `.gitkeep` and a structural `manifest.json` cataloguing CEB, PUCSL, and NASA POWER sources; **no actual PDF, XLSX, CSV, or JSON files from CEB, PUCSL, or NASA POWER have been downloaded into `data/raw/` yet**. Accordingly, production fact tables (`dw.fact_*`) MUST remain empty (`0` rows) in production seeding, and synthetic fixtures in `tests/fixtures/` are used strictly inside isolated integration/verification test runs with explicit cleanup or rollback.
  - **Host Environment Note**: Host port `5432` is occupied by an existing local Windows PostgreSQL service. Local `.env` uses `POSTGRES_PORT=5433` mapped to container port `5432` (`sl_grid_warehouse_db`, PostgreSQL 18) without modifying host services.

---

## 2. Multi-Schema Warehouse Architecture

The warehouse implements a **centralized analytical data warehouse using a Kimball Fact Constellation schema** across seven purpose-segregated PostgreSQL schemas (plus `public.schema_migrations` for migration tracking compatibility with Phase 0 tests):

| Schema | Architectural Responsibility | Allowed Objects |
|---|---|---|
| `raw` | Immutable provenance registry: source systems, downloaded source documents/files (URL, SHA-256, timestamps, reporting period), ingestion batches, and raw extracted record payloads. | Registry & lineage tables |
| `staging` | Typed, source-traceable landing tables prior to approval/warehouse load. Preserves raw text alongside parsed values and validation status; never silently drops malformed rows. | `stg_*` tables |
| `ref` | Controlled reference definitions: units, unit conversions, reporting period types, energy/plant/region/metric source mappings with verification status, data-quality rules, and source precedence rules. | Reference & mapping tables |
| `dw` | Conformed analytical dimensions (`dim_*`) and atomic/periodic fact tables (`fact_*`) enforcing strict grain, unit normalization, and referential integrity. | `dim_*`, `fact_*` tables & partitions |
| `mart` | Reusable analytical views (`vw_*`) and pre-aggregated materialized views (`mv_*`) exposing verified, non-double-counted metrics to analysts. | Views & materialized views |
| `audit` | ETL execution logs, row-level data-quality issues (13 issue classes, 4 lifecycle statuses), cross-source reconciliation cases, record lineage, and monitoring views. | Audit tables & summary views |
| `etl` | Database-side SQL and PL/pgSQL helper functions (`fn_*`) and transactional stored procedures (`sp_*`) for validation, reference promotion, fact loading, reconciliation, and MV refresh. | Functions & stored procedures |

---

## 3. Fact Constellation Dimensional Model Overview

### 3.1 Conformed Dimensions (`dw.dim_*`)
1. `dw.dim_date` — Calendar dates (`2019-01-01` to `2026-12-31`), ISO week/weekday, quarter, and Sri Lanka meteorological monsoon seasons.
2. `dw.dim_interval` — Sub-daily time intervals (`96` 15-minute slots `00:00`–`23:45` plus `24` hourly slots) classified into official Sri Lanka Time-of-Use tariff blocks (`DAY`, `PEAK`, `OFF_PEAK`).
3. `dw.dim_source_system` — Authoritative providers (`CEB`, `PUCSL`, `NASA_POWER`) with default timezone and authority scope.
4. `dw.dim_energy_source` — Verified Sri Lanka generation categories and fuel types (`Major Hydro`, `Mini Hydro`, `Thermal Coal`, `Thermal Oil`, `Solar`, `Wind`, `Biomass`, etc.) with `is_renewable` and `is_dispatchable` flags.
5. `dw.dim_region` — Verified ISO-3166-2:LK national (`LK`) and 9 provincial codes (`LK-1` to `LK-9`) plus official CEB Distribution Divisions (`DD1`–`DD4`) via parent-child hierarchy.
6. `dw.dim_consumption_sector` — Official CEB/PUCSL tariff and sales sectors (`Domestic`, `Industrial`, `General Purpose`, `Hotel`, `Government`, `Religious`, `Street Lighting`, `Bulk/LECO`).
7. `dw.dim_power_plant` — SCD Type 2 station/complex/category dimension (`plant_key`, `plant_code`, `entity_level`, `effective_from`, `effective_to`, `is_current`) with verified Sri Lankan power complexes/plants and aggregate reporting buckets.
8. `dw.dim_weather_location` — Verified meteorological grid sampling points aligned to Sri Lankan hydro catchments, wind corridors, solar hubs, thermal hubs, and load centers.
9. `dw.dim_metric` — Canonical measurement dictionary distinguishing Generation vs Demand vs Sales, Gross vs Net, Power (`MW`) vs Energy (`MWh`), Capacity (`MW`), Reported vs Estimated/Audited, and explicit additivity rules.

### 3.2 Fact Tables (`dw.fact_*`)
1. `dw.fact_dispatch_interval` — Range-partitioned by `date_key` (`y2023`, `y2024`, `y2025`, `y2026`, `default`). Grain: `(date_key, interval_key, plant_key, metric_key, source_system_key, dataset_revision)`.
2. `dw.fact_generation_period` — Grain: `(plant_key, metric_key, period_type_code, period_start_date_key, period_end_date_key, source_system_key, dataset_revision)`. Explicitly separates `DAILY`, `MONTHLY`, and `ANNUAL` totals.
3. `dw.fact_capacity_period` — Semi-additive installed and dependable capacity (`MW`). Grain: `(plant_key, metric_key, period_type_code, effective_start_date_key, effective_end_date_key, source_system_key, dataset_revision)`.
4. `dw.fact_electricity_sales` — Periodic billed energy (`MWh`), consumer count, and optional revenue (`LKR`). Grain: `(region_key, sector_key, metric_key, period_type_code, period_start_date_key, period_end_date_key, source_system_key, dataset_revision)`.
5. `dw.fact_weather_daily` — Daily NASA POWER meteorological observations per parameter and location. Grain: `(date_key, weather_location_key, metric_key, source_system_key, dataset_revision)`. Preserves sentinel missing-value codes (e.g., `-999`) while storing `NULL` in `standardized_value`.
6. `dw.fact_published_metric` — Official published aggregate statistics for historical trend analysis and cross-source reconciliation (`UNIQUE NULLS NOT DISTINCT`). Guarded against accidental summation with operational dispatch/generation facts.

---

## 4. Ordered SQL Migration Sequence (`database/migrations/`)

|Seq| Filename | Scope |
|---|---|---|
| 001 | `001_bootstrap.sql` | `public.schema_migrations` tracking table + 7 schemas (`raw`, `staging`, `ref`, `dw`, `mart`, `audit`, `etl`) |
| 002 | `002_raw_source_registry.sql` | `raw.source_system`, `raw.source_document`, `raw.ingestion_batch`, `raw.extracted_record` |
| 003 | `003_reference_tables.sql` | `ref.unit`, `ref.unit_conversion`, `ref.reporting_period_type`, `ref.energy_source_mapping`, `ref.plant_alias`, `ref.region_alias`, `ref.metric_mapping`, `ref.data_quality_rule`, `ref.source_precedence` |
| 004 | `004_audit_and_quality_tables.sql` | `audit.etl_run`, `audit.data_quality_issue`, `audit.reconciliation_case`, `audit.record_lineage` (created before facts so facts can enforce FK to `audit.etl_run`) |
| 005 | `005_dimensions.sql` | All 9 `dw.dim_*` conformed dimension tables with constraints |
| 006 | `006_facts_generation_and_dispatch.sql` | Partitioned `dw.fact_dispatch_interval` (+ yearly & default partitions) and `dw.fact_generation_period` |
| 007 | `007_facts_capacity_and_sales.sql` | `dw.fact_capacity_period` and `dw.fact_electricity_sales` |
| 008 | `008_facts_weather_and_published.sql` | `dw.fact_weather_daily` and `dw.fact_published_metric` |
| 009 | `009_staging_tables.sql` | `staging.stg_dispatch_observation`, `stg_generation_report`, `stg_electricity_sales`, `stg_plant_capacity`, `stg_weather_observation`, `stg_published_statistic` |
| 010 | `010_indexes_and_partition_tuning.sql` | B-Tree FK/filter indexes, partial current-revision indexes, and BRIN time-ordered indexes on high-volume dispatch/weather tables |
| 011 | `011_functions.sql` | `etl.fn_convert_unit`, `etl.fn_validate_reporting_period`, `etl.fn_normalize_interval_15min`, `etl.fn_calculate_yoy_change`, `etl.fn_get_dq_summary` |
| 012 | `012_procedures.sql` | `etl.sp_start_etl_run`, `etl.sp_finalize_etl_run`, `etl.sp_validate_staged_generation`, `etl.sp_load_approved_plant_aliases`, `etl.sp_load_generation_period`, `etl.sp_record_reconciliation_case`, `etl.sp_refresh_mart_views` |
| 013 | `013_triggers.sql` | `etl.fn_trg_touch_updated_at`, `etl.fn_trg_validate_alias_verification`, `etl.fn_trg_audit_dq_issue_resolution` + triggers on `ref.*` and `audit.*` |
| 014 | `014_analytical_and_audit_views.sql` | `audit.vw_data_quality_summary`, `mart.vw_generation_by_energy_source`, `mart.vw_historical_generation_trends`, `mart.vw_electricity_sales_summary`, `mart.vw_conflicting_source_metrics` |
| 015 | `015_materialized_views.sql` | `mart.mv_monthly_generation_summary`, `mart.mv_annual_energy_mix`, `mart.mv_monthly_sales_summary` + unique indexes enabling `REFRESH MATERIALIZED VIEW CONCURRENTLY` |
| 016 | `016_roles_and_privileges.sql` | Least-privilege roles (`grid_admin`, `grid_etl`, `grid_analyst`), schema `USAGE`, table/view/procedure privileges, and default privileges |
| 017 | `017_scheduler_metadata.sql` | `etl.scheduled_job_registry` & helper `etl.fn_detect_pg_cron_available()` supporting optional `pg_cron` or external cron/Task Scheduler execution |

*(Note: Ordering `004_audit_and_quality_tables.sql` ahead of `006`–`008` allows every warehouse fact table to enforce a strict `FOREIGN KEY (etl_run_id) REFERENCES audit.etl_run(etl_run_id)` without circular dependencies, following Section 9's instruction: "Adjust ordering for foreign-key and object dependencies.")*

---

## 5. Assumptions Requiring Validation in Phase 2 (Real Data Ingestion)

1. **PUCSL Daily Report Layout Shifts**: PUCSL PDF bulletins occasionally combine weekend/holiday editions or rename sub-stations (e.g., `"Sapu A"` vs `"Sapugaskanda A"`). Unverified aliases are stored as `PENDING_EVIDENCE` in `ref.plant_alias` and are blocked by trigger from `VERIFIED` promotion without explicit `verification_evidence`.
2. **CEB Regional vs Sectoral Sales**: CEB Statistical Digests publish tariff-sector breakdowns nationally and provincial breakdowns separately in some editions rather than a full `Province × Sector` cross-tabulation. `dw.fact_electricity_sales` supports `region_key` pointing to National (`LK`) when sector totals are national, and `sector_key` pointing to `ALL_SECTORS` when sales are published purely by province, preventing fabricated cross-product splits.
3. **Embedded Rooftop Solar**: Operational 15-minute dispatch from CEB System Control / PUCSL tracks grid-metered solar plants; non-metered rooftop net-metering/net-accounting solar appears only in monthly/annual CEB/PUCSL NCRE statistics (`fact_generation_period` / `fact_published_metric`).
4. **Capacity Factor Boundaries**: Capacity factor is intentionally excluded as a stored column on `dw.fact_capacity_period` because plant outages, mid-year commissioning, and gross-vs-net generation boundaries must be verified first.

---

## 6. Execution & Commit Milestones (TDD)

1. **Milestone 1**: Complete Phase 0 Red-to-Green foundation modules (`src/common/`, `src/ingestion/`, `src/preprocessing/`, `src/validation/`, `scripts/migrate.py`, `001_bootstrap.sql`) and verify existing unit/quality/migration tests pass.
2. **Milestone 2**: Write failing Phase 1 database schema, constraint, partitioning, function, procedure, trigger, view, MV, seeding, transaction, and role privilege integration tests (`tests/integration/` & `tests/unit/`).
3. **Milestone 3**: Implement SQL migrations `002`–`017` and idempotent reference seed framework (`database/seeds/` & `scripts/seed_reference.py`).
4. **Milestone 4**: Execute clean PostgreSQL 18 verification, idempotent re-seeding, transactional commit/rollback fixtures, `EXPLAIN (ANALYZE, BUFFERS)` benchmarks, and role privilege checks.
5. **Milestone 5**: Generate all 17 Phase 1 documentation deliverables (`docs/architecture/`, `docs/database/`, `docs/data_sources/`, `docs/testing/`) and commit cleanly to `feature/phase-1-warehouse-database`.

