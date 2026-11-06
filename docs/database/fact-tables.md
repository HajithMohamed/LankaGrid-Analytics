# Kimball Fact Constellation — Fact Tables Specification

## Overview

The **GridLens** data warehouse implements a Kimball Fact Constellation schema to model the multi-dimensional physical, operational, commercial, and meteorological realities of the National Electricity Grid of Sri Lanka. 

Rather than forcing disparate business processes into a single monolithic structure, GridLens models **six dedicated fact tables** sharing conformed dimensions. Each fact table models a distinct business process at its atomic physical grain.

---

## Fact Tables Summary Matrix

| Table Name | Schema | Grain | Additivity | Source System | Current Warehouse Rows |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `dw.fact_dispatch_interval` | `dw` | 15-minute interval per power plant | Semi-additive ($MW$) / Additive ($MWh$) | PUCSL Sub-Daily Dispatch Curves | **107,115** (March 2024 partition) |
| `dw.fact_generation_period` | `dw` | Periodic gross/net generation per station/fuel | Fully additive ($MWh$) | CEB Statistical Digest / PUCSL Daily Reports | Structured for periodic loads |
| `dw.fact_capacity_period` | `dw` | Rated nameplate and dependable capacity per station per period | Semi-additive ($MW$ over time) | CEB Long Term Generation Expansion Plans | Structured for periodic loads |
| `dw.fact_electricity_sales` | `dw` | Annual / monthly billed sales per province per tariff class | Additive ($MWh$ units, $LKR$ revenue, accounts) | CEB Statistical Digest (Sales & Accounts) | **49** (2020–2024 audited history) |
| `dw.fact_weather_daily` | `dw` | Daily meteorological observations per grid node | Semi-additive / intensive physical rates | NASA POWER API (6 Grid Nodes) | **21,924** (2020–2024 daily history) |
| `dw.fact_published_metric` | `dw` | Periodic national benchmark KPI | Non-additive / intensive rates and percentages | CEB Audited Annual Reports & PUCSL Reviews | Structured for periodic loads |

---

## 1. `dw.fact_dispatch_interval`

### Business Purpose
Captures high-resolution SCADA telemetry and operational dispatch instructions across Sri Lanka's generation fleet at 15-minute intervals. Enables deep analysis of diurnal load curves, unit ramp rates, spinning reserves, merit-order dispatch adherence, and renewable intermittency.

### Fact Grain
**One row per 15-minute interval per dispatchable power station.**

### Primary & Foreign Keys
- **Primary Key:** Composite `(dispatch_fact_id, date_key)` (enforces declarative PostgreSQL range partitioning by year).
- **Foreign Keys:**
  - `date_key` &rarr; `dw.dim_date(date_key)`
  - `interval_key` &rarr; `dw.dim_interval(interval_key)`
  - `plant_key` &rarr; `dw.dim_power_plant(plant_key)`
  - `energy_source_key` &rarr; `dw.dim_energy_source(energy_source_key)`
  - `metric_key` &rarr; `dw.dim_metric(metric_key)`
  - `source_system_key` &rarr; `dw.dim_source_system(source_system_key)`
  - `source_document_id` &rarr; `raw.source_document(source_document_id)`
  - `etl_run_id` &rarr; `audit.etl_run(etl_run_id)`

### Measures & Additivity
- `active_power_mw` (`NUMERIC(12,4)`): Instantaneous power generation rate in Megawatts. **Semi-additive:** Cannot be summed across time; must be averaged over time or evaluated at specific time slices. Can be summed across plants at a single time slice to obtain total grid instantaneous demand.
- `derived_energy_mwh` (`NUMERIC(12,4)`): Integrated energy output over the 15-minute slot ($\text{MWh} = \text{MW} \times 0.25\text{ hours}$). **Fully additive:** Can be summed across both plants and time horizons.
- `reported_value` (`NUMERIC(14,4)`): Original numeric observation reported in source workbook.

### Declarative Range Partitioning
The table is partitioned by `RANGE (date_key)` by calendar year:
- `dw.fact_dispatch_interval_y2020` (`20200101` to `20210101`)
- `dw.fact_dispatch_interval_y2021` (`20210101` to `20220101`)
- `dw.fact_dispatch_interval_y2022` (`20220101` to `20230101`)
- `dw.fact_dispatch_interval_y2023` (`20230101` to `20240101`)
- `dw.fact_dispatch_interval_y2024` (`20240101` to `20250101`) — currently populated with **107,115** validated telemetry records
- `dw.fact_dispatch_interval_y2025` (`20250101` to `20260101`)
- `dw.fact_dispatch_interval_y2026` (`20260101` to `20270101`)
- `dw.fact_dispatch_interval_default`

---

## 2. `dw.fact_generation_period`

### Business Purpose
Records official periodic energy generation (gross generation, net generation sent out, auxiliary plant consumption) reported at monthly, quarterly, or annual reconciliation intervals.

### Fact Grain
**One row per reporting period per power plant per fuel category.**

### Primary & Foreign Keys
- **Primary Key:** `generation_fact_id` (`BIGINT GENERATED ALWAYS AS IDENTITY`).
- **Foreign Keys:**
  - `period_start_date_key` &rarr; `dw.dim_date(date_key)`
  - `period_end_date_key` &rarr; `dw.dim_date(date_key)`
  - `plant_key` &rarr; `dw.dim_power_plant(plant_key)`
  - `energy_source_key` &rarr; `dw.dim_energy_source(energy_source_key)`
  - `metric_key` &rarr; `dw.dim_metric(metric_key)`
  - `source_system_key` &rarr; `dw.dim_source_system(source_system_key)`

### Measures & Additivity
- `gross_generation_mwh` (`NUMERIC(14,4)`): Total electrical energy produced at generator terminals. **Fully additive.**
- `net_generation_mwh` (`NUMERIC(14,4)`): Electrical energy injected into the high-voltage transmission grid. **Fully additive.**
- `auxiliary_energy_mwh` (`NUMERIC(12,4)`): Internal parasitic consumption of power plant equipment. **Fully additive.**

---

## 3. `dw.fact_capacity_period`

### Business Purpose
Tracks installed nameplate capacity, dependable capacity, seasonal hydro capability deratings, and scheduled/forced outage allocations across the national generation fleet.

### Fact Grain
**One row per effective reporting period per power plant / category.**

### Primary & Foreign Keys
- **Primary Key:** `capacity_fact_id` (`BIGINT GENERATED ALWAYS AS IDENTITY`).
- **Foreign Keys:**
  - `plant_key` &rarr; `dw.dim_power_plant(plant_key)`
  - `energy_source_key` &rarr; `dw.dim_energy_source(energy_source_key)`
  - `metric_key` &rarr; `dw.dim_metric(metric_key)`
  - `source_system_key` &rarr; `dw.dim_source_system(source_system_key)`
  - `effective_start_date_key` &rarr; `dw.dim_date(date_key)`
  - `effective_end_date_key` &rarr; `dw.dim_date(date_key)`

### Measures & Additivity
- `installed_capacity_mw` (`NUMERIC(12,4)`): Total manufacturer-rated nameplate capability in MW. **Semi-additive:** Additive across plants at a given point in time; never summed across time.
- `dependable_capacity_mw` (`NUMERIC(12,4)`): Realizable capacity under prevailing hydrological and thermal ambient conditions. **Semi-additive.**
- `unit_count` (`SMALLINT`): Number of physical generating units.

---

## 4. `dw.fact_electricity_sales`

### Business Purpose
Maintains audited commercial retail consumption, billing revenue, customer counts, and average effective tariffs across provincial administration boundaries and consumer tariff classes.

### Fact Grain
**One row per reporting period per geographic region per tariff consumption sector.**

### Primary & Foreign Keys
- **Primary Key:** `sales_fact_id` (`BIGINT GENERATED ALWAYS AS IDENTITY`).
- **Foreign Keys:**
  - `region_key` &rarr; `dw.dim_region(region_key)`
  - `sector_key` &rarr; `dw.dim_consumption_sector(sector_key)`
  - `metric_key` &rarr; `dw.dim_metric(metric_key)`
  - `source_system_key` &rarr; `dw.dim_source_system(source_system_key)`
  - `period_start_date_key` &rarr; `dw.dim_date(date_key)`
  - `period_end_date_key` &rarr; `dw.dim_date(date_key)`

### Measures & Additivity
- `energy_sold_mwh` (`NUMERIC(14,4)`): Total metered energy sold to retail end consumers. **Fully additive.**
- `consumer_account_count` (`BIGINT`): Active registered customer utility accounts. **Semi-additive across time, additive across sectors.**
- `revenue_lkr` (`NUMERIC(18,2)`): Total billed financial revenue in Sri Lankan Rupees. **Fully additive.**

### Verified History
Contains **49** audited rows spanning the 5-year historical horizon (2020–2024) extracted directly from official CEB Statistical Digest accounts.

---

## 5. `dw.fact_weather_daily`

### Business Purpose
Correlates meteorological variables (solar irradiance, rainfall, ambient temperature, wind speeds) with electricity generation and demand across 6 strategic energy node locations in Sri Lanka.

### Fact Grain
**One row per calendar day per meteorological node location per weather variable.**

### Primary & Foreign Keys
- **Primary Key:** `weather_fact_id` (`BIGINT GENERATED ALWAYS AS IDENTITY`).
- **Foreign Keys:**
  - `date_key` &rarr; `dw.dim_date(date_key)`
  - `weather_location_key` &rarr; `dw.dim_weather_location(weather_location_key)`
  - `metric_key` &rarr; `dw.dim_metric(metric_key)`
  - `source_system_key` &rarr; `dw.dim_source_system(source_system_key)`

### Measures & Additivity
- `standardized_value` (`NUMERIC(14,5)`): Standardized observation in canonical warehouse units ($kW\cdot h/m^2/day$ for irradiance, $^{\circ}C$ for temperature, $\%$ for humidity, $m/s$ for wind speed, $mm/day$ for precipitation).
- `original_reported_value` (`NUMERIC(14,5)`): Raw reported value before transformation.
- **Sentinel Rule:** Missing observations (`-999.0` in NASA POWER) are strictly preserved as `NULL` with `is_missing = TRUE` and `missing_value_code = 'NASA_FILL_VALUE_-999'` (never coerced to 0).

### Verified History
Contains **21,924** verified meteorological observations spanning 6 national grid energy nodes continuously across 2020 to 2024 retrieved from NASA POWER.

---

## 6. `dw.fact_published_metric`

### Business Purpose
Maintains audited national macroeconomic and grid reliability benchmark figures published annually or quarterly by CEB, PUCSL, and CBSL.

### Fact Grain
**One row per reporting period per published metric code per region.**

### Primary & Foreign Keys
- **Primary Key:** `published_metric_fact_id` (`BIGINT GENERATED ALWAYS AS IDENTITY`).
- **Foreign Keys:**
  - `period_start_date_key` &rarr; `dw.dim_date(date_key)`
  - `period_end_date_key` &rarr; `dw.dim_date(date_key)`
  - `metric_key` &rarr; `dw.dim_metric(metric_key)`
  - `region_key` &rarr; `dw.dim_region(region_key)`
  - `source_system_key` &rarr; `dw.dim_source_system(source_system_key)`

### Measures & Additivity
- `metric_value` (`NUMERIC(18,6)`): Reported scalar benchmark value (e.g., System Maximum Peak Demand MW, Transmission Loss %, Distribution Loss %).
- **Additivity:** Dependent on the specific metric; loss percentages and peak MW figures are non-additive intensive indicators.
