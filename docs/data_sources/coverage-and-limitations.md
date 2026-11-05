# Data Warehouse Historical Coverage, Boundary Constraints & Limitations

## Overview

GridLens models real, authoritative electricity grid and meteorological data from Sri Lanka. In strict adherence to warehouse governance and engineering integrity rules, **no synthetic measurements are ever fabricated**. Where data is unavailable from public authorities, the gaps are explicitly recognized, documented, and enforced in schema definitions.

---

## 1. Authoritative Historical Coverage

### CEB Billed Electricity Sales (2020–2024)
- **Temporal Horizon:** Full 5 calendar years (2020, 2021, 2022, 2023, 2024).
- **Spatial Coverage:** All 9 Sri Lankan administrative provinces (Western, Central, Southern, Northern, Eastern, North Western, North Central, Uva, Sabaragamuwa).
- **Sectoral Scope:** Domestic, Religious, Industrial, Commercial/Hotel, General Purpose, Government, Street Lighting, and LECO (Lanka Electricity Company) bulk sales.
- **Physical Measures:** Billed energy consumption ($MWh$), billed consumer revenue ($LKR$), active utility customer accounts, and average effective tariff rates ($LKR/kWh$).
- **Status in Warehouse:** **49 validated rows** loaded into `dw.fact_electricity_sales`.

### NASA POWER Meteorological Observations (2020–2024)
- **Temporal Horizon:** 5 continuous calendar years (2020-01-01 through 2024-12-31, 1,827 days per node).
- **Spatial Coverage:** 7 high-voltage grid transmission nodes representative of Sri Lanka's climate zones:
  1. *Colombo Grid Substation* (Western Province - Coastal Urban)
  2. *Kotmale Grid Substation* (Central Province - Wet Mountain / Major Hydro catchment)
  3. *Anuradhapura Grid Substation* (North Central Province - Dry Zone Solar Corridor)
  4. *Trincomalee Grid Substation* (Eastern Province - Northeast Monsoon corridor)
  5. *Hambantota Grid Substation* (Southern Province - High Solar & Wind corridor)
  6. *Jaffna Grid Substation* (Northern Province - Dry Zone Solar & Wind)
  7. *Badulla Grid Substation* (Uva Province - Intermediate Montane)
- **Physical Measures:** Surface all-sky solar insolation / Peak Sun Hours ($kWh/m^2/day$), daily precipitation ($mm$), daily maximum/minimum/average temperatures ($^\circ C$), and 10-meter wind speed ($m/s$).
- **Status in Warehouse:** **21,924 verified observations** loaded into `dw.fact_weather_daily`.

### PUCSL Sub-Daily Generation Dispatch Curves (March 2024)
- **Temporal Horizon:** Full month of March 2024 (2024-03-01 to 2024-03-31, all 31 days).
- **Temporal Resolution:** 96 continuous 15-minute intervals per 24-hour cycle.
- **Fleet Coverage:** 32 distinct generation stations, including major thermal (Lakvijaya Coal, Kelanitissa Combined Cycle, West Coast / Yugadanavi), major hydro (Victoria, Kotmale, Upper Kotmale, Samanalawewa, Randenigala, Laxapana complex), and non-conventional renewable aggregations (mini-hydro, solar, wind).
- **Status in Warehouse:** **107,115 validated telemetry records** loaded into `dw.fact_dispatch_interval_y2024`.

---

## 2. Gaps & Physical Limitations

### 1. Sub-Daily Telemetry Outside March 2024
- High-resolution 15-minute dispatch sheets are published by PUCSL as monthly multi-tab spreadsheets. While March 2024 provides 107k+ data points, sub-daily telemetry for other months/years is not currently ingested in the repository.
- **Warehouse Handling:** Partitions `fact_dispatch_interval_y2020` through `y2023`, `y2025`, and `y2026` exist as empty physical partitions. The warehouse will automatically route future incremental sheets to these partitions without schema alterations.

### 2. Physical Meaning of Missing Values vs. Zero
- **Never Treat Missing Measurements as Zero:**
  - $0\text{ MW}$ signifies an active, recorded reading that a power plant was completely offline, shut down, or producing zero generation (e.g., solar PV at midnight).
  - An omitted, unrecorded, or unparsed interval is strictly stored as `NULL`.
  - Storing `NULL` as $0\text{ MW}$ would severely distort capacity factors, load duration curves, and loss calculations.

### 3. LECO Bulk Sales Reconciliation
- In Sri Lanka, CEB sells bulk electricity to LECO (Lanka Electricity Company), which distributes it to consumers in coastal urban areas (e.g. Negombo, Galle, suburban Western Province).
- In CEB provincial sales digests, LECO bulk supply is reported as a separate line item. Summing CEB retail province sales with LECO bulk supply must be done carefully to avoid double-counting retail end-users.

### 4. Auxiliary Consumption & Transmission Loss Boundaries
- Instantaneous dispatch curves record gross active power generated at plant busbars.
- Net sent-out energy equals gross generation minus auxiliary parasitic station consumption (typically 6–8% for steam coal, 2–3% for gas turbines, <1% for hydro).
- System gross generation minus transmission/distribution losses equals metered retail consumption. GridLens cross-source reconciliation tracks this discrepancy in `audit.reconciliation_case`.

