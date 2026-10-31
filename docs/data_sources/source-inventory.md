# Data Source Inventory & Provenance Registry

## Project Scope
- **Target Domain**: Sri Lanka National Electricity Grid Analytics Data Warehouse
- **Primary Historical Year**: 2024
- **Time Standard**: Sri Lanka Standard Time (SLST) — `UTC+05:30` (Asia/Colombo)

---

## 1. Ceylon Electricity Board (CEB) — Statistical Digest 2024

| Field | Detail |
|---|---|
| **Provider** | Ceylon Electricity Board (CEB) |
| **Official Portal URL** | [https://ceb.lk/publication-media/other-publications/en](https://ceb.lk/publication-media/other-publications/en) |
| **Direct Download URL** | `https://ceb.lk/front_img/img_reports/1751344341Statistical_Digest_2024.pdf` |
| **Publication Title** | CEB Statistical Digest 2024 Operational and Commercial Summary |
| **Reporting Period** | Calendar Year 2024 (with 2023 restated baseline) |
| **Retrieval Date** | 2026-10-30T17:21:30+05:30 |
| **Local Immutable File** | [Statistical_Digest_2024.pdf](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/data/raw/ceb/2024/Statistical_Digest_2024.pdf) |
| **File Checksum (SHA-256)** | `b0af3107c2eb4847e1b67cc7487e960f8c05e5d4501d0138b4c516e479d6905b` |
| **File Size** | 675,770 bytes |
| **Units & Measurements** | Peak Demand (MW), Installed Capacity (MW), Gross & Net Generation (GWh), Sales by Tariff (GWh), Sales by Province (GWh), Revenue (LKR Million), Loss Ratio (%) |
| **Data Granularity** | Annual totals, monthly provincial sales, and consumer accounts by tariff class |
| **Time Standard** | Sri Lanka Standard Time (UTC+05:30) |
| **Source Status** | DOWNLOADED_VERIFIED |
| **Profiling Report** | [ceb-statistical-digest-2024-profiling.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/data_sources/ceb-statistical-digest-2024-profiling.md) |
| **Citation / Reference** | Ceylon Electricity Board, Corporate Planning Division, Colombo, Sri Lanka |

---

## 2. Public Utilities Commission of Sri Lanka (PUCSL) — 15-Minute Generation Dispatch (March 2024)

| Field | Detail |
|---|---|
| **Provider** | Public Utilities Commission of Sri Lanka (PUCSL) / CEB System Control Centre |
| **Official Portal URL** | [https://www.pucsl.gov.lk/daily-generation-reports-2/](https://www.pucsl.gov.lk/daily-generation-reports-2/) |
| **Direct Download URL** | `https://www.pucsl.gov.lk/wp-content/uploads/2024/04/15-Minutes-Report-31-Mar2024.xlsx` |
| **Publication Title** | Daily 15-Minute Generation Dispatch Curves - March 2024 |
| **Reporting Period** | 2024-03-01 to 2024-03-31 (31 daily sheets) |
| **Retrieval Date** | 2026-10-30T17:21:30+05:30 |
| **Local Immutable File** | [15-Minutes-Report-31-Mar2024.xlsx](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx) |
| **File Checksum (SHA-256)** | `d40c7d9b11293e2c42c45227c4d121854e90781c3586bf204780d73fb282573b` |
| **File Size** | 917,216 bytes |
| **Units & Measurements** | Active Power in Megawatts (MW) per 15-minute interval; derived energy in MWh ($MW \times 0.25$) |
| **Data Granularity** | 15-minute discrete intervals (96 intervals per 24 hours) across 32 individual generating stations and aggregate streams |
| **Time Standard** | Sri Lanka Standard Time (UTC+05:30) |
| **Source Status** | DOWNLOADED_VERIFIED |
| **Profiling Report** | [pucsl-dispatch-15min-2024-profiling.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/data_sources/pucsl-dispatch-15min-2024-profiling.md) |
| **Citation / Reference** | PUCSL Electricity Sector Directorate & CEB System Control Centre |

---

## 3. Public Utilities Commission of Sri Lanka (PUCSL) — Daily Generation & Dispatch Report (29 Dec 2024)

| Field | Detail |
|---|---|
| **Provider** | Public Utilities Commission of Sri Lanka (PUCSL) |
| **Official Portal URL** | [https://www.pucsl.gov.lk/daily-generation-reports-2/](https://www.pucsl.gov.lk/daily-generation-reports-2/) |
| **Direct Download URL** | `https://www.pucsl.gov.lk/wp-content/uploads/2024/12/Generation-Report-29th-Dec.pdf` |
| **Publication Title** | Daily Generation and Dispatch Report - 29 December 2024 |
| **Reporting Period** | 2024-12-29 |
| **Retrieval Date** | 2026-10-30T17:21:30+05:30 |
| **Local Immutable File** | [Generation-Report-29th-Dec-2024.pdf](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/data/raw/pucsl/2024/Generation-Report-29th-Dec-2024.pdf) |
| **File Checksum (SHA-256)** | `bb10974c344b80f8795c4150153a6f2a823702cd81fade3d72899886a237ee3e` |
| **File Size** | 808,269 bytes |
| **Units & Measurements** | Plant Dispatch (MWh), Maximum & Available Capacity (MW), Night Peak Load (MW), Day/Night Peak Demand (MW), Reservoir Storage (GWh) |
| **Data Granularity** | Daily station totals, fuel mix totals, and instantaneous peak demand |
| **Time Standard** | Sri Lanka Standard Time (UTC+05:30) |
| **Source Status** | DOWNLOADED_VERIFIED |
| **Profiling Report** | [pucsl-generation-report-2024-profiling.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/data_sources/pucsl-generation-report-2024-profiling.md) |
| **Citation / Reference** | PUCSL Electricity Sector Directorate & CEB System Control Centre |

---

## 4. NASA POWER Project — Meteorological Grid Point Observations (2024)

| Field | Detail |
|---|---|
| **Provider** | NASA Prediction of Worldwide Energy Resources (POWER) Project |
| **Official Portal URL** | [https://power.larc.nasa.gov/docs/services/api/temporal/daily/](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) |
| **API Endpoint** | `https://power.larc.nasa.gov/api/temporal/daily/point` |
| **Publication Title** | NASA POWER Meteorological and Solar Radiation Sri Lanka Grid Nodes 2024 |
| **Reporting Period** | 2024-01-01 to 2024-01-31 (January 2024 sample across energy hubs) |
| **Retrieval Date** | 2026-10-30T17:21:30+05:30 |
| **Local Immutable File** | [nasa_power_sl_nodes_2024.json](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/data/raw/nasa/2024/nasa_power_sl_nodes_2024.json) |
| **File Checksum (SHA-256)** | `9574ed078fa4941c0e5cf1ec7a261448c0d7d90b042734a6b153066972d1be8b` |
| **File Size** | 14,177 bytes |
| **Units & Measurements** | Solar Irradiance ($kW\cdot h/m^2/day$ or $MJ/m^2/day$), Air Temperature ($^\circ C$), Relative Humidity (%), Wind Speed ($m/s$), Precipitation ($mm/day$) |
| **Data Granularity** | Daily observations per geospatial grid coordinate (Victoria Hydro Catchment, Mannar Wind Corridor) |
| **Time Standard** | Local Solar Time (LST / UTC+05:30) |
| **Source Status** | DOWNLOADED_VERIFIED |
| **Profiling Report** | [nasa-power-meteorological-2024-profiling.md](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/data_sources/nasa-power-meteorological-2024-profiling.md) |
| **Citation / Reference** | NASA Langley Research Center POWER Project |
