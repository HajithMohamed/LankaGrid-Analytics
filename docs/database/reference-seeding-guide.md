# Reference Data Seeding Guide

## 1. Seeding Governance & Strict Separation Policy

Implemented in [seed_reference.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/seed_reference.py) and [001_static_reference_seed.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/seeds/001_static_reference_seed.sql), the project enforces a strict three-way separation:

| Data Category | Storage / Script Location | Permitted in Production Database? | Contents |
|---|---|:---:|---|
| **1. Verified Static Reference Data** | [seed_reference.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/seed_reference.py), [001_static_reference_seed.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/seeds/001_static_reference_seed.sql) | **YES** | Physical units & conversions, calendar dates (`2019`–`2026`), SLST `15-min` & hourly intervals, ISO-3166-2:LK provinces, CEB divisions `DD1`–`DD4`, official tariff sectors, verified Sri Lankan power plants & documented aliases, NASA POWER grid sampling points, canonical metric definitions, DQ rules, and source precedence. |
| **2. Authentic Source-Derived Fact Data** | Future Phase 2 ETL loaders reading `data/raw/` | **YES** *(once raw files are downloaded & checksum-verified)* | Actual generation, dispatch, capacity, sales, weather, and published benchmark measurements. **Currently 0 rows because `data/raw/` downloads are pending Phase 2.** |
| **3. Synthetic QA Test Fixtures** | `tests/fixtures/*`, `acquisition_status = 'SYNTHETIC_FIXTURE'` | **NO** *(isolated to `sl_grid_warehouse_test` with automatic cleanup/rollback)* | Deliberately defective, duplicate, negative, and boundary rows used strictly to test constraints, quality gates, and transaction rollbacks. |

---

## 2. Inventory of Seeded Reference & Dimension Tables

| Table | Seeded Rows | Authoritative Reference Basis |
|---|---:|---|
| `ref.unit` | 17 | SI / IEC electrical & meteorological units (`MW`, `kW`, `MWh`, `GWh`, `kWh`, `MJ/m2/day`, `C`, `mm/day`, `m/s`, `PCT`, `MCM`, `LKR`, `MLKR`, `COUNT`, `Hz`). |
| `ref.unit_conversion` | 9 | Deterministic physical conversions (`1 GWh = 1,000 MWh`, `MW -> MWh` gated by `requires_interval_hours = TRUE`). |
| `ref.reporting_period_type` | 6 | `INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`. |
| `raw.source_system` / `dw.dim_source_system` | 3 | `CEB`, `PUCSL`, `NASA_POWER`. |
| `dw.dim_date` | 2,922 | Deterministic calendar `2019-01-01` to `2026-12-31` + Sri Lanka Department of Meteorology monsoon seasons (`NORTHEAST_MONSOON`, `FIRST_INTER_MONSOON`, `SOUTHWEST_MONSOON`, `SECOND_INTER_MONSOON`). |
| `dw.dim_interval` | 120 | `96` x `15-min` slots (`00:00`–`23:45`) + `24` hourly slots mapped to CEB/PUCSL Time-of-Use blocks (`OFF_PEAK` `22:30–05:30`, `DAY` `05:30–18:30`, `PEAK` `18:30–22:30`). |
| `dw.dim_energy_source` | 9 | `MAJOR_HYDRO`, `THERMAL_COAL`, `THERMAL_OIL`, `MINI_HYDRO`, `WIND`, `SOLAR_UTILITY`, `SOLAR_ROOFTOP`, `BIOMASS`, `SYSTEM_AGGREGATE`. |
| `dw.dim_region` | 14 | `LK` National + 9 ISO-3166-2:LK Provinces (`LK-1`..`LK-9`) + 4 CEB Distribution Divisions (`CEB-DD1`..`CEB-DD4`). |
| `dw.dim_consumption_sector` | 9 | Official CEB/PUCSL tariff groups (`DOMESTIC`, `RELIGIOUS`, `INDUSTRIAL`, `GENERAL_PURPOSE`, `HOTEL`, `GOVERNMENT`, `STREET_LIGHTING`, `BULK_LECO`, `ALL_SECTORS`). |
| `dw.dim_power_plant` | 32 | Verified CEB hydro complexes (Mahaweli, Laxapana, Samanala, Uma Oya), Lakvijaya Coal (station + Units 1–3), Kelanitissa CCGT, Sapugaskanda A/B, Yugadanavi, Sobadhanavi, Mannar Wind, Baruthankanda Solar, plus reported NCRE/System aggregate categories. |
| `dw.dim_weather_location` | 6 | Verified Sri Lanka energy-zone coordinates (`Victoria`, `Laxapana`, `Mannar`, `Puttalam/Norochcholai`, `Hambantota`, `Colombo`). |
| `dw.dim_metric` | 14 | Canonical definitions and additivity rules across dispatch, generation, capacity, sales, losses, and weather. |
| `ref.plant_alias` / `energy_source_mapping` / `region_alias` / `metric_mapping` | 20 total | Evidence-documented provider mappings (`VERIFIED` with `verification_evidence`). |
| `ref.data_quality_rule` | 13 | All 13 required data quality issue classifications. |
| `ref.source_precedence` | 7 | Authoritative provider hierarchy per domain and reporting period. |

---

## 3. Execution & Idempotency Verification Commands

```powershell
# Seed primary warehouse database (sl_grid_warehouse)
.\.venv\Scripts\python.exe scripts/seed_reference.py

# Seed isolated test database (sl_grid_warehouse_test)
.\.venv\Scripts\python.exe scripts/seed_reference.py --test-db

# Re-run to verify strict idempotency (ON CONFLICT DO UPDATE -> zero duplicate rows)
.\.venv\Scripts\pytest.exe tests/integration/test_phase1_seeding.py
```

