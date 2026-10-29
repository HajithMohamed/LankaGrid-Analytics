# Dimensional Business-Process Matrix & Fact-Grain Specification

## 1. Enterprise Dimensional Bus Matrix

The Kimball Bus Matrix maps the six analytical business processes in schema `dw` ([006_facts_generation_and_dispatch.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/006_facts_generation_and_dispatch.sql)–[008_facts_weather_and_published.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/008_facts_weather_and_published.sql)) against the nine shared conformed dimensions ([005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)):

| Business Process | Fact Table | `dim_date` | `dim_interval` | `dim_power_plant` | `dim_energy_source` | `dim_region` | `dim_consumption_sector` | `dim_weather_location` | `dim_metric` | `dim_source_system` |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1. Sub-Daily Grid Dispatch & Demand | `dw.fact_dispatch_interval` | **X** | **X** | **X** | **X** | *(via plant)* | — | — | **X** | **X** |
| 2. Periodic Electricity Generation | `dw.fact_generation_period` | **X** *(start/end)* | — | **X** | **X** | *(via plant)* | — | — | **X** | **X** |
| 3. Plant & Category Installed Capacity | `dw.fact_capacity_period` | **X** *(start/end)* | — | **X** | **X** | *(via plant)* | — | — | **X** | **X** |
| 4. Billed Electricity Sales & Revenue | `dw.fact_electricity_sales` | **X** *(start/end)* | — | — | — | **X** | **X** | — | **X** | **X** |
| 5. Daily Meteorological Resource | `dw.fact_weather_daily` | **X** | — | — | — | *(via loc)* | — | **X** | **X** | **X** |
| 6. Official Published Benchmarks & Revisions | `dw.fact_published_metric` | **X** *(start/end)* | — | — | *(opt)* | *(opt)* | *(opt)* | — | **X** | **X** |

---

## 2. Detailed Fact Table Specifications & Grain Contracts

### Fact A: `dw.fact_dispatch_interval`
- **Business Event / Measurement**: Sub-daily operational active power dispatch or system demand reading recorded by CEB System Control Centre / PUCSL.
- **Exact Grain**: One verified dispatch or demand observation for a specific generation/reporting entity (`plant_key`), calendar date (`date_key`), sub-daily interval (`interval_key`), canonical metric (`metric_key`), source system (`source_system_key`), and dataset revision (`dataset_revision`).
- **Dimensions**: `dim_date`, `dim_interval`, `dim_power_plant`, `dim_energy_source`, `dim_metric`, `dim_source_system` (+ `ref.unit` for `reported_unit_code`).
- **Numeric Measures**: `active_power_mw NUMERIC(12,4)`, `derived_energy_mwh NUMERIC(12,4)` (populated only when reported or physics-derived via $MWh = MW \times \frac{\Delta t}{60}$), `reported_value NUMERIC(14,4)`.
- **Original Source & Expected Fields**: PUCSL Daily Generation & Dispatch Reports (`15-minute` load/dispatch tables: timestamp `00:00`–`23:45` SLST, thermal/hydro/wind/solar/demand `MW`).
- **Units**: Canonical `MW` (`active_power_mw`) and `MWh` (`derived_energy_mwh`); original unit preserved in `reported_unit_code`.
- **Aggregation Rules**:
  - `active_power_mw`: Additive across distinct simultaneous plants within the same `(date_key, interval_key, is_current_revision = TRUE)`; **non-additive (`AVG`/`MAX`/`MIN` only) across time intervals**.
  - `derived_energy_mwh`: Additive across both distinct plants and sequential non-overlapping intervals within a single revision.
- **Update / Revision Strategy**: Immutable per `dataset_revision`; revised releases insert a new revision (`v2`) and flip prior revisions' `is_current_revision = FALSE`.
- **Data-Quality Constraints**: `ck_fact_dispatch_power_nonneg` ($MW \ge 0$ unless `PUMPING_LOAD`), `ck_fact_dispatch_missing_is_null`, `ck_fact_dispatch_derived_energy_physics`, `uq_fact_dispatch_interval_grain`.
- **Historical Coverage**: Designed for multi-year sub-daily series (`2023`–`2026` yearly range partitions + `default`), primary target year `2024`.
- **Supported Business Questions**: Night-peak vs. day-trough load curves, TOU block (`PEAK`/`DAY`/`OFF_PEAK`) dispatch share, hydro peaking response, renewable ramp rates.

---

### Fact B: `dw.fact_generation_period`
- **Business Event / Measurement**: Integrated electrical energy generated over an explicit reporting period (`DAILY`, `MONTHLY`, or `ANNUAL`).
- **Exact Grain**: One periodic generation record per generation entity (`plant_key`), metric boundary (`metric_key`: Gross vs. Net), reporting period type (`period_type_code`), start/end dates (`period_start_date_key`, `period_end_date_key`), source system (`source_system_key`), and revision (`dataset_revision`).
- **Dimensions**: `dim_power_plant`, `dim_energy_source`, `dim_metric`, `dim_source_system`, `dim_date` (role-playing `period_start_date_key`, `period_end_date_key`), `ref.reporting_period_type`.
- **Numeric Measures**: `generation_mwh NUMERIC(14,4)`, `peak_generation_mw NUMERIC(12,4)`, `reported_source_value NUMERIC(16,4)`.
- **Original Source & Expected Fields**: PUCSL Daily Generation Reports (station daily `MWh` & station peak `MW`); CEB Statistical Digest (monthly and annual generation `GWh` by station/fuel category).
- **Units**: Normalized to `MWh`; source `MWh` or `GWh` preserved in `reported_unit_code`.
- **Aggregation Rules**:
  - `generation_mwh`: Fully additive across non-overlapping periods and non-overlapping entities **strictly within the same `(period_type_code, generation_boundary, source_system_key)` and `is_current_revision = TRUE`**.
  - `peak_generation_mw`: `MAX` only; never summed across time.
- **Update / Revision Strategy**: Handled idempotently by `etl.sp_load_generation_period` (`ON CONFLICT ON CONSTRAINT uq_fact_generation_period_grain DO UPDATE` + automatic `is_current_revision` superseding).
- **Data-Quality Constraints**: `ck_fact_gen_period_daily_exact` (`DAILY` requires `start = end`), `ck_fact_gen_period_non_negative`, `ck_fact_gen_period_missing_null`.
- **Historical Coverage**: `2019`–`2026` supported via `dim_date` (primary analytical focus `2023`–`2024`).
- **Supported Business Questions**: Daily/monthly/annual fuel mix, renewable vs. thermal dependency, Mahaweli vs. Laxapana hydro complex output, YoY generation growth.

---

### Fact C: `dw.fact_capacity_period`
- **Business Event / Measurement**: Official installed nameplate and dependable capacity reported for a plant or generation category over an effective reporting period.
- **Exact Grain**: One capacity record per `plant_key`, `metric_key`, `period_type_code`, `effective_start_date_key`, `effective_end_date_key`, `source_system_key`, and `dataset_revision`.
- **Dimensions**: `dim_power_plant`, `dim_energy_source`, `dim_metric`, `dim_source_system`, `dim_date` (effective start/end), `ref.reporting_period_type`.
- **Numeric Measures**: `installed_capacity_mw NUMERIC(12,4)`, `dependable_capacity_mw NUMERIC(12,4)`, `unit_count SMALLINT`, `reported_source_value NUMERIC(14,4)`.
- **Original Source & Expected Fields**: CEB Statistical Digest (Installed Capacity `MW`, Effective Capacity `MW`, Number of Units); PUCSL Plant Capacity tables.
- **Units**: `MW` and `COUNT`.
- **Aggregation Rules**: **Semi-additive**: summable across distinct non-overlapping plants at a single effective period; **NEVER summable across time periods**. Capacity factor is intentionally omitted from stored columns and may only be derived when generation period hours and capacity boundary are verified compatible.
- **Update / Revision Strategy**: Versioned per effective period and `dataset_revision` with `is_current_revision`.
- **Data-Quality Constraints**: `ck_fact_capacity_nonneg`, `ck_fact_capacity_dependable_le_installed` (`dependable_capacity_mw <= installed_capacity_mw`).
- **Historical Coverage**: `2019`–`2026`.
- **Supported Business Questions**: Installed capacity mix evolution, CEB vs. IPP/SPP capacity share, derating gaps between nameplate and dependable `MW`.

---

### Fact D: `dw.fact_electricity_sales`
- **Business Event / Measurement**: Billed end-consumer electricity consumption, consumer account counts, and optional tariff revenue.
- **Exact Grain**: One sales summary per geographic scope (`region_key`), consumer tariff sector (`sector_key`), `metric_key`, `period_type_code`, `period_start_date_key`, `period_end_date_key`, `source_system_key`, and `dataset_revision`.
- **Dimensions**: `dim_region`, `dim_consumption_sector`, `dim_metric`, `dim_source_system`, `dim_date` (start/end), `ref.reporting_period_type`.
- **Numeric Measures**: `energy_sold_mwh NUMERIC(14,4)`, `consumer_account_count BIGINT`, `revenue_lkr NUMERIC(18,2)`, `reported_energy_value NUMERIC(16,4)`.
- **Original Source & Expected Fields**: CEB Statistical Digest (Sales by Tariff Category `GWh`, Consumer Accounts, Revenue `LKR Mn`, Provincial / Distribution Division `DD1`–`DD4` sales). When a source publishes national tariff sales without provincial breakdown, `region_key` maps to National `LK`; when provincial totals lack tariff breakdown, `sector_key` maps to `ALL_SECTORS`.
- **Units**: `MWh` (converted from `GWh`), `COUNT`, `LKR` (converted from `MLKR`).
- **Aggregation Rules**: `energy_sold_mwh` and `revenue_lkr` are additive across non-overlapping periods and non-overlapping sectors/regions (`is_aggregate_bucket = FALSE`); `consumer_account_count` is **semi-additive** (never summed across months/years).
- **Update / Revision Strategy**: Versioned via `dataset_revision` and `is_current_revision`.
- **Data-Quality Constraints**: `ck_fact_sales_nonneg`, `ck_fact_sales_dates`, `ck_fact_sales_missing_null`.
- **Historical Coverage**: Monthly and annual series (`2019`–`2026`).
- **Supported Business Questions**: Sectoral electricity consumption share (Domestic vs. Industrial vs. Hotel), provincial/CEB division demand concentration, implied T&D losses when compared against compatible net generation.

---

### Fact E: `dw.fact_weather_daily`
- **Business Event / Measurement**: Daily meteorological observation for a verified Sri Lankan energy-zone sampling coordinate.
- **Exact Grain**: One meteorological parameter (`metric_key`) per verified sampling location (`weather_location_key`), calendar date (`date_key`), `source_system_key`, and `dataset_revision`.
- **Dimensions**: `dim_date`, `dim_weather_location` (linked to `dim_region`), `dim_metric`, `dim_source_system`.
- **Numeric Measures**: `standardized_value NUMERIC(14,5)`, `original_reported_value NUMERIC(14,5)`.
- **Original Source & Expected Fields**: NASA POWER Daily Point API (`ALLSKY_SFC_SW_DWN`, `T2M`, `PRECTOTCORR`, `WS10M`, `RH2M` plus sentinel `-999.0`).
- **Units**: `MJ/m2/day`, `C`, `mm/day`, `m/s`, `PCT`.
- **Aggregation Rules**: Parameter-specific via `dim_metric.aggregation_behavior` (`SUM` across time for `PRECTOTCORR`; `AVG` for `T2M`, `WS10M`, `RH2M`, `ALLSKY_SFC_SW_DWN`; **never summed across weather variables**).
- **Update / Revision Strategy**: Versioned per NASA POWER reprocessing release (`dataset_revision`).
- **Data-Quality Constraints**: `ck_fact_weather_missing_null` (`is_missing = TRUE` requires `standardized_value IS NULL`, preserving `-999.0` in `missing_value_code`), `ck_fact_weather_physical_bounds` (non-negative irradiance/rain/wind, `0..100%` humidity, `-20..60 C` air temperature).
- **Historical Coverage**: Daily (`2019`–`2026`, primary year `2024`).
- **Supported Business Questions**: Southwest vs. Northeast monsoon rainfall vs. hydro generation, Mannar wind speed vs. wind dispatch, Hambantota solar irradiance vs. utility solar output.

---

### Fact F: `dw.fact_published_metric`
- **Business Event / Measurement**: Officially published headline/aggregate statistics retained for multi-source reconciliation, revision tracking, and non-additive indicators (e.g., published T&D loss `%`, system load factor `%`).
- **Exact Grain**: One published aggregate value per `metric_key`, `period_type_code`, `period_start_date_key`, `period_end_date_key`, optional `region_key`, optional `energy_source_key`, optional `sector_key`, `source_system_key`, and `dataset_revision` (enforced via PostgreSQL 18 `UNIQUE NULLS NOT DISTINCT`).
- **Dimensions**: `dim_metric`, `dim_date`, `dim_source_system`, optional `dim_region`, `dim_energy_source`, `dim_consumption_sector`.
- **Numeric Measures**: `standardized_value NUMERIC(18,4)`, `published_value NUMERIC(18,4)`.
- **Original Source & Expected Fields**: Summary tables in CEB Statistical Digests and PUCSL annual/monthly regulatory reports.
- **Units**: Preserved in `published_unit_code` and normalized in `standardized_unit_code`.
- **Aggregation Rules**: **STRICT NON-DOUBLE-COUNTING RULE**: Guarded by `is_standalone_published_aggregate = TRUE`. **Never union or sum `dw.fact_published_metric` together with `dw.fact_dispatch_interval`, `dw.fact_generation_period`, or `dw.fact_electricity_sales`**, as doing so double-counts the underlying electricity.
- **Supported Business Questions**: CEB vs. PUCSL published figure reconciliation, provisional-to-audited revision variance, historical headline T&D loss trends.

---

## 3. Summary Matrix: Which Facts Can and Cannot Be Summed

| Combination / Operation | Permitted? | Physical / Analytical Reason |
|---|:---:|---|
| Sum `fact_generation_period.generation_mwh` across plants for one `DAILY` date (`is_current_revision = TRUE`, `GROSS`) | **YES** | Homogeneous `MWh` energy grain, single boundary, non-overlapping plants (excluding `AGG_*` if individual plants are included). |
| Sum `DAILY` + `MONTHLY` + `ANNUAL` rows in `fact_generation_period` | **NO** | Triple-counts the same electricity across nested reporting granularities. |
| Sum `v1` + `v2` revisions of the same period | **NO** | Double-counts superseded revisions; always filter `is_current_revision = TRUE`. |
| Sum `GROSS` + `NET` generation rows | **NO** | Physically incompatible generator-terminal vs. grid-sent-out boundaries. |
| Sum `fact_dispatch_interval.active_power_mw` across 96 daily intervals | **NO** | Summing instantaneous `MW` over 96 intervals inflates energy by $4\times$; integrate via $\sum (\text{MW} \times 0.25\text{ h}) = \text{MWh}$. |
| Sum `fact_capacity_period.installed_capacity_mw` across 12 months | **NO** | Capacity is a semi-additive stock measure, not a flow measure. |
| Sum `fact_published_metric` with `fact_generation_period` or `fact_dispatch_interval` | **NO** | `fact_published_metric` stores headline aggregates already summarizing plant/interval operations. |
