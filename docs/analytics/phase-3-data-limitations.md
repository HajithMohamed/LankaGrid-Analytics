# Phase 3 Data Boundaries, Scope Limitations & Quality Disclosures
## GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka

In strict compliance with the **Antigravity Agent Governance** data integrity rules and Lecture 6 data cleaning protocols, this document transparently records all historical boundaries, scope differences, missing fields, and quarantined records.

---

## 1. Historical Dataset Temporal Boundaries

| Dataset | Source Provider | Historical Window | Coverage Granularity | Verified Record Count |
|---|---|---|---|---|
| **Electricity Sales by Sector** | Ceylon Electricity Board (CEB) Statistical Digest | 2020–2024 (5 Years) | Annual per sector | 49 Audited Rows |
| **Meteorological Observations** | NASA POWER Agroclimatology | 2020–2024 (5 Years) | Daily across 2 monitoring stations (Victoria Catchment & Mannar Wind) | 21,924 Observations |
| **System Dispatch Telemetry** | Public Utilities Commission of Sri Lanka (PUCSL) | March 1–31, 2024 | 15-Minute per station | 107,115 Facts |

---

## 2. Operational Scope Differences (Dispatch vs Statistical Digest)

1. **Embedded Rooftop Solar PV**:
   - The PUCSL 15-minute dispatch telemetry workbook monitors grid-scale power stations and major utility feeders connected to the CEB transmission network.
   - Rooftop solar installations under Net Metering, Net Accounting, and Net Plus schemes generate electricity behind the customer's utility meter.
   - Consequently, rooftop solar generation **does not appear in the 15-minute active dispatch telemetry** ($MW$), but its impact is physically manifested as reduced gross grid daytime demand and lower billed domestic sales in CEB annual digests.
   - Analysts must not mistake low utility solar dispatch (1.63% of grid dispatch) for total national solar utilization.

2. **Untelemetered Mini Hydro & Biomass**:
   - Small private Mini Hydro plants and Agricultural Biomass generators are grouped into regional bulk dispatch aggregates in the PUCSL sheets rather than individually sub-metered per turbine.
   - The warehouse preserves these aggregate reporting entities (e.g., `Mini Hydro (Total)`, `Biomass (Total)`) as distinct entities in `dw.dim_power_plant`.

---

## 3. Source Discrepancies and Missing Fields

1. **Consumer Account Counts on LECO Bulk Supply**:
   - In the CEB Audited Statistical Digest (Page 5, Sales by Tariff Category), the line item for LECO bulk supply reports total billed energy (`energy_sold_mwh = 1,520,000 to 1,640,000 MWh`) and billed revenue, but leaves `consumer_account_count` as `NULL`.
   - **Handling**: In adherence to the core rule *"Never treat missing as zero"*, the loader preserves `consumer_account_count = NULL` for LECO, preventing distortion of customer density and average consumption per consumer calculations.

2. **Quarantine Accounting of Negative Power Readings (Barge Plant)**:
   - In the authentic PUCSL March 2024 dispatch workbook (`15-Minutes-Report-31-Mar2024.xlsx`), exactly **21 readings** for `Barge` thermal station report negative numbers (e.g. `-0.1 MW` to `-0.8 MW`).
   - In electricity engineering, small negative readings during shutdown reflect station auxiliary power consumption imported from the grid to keep station transformers and lubrication systems energized.
   - Because `dw.fact_dispatch_interval` has an explicit non-negative check constraint (`ck_fdi_power_nonnegative: active_power_mw >= 0.0`), these 21 anomalous rows were automatically quarantined during ETL into `staging.stg_dispatch_observation` (`row_status = 'quarantined'`), with corresponding issue logs in `audit.data_quality_issue` under rule `DQ_GEN_NEGATIVE_OUTPUT`.
   - Staging Total: 107,136 readings $\rightarrow$ Quarantined: 21 rows $\rightarrow$ Loaded Facts: **107,115 clean facts**.

---

## 4. Academic Guidance for Downstream Analysts

- **No Data Fabrication**: Where daily generation reports for specific days outside March 2024 were unavailable in the PUCSL portal, they were not interpolated or synthesized.
- **Unit Integrity**: Always distinguish active power rate ($MW$) from integrated energy volume ($MWh$). For 15-minute intervals, $MWh = MW \times 0.25\text{ hours}$.
- **Reconciliation Precedence**: When annual statistical digests and daily operational reports differ slightly, CEB audited annual statistical digests hold precedence for financial and billing reconciliation, while PUCSL 15-minute reports hold precedence for intraday load profiling and ramping dynamics.

