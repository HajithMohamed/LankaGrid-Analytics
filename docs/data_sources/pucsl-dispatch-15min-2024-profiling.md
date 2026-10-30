# Data Source Profiling: PUCSL 15-Minute Generation Dispatch (March 2024)

## 1. Source Identification & Metadata
- **Source Identifier**: `PUCSL-DISPATCH-15MIN-2024-03`
- **Provider / Agency**: Public Utilities Commission of Sri Lanka (PUCSL)
- **Official URL / Endpoint**: `https://www.pucsl.gov.lk/wp-content/uploads/2024/04/15-Minutes-Report-31-Mar2024.xlsx`
- **Retrieval Date & Time**: `2026-10-30T17:21:30+05:30`
- **Local Immutable Filepath**: [15-Minutes-Report-31-Mar2024.xlsx](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx)
- **Cryptographic Hash (SHA-256)**: `d40c7d9b11293e2c42c45227c4d121854e90781c3586bf204780d73fb282573b`
- **File Format & MIME Type**: XLSX (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)
- **File Size**: 917,216 bytes

---

## 2. Temporal & Geospatial Scope
- **Reporting Period Covered**: `2024-03-01` to `2024-03-31` (31 daily sheets)
- **Observation Frequency / Granularity**: 15-minute intervals (96 intervals per 24-hour cycle)
- **Time Zone & Daylight Rules**: Sri Lanka Standard Time (`Asia/Colombo`, UTC+05:30, no DST)
- **Geospatial Scope**: National grid transmission interconnection nodes and power plants across Sri Lanka.

---

## 3. Structural & Domain Content
- **Entities Covered**:
  - Major Hydro: Canyon, WPS (Wimalasurendra), Olax (Old Laxapana), Nlax (New Laxapana), Polp (Polpitiya), Broadlands, Upper Kothmale, Koth (Kotmale), Vict (Victoria), Rand (Randenigala), Rant (Rantembe), Uku (Ukuwela), Bowa (Bowatenna), Sam (Samanalawewa), Kukule (Kukule Ganga), Uma Oya.
  - Coal: LVPS 1, LVPS 2, LVPS 3 (Lakvijaya Units 1, 2, 3).
  - Oil / Thermal: Sapu A (Sapugaskanda A), Sapu B (Sapugaskanda B), Uthuru Janani, Barge, KCCP (Kelanitissa Combined Cycle), ACE Embili, ACE Matara, WCP (West Coast / Yugadanavi), KCCPS2, KPS(GT7), KPS(GT), KPS_DPP_MATU, KPS_DPP_HAMBA.
  - Non-Conventional Renewable Aggregates: Solar**, Wind **, BMP** (Biomass), CEB/IPP Mini Hydro***.
  - Category and System Totals: Total MW, Coal, Oil- CEB owned, Oil-IPP owned, Major Hydro, Wind, Solar, Biomass, Mini Hydro.
- **Physical Measures & Units**: Active Power in Megawatts (**MW**).
- **Sheet Layout Structure**:
  - Header Row 0: `Actual System Dispatch ... [Date]`
  - Header Row 1: `Time`, `0:15`, `0:30`, ..., `24:00` (96 columns)
  - Rows 2–36: Plant/Unit specific 15-minute dispatch values.
  - Rows 37–45: System total and technology subtotals.

---

## 4. Data Quality & Preprocessing Assessment
- **Missing Values & Sentinels**:
  - Blank cells / `None` signify unrecorded/missing intervals.
  - `0` signifies physical shutdown or zero generation (e.g. solar at night, plant offline).
  - Never treat missing/unrecorded intervals as zero.
- **Null Frequency**: Low in primary hydro/thermal; telemetered renewable streams occasionally contain blank intervals during telemetry outages.
- **Duplicate Records**: Daily sheets are distinct (`01.03` through `31.03`); duplicate checks verify that no station appears more than once per sheet.
- **Outliers & Physical Violations**:
  - Values must be $\ge 0$ (negative power is rejected except for auxiliary/pumped load).
  - Station dispatch must not exceed rated nameplate capacity $P > P_{\text{installed}} \times 1.05$.
- **Derived Measures**: Energy in Megawatt-hours is derived deterministically:
  $$\text{derived\_energy\_mwh} = \text{active\_power\_mw} \times 0.25$$

---

## 5. Kimball Warehouse Mapping Proposal
- **Target Staging Table**: [stg_dispatch_observation](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql#L11-L34)
- **Target Fact Table**: [dw.fact_dispatch_interval](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/006_facts_generation_and_dispatch.sql#L10-L73) (Partition: `dw.fact_dispatch_interval_y2024`)
- **Conformed Dimensions**:
  - `dw.dim_date` (`date_key = YYYYMMDD`)
  - `dw.dim_interval` (`interval_key = 1..96`)
  - `dw.dim_power_plant` (`plant_key` via `ref.plant_alias`)
  - `dw.dim_energy_source` (`energy_source_key`)
  - `dw.dim_metric` (`metric_code = 'PLANT_DISPATCH_MW'`)
  - `dw.dim_source_system` (`source_code = 'PUCSL'`)
