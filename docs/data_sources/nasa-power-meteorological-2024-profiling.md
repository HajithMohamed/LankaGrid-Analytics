# Data Source Profiling: NASA POWER Meteorological Grid Points (2024)

## 1. Source Identification & Metadata
- **Source Identifier**: `NASA-POWER-DAILY-2024`
- **Provider / Agency**: NASA Langley Research Center (NASA POWER Project)
- **Official URL / Endpoint**: `https://power.larc.nasa.gov/api/temporal/daily/point`
- **Retrieval Date & Time**: `2026-10-30T17:21:30+05:30`
- **Local Immutable Filepath**: [nasa_power_sl_nodes_2024.json](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/data/raw/nasa/2024/nasa_power_sl_nodes_2024.json)
- **Cryptographic Hash (SHA-256)**: `9574ed078fa4941c0e5cf1ec7a261448c0d7d90b042734a6b153066972d1be8b`
- **File Format & MIME Type**: JSON (`application/json`)
- **File Size**: 14,177 bytes

---

## 2. Temporal & Geospatial Scope
- **Reporting Period Covered**: `2024-01-01` to `2024-01-31` (Daily observations for sample month)
- **Observation Frequency / Granularity**: Daily point values
- **Time Zone & Daylight Rules**: Local Solar Time (`LST / UTC+05:30` - preserved explicitly; never improperly conflated with arbitrary standard clock intervals)
- **Geospatial Scope**: Strategic Sri Lanka renewable energy nodes:
  - Victoria Hydro Catchment Hub (`lat: 7.2400, lon: 80.7850`)
  - Mannar Wind Corridor Hub (`lat: 9.0300, lon: 79.8800`)

---

## 3. Structural & Domain Content
- **Entities Covered**: Meteorological grid points associated with hydro catchment basins and wind corridors.
- **Physical Measures & Parameters**:
  - `ALLSKY_SFC_SW_DWN`: All Sky Surface Shortwave Downward Irradiance ($\text{kW}\cdot\text{h}/\text{m}^2/\text{day}$ or $\text{MJ}/\text{m}^2/\text{day}$)
  - `T2M`: Temperature at 2 Meters ($^\circ\text{C}$)
  - `RH2M`: Relative Humidity at 2 Meters ($\%$)
  - `WS10M`: Wind Speed at 10 Meters ($\text{m}/\text{s}$)
  - `WS50M`: Wind Speed at 50 Meters ($\text{m}/\text{s}$)
  - `PRECTOTCORR`: Bias-Corrected Precipitation ($\text{mm}/\text{day}$)
- **JSON Structure**:
  - Nested dictionary: `nodes -> <node_id> -> properties -> parameter -> <PARAM> -> {YYYYMMDD: value}`.
  - Fill value for missing observations: `-999.0`.

---

## 4. Data Quality & Preprocessing Assessment
- **Missing Value Sentinel**:
  - `-999.0` is the standard NASA POWER missing-data sentinel.
  - Under no circumstances treat `-999.0` as a physical measurement or coerce it to $0.0$.
  - It must be parsed to `None` / `NULL` with `is_missing = TRUE` and `missing_value_code = 'NASA_FILL_VALUE_-999'`.
- **Physical Boundary Checks**:
  - Solar Irradiance: $\ge 0$
  - Relative Humidity: $0\% \le \text{RH} \le 100\%$
  - Temperature: $-20^\circ\text{C} \le T \le 60^\circ\text{C}$
  - Wind Speed: $\ge 0\text{ m/s}$
  - Precipitation: $\ge 0\text{ mm/day}$

---

## 5. Kimball Warehouse Mapping Proposal
- **Target Staging Table**: [stg_weather_observation](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql#L118-L140)
- **Target Fact Table**: [dw.fact_weather_daily](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/008_facts_weather_and_published.sql#L10-L65)
- **Conformed Dimensions**:
  - `dw.dim_date` (`date_key = YYYYMMDD`)
  - `dw.dim_weather_location` (`weather_location_key`)
  - `dw.dim_metric` (`SOLAR_IRRADIANCE_SW_DWN`, `AIR_TEMP_2M_C`, `REL_HUMIDITY_2M_PCT`, `WIND_SPEED_10M_MS`, `PRECIPITATION_DAILY_MM`)
  - `dw.dim_source_system` (`NASA_POWER`)

