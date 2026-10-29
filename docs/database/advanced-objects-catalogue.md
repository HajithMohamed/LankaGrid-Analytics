# Advanced PostgreSQL 18 Database Objects Catalogue

Every advanced PostgreSQL feature implemented in [006_facts_generation_and_dispatch.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/006_facts_generation_and_dispatch.sql) through [017_scheduler_metadata.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/017_scheduler_metadata.sql) is justified by concrete data-integrity, analytical-correctness, or query-performance needs.

---

## A. Relational & Domain Constraints

| Attribute | Detail |
|---|---|
| **Object Names** | `ck_fact_dispatch_power_nonneg`, `ck_fact_dispatch_derived_energy_physics`, `ck_fact_gen_period_daily_exact`, `ck_fact_capacity_dependable_le_installed`, `ck_fact_weather_missing_null`, `ck_fact_weather_physical_bounds`, `ck_dim_power_plant_lat/lon`, `uq_fact_published_metric_grain` (`UNIQUE NULLS NOT DISTINCT`), `uq_dim_power_plant_current` |
| **Purpose** | Enforce physical laws of electricity, geographical bounds of Sri Lanka, grain uniqueness, and `NULL`-vs-`0` missing-data semantics directly at the storage engine layer. |
| **Connected Tables** | All `dw.dim_*` and `dw.fact_*` tables ([005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)–[008_facts_weather_and_published.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/008_facts_weather_and_published.sql)). |
| **How It Works** | Declarative `CHECK`, `FOREIGN KEY`, `UNIQUE`, partial unique index (`WHERE is_current = TRUE`), and PostgreSQL 18 `UNIQUE NULLS NOT DISTINCT` constraints abort invalid row writes immediately. |
| **Related Business Functionality** | Prevents negative generation, $MWh \ne MW \times \Delta t$ integration bugs, dependable > nameplate capacity errors, sentinel `-999` turning into `0.0`, and duplicate national benchmark rows. |
| **Tests** | `test_negative_and_impossible_measurements_rejected`, `test_missing_weather_sentinel_preserved_as_null_and_duplicate_prevented` in [test_phase1_schema_and_constraints.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_schema_and_constraints.py). |
| **Correctness Justification** | Application parsers can evolve across 6 team members; database-enforced invariants guarantee corrupt physics can never enter `dw.*`. |

---

## B. Reusable Analytical & Audit Views

| Object Name | Purpose | Connected Tables | How It Works | Business Functionality | Tests | Justification |
|---|---|---|---|---|---|---|
| `audit.vw_data_quality_summary` & `audit.data_quality_summary` | Summarize row-level DQ issues by ETL run, rule, class, severity, and resolution status. | `audit.data_quality_issue`, `ref.data_quality_rule`, `audit.etl_run` | Groups issue counts and first/last detection timestamps. | QA governance and quarantine triage. | `test_procedures_views_mvs_reconciliation_and_no_double_counting` | Gives `grid_analyst` safe visibility into data quality without exposing raw/staging write tables. |
| `mart.vw_generation_by_energy_source` | Grain-safe generation aggregation by fuel/category. | `dw.fact_generation_period`, `dw.dim_date`, `dw.dim_energy_source`, `dw.dim_source_system` | Filters `is_current_revision = TRUE` and retains `period_type_code`, `generation_boundary`, and `source_code` in `GROUP BY`. | Fuel-mix analysis across hydro, coal, thermal oil, solar, wind, and biomass. | `test_procedures_views_mvs_reconciliation_and_no_double_counting` | Prevents accidental summation across `DAILY` + `MONTHLY` + `ANNUAL` or `v1` + `v2` revisions. |
| `mart.vw_historical_generation_trends` | Annual generation series with YoY growth `%`. | `dw.fact_generation_period`, `dw.dim_date`, `dw.dim_energy_source`, `dw.dim_source_system` | Uses `LAG()` partitioned by `(period_type_code, generation_boundary, energy_source_code, source_code)` and `etl.fn_calculate_yoy_change`. | Multi-year sector transition tracking. | [test_phase1_advanced_objects.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_advanced_objects.py) | Ensures YoY comparisons only compare matching boundaries and providers. |
| `mart.vw_electricity_sales_summary` | Regional and tariff-sector billed sales summary. | `dw.fact_electricity_sales`, `dw.dim_date`, `dw.dim_region`, `dw.dim_consumption_sector`, `dw.dim_source_system` | Sums `energy_sold_mwh` and `revenue_lkr` while applying `MAX` (not `SUM`) to semi-additive `consumer_account_count`. | Tariff and regional consumption analytics. | [test_phase1_advanced_objects.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_advanced_objects.py) | Protects analysts from summing monthly customer headcounts $12\times$ per year. |
| `mart.vw_conflicting_source_metrics` | Expose CEB vs. PUCSL cross-source discrepancies. | `audit.reconciliation_case`, `dw.dim_metric` | Joins variance calculations (`absolute_variance` generated column + `pct_variance`) with metric boundary metadata. | Source reconciliation & audit reporting. | `test_procedures_views_mvs_reconciliation_and_no_double_counting` | Surfaces source conflicts transparently without overwriting published figures. |

---

## C. Pre-Aggregated Materialized Views

| Object Name | Purpose | Connected Tables | How It Works | Business Functionality | Tests | Performance / Correctness Justification |
|---|---|---|---|---|---|---|
| `mart.mv_monthly_generation_summary` | Pre-aggregate monthly/daily rollups by energy source. | `dw.fact_generation_period`, `dw.dim_date`, `dw.dim_energy_source`, `dw.dim_source_system` | Backed by unique index `uq_mv_monthly_generation_summary` enabling `REFRESH MATERIALIZED VIEW CONCURRENTLY`. | Fast monthly generation dashboards/queries. | `test_procedures_views_mvs_reconciliation_and_no_double_counting` | Avoids rescanning multi-year station-daily rows on repeated analytical reads while allowing non-blocking concurrent refresh. |
| `mart.mv_annual_energy_mix` | Pre-compute annual fuel share `%` of system total. | `dw.fact_generation_period`, `dw.dim_date`, `dw.dim_energy_source`, `dw.dim_source_system` | Windowed `SUM(...) OVER (PARTITION BY ...)` + unique index `uq_mv_annual_energy_mix`. | Annual renewable vs. thermal mix share. | `test_procedures_views_mvs_reconciliation_and_no_double_counting` | Eliminates repetitive window passes over `fact_generation_period`. |
| `mart.mv_monthly_sales_summary` | Pre-aggregate monthly electricity sales by region & tariff sector. | `dw.fact_electricity_sales`, `dw.dim_date`, `dw.dim_region`, `dw.dim_consumption_sector`, `dw.dim_source_system` | Backed by `uq_mv_monthly_sales_summary` for concurrent refresh via `etl.sp_refresh_mart_views(TRUE)`. | Sectoral & provincial sales reporting. | `test_least_privilege_database_roles`, `test_procedures_views_mvs_reconciliation_and_no_double_counting` | Low-latency read access for `grid_analyst`. |

---

## D. SQL & PL/pgSQL Functions ([011_functions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/011_functions.sql))

| Object Name | Purpose | Connected Tables | How It Works | Business Functionality | Tests | Justification |
|---|---|---|---|---|---|---|
| `etl.fn_convert_unit` | Deterministic, physics-safe unit conversion. | `ref.unit`, `ref.unit_conversion` | Preserves `NULL`; looks up multiplier/offset; enforces positive `p_interval_hours` when `requires_interval_hours = TRUE` (`MW -> MWh`); raises `ERRCODE 22023` on invalid pairs. | Standardizing `GWh -> MWh`, `kW -> MW`, `MLKR -> LKR`, and `15-min MW -> MWh`. | `test_plpgsql_functions_contracts` | Centralizes unit math and makes accidental `MW == MWh` conversion impossible. |
| `etl.fn_validate_reporting_period` | Verify start/end dates match declared granularity. | `ref.reporting_period_type` | Checks span bounds and exact calendar boundaries (`DAILY` 1-day, `MONTHLY` 1st-to-month-end, `ANNUAL` Jan 1–Dec 31). | Prevents annual totals from being loaded as daily records. | `test_plpgsql_functions_contracts` | Enforces Section 4 requirement against granularity conflation. |
| `etl.fn_normalize_interval_15min` | Map any `TIMESTAMPTZ` to SLST `Asia/Colombo` (`+05:30`) 15-min slot & TOU block. | Pure `IMMUTABLE` function aligned with `dw.dim_interval` | Converts timezone to `Asia/Colombo`, computes `date_key`, slot `1..96`, and `OFF_PEAK` / `DAY` (`05:30–18:30`) / `PEAK` (`18:30–22:30`). | Sub-daily dispatch ingestion & TOU slicing. | `test_plpgsql_functions_contracts` | Guarantees uniform `+05:30` timestamp handling regardless of client timezone. |
| `etl.fn_calculate_yoy_change` | Safe YoY percentage growth calculation. | Used by `mart.vw_historical_generation_trends` | Returns `NULL` when baseline is `NULL` or `0`; otherwise `ROUND(((curr - prior)/ABS(prior))*100, 4)`. | Historical trend reporting. | `test_plpgsql_functions_contracts` | Prevents division-by-zero errors and fabricated `0%` growth on missing baselines. |
| `etl.fn_get_dq_summary` | Parameterized DQ diagnostic table function. | `audit.data_quality_issue` | Aggregates issues optionally filtered by `p_etl_run_id`. | Post-batch ETL gate evaluation. | [test_phase1_advanced_objects.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_advanced_objects.py) | Reusable programmatic summary for Python quality gates. |

---

## E. Stored Procedures ([012_procedures.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/012_procedures.sql))

| Object Name | Purpose | Connected Tables | How It Works | Business Functionality | Tests | Justification |
|---|---|---|---|---|---|---|
| `etl.sp_start_etl_run` & `etl.sp_finalize_etl_run` | Open and close `audit.etl_run` execution records. | `audit.etl_run` | Inserts `RUNNING` row returning `p_etl_run_id`; updates final status, row counters, and error message. | End-to-end ETL observability. | `test_procedures_views_mvs_reconciliation_and_no_double_counting`, `test_transactional_batch_commit_idempotency_and_rollback` | Standardizes audit logging across all pipelines. |
| `etl.sp_validate_staged_generation` | Validate staged generation rows without deleting bad records. | `staging.stg_generation_report`, `dw.dim_power_plant`, `ref.plant_alias`, `audit.data_quality_issue` | Flags missing values, negative energy, invalid periods, and unmatched plants; logs `audit.data_quality_issue`; marks staging rows `valid` or `quarantined`. | Pre-warehouse quality gate. | `test_procedures_views_mvs_reconciliation_and_no_double_counting` | Preserves malformed source records in quarantine for inspection. |
| `etl.sp_load_approved_plant_aliases` | Audit verified vs. pending plant aliases. | `ref.plant_alias`, `dw.dim_power_plant` | Counts `VERIFIED` aliases linked to active plants vs. `PENDING_EVIDENCE` aliases. | Entity resolution governance. | [phase1_sql_assertions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/tests/phase1_sql_assertions.sql) | Ensures unverified aliases are never silently merged. |
| `etl.sp_load_generation_period` | Idempotent staging-to-warehouse loader with revision superseding. | `staging.stg_generation_report`, `dw.fact_generation_period`, `audit.record_lineage` | Converts units to `MWh`, marks older revisions `is_current_revision = FALSE`, performs `INSERT ... ON CONFLICT DO UPDATE`, and logs `audit.record_lineage`. | Generation fact loading. | `test_procedures_views_mvs_reconciliation_and_no_double_counting`, `test_transactional_batch_commit_idempotency_and_rollback` | Guarantees zero duplicates on re-runs and zero double-counting across revisions. |
| `etl.sp_record_reconciliation_case` | Compare cross-source metrics over compatible periods/boundaries. | `audit.reconciliation_case`, `dw.dim_metric`, `ref.source_precedence` | Validates period compatibility, computes `%` variance, flags `CONFLICT_FLAGGED` vs `WITHIN_TOLERANCE`, and attaches authoritative source from `ref.source_precedence`. | CEB vs. PUCSL conflict reconciliation. | `test_procedures_views_mvs_reconciliation_and_no_double_counting` | Enforces apples-to-apples reconciliation rules. |
| `etl.sp_refresh_mart_views` | Refresh all `mart.mv_*` materialized views. | `mart.mv_monthly_generation_summary`, `mart.mv_annual_energy_mix`, `mart.mv_monthly_sales_summary` | Executes `REFRESH MATERIALIZED VIEW [CONCURRENTLY]` across all three MVs. | Post-load analytical cache refresh. | `test_procedures_views_mvs_reconciliation_and_no_double_counting` | Single atomic entrypoint for manual or scheduled MV refreshes. |

---

## F. Governance Triggers ([013_triggers.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/013_triggers.sql))

| Object Name | Purpose | Connected Tables | How It Works | Business Functionality | Tests | Justification |
|---|---|---|---|---|---|---|
| `trg_ref_*_updated_at` (`etl.fn_trg_touch_updated_at`) | Maintain accurate `updated_at` audit timestamps on reference edits. | All 9 `ref.*` tables | `BEFORE UPDATE FOR EACH ROW` sets `NEW.updated_at := CURRENT_TIMESTAMP`. | Reference governance auditing. | `test_triggers_guard_alias_evidence_and_dq_resolution` | Lightweight row metadata maintenance with zero heavy ETL logic. |
| `trg_validate_*_evidence` (`etl.fn_trg_validate_verification_evidence`) | Block unverified alias merges. | `ref.plant_alias`, `ref.energy_source_mapping`, `ref.region_alias` | `BEFORE INSERT OR UPDATE` raises exception if `verification_status = 'VERIFIED'` and `verification_evidence` is `NULL`/blank. | Prevents speculative merging of plant/region names. | `test_triggers_guard_alias_evidence_and_dq_resolution` | Directly enforces Section 5 rule: *"require evidence before merging identities"*. |
| `trg_audit_dq_issue_resolution` (`etl.fn_trg_audit_dq_issue_resolution`) | Enforce signed-off DQ resolution workflow. | `audit.data_quality_issue` | Requires `resolved_by` and `resolution_justification` when transitioning to `accepted` or `corrected`, auto-populating `resolved_at`. | Data quality sign-off accountability. | `test_triggers_guard_alias_evidence_and_dq_resolution` | Prevents silent dismissal of quarantined data errors. |

---

## G–K. Partitioning, Indexing, Transactions, Roles & Scheduler
Detailed specifications and benchmarks are documented in:
- [etl-transaction-design.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/database/etl-transaction-design.md)
- [indexing-and-partitioning-strategy.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/database/indexing-and-partitioning-strategy.md)
- [role-and-privilege-matrix.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/database/role-and-privilege-matrix.md)
- [postgresql-setup-and-migration-guide.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/database/postgresql-setup-and-migration-guide.md)
