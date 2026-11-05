# Kimball Fact Constellation — Fact Tables Specification

## Overview

The **GridLens** data warehouse implements a Kimball Fact Constellation schema to model the multi-dimensional physical, operational, commercial, and meteorological realities of the National Electricity Grid of Sri Lanka. 

Rather than forcing disparate business processes into a single monolithic structure, GridLens models **six dedicated fact tables** sharing conformed dimensions. Each fact table models a distinct business process at its atomic physical grain.

---

## Fact Tables Summary Matrix

| Table Name | Schema | Grain | Additivity | Source System | Current Warehouse Rows |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `fact_dispatch_interval` | `dw` | 15-minute interval per power plant / generation unit | Semi-additive (MW power) / Additive (MWh energy) | PUCSL Sub-Daily Dispatch Curves | **107,115** (March 2024 partition) |
| `fact_generation_period` | `dw` | Periodic gross/net generation per station/fuel | Fully additive (MWh) | CEB Statistical Digest / PUCSL Daily Reports | Structured for periodic loads |
| `fact_capacity_period` | `dw` | Rated nameplate and peak availability per station per period | Semi-additive (MW over time) | CEB Long Term Generation Expansion Plans | Structured for periodic loads |
| `fact_electricity_sales` | `dw` | Annual / monthly billed sales per province per tariff class | Additive (MWh units, LKR revenue, accounts) | CEB Statistical Digest (Sales & Accounts) | **49** (2020–2024 audited history) |
| `fact_weather_daily` | `dw` | Daily meteorological observations per grid transmission node | Semi-additive / intensive physical rates | NASA POWER API (7 Grid Nodes) | **21,924** (2020–2024 daily history) |
| `fact_published_metric` | `dw` | Periodic macroeconomic and system-wide published KPI | Non-additive / intensive rates and percentages | CEB Audited Annual Reports & PUCSL Reviews | Structured for periodic loads |

---

## 1. `dw.fact_dispatch_interval`

### Business Purpose
Captures high-resolution SCADA telemetry and operational dispatch instructions across Sri Lanka's generation fleet at 15-minute intervals. Enables deep analysis of diurnal load curves, unit ramp rates, spinning reserves, merit-order dispatch adherence, and renewable intermittency.

### Fact Grain
**One row per 15-minute telemetry interval per generation unit or dispatchable power station.**

### Primary & Foreign Keys
- **Primary Key:** Composite `(dispatch_interval_id, interval_timestamp_utc)` (enforces declarative PostgreSQL partitioning).
- **Foreign Keys:**
  - `date_id` &rarr; `dw.dim_date(date_id)`
  - `time_id` &rarr; `dw.dim_time_of_day(time_id)`
  - `plant_id` &rarr; `dw.dim_power_plant(plant_id)`
  - `unit_id` &rarr; `dw.dim_generation_unit(unit_id)` (nullable for station-level aggregations)
  - `fuel_type_id` &rarr; `dw.dim_fuel_type(fuel_type_id)`
  - `grid_substation_id` &rarr; `dw.dim_grid_substation(grid_substation_id)`

### Measures & Additivity
- `active_power_mw` (`NUMERIC(10,3)`): Instantaneous power generation rate in Megawatts. **Semi-additive:** Cannot be summed across time; must be averaged over time or evaluated at specific time slices. Can be summed across plants at a single time slice to obtain total grid instantaneous demand.
- `dispatch_energy_mwh` (`NUMERIC(12,4)`): Integrated energy output over the 15-minute slot ($\text{MWh} = \text{MW} \times 0.25\text{ hours}$). **Fully additive:** Can be summed across both plants and time horizons.
- `unit_frequency_hz` (`NUMERIC(5,2)`): Grid frequency at interval. **Non-additive:** Intensive state variable.
- `spinning_reserve_mw` (`NUMERIC(10,3)`): Headroom capacity available within 10 minutes. **Semi-additive.**

### Declarative Range Partitioning
The table is partitioned by `RANGE (interval_timestamp_utc)` by calendar year:
- `dw.fact_dispatch_interval_y2020`
- `dw.fact_dispatch_interval_y2021`
- `dw.fact_dispatch_interval_y2022`
- `dw.fact_dispatch_interval_y2023`
- `dw.fact_dispatch_interval_y2024` (Currently populated with **107,115** validated telemetry records)
- `dw.fact_dispatch_interval_y2025`
- `dw.fact_dispatch_interval_y2026`
- `dw.fact_dispatch_interval_default`

---

## 2. `dw.fact_generation_period`

### Business Purpose
Records official periodic energy generation (gross generation, net generation sent out, auxiliary plant consumption) reported at monthly, quarterly, or annual reconciliation intervals.

### Fact Grain
**One row per reporting period per power plant per fuel category.**

### Primary & Foreign Keys
- **Primary Key:** `generation_period_id` (`BIGINT GENERATED ALWAYS AS IDENTITY`).
- **Foreign Keys:**
  - `date_id` &rarr; `dw.dim_date(date_id)`
  - `plant_id` &rarr; `dw.dim_power_plant(plant_id)`
  - `fuel_type_id` &rarr; `dw.dim_fuel_type(fuel_type_id)`

### Measures & Additivity
- `gross_generation_mwh` (`NUMERIC(14,4)`): Total electrical energy produced at generator terminals. **Fully additive.**
- `net_generation_mwh` (`NUMERIC(14,4)`): Electrical energy injected into the high-voltage transmission grid. **Fully additive.**
- `auxiliary_consumption_mwh` (`NUMERIC(12,4)`): Internal parasitic consumption of power plant equipment. **Fully additive.**
- `auxiliary_consumption_pct` (`NUMERIC(5,2)`): Calculated parasitic ratio ($\frac{\text{aux}}{\text{gross}} \times 100$). **Non-additive.**

---

## 3. `dw.fact_capacity_period`

### Business Purpose
Tracks installed nameplate capacity, dependable capacity, seasonal hydro capability deratings, and scheduled/forced outage allocations across the national generation fleet.

### Fact Grain
**One row per reporting period per generation unit / plant.**

### Primary & Foreign Keys
- **Primary Key:** `capacity_period_id` (`BIGINT GENERATED ALWAYS AS IDENTITY`).
- **Foreign Keys:**
  - `date_id` &rarr; `dw.dim_date(date_id)`
  - `plant_id` &rarr; `dw.dim_power_plant(plant_id)`
  - `unit_id` &rarr; `dw.dim_generation_unit(unit_id)`
  - `fuel_type_id` &rarr; `dw.dim_fuel_type(fuel_type_id)`

### Measures & Additivity
- `nameplate_capacity_mw` (`NUMERIC(10,3)`): Manufacturer rated physical capability. **Semi-additive:** Cannot be summed across time (a 300 MW plant in January and February is still a 300 MW plant, not 600 MW). Additive across plants at any given point in time.
- `dependable_capacity_mw` (`NUMERIC(10,3)`): Realizable capacity under ambient temperature and water head conditions. **Semi-additive.**
- `planned_outage_mw` (`NUMERIC(10,3)`): Capacity undergoing scheduled maintenance. **Semi-additive.**
- `forced_outage_mw` (`NUMERIC(10,3)`): Capacity unavailable due to unscheduled breakdowns. **Semi-additive.**

---

## 4. `dw.fact_electricity_sales`

### Business Purpose
Maintains audited commercial retail consumption, billing revenue, customer counts, and average effective tariffs across provincial administration boundaries and consumer tariff classes.

### Fact Grain
**One row per calendar year per administrative province / area per tariff customer class.**

### Primary & Foreign Keys
- **Primary Key:** `sales_id` (`BIGINT GENERATED ALWAYS AS IDENTITY`).
- **Foreign Keys:**
  - `date_id` &rarr; `dw.dim_date(date_id)`
  - `customer_class_id` &rarr; `dw.dim_tariff_customer_class(customer_class_id)`
  - `area_id` &rarr; `dw.dim_administrative_area(area_id)`

### Measures & Additivity
- `billed_units_mwh` (`NUMERIC(14,4)`): Total metered energy sold to retail end consumers. **Fully additive.**
- `billed_revenue_lkr` (`NUMERIC(16,2)`): Total billed financial revenue in Sri Lankan Rupees. **Fully additive.**
- `customer_count` (`INTEGER`): Active registered customer utility accounts. **Semi-additive across time, additive across customer classes.**
- `average_tariff_lkr_per_kwh` (`NUMERIC(8,2)`): Unit economic realization ($\frac{\text{Revenue LKR}}{\text{Billed kWh}}$). **Non-additive:** Must always be calculated from underlying additive totals.

### Verified History
Contains **49** audited rows spanning the 5-year historical horizon (2020–2024) extracted directly from official CEB Statistical Digest accounts.

---

## 5. `dw.fact_weather_daily`

### Business Purpose
Correlates macro weather variables (solar irradiance, rainfall, ambient temperature, wind speeds) with electricity generation and demand across seven strategic grid transmission node locations in Sri Lanka.

### Fact Grain
**One row per calendar day per grid transmission node location.**

### Primary & Foreign Keys
- **Primary Key:** `weather_daily_id` (`BIGINT GENERATED ALWAYS AS IDENTITY`).
- **Foreign Keys:**
  - `date_id` &rarr; `dw.dim_date(date_id)`
  - `grid_substation_id` &rarr; `dw.dim_grid_substation(grid_substation_id)`

### Measures & Additivity
- `solar_irradiance_all_sky_kwh_m2` (`NUMERIC(8,4)`): Daily all-sky surface solar insolation. Equivalent to Peak Sun Hours (PSH). **Non-additive across space, averaged over time.**
- `precipitation_mm` (`NUMERIC(8,2)`): Daily total liquid precipitation. **Fully additive over time for a given node.**
- `temp_max_c` / `temp_min_c` / `temp_avg_c` (`NUMERIC(5,2)`): Daily ambient temperatures in Celsius. **Non-additive intensive states.**
- `wind_speed_10m_mps` (`NUMERIC(6,2)`): Daily mean wind speed at 10-meter elevation in meters per second. **Non-additive.**

### Verified History
Contains **21,924** verified meteorological observations spanning all 7 national transmission grid nodes continuously across 2020 to 2024 retrieved from NASA POWER.

---

## 6. `dw.fact_published_metric`

### Business Purpose
Maintains audited national macroeconomic and grid reliability benchmark figures published annually or quarterly by CEB, PUCSL, and the Central Bank of Sri Lanka (CBSL).

### Fact Grain
**One row per reporting period per published metric code.**

### Primary & Foreign Keys
- **Primary Key:** `metric_fact_id` (`BIGINT GENERATED ALWAYS AS IDENTITY`).
- **Foreign Keys:**
  - `date_id` &rarr; `dw.dim_date(date_id)`
  - `metric_id` &rarr; `ref.published_metric_definition(metric_id)`

### Measures & Additivity
- `metric_value` (`NUMERIC(16,4)`): Reported scalar value (e.g., System Maximum Peak Demand MW, Transmission Loss %, Distribution Loss %, Per Capita Consumption kWh/person).
- **Additivity:** Dependent on the specific metric; loss percentages and peak MW figures are non-additive and must be treated as intensive performance indicators.

