# Authoritative Verified Database Schema & Object Inventory
## National Electricity Grid Analytics Data Warehouse — Sri Lanka (GridLens)

**Document Reference:** `docs/academic/verified-database-schema-inventory.md`  
**Database Target:** PostgreSQL 18-alpine (Port `5433`)  
**Audit Methodology:** Introspection via `information_schema`, `pg_catalog`, `pg_matviews`, `pg_proc`, `pg_inherits`, and live row counting  
**Audit Execution Date:** November 2026  
**Status:** 100% VERIFIED AGAINST LIVE DATABASE & MIGRATIONS `001_` TO `021_`  

---

## 1. Physical Schema Architecture

GridLens segregates database objects into **eight dedicated schemas**, enforcing strict separation of concerns across ingestion, reference data, staging, dimensional modeling, audit governance, and analytical marts:

| Schema Name | Purpose & Lifecycle | Primary Object Types | Object Count |
| :--- | :--- | :--- | :---: |
| **`raw`** | Immutable raw metadata tracking and extracted payload preservation. | Base tables | 4 |
| **`staging`** | Transient staging zone for type conversion, cleaning, and quarantine evaluation. | Base tables | 6 |
| **`ref`** | Reference standards, source aliases, unit conversions, and precedence rules. | Base tables | 9 |
| **`dw`** | Enterprise Kimball dimensional warehouse (9 dimensions, 6 facts, partitions). | Base tables | 23 |
| **`audit`** | Data governance, row-level lineage, ETL run tracking, and quality issues. | Base tables & views | 6 |
| **`etl`** | Stored procedures and functions orchestrating validation, loading, and transformations. | Routines & registry | 23 |
| **`mart`** | Pre-aggregated materialized views and views optimized for analytical reporting. | MVs & views | 9 |
| **`public`** | System metadata and schema migration tracking. | Base table | 1 |

---

## 2. Kimball Dimensional Model Core (`dw` Schema)

The dimensional core implements a **Fact Constellation Schema** consisting of **9 Conformed Dimensions** and **6 Fact Tables**:

### 2.1 Conformed Dimension Inventory (9 Dimensions)

| Dimension Name | Primary Key | Key Business Attributes | Row Count | Evidence / Migration Reference |
| :--- | :--- | :--- | :---: | :--- |
| **`dw.dim_date`** | `date_key` (INT, `YYYYMMDD`) | `calendar_date`, `calendar_year`, `month_number`, `month_name`, `sl_monsoon_season`, `is_weekend`, `quarter_number` | **2,922** | `database/migrations/005_dimensions.sql` |
| **`dw.dim_interval`** | `interval_key` (INT) | `interval_index` (1–96), `start_time`, `end_time`, `duration_minutes` (15), `tariff_time_block` (`DAY`, `PEAK`, `OFF_PEAK`) | **120** | `database/migrations/005_dimensions.sql` |
| **`dw.dim_source_system`** | `source_system_key` (INT) | `source_code` (`PUCSL`, `CEB`, `NASA_POWER`), `organization_name`, `default_time_zone`, `official_portal_url` | **3** | `database/migrations/005_dimensions.sql` |
| **`dw.dim_energy_source`** | `energy_source_key` (INT) | `energy_source_code`, `energy_category`, `fuel_type`, `is_renewable`, `is_dispatchable`, `is_indigenous` | **9** | `database/migrations/005_dimensions.sql` |
| **`dw.dim_region`** | `region_key` (INT) | `region_code`, `region_name`, `region_level` (`PROVINCE`, `COUNTRY`), `iso_code`, `parent_region_key` | **14** | `database/migrations/005_dimensions.sql` |
| **`dw.dim_consumption_sector`** | `sector_key` (INT) | `sector_code` (`DOMESTIC`, `INDUSTRIAL`, `HOTEL`, etc.), `sector_name`, `tariff_group`, `is_aggregate_bucket` | **10** | `database/migrations/005_dimensions.sql` |
| **`dw.dim_power_plant`** | `plant_key` (INT) | `plant_code`, `plant_name`, `operator_type`, `energy_source_key` (FK), `region_key` (FK), `hydro_complex` | **41** | `database/migrations/005_dimensions.sql` |
| **`dw.dim_weather_location`** | `weather_location_key` (INT) | `location_code`, `location_name`, `region_key` (FK), `latitude_deg`, `longitude_deg`, `elevation_m` | **6** | `database/migrations/005_dimensions.sql` |
| **`dw.dim_metric`** | `metric_key` (INT) | `metric_code`, `metric_name`, `measurement_class`, `canonical_unit_code`, `is_summable_across_time` | **15** | `database/migrations/005_dimensions.sql` |

### 2.2 Fact Table Inventory (6 Fact Tables)

| Fact Table Name | Primary Key | Fact Grain | Core Metric Columns | Row Count | Operational Status |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **`dw.fact_dispatch_interval`** | `(dispatch_fact_id, date_key)` | Plant $\times$ 15-Minute Slot $\times$ Energy Source | `active_power_mw`, `derived_energy_mwh`, `frequency_hz`, `declared_availability_mw` | **107,115** | **Actively Populated** (Partitioned by Year; March 2024 loaded) |
| **`dw.fact_generation_period`** | `generation_fact_id` | Plant / Source $\times$ Aggregation Period | `gross_generation_mwh`, `net_generation_mwh`, `auxiliary_consumption_mwh`, `operational_hours` | **18** | **Actively Populated** (Verified PUCSL daily report dates) |
| **`dw.fact_capacity_period`** | `capacity_fact_id` | Plant $\times$ Energy Source $\times$ Effective Period | `installed_capacity_mw`, `dependable_capacity_mw`, `peak_firm_capacity_mw` | **0** | **Implemented (Unpopulated)** (Schema ready for utility capacity filings) |
| **`dw.fact_electricity_sales`** | `sales_fact_id` | Tariff Sector $\times$ Region $\times$ Year | `billed_energy_mwh`, `billed_energy_gwh`, `billed_amount_lkr`, `consumer_count`, `average_monthly_consumption_kwh` | **49** | **Actively Populated** (Audited 5-Year CEB Sales 2020–2024) |
| **`dw.fact_weather_daily`** | `weather_fact_id` | Location $\times$ Metric $\times$ Calendar Day | `raw_value`, `standardized_value`, `is_missing`, `source_quality_flag` | **21,924** | **Actively Populated** (5 Years NASA POWER Daily Reanalysis) |
| **`dw.fact_published_metric`** | `published_metric_fact_id` | Entity $\times$ Published Metric $\times$ Period | `published_value`, `unit_code`, `dataset_revision` | **0** | **Implemented (Unpopulated)** (Schema ready for macro digest statistics) |

---

## 3. Physical Partitioning Architecture on `dw.fact_dispatch_interval`

`dw.fact_dispatch_interval` is partitioned using **PostgreSQL 18 Declarative Range Partitioning** over `date_key` (`PARTITION BY RANGE (date_key)`).

### Partition Table Layout:

```sql
dw.fact_dispatch_interval (Parent Partitioned Table)
  ├── dw.fact_dispatch_interval_y2020  [20200101 to 20210101) - rows: 0
  ├── dw.fact_dispatch_interval_y2021  [20210101 to 20220101) - rows: 0
  ├── dw.fact_dispatch_interval_y2022  [20220101 to 20230101) - rows: 0
  ├── dw.fact_dispatch_interval_y2023  [20230101 to 20240101) - rows: 0
  ├── dw.fact_dispatch_interval_y2024  [20240101 to 20250101) - rows: 107,115 (March 2024 facts)
  ├── dw.fact_dispatch_interval_y2025  [20250101 to 20260101) - rows: 0
  ├── dw.fact_dispatch_interval_y2026  [20260101 to 20270101) - rows: 0
  └── dw.fact_dispatch_interval_default (DEFAULT Catch-all)   - rows: 0
```

### Partition Indexes:
Each child partition inherits:
- `pk_fact_dispatch_interval` on `(dispatch_fact_id, date_key)`
- `uq_fact_dispatch_interval_grain` on `(date_key, interval_key, plant_key, energy_source_key, metric_key, dataset_revision)`
- B-Tree index on `(plant_key, date_key)`
- BRIN index on `original_timestamp` (`idx_brin_fact_dispatch_timestamp`)

---

## 4. Staging Schema (`staging`)

The staging schema isolates transient ingested data prior to transformation and validation:

| Staging Table Name | Ingestion Source | Row Count | Mapped Core Target |
| :--- | :--- | :---: | :--- |
| **`staging.stg_dispatch_observation`** | PUCSL 15-Minute Operational Excel Telemetry | **107,136** | `dw.fact_dispatch_interval` |
| **`staging.stg_electricity_sales`** | CEB Statistical Digest Annual CSV/PDF tables | **167** | `dw.fact_electricity_sales` |
| **`staging.stg_generation_report`** | PUCSL Daily Generation Summary Sheets | **105** | `dw.fact_generation_period` |
| **`staging.stg_weather_observation`** | NASA POWER Daily Reanalysis API JSON | **44,220** | `dw.fact_weather_daily` |
| **`staging.stg_plant_capacity`** | CEB / SLSEA Installed Capacity Registries | **0** | `dw.fact_capacity_period` (Unpopulated) |
| **`staging.stg_published_statistic`** | Central Bank / Regulatory Summary Compilations | **0** | `dw.fact_published_metric` (Unpopulated) |

---

## 5. Audit, Lineage & Quality Governance Schema (`audit`)

The audit schema tracks batch execution, row-level provenance, and data quality rejections:

| Audit Object Name | Object Type | Description | Row Count |
| :--- | :---: | :--- | :---: |
| **`audit.data_quality_issue`** | Base Table | Records isolated records failing quality assertions with rule codes and severity. | **926** |
| **`audit.record_lineage`** | Base Table | Row-level audit trail linking target fact IDs back to raw extraction batch and source line. | **272,526** |
| **`audit.etl_run`** | Base Table | Execution logs tracking ETL batch runs, status (`SUCCESS`), duration, and row counts. | **21** |
| **`audit.reconciliation_case`** | Base Table | Cross-source variance logs comparing disparate provider reports. | **0** |
| **`audit.data_quality_summary`** | View | Dynamic aggregation view summarizing issues by rule code, table, and severity. | N/A |
| **`audit.vw_data_quality_summary`** | View | Formatted analytical view reporting percentage distribution of quality issues. | N/A |

---

## 6. Analytical Marts Schema (`mart`)

The `mart` schema provides pre-aggregated materialized views and views optimized for sub-second executive reporting:

### 6.1 Materialized Views (5 MVs)

| Materialized View Name | Grain / Aggregation Level | Refresh Mechanism | Target Analytical Queries |
| :--- | :--- | :--- | :--- |
| **`mart.mv_daily_dispatch_by_source`** | `(date_key, energy_source_key)` | `REFRESH MATERIALIZED VIEW CONCURRENTLY` via unique index | Q01, Q02, Q04, Q08 |
| **`mart.mv_monthly_weather_summary`** | `(calendar_year, month_number, weather_location_key)` | `REFRESH MATERIALIZED VIEW CONCURRENTLY` via unique index | Q13, Q14, Q15 |
| **`mart.mv_annual_energy_mix`** | `(calendar_year, energy_source_key)` | Periodic batch refresh | Q01, Q21 |
| **`mart.mv_monthly_generation_summary`** | `(calendar_year, month_number, energy_source_key)` | Periodic batch refresh | Q01, Q07, Q19 |
| **`mart.mv_monthly_sales_summary`** | `(calendar_year, month_number, sector_key)` | Periodic batch refresh | Q09, Q10, Q11 |

### 6.2 Analytical Views (4 Views)
- `mart.vw_conflicting_source_metrics`: Compares generation reported across PUCSL vs CEB sources.
- `mart.vw_electricity_sales_summary`: Annual and sectoral billed units, revenue, and consumer account intensities.
- `mart.vw_generation_by_energy_source`: Technology share rankings.
- `mart.vw_historical_generation_trends`: Multi-year generation trajectory.

---

## 7. Stored Procedures, Functions & Triggers

### 7.1 ETL Stored Procedures (`etl` & `mart`)
- `etl.sp_start_etl_run(source_code, batch_name, OUT run_id)`
- `etl.sp_finalize_etl_run(run_id, status_code, message)`
- `etl.sp_validate_staged_dispatch(run_id)`
- `etl.sp_validate_staged_sales(run_id)`
- `etl.sp_validate_staged_generation(run_id)`
- `etl.sp_validate_staged_weather(run_id)`
- `etl.sp_load_dispatch_interval(run_id)`
- `etl.sp_load_electricity_sales(run_id)`
- `etl.sp_load_generation_period(run_id)`
- `etl.sp_load_weather_daily(run_id)`
- `etl.sp_load_approved_plant_aliases()`
- `etl.sp_record_reconciliation_case(...)`
- `etl.sp_refresh_mart_views()`
- `mart.sp_refresh_analytical_marts()`: Concurrently refreshes `mv_daily_dispatch_by_source` and `mv_monthly_weather_summary` without write locks.

### 7.2 Transformation Functions (`etl`)
- `etl.fn_normalize_interval_15min(time_val)`: Normalizes arbitrary timestamps to slot indices 1–96.
- `etl.fn_convert_unit(amount, from_unit, to_unit)`: Precise physical conversion (MW $\rightarrow$ kW, MJ $\rightarrow$ PSH).
- `etl.fn_calculate_yoy_change(curr_val, prev_val)`: Standardized growth calculation.
- `etl.fn_validate_reporting_period(start_dt, end_dt, period_type)`: Temporal consistency assertion.
- `etl.fn_get_dq_summary(run_id)`: Formats run-specific quarantine statistics.

### 7.3 Integrity Triggers
- `audit.data_quality_issue` $\rightarrow$ `trg_audit_dq_issue_resolution` (Enforces resolution timestamps).
- `ref.*` tables $\rightarrow$ `trg_ref_*_updated_at` & `trg_validate_*_evidence` (Audit provenance on reference data additions).

---

## 8. Summary Comparison: Documented vs Actual Physical Schema

| Feature / Concept | Previous / Incorrect Claim | Verified Actual Implementation |
| :--- | :--- | :--- |
| **Staging Schema** | `stg` | **`staging`** |
| **Interval Dimension** | `dw.dim_time_of_day` | **`dw.dim_interval`** |
| **Sector Dimension** | `dw.dim_tariff_sector` | **`dw.dim_consumption_sector`** |
| **Customer Class Dimension** | `dw.dim_customer_class` | **Does not exist as separate table**; modeled via `tariff_group` in `dw.dim_consumption_sector` |
| **Daily Generation Fact** | `dw.fact_daily_generation` | **`dw.fact_generation_period`** |
| **Total Dimensions** | 8 dimensions claimed | **9 Conformed Dimensions** (including `dim_region`, `dim_source_system`) |
| **Total Fact Tables** | 4 facts claimed | **6 Fact Tables** (4 populated, 2 implemented unpopulated) |
| **Dispatch Fact Partitioning** | Monthly range partitions | **Yearly range partitions** (`fact_dispatch_interval_y2020` to `y2026` + `default`) |
| **Quarantine Table** | `audit.quarantine_records` | **`audit.data_quality_issue`** (926 records) |
| **Lineage Table** | Claimed in text | **`audit.record_lineage`** (272,526 records) |
| **ETL Log Table** | `audit.etl_batch_log` | **`audit.etl_run`** (21 runs) |

