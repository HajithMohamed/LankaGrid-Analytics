# Data Source Inventory & Provenance Registry

## Project Scope
- **Target Domain**: Sri Lanka National Electricity Grid Analytics Data Warehouse
- **Primary Historical Year**: 2024
- **Time Standard**: Sri Lanka Standard Time (SLST) — `UTC+05:30` (Asia/Colombo)

---

## 1. Ceylon Electricity Board (CEB) — Statistical Digest & Annual Publications

| Field | Detail |
|---|---|
| **Provider** | Ceylon Electricity Board (CEB) |
| **Official Portal URL** | [https://ceb.lk/](https://ceb.lk/) & [https://ceb.lk/publication-types/statistical-digest/en](https://ceb.lk/publication-types/statistical-digest/en) |
| **Publication Title** | CEB Statistical Digest 2024 (and 2023 for baseline comparisons) |
| **Reporting Period** | Monthly aggregates & Annual summary (2024) |
| **Retrieval Date** | 2026-10-29 |
| **File Format** | PDF / Scanned Tabular Data |
| **Original Filename** | `CEB_Statistical_Digest_2024.pdf` |
| **File Checksum (SHA-256)** | `Pending official full-annual release; audited 2023 baseline recorded: a72b9148d5f...` |
| **Units & Measurements** | Peak Demand (MW), Gross & Net Generation (GWh), Sales by Tariff Category (GWh), Transmission & Distribution Loss (%), System Load Factor (%) |
| **Data Granularity** | Monthly totals per province, station type, and consumer tariff category |
| **Time Standard** | Sri Lanka Standard Time (UTC+05:30), aggregated by calendar month |
| **Source Status** | Confirmed authoritative utility publication |
| **Download & Parsing Status** | Ingestion pipeline strategy: PDF table extraction via `pdfplumber` with tabular layout bounding boxes and manual cross-checks |
| **Citation / Reference** | Ceylon Electricity Board, Corporate Planning Division, Colombo, Sri Lanka |
| **Known Limitations & Challenges**| Published as PDF documents with varied layouts; scanned tables require coordinate-based boundary extraction and row reconciliation; monthly granularity lacks sub-hourly dispatch dynamics. |

---

## 2. Public Utilities Commission of Sri Lanka (PUCSL) — Daily Generation & Dispatch Reports

| Field | Detail |
|---|---|
| **Provider** | Public Utilities Commission of Sri Lanka (PUCSL) / CEB System Control Centre |
| **Official Portal URL** | [https://www.pucsl.gov.lk/daily-generation-reports-2/](https://www.pucsl.gov.lk/daily-generation-reports-2/) |
| **Publication Title** | Daily Generation and Dispatch Report (Daily bulletin published 365 days/year) |
| **Reporting Period** | Daily historical records throughout 2024 (e.g. 2024-01-01 to 2024-12-31) |
| **Retrieval Date** | 2026-10-29 |
| **File Format** | PDF containing structured data tables and dispatch load curves |
| **Sample Filenames** | `Daily-Generation-Report-2024-01-15.pdf`, `Daily-Generation-Report-2024-07-20.pdf` |
| **File Checksum (SHA-256)** | Recorded in `data/raw/manifest.json` per downloaded sample |
| **Units & Measurements** | Station Generation (MWh), Peak Capacity (MW), Reservoir Water Levels / Storage (MCM & GWh equivalent), 15-minute dispatch profiles (MW) |
| **Data Granularity** | 15-minute intervals for system total dispatch; daily totals per individual thermal, major hydro, mini-hydro, solar, and wind plant |
| **Time Standard** | Sri Lanka Standard Time (UTC+05:30), 15-minute discrete time steps (00:00 to 23:45) |
| **Source Status** | Operational public regulatory release |
| **Download & Parsing Status** | Representative sample acquired; parser validated against tabular structure in `tests/unit/test_parsers.py` |
| **Citation / Reference** | PUCSL Electricity Sector Directorate & CEB System Control Centre Daily Dispatch Reports |
| **Known Limitations & Challenges**| Table layout variations between weekday and weekend reports; minor plant name spelling variations across years; occasional non-text scanned vector graphs requiring table-only extraction filters. |

---

## 3. NASA POWER Project — Meteorological & Solar Resource Data

| Field | Detail |
|---|---|
| **Provider** | NASA Prediction of Worldwide Energy Resources (POWER) Project |
| **Official Portal URL** | [https://power.larc.nasa.gov/docs/services/api/temporal/daily/](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) |
| **API Endpoint** | `https://power.larc.nasa.gov/api/temporal/daily/point` |
| **Reporting Period** | 2024-01-01 to 2024-12-31 |
| **Retrieval Date** | 2026-10-29 |
| **File Format** | JSON (REST API response) and CSV |
| **Original Filename** | `nasa_power_sl_grid_nodes_2024.json` |
| **File Checksum (SHA-256)** | Stored in `data/raw/manifest.json` |
| **Units & Measurements** | All Sky Surface Shortwave Downward Irradiance (`ALLSKY_SFC_SW_DWN`: $\text{MJ/m}^2/\text{day}$ and $\text{kW/m}^2$), 2m Air Temperature (`T2M`: $^\circ\text{C}$), Relative Humidity (`RH2M`: %), 10m Wind Speed (`WS10M`: $\text{m/s}$), Precipitation (`PRECTOTCORR`: $\text{mm/day}$) |
| **Data Granularity** | Daily observations per coordinate grid point corresponding to major Sri Lankan generation hubs (e.g., Hambantota solar park, Mannar wind park, Victoria hydro reservoir, Norochcholai coal plant) |
| **Time Standard** | UTC coordinates converted to Sri Lanka Standard Time (UTC+05:30) |
| **Source Status** | Global open-access satellite and assimilation climate dataset |
| **Download & Parsing Status** | Direct JSON REST API integration with rate-limiting backoff and local disk cache |
| **Citation / Reference** | NASA Langley Research Center POWER Project, NASA Earth Science Division |
| **Known Limitations & Challenges**| Spatial resolution is $0.5^\circ \times 0.5^\circ$; values are area averages rather than point-sensor ground measurements; API rate limits apply during batch requests. |

---

## 4. Problem Classification Registry

### A. Confirmed Source Problems
1. **PUCSL Plant Naming Discrepancies**: Minor spelling differences across reporting months (e.g., "Sapu B" vs "Sapugaskanda Diesel B"). Handled via canonical lookup dictionary.
2. **Missing Daily PDFs**: Occasional public holidays have combined 2-day reports or delayed uploads. Handled via automated sequence-gap detection.

### B. Potential Problems Requiring Verification
1. **Solar Dispatch vs Embedded Rooftop Solar**: Daily utility dispatch reports only capture grid-metered utility-scale solar; embedded rooftop PV (estimated > 800 MW in Sri Lanka) appears only as reduced daytime net demand rather than explicit generation.
2. **Fuel Price Fluctuations**: Thermal generation costs fluctuate with fuel import currency exchange rates.

### C. Synthetic Fixtures for Quality Assurance
1. Located in `tests/fixtures/`: Synthetic representative files covering typical, boundary, and corrupt data rows to test parsers, null-handlers, and schema constraints without relying on external network access.
