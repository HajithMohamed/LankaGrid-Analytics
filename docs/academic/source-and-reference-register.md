# Data Source Provenance & Academic Reference Register
## National Electricity Grid Analytics Data Warehouse — Sri Lanka (GridLens)

**Document Reference:** `docs/academic/source-and-reference-register.md`  
**Purpose:** Formal academic source citations, primary data provider metadata, digital object identifiers (DOIs), and verification registry.  

---

## 1. Primary Empirical Data Source Registry

| Source ID | Institution / Data Provider | Official Publication Title | Reporting Period | Storage Location | Checksum Verification | Physical Granularity |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| **SRC-PUCSL-01** | Public Utilities Commission of Sri Lanka (PUCSL) | *15-Minutes-Report-31-Mar2024.xlsx* (Transmission System Operational Dispatch Telemetry) | March 1–31, 2024 (744 Hours) | `data/raw/pucsl/2024/` | Recorded in `data/raw/manifest.json` | 15-Minute interval active power (MW) per generator unit |
| **SRC-PUCSL-02** | Public Utilities Commission of Sri Lanka (PUCSL) | *Daily Generation & Dispatch Reports* (Operational Daily Sheets) | March 2024 | `data/raw/pucsl/` | Verified against Sheet `01.03` control totals | Daily integrated energy (MWh) by utility & IPP category |
| **SRC-CEB-01** | Ceylon Electricity Board (CEB) — Corporate Planning Division | *CEB Statistical Digest 2020* | Jan 1, 2020 – Dec 31, 2020 | `data/raw/ceb/` | SHA-256 Verified | Annual billed sales (GWh) by consumer tariff sector & province |
| **SRC-CEB-02** | Ceylon Electricity Board (CEB) — Corporate Planning Division | *CEB Statistical Digest 2021* | Jan 1, 2021 – Dec 31, 2021 | `data/raw/ceb/` | SHA-256 Verified | Annual billed sales (GWh) by consumer tariff sector & province |
| **SRC-CEB-03** | Ceylon Electricity Board (CEB) — Corporate Planning Division | *CEB Statistical Digest 2022* | Jan 1, 2022 – Dec 31, 2022 | `data/raw/ceb/` | SHA-256 Verified | Annual billed sales (GWh) by consumer tariff sector & province |
| **SRC-CEB-04** | Ceylon Electricity Board (CEB) — Corporate Planning Division | *CEB Statistical Digest 2023* | Jan 1, 2023 – Dec 31, 2023 | `data/raw/ceb/` | SHA-256 Verified | Annual billed sales (GWh) by consumer tariff sector & province |
| **SRC-CEB-05** | Ceylon Electricity Board (CEB) — Corporate Planning Division | *CEB Statistical Digest 2024* (Provisional Audited Accounts) | Jan 1, 2024 – Dec 31, 2024 | `data/raw/ceb/` | SHA-256 Verified | Annual billed sales (GWh) by consumer tariff sector & province |
| **SRC-NASA-01** | NASA Langley Research Center — POWER Project | *NASA POWER Daily Meteorological Reanalysis API (MERRA-2 / GEOS-FP)* | Jan 1, 2020 – Dec 31, 2024 (1,827 Days) | `data/raw/nasa_power/` | SHA-256 Verified | Daily solar irradiance ($MJ/m^2$), air temp ($^\circ C$), rain ($mm$), wind ($m/s$) |
| **SRC-SLSEA-01** | Sri Lanka Sustainable Energy Authority (SLSEA) | *National Energy Balance & Renewable Resource Atlas* | 2020–2024 | `docs/data_sources/` | Registry Cross-Reference | Plant nameplate capacities (MW) and grid interconnects |

---

## 2. Academic Literature & Textual Citations

1. **Kimball, R., & Ross, M. (2013).** *The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling (3rd ed.)*. John Wiley & Sons.
   - *Applied in GridLens:* Fact constellation schema design, fact granularity definitions, conformed dimensions (`dim_date`, `dim_power_plant`, `dim_tariff_sector`), non-additive measure handling (Lecture 1–4).
2. **Inmon, W. H. (2005).** *Building the Data Warehouse (4th ed.)*. John Wiley & Sons.
   - *Applied in GridLens:* Enterprise data architecture, immutable staging area decoupling, audit and provenance tracking.
3. **Gray, J., Bosworth, A., Layman, A., & Pirahesh, H. (1997).** *Data Cube: A Relational Aggregation Operator Generalizing Group-By, Cross-Tab, and Sub-Totals*. Data Mining and Knowledge Discovery, 1(1), 29–53.
   - *Applied in GridLens:* `ROLLUP` (Q01), `CUBE` (Q15), and `GROUPING SETS` (Q21, Q23) query engineering (Lecture 8).
4. **PostgreSQL Global Development Group. (2024).** *PostgreSQL 18 Documentation: Table Partitioning, Materialized Views, and Window Functions*.
   - *Applied in GridLens:* Declarative range partitioning (`PARTITION BY RANGE (date_key)`), unique indexing for `REFRESH MATERIALIZED VIEW CONCURRENTLY`, `LAG()` first derivatives.
5. **Public Utilities Commission of Sri Lanka (PUCSL). (2024).** *Electricity Transmission System Operational Performance Reports (March 2024)*. Colombo, Sri Lanka.
   - *Applied in GridLens:* 15-minute SCADA telemetry integration, reconciliation control benchmarks (Sheet `01.03`).
6. **Ceylon Electricity Board (CEB). (2020–2024).** *Statistical Digests: Five-Year Electrical Energy Balance, Billed Consumption & Customer Accounts*. Colombo, Sri Lanka.
   - *Applied in GridLens:* Tariff sales facts (`dw.fact_electricity_sales`), sector trajectory and CAGR analysis (Q09–Q12).
7. **Stackhouse, P. W., et al. (2020).** *NASA POWER: Prediction of Worldwide Energy Resources Solar and Meteorological Datasets for Renewable Energy Modeling*. NASA Langley Research Center.
   - *Applied in GridLens:* Climatic observations for Victoria Catchment (`LOC_VICTORIA_CATCHMENT`) and Mannar Wind Farm (`LOC_MANNAR_WIND`).
8. **Box, G. E., Jenkins, G. M., Reinsel, G. C., & Ljung, G. M. (2015).** *Time Series Analysis: Forecasting and Control (5th ed.)*. John Wiley & Sons.
   - *Applied in GridLens:* Centered moving average trend extraction, smoothing window frames `ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING` (Q02, Lecture 5).

---

## 3. Provenance & Integrity Statement

Every numerical figure, operational boundary, and seasonal trend presented in the GridLens documentation and analytical outputs is derived strictly from the official primary data sources listed above. **No measurements, sales figures, plant capacities, or meteorological facts have been fabricated, synthesized, or unfaithfully altered.**

