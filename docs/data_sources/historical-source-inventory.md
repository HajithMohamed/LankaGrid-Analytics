# Five-Year Historical Source Inventory (2020–2024)

## 1. Executive Overview

This document provides the authentic primary provenance inventory for the 5-year historical expansion (calendar years 2020 to 2024) of the **GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka**.

In accordance with project governance (`AGENTS.md` and `.agents/rules/`):
- **Zero Fabrication**: All historical measurements originate from authentic, verifiable official public archives.
- **Unit Integrity**: Instantaneous active power (MW) is strictly decoupled from integrated energy (MWh/GWh). Solar irradiance is maintained with native reported values and converted into canonical SI units ($1\text{ kWh/m}^2/\text{day} = 3.6\text{ MJ/m}^2/\text{day}$).
- **Immutable Provenance**: Every raw artifact is preserved in `data/raw/` with verified cryptographic SHA-256 hashes recorded in `data/raw/manifest.json`.

---

## 2. Source Inventory Summary

| Source Code | Primary Entity / Authority | Data Modality | Coverage Window | Granularity | Total Files | SHA-256 Status |
|---|---|---|---|---|---|---|
| **CEB-STAT-DIGEST** | Ceylon Electricity Board (CEB) | Annual Statistical Digest PDF | 2020 – 2024 | Annual / Sectoral / Provincial | 5 PDFs | Verified |
| **PUCSL-DISPATCH** | Public Utilities Commission of Sri Lanka | Grid Dispatch Excel (.xlsx) | March 2024 (31 days) | 15-Minute Interval | 1 Workbook (31 sheets) | Verified |
| **PUCSL-DAILY-GEN** | Public Utilities Commission of Sri Lanka | Daily Generation Report PDF | Dec 2024 Sample | Daily / Plant-level | 1 PDF | Verified |
| **NASA-POWER-WEATHER** | NASA Langley Research Center POWER Project | Solar & Meteorological JSON | 2020-01-01 – 2024-12-31 | Daily Point Observations | 2 JSON Files (5-Year & 2024) | Verified |

---

## 3. Ceylon Electricity Board (CEB) — Statistical Digests (2020–2024)

Official Archive: `https://ceb.lk/publication-media/statistical-reports/141/en`

All 5 annual digests were acquired directly from the official CEB publications repository. The digests represent finalized, audited operational accounting figures published by the CEB Corporate Strategy and Regulatory Affairs Division.

### 3.1 Digest File Provenance Table

| Year | File Location | File Size (Bytes) | SHA-256 Checksum | Retrieval URL |
|---|---|---|---|---|
| **2020** | `data/raw/ceb/2020/Statistical_Digest_2020.pdf` | 5,299,544 | `58228a1ce42e68b6a77553a0d95dc7bc02925afb314df2f9c3442f6cd4d6991a` | [ceb.lk/.../Statistical_Digest_2020.pdf](https://ceb.lk/front_img/img_reports/1638258385Statistical_Digest_2020.pdf) |
| **2021** | `data/raw/ceb/2021/Statistical_Digest_2021.pdf` | 714,608 | `d0d83805b0a271ed9d0bc9aee01f2549d8e6fe18ee3661b84fe3682b96633d72` | [ceb.lk/.../Statistical_Digest_2021.pdf](https://ceb.lk/front_img/img_reports/1666675204Statistical_Digest_2021.pdf) |
| **2022** | `data/raw/ceb/2022/Statistical_Digest_2022.pdf` | 1,999,717 | `a33560020cc904928cebcf090a1738a2e7b1995c365445e07f9471c15c8fefe4` | [ceb.lk/.../Statistical_Digest_2022.pdf](https://ceb.lk/front_img/img_reports/1698299867Statistical_Digest_2022.pdf) |
| **2023** | `data/raw/ceb/2023/Statistical_Digest_2023.pdf` | 580,335 | `db8a8237c764822a98ba3b2ef6c466a490e31ebe4cf079d2ff9c66eedc20502e` | [ceb.lk/.../Statistical_Digest_2023.pdf](https://ceb.lk/front_img/img_reports/1729227568Statistical_Digest_2023.pdf) |
| **2024** | `data/raw/ceb/2024/Statistical_Digest_2024.pdf` | 675,770 | `b0af3107c2eb4847e1b67cc7487e960f8c05e5d4501d0138b4c516e479d6905b` | [ceb.lk/.../Statistical_Digest_2024.pdf](https://ceb.lk/front_img/img_reports/1749807535Statistical_Digest_2024.pdf) |

### 3.2 Extracted Domain Metrics (Audited Operational Indicators)

1. **Electricity Sales by Tariff / Consumer Category (GWh & MWh)**:
   - Domestic, Industrial, General Purpose, Hotel, Religious, Street Lighting, Government/Public, Bulk Supply to LECO (Lanka Electricity Company).
2. **Consumer Accounts by Category**:
   - Number of active metered customer accounts across all 9 customer classes.
3. **National Generation & Capacity**:
   - Total Gross Generation, Net Generation, and Station Auxiliary Consumption.
   - Total System Installed Capacity (MW) by technology (Hydro, Thermal Coal, Thermal Oil, Wind, Solar).
   - Rooftop Solar PV installed capacity additions (MW).
4. **Peak Demand & Network Efficiency**:
   - National System Maximum Demand (MW) and recorded peak timestamp.
   - Transmission and Distribution (T&D) losses (%) and system loss energy (GWh).

---

## 4. Public Utilities Commission of Sri Lanka (PUCSL) — Operational Datasets

Official Archive: `https://www.pucsl.gov.lk/daily-generation-reports-2/`

### 4.1 Dispatch Workbook (March 2024 Full Month)

| Attribute | Specification |
|---|---|
| **File Path** | `data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx` |
| **File Size** | 917,216 bytes |
| **SHA-256 Checksum** | `f6ffc05f778a46e16f6b7c25143a53d12d8a43f8a46cf7e48b8b9354e606a5e1` |
| **Temporal Coverage** | 2024-03-01 to 2024-03-31 (31 full days) |
| **Sheet Layout** | 31 individual daily sheets named `01.03` through `31.03` |
| **Time Granularity** | 96 intervals per day (15-minute intervals: 00:00 to 23:45 SLST) |
| **Entities Included** | All grid-connected dispatchable plants (~50 units/stations), IPPs, wind farms, solar complexes |
| **Physical Measurements** | Active Power ($P$ in MW) and Integrated Energy ($E = P \times 0.25$ in MWh) |

### 4.2 Historical PUCSL Archives Availability Assessment

The PUCSL portal provides daily generation PDFs and occasional multi-day dispatch workbooks. Detailed sub-daily (15-minute) workbooks prior to 2024 are archived irregularly on the PUCSL public server with intermittent download availability and format restructuring across years.

The warehouse architecture incorporates dynamic partition ranges (`dw.fact_dispatch_interval_y2020` through `_y2025`) and version-aware parsers to ensure that earlier multi-month or annual dispatch archives can be loaded idempotently as additional historical spreadsheets are acquired.

---

## 5. NASA POWER Solar & Meteorological Dataset (2020–2024)

Official API Endpoint: `https://power.larc.nasa.gov/api/temporal/daily/point`

### 5.1 Dataset File Provenance Table

| File Location | Size (Bytes) | SHA-256 Checksum | Temporal Range | Total Node Observations |
|---|---|---|---|---|
| `data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json` | 695,087 | `fe590598b0a559229a18c24cd1e5c0448057acc1a59b4ba8039540e17d52c109` | 2020-01-01 to 2024-12-31 (1,827 days) | 21,924 point measurements |
| `data/raw/nasa/2024/nasa_power_sl_nodes_2024.json` | 143,158 | `51006e8b4eebca82348b6c8673752e50529d846bfa332ee483ef3b8e5c85b51a` | 2024-01-01 to 2024-01-31 (31 days) | 372 point measurements |

### 5.2 Meteorological Observation Nodes

1. **Node 1: Victoria Hydro Catchment**
   - Coordinates: Latitude $7.2400^\circ\text{ N}$, Longitude $80.7850^\circ\text{ E}$, Elevation $438\text{ m}$.
   - Energy Zone: Central Highlands Hydro Catchment (`HYDRO_CATCHMENT`).
   - Strategic Importance: Primary reservoir for the Mahaweli complex (210 MW installed capacity).

2. **Node 2: Mannar Wind Corridor**
   - Coordinates: Latitude $9.0300^\circ\text{ N}$, Longitude $79.8800^\circ\text{ E}$, Elevation $3\text{ m}$.
   - Energy Zone: Northern Coastal Wind Corridor (`WIND_CORRIDOR`).
   - Strategic Importance: Site of the 100 MW Thambapavani Wind Farm.

### 5.3 Extracted Meteorological Parameters & Unit Conversions

| Parameter Code | NASA Variable Name | Description | Native Unit | Canonical Warehouse Unit | Conversion Factor |
|---|---|---|---|---|---|
| `SOLAR_IRRADIANCE_SW_DWN` | `ALLSKY_SFC_SW_DWN` | All Sky Surface Shortwave Downward Irradiance | $\text{kWh/m}^2/\text{day}$ | $\text{MJ/m}^2/\text{day}$ | $\times 3.6$ |
| `TEMP_MEAN_2M` | `T2M` | Temperature at 2 Meters AGL | $^\circ\text{C}$ | $^\circ\text{C}$ | $1.0$ (Identity) |
| `RELATIVE_HUMIDITY_2M` | `RH2M` | Relative Humidity at 2 Meters AGL | $\%$ | $\%$ | $1.0$ (Identity) |
| `WIND_SPEED_10M` | `WS10M` | Wind Speed at 10 Meters AGL | $\text{m/s}$ | $\text{m/s}$ | $1.0$ (Identity) |
| `WIND_SPEED_50M` | `WS50M` | Wind Speed at 50 Meters (Turbine Hub Height) | $\text{m/s}$ | $\text{m/s}$ | $1.0$ (Identity) |
| `PRECIPITATION_CORRECTED` | `PRECTOTCORR` | Corrected Total Precipitation | $\text{mm/day}$ | $\text{mm/day}$ | $1.0$ (Identity) |

---

## 6. Manifest Verification Command

All files are registered in `data/raw/manifest.json`. Verification is automated via pytest:

```bash
python -m pytest tests/unit/test_manifest.py -v
```

All hashes match exactly with zero discrepancy.
