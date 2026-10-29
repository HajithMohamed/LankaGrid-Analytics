# Data Source Profiling Template

Use this template whenever auditing or onboarding a new data source or file release into the Sri Lanka Electricity Grid Data Warehouse.

---

## 1. Source Identification & Metadata
- **Source Identifier**: `[e.g., PUCSL_GEN_DAILY_2024]`
- **Provider / Agency**: `[CEB / PUCSL / NASA POWER / Central Bank / Other]`
- **Official URL / Endpoint**: `[Direct link to download or API documentation]`
- **Retrieval Date & Time**: `[YYYY-MM-DDTHH:MM:SS+05:30]`
- **Local Immutable Filepath**: `data/raw/[provider]/[year]/[filename]`
- **Cryptographic Hash (SHA-256)**: `[Run: python scripts/compute_checksum.py <file>]`
- **File Format & MIME Type**: `[PDF / XLSX / CSV / JSON]`
- **File Size**: `[e.g., 284,192 bytes]`

---

## 2. Temporal & Geospatial Scope
- **Reporting Period Covered**: `[Start Date to End Date, e.g. 2024-01-01 to 2024-12-31]`
- **Observation Frequency / Granularity**: `[15-minute / Hourly / Daily / Monthly / Annual]`
- **Time Zone & Daylight Rules**: `[Sri Lanka Standard Time UTC+05:30 / UTC]`
- **Geospatial Scope**: `[National Total / Provincial / Substation Node / Lat-Lon Coordinates]`

---

## 3. Structural & Domain Content
- **Entities Covered**: `[Power Stations / Transmission Feeders / Consumer Tariff Groups / Weather Nodes]`
- **Physical Measures & Units**:
  - `[e.g., Active Power: MW]`
  - `[e.g., Daily Energy: MWh]`
  - `[e.g., Reservoir Storage: MCM / GWh]`
  - `[e.g., Solar Irradiance: kW/m²]`
  - `[e.g., Temperature: °C]`
- **Table / Sheet Layout Structure**: `[Header row index, footer notes index, multi-table layout description]`

---

## 4. Data Quality & Preprocessing Assessment
- **Missing Values & Sentinels**: `[List any symbols representing missing data: '-', 'N/A', 'blank', '9999']`
- **Null Frequency**: `[Estimated % of missing records and affected columns]`
- **Duplicate Records**: `[Presence of duplicate timestamps, duplicate station names, or multiple versions]`
- **Outliers & Physical Violations**: `[Any negative values, readings exceeding plant capacity, frequency anomalies]`
- **Inconsistencies & Reconciliations**: `[Does sum of units equal station total? Does gross minus losses equal net sales?]`
- **Unit Conversion Required**: `[e.g., Convert kW to MW (/1000), convert GWh to MWh (*1000)]`

---

## 5. Kimball Warehouse Mapping Proposal
- **Target Fact Table**: `[e.g., fact_daily_generation / fact_grid_dispatch_15min]`
- **Target Grain**: `[e.g., One record per plant per day]`
- **Referenced Dimensions**: `[dim_date, dim_power_plant, dim_fuel_type, dim_location]`
- **Primary Business Key**: `[e.g., (plant_code, report_date)]`

---

## 6. Verification Sign-Off
- **Auditor / Team Member**: `[Member Name / ID]`
- **Audit Date**: `[YYYY-MM-DD]`
- **Sign-off Status**: `[APPROVED FOR PIPELINE / CONDITIONAL ON PREPROCESSING / REJECTED]`
- **Special Notes**: `[Any parsing quirks, layout shifts, or edge cases to consider in tests]`
