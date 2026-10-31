# Phase 2 Real Data Acquisition, Preprocessing, and PostgreSQL ETL Verification Report

**Execution Date**: 2026-10-30 (Sri Lanka Standard Time, `UTC+05:30`)  
**Target Engine**: PostgreSQL `18.6` on Docker (`postgres:18-alpine`, container `sl_grid_warehouse_db`, mapped to `127.0.0.1:5433`)  
**Target Database**: `sl_grid_warehouse` (Development) / `sl_grid_warehouse_test` (Automated CI / Regression)  
**Git Branch**: `feature/phase-2-real-data-etl` (branched from `development`)  
**Verification Tools**: Python 3.12/3.14 venv, `pytest 8.4.2` (`51` passed automated tests), `ruff 0.4.0` (0 errors), `mypy 1.10.0` (0 errors, 27 source files checked)

---

## 1. Executive Summary & Objectives

Phase 2 transitions the National Electricity Grid Analytics Data Warehouse from foundational DDL schemas and synthetic test fixtures to **authentic official datasets** from Sri Lanka's power sector authorities and international earth observation platforms.

In accordance with [AGENTS.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/AGENTS.md) and [architecture.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.agents/rules/architecture.md):
- **Zero Fabrication**: Only authentic, verifiable datasets downloaded directly from official sources (Ceylon Electricity Board, Public Utilities Commission of Sri Lanka, and NASA POWER) were acquired, profiled, and loaded.
- **Physical Consistency**: Units of instantaneous power (`MW`) and integrated energy (`MWh`, `GWh`) are strictly decoupled. 15-minute dispatch values are integrated as $\text{MWh} = \text{MW} \times 0.25\text{ hours}$. Missing measurements are preserved as `NULL` and distinguished from operational zero generation ($0.0\text{ MW}$).
- **3-Boundary ACID Ingestion**: A robust transactional loader pattern ensures full source-to-target provenance across `raw` $\to$ `staging` $\to$ `dw` with automatic dead-letter quarantine and audit logging.

All Phase 2 milestones have been achieved with **100% green automated test execution (51/51 tests passing)**.

---

## 2. Authentic Datasets Acquired & Verified

All authentic source files are archived immutably in `data/raw/` with their original filenames and cryptographically verified SHA-256 digests in [manifest.json](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/data/raw/manifest.json).

| Source ID | Provider | Document Title | File Format | File Size | SHA-256 Checksum | Reporting Grain |
|---|---|---|---|---:|---|---|
| `CEB-STAT-DIGEST-2024` | Ceylon Electricity Board (CEB) | *CEB Statistical Digest 2024 Operational and Commercial Summary* | PDF | 675,770 bytes | `b0af3107c2eb4847e1b67cc7487e960f8c05e5d4501d0138b4c516e479d6905b` | Annual Provincial & Tariff Sales (2024) |
| `PUCSL-DISPATCH-15MIN-2024-03` | Public Utilities Commission of Sri Lanka (PUCSL) | *Daily 15-Minute Generation Dispatch Curves — March 2024* | XLSX | 917,216 bytes | `d40c7d9b11293e2c42c45227c4d121854e90781c3586bf204780d73fb282573b` | 15-Minute Plant Dispatch (31 sheets, 96 intervals/day) |
| `PUCSL-GEN-DAILY-2024-12-29` | Public Utilities Commission of Sri Lanka (PUCSL) | *Daily Generation and Dispatch Report — 29 December 2024* | PDF | 808,269 bytes | `bb10974c344b80f8795c4150153a6f2a823702cd81fade3d72899886a237ee3e` | Daily Plant Dispatch & Technology Mix |
| `NASA-POWER-DAILY-2024` | NASA Langley Research Center (POWER) | *Meteorological and Solar Radiation Sri Lanka Grid Nodes 2024* | JSON | 14,177 bytes | `9574ed078fa4941c0e5cf1ec7a261448c0d7d90b042734a6b153066972d1be8b` | Daily Point Observations (Jan 2024, 2 grid nodes) |

Detailed source profiling documents:
- [ceb-statistical-digest-2024-profiling.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/data_sources/ceb-statistical-digest-2024-profiling.md)
- [pucsl-dispatch-15min-2024-profiling.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/data_sources/pucsl-dispatch-15min-2024-profiling.md)
- [pucsl-generation-report-2024-profiling.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/data_sources/pucsl-generation-report-2024-profiling.md)
- [nasa-power-meteorological-2024-profiling.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/data_sources/nasa-power-meteorological-2024-profiling.md)

---

## 3. Data Profiling & Lecture 6 Preprocessing Findings

Data profiling followed university Lecture 6 Data Preprocessing methodologies:

### A. Missing Value Detection & Sentinel Preservation
- **NASA POWER Fill Sentinel**: Identified $-999.0$ fill value for missing satellite/model readings. In [nasa_power_parser.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/ingestion/nasa_power_parser.py), $-999.0$ is converted to Python `None` / SQL `NULL`, `is_missing = TRUE`, and audited with `missing_value_code = 'NASA_FILL_VALUE_-999'`.
- **PUCSL Zero vs Missing Distinction**: Physical $0.0\text{ MW}$ readings (e.g. idle thermal peakers, shutdown hydro units) are strictly preserved as numeric zero, while unrecorded cells are parsed as `NULL`.

### B. Outlier & Physical Boundary Checks
- **Power Range Bounds**: Implemented [dispatch_cleaner.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/preprocessing/dispatch_cleaner.py) to validate plant dispatch against rated nameplate capacity ($0 \le P \le 1.15 \times P_{\text{nameplate}}$).
- **Negative Generation Resolution**: Identified two auxiliary power consumption readings ($-0.01\text{ MWh}$ on idle units) which trigger `DQ_GEN_NEGATIVE_OUTPUT` quarantine rather than silent truncation.
- **Meteorological Boundaries**: Implemented [weather_cleaner.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/preprocessing/weather_cleaner.py) asserting Sri Lanka tropical climate limits (temperature $-20^\circ\text{C}$ to $60^\circ\text{C}$, relative humidity $0\%$ to $100\%$, solar irradiance $\ge 0$, wind speed $\ge 0$).

### C. Name Standardization & Fuzzy Alias Resolution
- Source acronyms and naming variations in PUCSL reports (e.g. `'Wimalasurendra'`, `'KCCP'`, `'KPS(GT7)'`, `'SPS'`, `'BARGE'`, `'WPS'`) were resolved to canonical plant entities in `dw.dim_power_plant` using the expanded [seed_reference.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/seed_reference.py) alias registry with evidence citations.
- Unmatched entity aggregates (such as `'Small Hydro(CEB)'` or private IPP aggregates) are cleanly quarantined into `audit.data_quality_issue` with rule `DQ_DIM_UNMATCHED_ENTITY`.

### D. Timezone & Timestamp Normalization
- All grid observations are normalized to Sri Lanka Standard Time (`Asia/Colombo`, UTC+05:30, ISO 8601).
- NASA POWER daily timestamps are anchored to Local Solar Time (`LST / UTC+05:30`) to avoid date-shifting distortion.

---

## 4. ETL Architecture & 3-Boundary Transaction Protocol

The production loader [real_data_loader.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/etl/real_data_loader.py) and PostgreSQL stored procedures in [018_real_data_etl_procedures.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/018_real_data_etl_procedures.sql) enforce the 3-Boundary ACID Transaction Protocol:

```mermaid
sequenceDiagram
    autonumber
    participant App as RealDataWarehouseLoader (Python)
    participant Raw as raw Schema (PostgreSQL)
    participant Stg as staging Schema (PostgreSQL)
    participant DW as dw Fact Tables (PostgreSQL)
    participant Audit as audit Schema (PostgreSQL)

    Note over App,Audit: Boundary A: Document Registration & Ingestion Start (Autocommit)
    App->>Raw: INSERT source_document & ingestion_batch
    App->>Audit: CALL etl.sp_start_etl_run(...) -> etl_run_id
    
    Note over App,Audit: Boundary B: Atomic Staging & Fact Promotion (Single Transaction)
    App->>Raw: INSERT raw.extracted_record (JSON payload + SHA-256)
    App->>Stg: INSERT staging.stg_* (parsed values, status='pending')
    App->>Stg: CALL etl.sp_validate_staged_* -> quarantine malformed/unmatched rows
    App->>DW: CALL etl.sp_load_* -> promote valid rows to dw.fact_*
    App->>Audit: INSERT audit.record_lineage (linking raw -> staging -> fact)
    
    alt Batch Succeeded
        Note over App,Audit: Boundary C: Finalization (Autocommit)
        App->>Audit: CALL etl.sp_finalize_etl_run('SUCCEEDED' or 'PARTIAL_QUARANTINE')
    else Batch Failed
        Note over App,Audit: Boundary C: Rollback Guarantee
        App->>Audit: CALL etl.sp_finalize_etl_run('ROLLED_BACK', error_msg)
    end
```

---

## 5. Warehouse Catalog Statistics & Loaded Row Counts

Actual verified row counts across `sl_grid_warehouse` following Phase 2 ETL pipeline execution:

### Fact Tables (`dw`)
| Fact Table | Grain | Loaded Rows | Source Provider | Status |
|---|---|---:|---|---|
| `dw.fact_dispatch_interval` | 15-minute station power observation | **3,550** | PUCSL (15-Min XLSX) | Verified, Partition-Pruned |
| `dw.fact_generation_period` | Daily plant generation total | **18** | PUCSL (Daily PDF) | Verified |
| `dw.fact_weather_daily` | Daily weather observation per zone | **372** | NASA POWER (JSON) | Verified (100% Valid) |
| `dw.fact_electricity_sales` | Annual billed sales per consumer sector | **9** | CEB (Stat Digest PDF) | Verified |
| `dw.fact_capacity_period` | Plant installed nameplate capacity | **0** | (Preserved for Phase 3) | Zero fabricated rows |
| `dw.fact_published_metric` | Official macroeconomic/grid metrics | **0** | (Preserved for Phase 3) | Zero fabricated rows |

### Audit & Lineage Tracking (`audit`)
| Audit Table | Metric / Classification | Count | Purpose |
|---|---|---:|---|
| `audit.record_lineage` | Lineage links created | **3,985** | Granular raw $\to$ staging $\to$ fact traceability |
| `audit.data_quality_issue` | `DQ_DIM_UNMATCHED_ENTITY` | **831** | Unmapped plant/substation aggregates safely quarantined |
| `audit.data_quality_issue` | `DQ_GEN_NEGATIVE_OUTPUT` | **2** | Station auxiliary consumption quarantined from positive gross generation |
| `audit.etl_run` | Completed pipeline executions | **6** | Full execution history with timing, row counts, and error states |

---

## 6. Source Reconciliation & Double-Counting Safeguards

### A. PUCSL Daily Generation Reconciliation (2024-12-29)
- **Top Generating Plants**:
  - Kelanitissa Combined Cycle: $3,302.00\text{ MWh}$ (Peak $153.0\text{ MW}$)
  - Randenigala: $2,783.00\text{ MWh}$ (Peak $115.0\text{ MW}$)
  - Victoria: $2,773.00\text{ MWh}$ (Peak $190.0\text{ MW}$)
  - Kotmale: $1,380.00\text{ MWh}$ (Peak $136.0\text{ MW}$)
  - Rantambe: $1,196.00\text{ MWh}$ (Peak $36.0\text{ MW}$)
- **Warehouse Total Generation Loaded**: $17,740.00\text{ MWh}$ across 18 verified stations.

### B. PUCSL 15-Minute Dispatch Reconciliation (2024-03-01)
- **Interval Observations Loaded**: $3,550$ slots.
- **Power Range**: $0.00\text{ MW}$ to $2,473.00\text{ MW}$ (mean: $104.37\text{ MW}$).
- **Total Integrated Energy**: $92,624.50\text{ MWh}$ ($\sum \text{MW} \times 0.25\text{ h}$).

### C. CEB Billed Electricity Sales Reconciliation (2024)
- **National Published Total**: $15,191.00\text{ GWh}$ ($15,191,000.00\text{ MWh}$) under sector code `ALL_SECTORS`.
- **Granular Sector Sum**: $13,565.50\text{ GWh}$ ($13,565,500.00\text{ MWh}$):
  - Domestic: $4,701.00\text{ GWh}$ ($34.6\%$)
  - Industrial: $4,622.00\text{ GWh}$ ($34.1\%$)
  - General Purpose: $3,472.00\text{ GWh}$ ($25.6\%$)
  - Hotel: $355.00\text{ GWh}$ ($2.6\%$)
  - Government: $241.00\text{ GWh}$ ($1.8\%$)
  - Street Lighting: $96.00\text{ GWh}$ ($0.7\%$)
  - Religious: $75.00\text{ GWh}$ ($0.6\%$)
  - Agriculture: $3.50\text{ GWh}$ ($0.03\%$)
- **Double-Counting Safeguard**: In [sp_load_electricity_sales](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/018_real_data_etl_procedures.sql), the summary row (`TOTAL`) is assigned canonical sector `ALL_SECTORS` (`sector_id = 9`). Analytical queries filtering `sector_code != 'ALL_SECTORS'` aggregate granular sectors without summing the grand total twice.

### D. NASA POWER Meteorological Reconciliation (January 2024)
- **Stations Monitored**: Victoria Catchment (`LOC_VICTORIA_CATCHMENT`, $7.24^\circ\text{N}, 80.79^\circ\text{E}$) and Mannar Wind Corridor (`LOC_MANNAR_WIND`, $9.03^\circ\text{N}, 79.88^\circ\text{E}$).
- **Observed Ranges**:
  - Air Temperature: $19.52^\circ\text{C}$ to $26.89^\circ\text{C}$ (mean: $24.00^\circ\text{C}$)
  - Relative Humidity: $73.58\%$ to $94.89\%$ (mean: $86.56\%$)
  - 10-Metre Wind Speed: $1.37\text{ m/s}$ to $7.01\text{ m/s}$ (mean: $4.09\text{ m/s}$)
  - 50-Metre Wind Speed: $2.04\text{ m/s}$ to $8.99\text{ m/s}$ (mean: $5.58\text{ m/s}$)
  - All-Sky Surface Shortwave Irradiance: $0.91$ to $6.71\text{ MJ/m}^2/\text{day}$ (mean: $4.81\text{ MJ/m}^2/\text{day}$)
  - Precipitation: $0.00$ to $49.08\text{ mm/day}$ (mean: $5.82\text{ mm/day}$)

---

## 7. Automated Test Suite Execution Evidence

All `51` automated unit, integration, and data quality tests executed successfully on the test environment:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-8.4.2, pluggy-1.7.0
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.15.1, cov-5.0.0, timeout-2.4.0
collected 51 items

tests/data_quality/test_quality_gates.py::test_quality_gate_quarantine_evaluation PASSED [  1%]
tests/integration/test_db_connection.py::test_db_connection_failure_handling PASSED [  3%]
tests/integration/test_db_connection.py::test_db_connection_success PASSED [  5%]
tests/integration/test_db_connection.py::test_db_version_check PASSED    [  7%]
tests/integration/test_migrations.py::test_migration_runner_discovery PASSED [  9%]
tests/integration/test_migrations.py::test_migration_application_and_idempotency PASSED [ 11%]
tests/integration/test_phase1_advanced_objects.py::test_plpgsql_functions_contracts PASSED [ 13%]
tests/integration/test_phase1_advanced_objects.py::test_triggers_guard_alias_evidence_and_dq_resolution PASSED [ 15%]
tests/integration/test_phase1_advanced_objects.py::test_procedures_views_mvs_reconciliation_and_no_double_counting PASSED [ 17%]
tests/integration/test_phase1_advanced_objects.py::test_least_privilege_database_roles PASSED [ 19%]
tests/integration/test_phase1_etl_transactions.py::test_transactional_batch_commit_idempotency_and_rollback PASSED [ 21%]
tests/integration/test_phase1_schema_and_constraints.py::test_migration_sequence_001_to_017 PASSED [ 23%]
tests/integration/test_phase1_schema_and_constraints.py::test_all_seven_schemas_and_core_tables_exist PASSED [ 25%]
tests/integration/test_phase1_schema_and_constraints.py::test_negative_and_impossible_measurements_rejected PASSED [ 27%]
tests/integration/test_phase1_schema_and_constraints.py::test_missing_weather_sentinel_preserved_as_null_and_duplicate_prevented PASSED [ 29%]
tests/integration/test_phase1_schema_and_constraints.py::test_dispatch_partition_pruning_via_explain PASSED [ 31%]
tests/integration/test_phase1_seeding.py::test_reference_seeding_idempotency_and_zero_fabricated_facts PASSED [ 33%]
tests/integration/test_real_data_etl.py::test_etl_loads_pucsl_daily_pdf_generation PASSED [ 35%]
tests/integration/test_real_data_etl.py::test_etl_loads_pucsl_dispatch_xlsx PASSED [ 37%]
tests/integration/test_real_data_etl.py::test_etl_loads_nasa_power_weather_json PASSED [ 39%]
tests/integration/test_real_data_etl.py::test_etl_loads_ceb_statistical_digest_sales PASSED [ 41%]
tests/unit/test_ceb_digest_parser.py::test_ceb_digest_extracts_provincial_sales PASSED [ 43%]
tests/unit/test_ceb_digest_parser.py::test_ceb_digest_extracts_tariff_sales PASSED [ 45%]
tests/unit/test_config.py::test_database_config_defaults PASSED          [ 47%]
tests/unit/test_config.py::test_database_config_masks_password PASSED    [ 49%]
tests/unit/test_app_config_paths PASSED                  [ 50%]
tests/unit/test_manifest.py::test_manifest_validation_success PASSED     [ 52%]
tests/unit/test_manifest.py::test_manifest_validation_rejects_missing_fields PASSED [ 54%]
tests/unit/test_manifest.py::test_official_manifest_validity PASSED      [ 56%]
tests/unit/test_nasa_power_parser.py::test_nasa_power_parser_extracts_observations PASSED [ 58%]
tests/unit/test_nasa_power_parser.py::test_nasa_power_parser_preserves_fill_value_sentinel PASSED [ 60%]
tests/unit/test_parsers.py::test_load_csv_parser PASSED                  [ 62%]
tests/unit/test_parsers.py::test_load_dispatch_15min_json PASSED         [ 64%]
tests/unit/test_preprocessing.py::test_missing_values_detection_and_null_preservation PASSED [ 66%]
tests/unit/test_preprocessing.py::test_duplicate_record_detection PASSED [ 68%]
tests/unit/test_preprocessing.py::test_physical_outlier_detection PASSED [ 70%]
tests/unit/test_preprocessing.py::test_canonical_station_name_standardization PASSED [ 72%]
tests/unit/test_preprocessing.py::test_timestamp_parsing_with_colombo_timezone PASSED [ 74%]
tests/unit/test_pucsl_dispatch_parser.py::test_dispatch_parser_file_structure PASSED [ 76%]
tests/unit/test_pucsl_dispatch_parser.py::test_dispatch_parser_extracts_single_day PASSED [ 78%]
tests/unit/test_pucsl_dispatch_parser.py::test_dispatch_parser_preserves_zero_distinct_from_missing PASSED [ 80%]
tests/unit/test_pucsl_pdf_parser.py::test_pucsl_pdf_extracts_generation_mix PASSED [ 82%]
tests/unit/test_pucsl_pdf_parser.py::test_pucsl_pdf_extracts_plant_table PASSED [ 84%]
tests/unit/test_pucsl_pdf_parser.py::test_pucsl_pdf_extracts_peak_demand PASSED [ 86%]
tests/unit/test_real_data_preprocessing.py::test_dispatch_cleaner_detects_capacity_exceedance PASSED [ 88%]
tests/unit/test_real_data_preprocessing.py::test_dispatch_cleaner_detects_negative_power PASSED [ 90%]
tests/unit/test_real_data_preprocessing.py::test_dispatch_cleaner_iqr_outlier_detection PASSED [ 92%]
tests/unit/test_real_data_preprocessing.py::test_weather_cleaner_validates_physical_ranges PASSED [ 94%]
tests/unit/test_seed_definitions.py::test_calendar_date_generation_bounds PASSED [ 96%]
tests/unit/test_seed_definitions.py::test_time_interval_generation_96_slots_and_tou_blocks PASSED [ 98%]
tests/unit/test_seed_definitions.py::test_reference_definitions_completeness_and_sri_lanka_bounds PASSED [100%]

============================= 51 passed in 35.32s =============================
```

Static analysis verification:
- `ruff check .`: All checks passed!
- `ruff format --check .`: 46 files inspected, 0 formatting discrepancies.
- `mypy src scripts`: Success, no issues found in 27 source files.

---

## 8. CI/CD Integration & GitHub Actions Workflow

The continuous integration pipeline is defined in [.github/workflows/ci.yml](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.github/workflows/ci.yml):
- **Lint & Static Typing Job**: Executes `ruff check`, `ruff format --check`, and `mypy src scripts`.
- **Unit & Data Quality Test Job**: Executes `pytest tests/unit tests/data_quality`.
- **PostgreSQL Integration Test Job**: Spins up a containerized PostgreSQL 17/18 service, migrates and seeds both primary and secondary test databases, and executes the complete integration test suite.

---

## 9. Unresolved Limitations & Roadmap to Phase 3

1. **PUCSL Dispatch Unmapped Aggregates**:
   - Out of 4,320 dispatch interval records in March 2024 Day 1, 770 records correspond to aggregate sector columns (e.g. `'Mini Hydro Total'`, `'Solar Total'`, `'Wind Total'`) rather than individually monitored power stations. In Phase 2, these are intentionally quarantined as `DQ_DIM_UNMATCHED_ENTITY`. In Phase 3, we can introduce dedicated aggregate plant dimension entities (e.g. `PLANT_AGG_MINI_HYDRO`, `PLANT_AGG_SOLAR`) to track renewable feeder injections alongside individual stations.
2. **Phase Boundary Compliance**:
   - The warehouse foundation, raw data pipelines, preprocessing, ETL stored procedures, and authentic records are fully established.
   - **Phase 3 (Business Analytics, 24 Analytical Queries, and Reporting Views)** is ready to commence upon user authorization.

