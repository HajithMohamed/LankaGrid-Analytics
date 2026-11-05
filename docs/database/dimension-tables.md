# Conformed Dimensions Specification

## Overview

The GridLens data warehouse implements **nine conformed dimensions** that provide standardized analytical filtering, slicing, dicing, and drill-down across all six fact tables in the Kimball Fact Constellation. 

Conformed dimensions ensure consistent definitions across business domains (Generation, Dispatch, Commercial Sales, and Weather Analytics) and eliminate duplicate attribute hierarchies.

---

## Conformed Dimensions Matrix

| Dimension Table | Surrogate Key | Natural / Business Key | Hierarchy Levels | SCD Policy | Referencing Facts |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `dim_date` | `date_id` (`INT`) | `full_date` (`DATE`) | Day &rarr; Month &rarr; Quarter &rarr; Year | Type 0 (Static Calendar) | All 6 Facts |
| `dim_time_of_day` | `time_id` (`INT`) | `time_of_day` (`TIME`) | 15-Min &rarr; Hour &rarr; TOU Band | Type 0 (Static Clock) | `fact_dispatch_interval` |
| `dim_power_plant` | `plant_id` (`INT`) | `plant_code` (`VARCHAR`) | Plant &rarr; Grid Substation &rarr; Province | Type 2 (History Tracking) | `fact_dispatch_interval`, `fact_generation_period`, `fact_capacity_period` |
| `dim_generation_unit` | `unit_id` (`INT`) | `unit_code` (`VARCHAR`) | Unit &rarr; Power Plant | Type 1 (Attribute Overwrite) | `fact_dispatch_interval`, `fact_capacity_period` |
| `dim_fuel_type` | `fuel_type_id` (`INT`) | `fuel_code` (`VARCHAR`) | Sub-category &rarr; Fuel Type &rarr; Major Category | Type 1 | `fact_dispatch_interval`, `fact_generation_period`, `fact_capacity_period` |
| `dim_grid_substation`| `grid_substation_id` (`INT`) | `substation_code` (`VARCHAR`)| Substation &rarr; District &rarr; Province | Type 1 | `fact_dispatch_interval`, `fact_weather_daily` |
| `dim_transmission_line`| `transmission_line_id` (`INT`)| `line_code` (`VARCHAR`) | Sending &rarr; Receiving Substation | Type 1 | Grid Topology Marts |
| `dim_tariff_customer_class`| `customer_class_id` (`INT`)| `class_code` (`VARCHAR`)| Customer Category &rarr; Tariff Block | Type 1 | `fact_electricity_sales` |
| `dim_administrative_area`| `area_id` (`INT`) | `area_code` (`VARCHAR`) | District &rarr; Province &rarr; CEB Division | Type 1 | `fact_electricity_sales` |

---

## 1. `dw.dim_date`

### Purpose
Master calendar conformed dimension supporting multi-year historical analysis, calendar hierarchies, seasonal monsoon periods, and Sri Lankan statutory holidays.

### Attributes
- `date_id` (`INTEGER`): Surrogate primary key formatted as integer `YYYYMMDD` (e.g. `20240315`).
- `full_date` (`DATE`): Natural calendar date.
- `day_of_week` (`SMALLINT`): 1 (Monday) to 7 (Sunday).
- `day_name` (`VARCHAR(10)`): Monday, Tuesday, etc.
- `day_of_month` (`SMALLINT`): 1 to 31.
- `day_of_year` (`SMALLINT`): 1 to 366.
- `week_of_year` (`SMALLINT`): ISO-8601 week number (1 to 53).
- `month_number` (`SMALLINT`): 1 to 12.
- `month_name` (`VARCHAR(10)`): January through December.
- `calendar_quarter` (`SMALLINT`): 1, 2, 3, or 4.
- `calendar_year` (`SMALLINT`): e.g. 2020 through 2026.
- `is_weekend` (`BOOLEAN`): True if Saturday or Sunday.
- `is_sri_lanka_holiday` (`BOOLEAN`): Official public/mercantile/bank holiday in Sri Lanka.
- `monsoon_season` (`VARCHAR(32)`): Sri Lanka climate regime:
  - *Northeast Monsoon* (December to February)
  - *First Inter-Monsoon* (March to April)
  - *Southwest Monsoon* (May to September)
  - *Second Inter-Monsoon* (October to November)

---

## 2. `dw.dim_time_of_day`

### Purpose
High-resolution diurnal time dimension modeling exactly 96 intervals of 15 minutes across the 24-hour cycle. Integrates CEB official Time-of-Use (TOU) tariff bands.

### Attributes
- `time_id` (`INTEGER`): Surrogate primary key `0` through `95` (or minutes from midnight `0000` to `2345`).
- `time_of_day` (`TIME`): Clock time `00:00:00` to `23:45:00`.
- `hour_24` (`SMALLINT`): 0 to 23.
- `minute_of_hour` (`SMALLINT`): 0, 15, 30, 45.
- `quarter_hour_slot` (`SMALLINT`): 1 to 96 sequential daily interval index.
- `time_of_use_band` (`VARCHAR(20)`):
  - **Day Peak**: 18:30 to 22:30 (highest tariff / highest operational stress)
  - **Day Off-Peak**: 05:30 to 18:30 (standard day load)
  - **Night Off-Peak**: 22:30 to 05:30 (minimum baseload demand)

---

## 3. `dw.dim_power_plant` (Slowly Changing Dimension Type 2)

### Purpose
Represents grid-connected generation facilities across hydro, thermal, solar, and wind sectors. Implements Kimball SCD Type 2 tracking to preserve historical accuracy when plant capacities are uprated or operational ownership transfers occur.

### Attributes
- `plant_id` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `plant_code` (`VARCHAR(32)`): Business key (e.g. `LAKVIJAYA`, `VICTORIA`, `KOTMALE`).
- `plant_name` (`VARCHAR(128)`): Official name plate.
- `primary_energy_source` (`VARCHAR(32)`): Major energy source.
- `grid_substation_id` (`INTEGER`): Foreign key to interconnecting substation.
- `installed_capacity_mw` (`NUMERIC(8,2)`): Total registered nameplate rating.
- `commissioning_year` (`SMALLINT`): Year entered commercial operation.
- `operator_name` (`VARCHAR(64)`): CEB Generation, IPP (Independent Power Producer), or SPP.
- `latitude` / `longitude` (`NUMERIC(9,6)`): Exact geographic coordinates.
- `effective_from` (`TIMESTAMPTZ`): SCD Type 2 validity start timestamp.
- `effective_to` (`TIMESTAMPTZ`): SCD Type 2 validity end timestamp (`NULL` for current).
- `is_current` (`BOOLEAN`): True if this row represents active plant state.

---

## 4. `dw.dim_generation_unit`

### Purpose
Captures individual turbine-generator units within multi-unit power complexes (e.g., Lakvijaya Units 1, 2, and 3; Victoria Units 1, 2, and 3).

### Attributes
- `unit_id` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `unit_code` (`VARCHAR(32)`): Unique unit identifier (e.g. `LAKVIJAYA_U1`).
- `plant_id` (`INTEGER`): Foreign key to parent power plant.
- `unit_number` (`SMALLINT`): Sequential unit number (1, 2, 3).
- `unit_nameplate_mw` (`NUMERIC(8,2)`): Unit-specific generation rating.
- `turbine_type` (`VARCHAR(64)`): Francis Hydro, Pelton, Steam Turbine, Gas Turbine, Combined Cycle.

---

## 5. `dw.dim_fuel_type`

### Purpose
Standardized taxonomy of generation primary and secondary fuels, calorific content, and greenhouse gas emission benchmarks.

### Attributes
- `fuel_type_id` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `fuel_code` (`VARCHAR(32)`): Business key (e.g. `COAL`, `MAJOR_HYDRO`, `HEAVY_FUEL_OIL`, `SOLAR`).
- `fuel_name` (`VARCHAR(64)`): Full descriptive name.
- `fuel_category` (`VARCHAR(32)`):
  - `Hydro` (Major Hydro, Mini Hydro)
  - `Thermal - Coal`
  - `Thermal - Oil` (Auto Diesel, Heavy Fuel Oil, Naphtha)
  - `Renewable - Non-Conventional` (Solar PV, Wind, Biomass/Dendro, Waste-to-Energy)
- `is_renewable` (`BOOLEAN`): Physical renewable status.
- `emission_factor_kg_co2_per_mwh` (`NUMERIC(8,2)`): Standardized IPCC carbon intensity benchmark.

---

## 6. `dw.dim_grid_substation`

### Purpose
High-voltage transmission grid nodes interconnecting generation and regional distribution networks.

### Attributes
- `grid_substation_id` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `substation_code` (`VARCHAR(32)`): Substation code (e.g. `KOTMALE_GS`, `BIYAGAMA_GS`).
- `substation_name` (`VARCHAR(128)`): Full substation name.
- `voltage_levels_kv` (`VARCHAR(32)`): Operating voltage (e.g. `220kV`, `132kV`, `33kV`).
- `province` (`VARCHAR(32)`): Administrative province.
- `latitude` / `longitude` (`NUMERIC(9,6)`): Coordinates (used for NASA POWER weather mapping).

---

## 7. `dw.dim_transmission_line`

### Purpose
Models high-voltage grid corridors (220 kV and 132 kV) interconnecting transmission grid substations.

### Attributes
- `transmission_line_id` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `line_code` (`VARCHAR(64)`): Standard corridor code (e.g. `TL-KOT-BIY-220`).
- `sending_substation_id` (`INTEGER`): Foreign key to origin node.
- `receiving_substation_id` (`INTEGER`): Foreign key to termination node.
- `voltage_kv` (`NUMERIC(6,2)`): Nominal voltage in kilovolts.
- `length_km` (`NUMERIC(7,2)`): Circuit route length.
- `thermal_rating_mva` (`NUMERIC(8,2)`): Maximum continuous thermal corridor capacity.

---

## 8. `dw.dim_tariff_customer_class`

### Purpose
Official CEB retail customer categories as gazetted by the Public Utilities Commission of Sri Lanka (PUCSL).

### Attributes
- `customer_class_id` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `class_code` (`VARCHAR(32)`): Business key (e.g. `DOMESTIC`, `RELIGIOUS`, `INDUSTRIAL`, `HOTEL`, `GENERAL_PURPOSE`, `GOVERNMENT`, `STREET_LIGHTING`).
- `class_name` (`VARCHAR(64)`): Full tariff category label.
- `tariff_category` (`VARCHAR(32)`): Low Voltage (LV), Medium Voltage (MV), or High Voltage (HV).
- `billing_basis` (`VARCHAR(32)`): Two-part tariff (Energy + Fixed Charge) or Maximum Demand.

---

## 9. `dw.dim_administrative_area`

### Purpose
Hierarchical geography covering Sri Lanka's 9 provinces, 25 administrative districts, and CEB Distribution Divisions (DD1, DD2, DD3, DD4, and LECO).

### Attributes
- `area_id` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `area_code` (`VARCHAR(32)`): Code (e.g. `WP-COL`, `CP-KAN`).
- `province_name` (`VARCHAR(32)`): Western, Central, Southern, Northern, Eastern, North Western, North Central, Uva, Sabaragamuwa.
- `district_name` (`VARCHAR(32)`): Colombo, Gampaha, Kalutara, Kandy, etc.
- `ceb_distribution_division` (`VARCHAR(16)`): Official utility jurisdiction (`DD1`, `DD2`, `DD3`, `DD4`, `LECO`).

