# Data Source Profiling: PUCSL Daily Generation Report (29 December 2024)

## 1. Source Identification & Metadata
- **Source Identifier**: `PUCSL-GEN-DAILY-2024-12-29`
- **Provider / Agency**: Public Utilities Commission of Sri Lanka (PUCSL)
- **Official URL / Endpoint**: `https://www.pucsl.gov.lk/wp-content/uploads/2024/12/Generation-Report-29th-Dec.pdf`
- **Retrieval Date & Time**: `2026-10-30T17:21:30+05:30`
- **Local Immutable Filepath**: [Generation-Report-29th-Dec-2024.pdf](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/data/raw/pucsl/2024/Generation-Report-29th-Dec-2024.pdf)
- **Cryptographic Hash (SHA-256)**: `bb10974c344b80f8795c4150153a6f2a823702cd81fade3d72899886a237ee3e`
- **File Format & MIME Type**: PDF (`application/pdf`, version 1.7)
- **File Size**: 808,269 bytes

---

## 2. Temporal & Geospatial Scope
- **Reporting Period Covered**: `2024-12-29` (Single-day audited operational report)
- **Observation Frequency / Granularity**: Daily station generation totals and capacity availability
- **Time Zone & Daylight Rules**: Sri Lanka Standard Time (`Asia/Colombo`, UTC+05:30)
- **Geospatial Scope**: All grid-connected generating facilities across Sri Lanka.

---

## 3. Structural & Domain Content
- **Entities Covered**:
  - Major Hydro plants: Wimalasurendra, Old Laxapana, Canyon, New Laxapana, Polpitiya, Broadlands, Kotmale, Victoria, Randenigala, Rantembe, Ukuwela, Bowatenna, Nilambe, Samanalawewa, Kukule Ganga, Upper Kotmale, Uma Oya.
  - Thermal plants: Lakvijaya Coal, Kelanitissa CCGT, Kelanitissa GT, Sapugaskanda A & B, West Coast (Yugadanavi), Barge.
  - Non-Conventional Renewable categories: Mini Hydro, IPP Wind, CEB Wind (Thambapavani), IPP Solar (Bulk), Solar Rooftop PV, Biomass/Solid Waste.
- **Physical Measures & Units**:
  - Plant Dispatch & Generation: Megawatt-hours (**MWh**)
  - Maximum Rated Capacity: Megawatts (**MW**)
  - Available Capacity: Megawatts (**MW**)
  - Night Peak Load: Megawatts (**MW**)
  - Day Peak Maximum Demand & Off Peak Minimum Demand: Megawatts (**MW**)
  - Reservoir Storage: Gigawatt-hours (**GWh**)
- **Document Layout Structure**:
  - Page 2, Table 01: Technology-level daily generation mix in MWh.
  - Page 2, Table 02 & 03: Cumulative monthly and annual dispatch by technology in GWh.
  - Page 4, Table 2: Plant-by-plant table containing Maximum Capacity (MW), Available Capacity (MW), Night Peak Load (MW), and Plant Dispatch (MWh).
  - Page 5: Night Peak MW contribution by technology; Day/Night peak demand; Reservoir storage levels in GWh.

---

## 4. Data Quality & Preprocessing Assessment
- **Missing Values & Sentinels**:
  - `-` indicates zero generation or plant not dispatched.
  - `*` denotes estimated figures (e.g. non-telemetered mini hydro and rooftop solar).
- **Outliers & Physical Violations**:
  - Available Capacity must satisfy: $\text{Available Capacity} \le \text{Maximum Capacity}$.
  - Night peak load must not exceed available capacity.
  - Plant generation must be $\ge 0$.
- **Source Inconsistencies & Reconciliations**:
  - Sum of telemetered generation: 37,189 MWh.
  - Sum including estimated unserved energy and non-telemetered NCRE: 40,414 MWh.
  - Must distinguish reported telemetered vs estimated quantities using `value_nature` attribute (`REPORTED` vs `ESTIMATED`).

---

## 5. Kimball Warehouse Mapping Proposal
- **Target Staging Tables**:
  - [stg_generation_report](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql#L36-L63)
  - [stg_plant_capacity](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql#L92-L116)
- **Target Fact Tables**:
  - [dw.fact_generation_period](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/006_facts_generation_and_dispatch.sql#L99-L159)
  - [dw.fact_capacity_period](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/007_facts_capacity_and_sales.sql#L10-L67)
- **Conformed Dimensions**:
  - `dw.dim_date` (`date_key = 20241229`)
  - `dw.dim_power_plant` (`plant_key`)
  - `dw.dim_energy_source` (`energy_source_key`)
  - `dw.dim_metric` (`GROSS_GENERATION_MWH`, `INSTALLED_CAPACITY_MW`, `DEPENDABLE_CAPACITY_MW`)
  - `dw.dim_source_system` (`PUCSL`)
