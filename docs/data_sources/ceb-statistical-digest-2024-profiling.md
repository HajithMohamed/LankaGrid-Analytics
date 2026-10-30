# Data Source Profiling: CEB Statistical Digest (2024)

## 1. Source Identification & Metadata
- **Source Identifier**: `CEB-STAT-DIGEST-2024`
- **Provider / Agency**: Ceylon Electricity Board (CEB)
- **Official URL / Endpoint**: `https://ceb.lk/front_img/img_reports/1751344341Statistical_Digest_2024.pdf`
- **Retrieval Date & Time**: `2026-10-30T17:21:30+05:30`
- **Local Immutable Filepath**: [Statistical_Digest_2024.pdf](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/data/raw/ceb/2024/Statistical_Digest_2024.pdf)
- **Cryptographic Hash (SHA-256)**: `b0af3107c2eb4847e1b67cc7487e960f8c05e5d4501d0138b4c516e479d6905b`
- **File Format & MIME Type**: PDF (`application/pdf`, version 1.5)
- **File Size**: 675,770 bytes

---

## 2. Temporal & Geospatial Scope
- **Reporting Period Covered**: Calendar Year `2024` (with `2023` restated comparison)
- **Observation Frequency / Granularity**: Annual totals and monthly provincial/tariff breakdowns
- **Time Zone & Daylight Rules**: Sri Lanka Standard Time (`Asia/Colombo`, UTC+05:30)
- **Geospatial Scope**: National coverage partitioned by CEB Distribution Divisions (Divisions 1–4) and Administrative Provinces.

---

## 3. Structural & Domain Content
- **Entities Covered**:
  - Administrative Provinces: Colombo City, Western Province North, Central, Northern, North Western, North Central, Southern, Eastern, Uva, Sabaragamuwa, LECO franchise areas.
  - Consumer Tariff Classes: Domestic, Religious, General Purpose (GP 1–3), Hotel (H 1–3), Industrial (IP 1–3), Government (GV 1–3), Agriculture, Street Lighting.
- **Physical Measures & Units**:
  - Electricity Sales: Gigawatt-hours (**GWh**)
  - Revenue from Electricity Sales: LKR Million
  - Consumer Accounts: Integer count (Nos.)
  - Average Price: LKR/kWh
  - Monthly Average Sales: kWh/Consumer
- **Document Layout Structure**:
  - Page 3: Generation statistics by ownership and station type, including number of stations and installed capacity in MW.
  - Page 5: Electricity Sales by Distribution Divisions in GWh (Distribution Provinces and LECO). Total 2024 Sales = 15,191 GWh.
  - Page 5 (Lower): Electricity Sales by Tariff in GWh.
  - Page 8: CEB Electricity Sales & Consumer Accounts by Tariff.

---

## 4. Data Quality & Preprocessing Assessment
- **Missing Values & Sentinels**:
  - `-` indicates zero or not applicable (e.g. temporary connections in some divisions).
  - `*` indicates restated historical data from prior audited accounts.
- **Unit Normalization**:
  - Warehouse canonical unit for billed energy sales is **MWh**.
  - Convert reported GWh to MWh:
    $$\text{sales\_mwh} = \text{sales\_gwh} \times 1{,}000.0$$
- **Reconciliation Check**:
  - Sum of tariff sales equals Total Sales:
    $$4{,}701 + 75 + 3{,}472 + 355 + 4{,}622 + 241 + 3.5 + 1{,}625 + 96 = 15{,}191\text{ GWh} \pm 1\text{ GWh}$$
  - Provincial sales sum matches the national total (15,191 GWh).

---

## 5. Kimball Warehouse Mapping Proposal
- **Target Staging Table**: [stg_electricity_sales](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql#L65-L90)
- **Target Fact Table**: [dw.fact_electricity_sales](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/007_facts_capacity_and_sales.sql#L69-L126)
- **Conformed Dimensions**:
  - `dw.dim_date` (`date_key = 20241231` for annual period `2024-01-01` to `2024-12-31`)
  - `dw.dim_region` (`region_key` via `ref.region_alias`)
  - `dw.dim_consumption_sector` (`sector_key`)
  - `dw.dim_metric` (`ELECTRICITY_SALES_MWH`)
  - `dw.dim_source_system` (`CEB`)
