# Conformed Dimensions Specification

## Overview

The GridLens data warehouse implements **nine conformed dimensions** in the `dw` schema, defined in `database/migrations/005_dimensions.sql` and seeded in `scripts/seed_reference.py`. These conformed dimensions provide standardized filtering, slicing, dicing, and multi-tier aggregation across all fact tables in the Kimball Fact Constellation.

Conformed dimensions ensure consistent definitions across business domains (Generation, Dispatch, Commercial Sales, and Meteorological Analytics) and eliminate duplicate attribute hierarchies.

---

## Conformed Dimensions Matrix

| Dimension Table | Surrogate Key | Natural / Business Key | Hierarchy Levels | SCD Policy | Referencing Facts |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `dw.dim_date` | `date_key` (`INT`) | `calendar_date` (`DATE`) | Date &rarr; Month &rarr; Quarter &rarr; Year | Type 0 (Static Calendar) | All Facts |
| `dw.dim_interval` | `interval_key` (`INT`) | `slot_number` (`SMALLINT`) | 15-Min Slot (1–96) &rarr; TOU Tariff Band | Type 0 (Static Intervals) | `fact_dispatch_interval` |
| `dw.dim_source_system` | `source_system_key` (`INT`) | `source_code` (`VARCHAR`) | System &rarr; Organization | Type 1 (Provenance) | All Facts |
| `dw.dim_energy_source` | `energy_source_key` (`INT`) | `source_code` (`VARCHAR`) | Source Code &rarr; Dispatch Tier &rarr; Primary Category | Type 1 | `fact_dispatch_interval`, `fact_generation_period`, `fact_capacity_period` |
| `dw.dim_region` | `region_key` (`INT`) | `region_code` (`VARCHAR`) | Province / District &rarr; Distribution Division &rarr; National | Type 1 | `fact_electricity_sales`, `fact_published_metric` |
| `dw.dim_consumption_sector` | `sector_key` (`INT`) | `sector_code` (`VARCHAR`) | Customer Sector &rarr; Voltage Level | Type 1 | `fact_electricity_sales` |
| `dw.dim_power_plant` | `power_plant_key` (`INT`) | `plant_code` (`VARCHAR`) | Power Station &rarr; Energy Source &rarr; Region | Type 2 (History Tracking) | `fact_dispatch_interval`, `fact_generation_period`, `fact_capacity_period` |
| `dw.dim_weather_location` | `weather_location_key` (`INT`) | `location_code` (`VARCHAR`) | Sampling Node &rarr; Energy Zone Type &rarr; Region | Type 1 | `fact_weather_daily` |
| `dw.dim_metric` | `metric_key` (`INT`) | `metric_code` (`VARCHAR`) | Metric Indicator &rarr; Business Domain &rarr; Measurement Class | Type 1 | `fact_published_metric` |

---

## 1. `dw.dim_date`

### Purpose
Master calendar conformed dimension supporting multi-year historical analysis (2020–2026), calendar hierarchies, seasonal monsoon periods, and Sri Lankan statutory holidays.

### Attributes
- `date_key` (`INTEGER`): Surrogate primary key formatted as integer `YYYYMMDD` (e.g., `20240315`).
- `calendar_date` (`DATE`): Natural calendar date.
- `calendar_year` (`SMALLINT`): Calendar year (2020 through 2026).
- `calendar_quarter` (`SMALLINT`): Calendar quarter (1 to 4).
- `calendar_month` (`SMALLINT`): Calendar month (1 to 12).
- `month_name` (`VARCHAR(20)`): January through December.
- `month_short_name` (`CHAR(3)`): Jan through Dec.
- `day_of_month` (`SMALLINT`): Day of the month (1 to 31).
- `day_of_year` (`SMALLINT`): Day of the year (1 to 366).
- `day_of_week` (`SMALLINT`): 1 (Monday) to 7 (Sunday).
- `day_name` (`VARCHAR(12)`): Monday through Sunday.
- `iso_week_number` (`SMALLINT`): ISO-8601 week number (1 to 53).
- `iso_year` (`SMALLINT`): ISO-8601 year.
- `is_weekend` (`BOOLEAN`): True if Saturday or Sunday.
- `is_statutory_holiday` (`BOOLEAN`): Official public, bank, or mercantile holiday in Sri Lanka.
- `monsoon_regime` (`VARCHAR(32)`): Sri Lanka climate regime:
  - *Northeast Monsoon* (December to February)
  - *First Inter-Monsoon* (March to April)
  - *Southwest Monsoon* (May to September)
  - *Second Inter-Monsoon* (October to November)

---

## 2. `dw.dim_interval`

### Purpose
High-resolution diurnal time interval dimension modeling exactly 96 intervals of 15 minutes across the 24-hour cycle. Integrates CEB official Time-of-Use (TOU) tariff bands.

### Attributes
- `interval_key` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `slot_number` (`SMALLINT`): Interval index from `1` (`00:00–00:15`) to `96` (`23:45–24:00`).
- `interval_start_time` (`TIME`): Starting clock time (e.g., `00:00:00`, `18:30:00`).
- `interval_end_time` (`TIME`): Ending clock time (e.g., `00:15:00`, `18:45:00`).
- `tou_bucket` (`VARCHAR(24)`): Official CEB tariff band:
  - **DAY_PEAK**: 18:30 to 22:30 (slots 75–90) — peak operational demand and highest tariff.
  - **DAY_OFF_PEAK**: 05:30 to 18:30 (slots 23–74) — standard diurnal baseload.
  - **NIGHT_OFF_PEAK**: 22:30 to 05:30 (slots 91–96 and 1–22) — nocturnal valley.
- `quarter_hour_label` (`VARCHAR(16)`): Formatted human label (e.g., `"18:30 - 18:45"`).

---

## 3. `dw.dim_source_system`

### Purpose
Authoritative registry of upstream electricity grid and meteorological data providers ensuring end-to-end data provenance.

### Attributes
- `source_system_key` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `source_code` (`VARCHAR(32)`): Unique natural business key (`CEB`, `PUCSL`, `NASA_POWER`).
- `source_name` (`VARCHAR(128)`): Full descriptive name of provider.
- `organization_name` (`VARCHAR(160)`): Governing entity.
- `official_url` (`TEXT`): Upstream official publication portal.
- `default_timezone` (`VARCHAR(64)`): Timezone (`Asia/Colombo` or `UTC+05:30`).
- `access_method` (`VARCHAR(32)`): Acquisition protocol (`PORTAL_PDF`, `REST_API_JSON`, `PORTAL_XLSX`).

---

## 4. `dw.dim_energy_source`

### Purpose
Standardized taxonomy of generation primary and secondary fuels, calorific content, and greenhouse gas emission benchmarks.

### Attributes
- `energy_source_key` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `source_code` (`VARCHAR(32)`): Unique code (e.g., `MAJOR_HYDRO`, `COAL`, `AUTO_DIESEL`, `SOLAR_PV`, `WIND_POWER`, `THERMAL_OIL`, `BIOMASS`).
- `source_name` (`VARCHAR(64)`): Full descriptive name.
- `primary_category` (`VARCHAR(32)`): `RENEWABLE` or `NON_RENEWABLE`.
- `dispatch_tier` (`VARCHAR(24)`): Operational dispatch regime:
  - `MUST_RUN`: Non-dispatchable renewables (Solar, Wind, Run-of-River Hydro).
  - `BASELOAD`: Low marginal-cost continuous thermal (Lakvijaya Coal).
  - `INTERMEDIATE`: Pondage and reservoir hydro (Victoria, Kotmale, Laxapana).
  - `PEAKING`: Fast-start thermal oil and gas turbines (Kelanitissa, Barge).
- `ipcc_carbon_intensity_g_co2_per_kwh` (`NUMERIC(8,2)`): Standardized IPCC emissions factor.

---

## 5. `dw.dim_region`

### Purpose
Hierarchical geography covering Sri Lanka's administrative provinces and official CEB Distribution Divisions (DD1, DD2, DD3, DD4, and LECO).

### Attributes
- `region_key` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `region_code` (`VARCHAR(16)`): ISO code or utility identifier (`LK`, `LK-1` through `LK-9`).
- `region_name` (`VARCHAR(64)`): Province name (Western, Central, Southern, Northern, Eastern, North Western, North Central, Uva, Sabaragamuwa).
- `region_type` (`VARCHAR(24)`): `NATIONAL`, `CEB_PROVINCE`, or `ADMIN_DISTRICT`.
- `distribution_division` (`VARCHAR(16)`): Official utility jurisdiction (`DD1`, `DD2`, `DD3`, `DD4`, `LECO`, `NATIONAL`).

---

## 6. `dw.dim_consumption_sector`

### Purpose
Official CEB retail customer categories as gazetted by the Public Utilities Commission of Sri Lanka (PUCSL).

### Attributes
- `sector_key` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `sector_code` (`VARCHAR(32)`): Business key (e.g., `DOMESTIC`, `RELIGIOUS`, `INDUSTRIAL`, `HOTEL`, `GENERAL_PURPOSE`, `GOVERNMENT`, `STREET_LIGHTING`, `BULK_SUPPLY`).
- `sector_name` (`VARCHAR(64)`): Full tariff category label.
- `voltage_level` (`VARCHAR(24)`): `LOW_VOLTAGE`, `MEDIUM_VOLTAGE`, or `HIGH_VOLTAGE`.
- `is_subsidized` (`BOOLEAN`): True for lifeline domestic and religious categories.

---

## 7. `dw.dim_power_plant` (Slowly Changing Dimension Type 2)

### Purpose
Represents grid-connected generation facilities across hydro, thermal, solar, and wind sectors. Implements Kimball SCD Type 2 tracking to preserve historical accuracy when plant capacities are uprated or operational ownership transfers occur.

### Attributes
- `power_plant_key` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `plant_code` (`VARCHAR(48)`): Business key (e.g., `LAKVIJAYA_COAL`, `VICTORIA_HYDRO`, `MANNAR_WIND`).
- `plant_name` (`VARCHAR(128)`): Official facility name plate.
- `operator_type` (`VARCHAR(24)`): `CEB`, `IPP`, `SPP`, or `COMMUNITY`.
- `installed_capacity_mw` (`NUMERIC(8,2)`): Total registered nameplate active power rating in MW.
- `grid_connection_voltage_kv` (`NUMERIC(6,2)`): Interconnection voltage (220 kV, 132 kV, 33 kV).
- `latitude_deg` / `longitude_deg` (`NUMERIC(8,5)`): Exact geographic coordinates bounded to Sri Lanka.
- `effective_from` (`DATE`): SCD Type 2 validity start date.
- `effective_to` (`DATE`): SCD Type 2 validity end date (`NULL` for current active record).
- `is_current` (`BOOLEAN`): True if this row represents the active plant configuration.

---

## 8. `dw.dim_weather_location`

### Purpose
Verified Sri Lanka meteorological grid sampling points bounded strictly to island coordinates, representing key generation catchment areas and solar/wind hubs.

### Attributes
- `weather_location_key` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `location_code` (`VARCHAR(48)`): Business code:
  - `LOC_VICTORIA_CATCHMENT` (Victoria / Mahaweli Hydro Catchment)
  - `LOC_LAXAPANA_CATCHMENT` (Castlereagh / Laxapana Hydro Catchment)
  - `LOC_MANNAR_WIND` (Mannar Island Wind Corridor)
  - `LOC_PUTTALAM_COAL` (Norochcholai / Puttalam Coastal Corridor)
  - `LOC_HAMBANTOTA_SOLAR` (Hambantota Dry-Zone Solar Hub)
  - `LOC_COLOMBO_LOAD` (Colombo / Kelanitissa Load & Thermal Hub)
- `location_name` (`VARCHAR(128)`): Full location label.
- `energy_zone_type` (`VARCHAR(32)`): `HYDRO_CATCHMENT`, `WIND_CORRIDOR`, `SOLAR_HUB`, `THERMAL_HUB`, `LOAD_CENTER`.
- `region_key` (`INTEGER`): Foreign key to `dw.dim_region`.
- `latitude_deg` / `longitude_deg` (`NUMERIC(8,5)`): Coordinate bounds.
- `elevation_m` (`NUMERIC(7,2)`): Elevation in meters above sea level.
- `spatial_resolution_deg` (`NUMERIC(5,3)`): Grid cell resolution (0.500° for NASA POWER).
- `source_provider` (`VARCHAR(32)`): Primary source (`NASA_POWER`).

---

## 9. `dw.dim_metric`

### Purpose
Canonical indicator dictionary establishing physical dimensions, units ($MW$, $MWh$, $GWh$, $kW\cdot h/m^2/day$), additivity rules, and measurement domains.

### Attributes
- `metric_key` (`INTEGER GENERATED ALWAYS AS IDENTITY`): Surrogate primary key.
- `metric_code` (`VARCHAR(48)`): Unique code (e.g., `PLANT_DISPATCH_MW`, `DAILY_GROSS_GENERATION_MWH`, `ALLSKY_SFC_SW_DWN`, `T2M`, `TRANSMISSION_LOSS_PCT`).
- `metric_name` (`VARCHAR(128)`): Human-readable metric title.
- `business_domain` (`VARCHAR(48)`): `DISPATCH`, `GENERATION`, `SALES`, `WEATHER`, `GRID_PERFORMANCE`.
- `measurement_class` (`VARCHAR(24)`): `POWER`, `ENERGY`, `CAPACITY`, `COUNT`, `CURRENCY`, `PERCENTAGE`, `METEOROLOGICAL`, `STORAGE`, `RATIO`.
- `canonical_unit_code` (`VARCHAR(24)`): Foreign key to `ref.unit (unit_code)`.
- `generation_boundary` (`VARCHAR(20)`): `GROSS`, `NET`, `AUXILIARY`, `NOT_APPLICABLE`.
- `value_nature` (`VARCHAR(24)`): `REPORTED`, `ESTIMATED`, `DERIVED`, `AUDITED_FINAL`, `PROVISIONAL`.
- `aggregation_behavior` (`VARCHAR(32)`): `SUM`, `AVG`, `MIN`, `MAX`, `NON_ADDITIVE`, `SEMI_ADDITIVE_PERIOD_END`.
- `is_summable_across_time` (`BOOLEAN`): True if additive over temporal dimensions.
- `is_summable_across_entities` (`BOOLEAN`): True if additive across facilities or sectors.
- `comparability_group` (`VARCHAR(64)`): Grouping code for benchmarking.
- `definition_notes` (`TEXT`): Authoritative domain definition.
