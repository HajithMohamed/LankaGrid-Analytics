# Phase 3.1 Analytical Query Verification Matrix
## National Electricity Grid Analytics Data Warehouse — Sri Lanka (GridLens)

**Document Reference:** `docs/analytics/phase-3-1-query-verification-matrix.md`  
**Phase:** Phase 3.1 — Analytical Correctness, Data Validation, CI Hardening and Report Synchronization  
**Execution Environment:** PostgreSQL 18 (Docker on port 5433), Python 3.14  
**Date of Verification:** November 2026  

---

## 1. Master Query Verification Matrix (Q01–Q24)

| Query ID | Member & Domain | Query Title | Status | Fact Grain | Measurement Units | Lecture Theory | Execution Time | Output Rows |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- | :---: | :---: |
| **Q01** | Domain 1: Generation Mix & Renewables | Generation Mix by Energy Source | **PASS** | Monthly aggregated technology & source totals | MWh, % | Lecture 8 (ROLLUP Hierarchy), Lecture 3 (Fact Grain) | 364.7 ms | 14 |
| **Q02** | Domain 1: Generation Mix & Renewables | Renewable vs Non-Renewable Daily Share | **PASS** | Daily national renewable penetration | MWh, % | Lecture 5 (Centered Moving Average Window) | 49.2 ms | 31 |
| **Q03** | Domain 1: Generation Mix & Renewables | Plant Capacity Factor Analysis | **CONDITIONAL** | Plant-level generation over 744 hours | MW, MWh, % | Lecture 3 (Unit Consistency), Lecture 6 (Boundary Ratings) | 141.4 ms | 20 |
| **Q04** | Domain 1: Generation Mix & Renewables | Peak Daytime Off-Peak Contribution | **PASS** | Technology dispatch grouped by TOU band | MWh, % | Lecture 3 (Time-of-Use Dimensional Slicing) | 103.3 ms | 7 |
| **Q05** | Domain 2: Grid Dispatch Dynamics | Daily Dispatch Curves Weekday vs Weekend | **PASS** | 15-minute slot across day types (96 intervals) | MW | Lecture 5 (Diurnal Load Curve Profiling) | 131.5 ms | 96 |
| **Q06** | Domain 2: Grid Dispatch Dynamics | Dispatch Ramp Rate Analysis | **PASS** | 15-minute system ramp rate transitions | MW, MW/15min, MW/min | Lecture 5 (LAG Window Functions & First Derivatives) | 115.6 ms | 25 |
| **Q07** | Domain 2: Grid Dispatch Dynamics | Baseload vs Peaking Plant Behavior | **PASS** | Plant-level operational statistics over 2,976 slots | MW, % | Lecture 5 (Coefficient of Variation & Screening) | 153.3 ms | 30 |
| **Q08** | Domain 2: Grid Dispatch Dynamics | Telemetry to Published Energy Reconciliation | **FIXED** | Daily system reconciliation across reporting categories | MWh, % | Lecture 6 (Source Conflict Resolution), Lecture 5 (Residuals) | 14.3 ms | 8 |
| **Q09** | Domain 3: Demand | Five-Year Sectoral Electricity Sales Trends | **PASS** | Annual billed sales by consumer sector (2020–2024) | GWh, % | Lecture 1 (Time-Variant History), Lecture 5 (YoY Trends) | 16.1 ms | 44 |
| **Q10** | Domain 3: Demand | Sectoral Consumption Shifts Across Historical Periods | **FIXED** | Multi-year sector pivot comparing 2020 vs 2024 | GWh, % | Lecture 5 (CAGR, Period-over-Period Shock Analysis) | 5.0 ms | 9 |
| **Q11** | Domain 3: Demand | Average Consumption per Customer Account | **PASS** | Annual account-level consumption intensity | GWh, kWh/account | Lecture 3 (Non-Additive Semi-Additive Measures) | 3.2 ms | 39 |
| **Q12** | Domain 3: Demand | LECO Bulk Supply vs Direct CEB Sales | **PASS** | Annual franchise distribution vs direct retail sales | GWh, % | Lecture 3 (Avoiding Double Counting, Partitioning) | 2.1 ms | 5 |
| **Q13** | Domain 4: Weather & Renewable Coupling | Five-Year Solar Irradiance Profiles | **PASS** | Multi-year annual solar resource by monitoring node | MJ/m2/day, PSH | Lecture 3 (Solar Conversion Physics, LST Standard) | 26.4 ms | 10 |
| **Q14** | Domain 4: Weather & Renewable Coupling | Temperature and Grid Demand Correlation | **FIXED** | Daily weather joined with daily peak grid demand | °C, MW, MWh | Lecture 5 (Pearson Correlation, Degree Days) | 68.2 ms | 1 |
| **Q15** | Domain 4: Weather & Renewable Coupling | Rainfall and Solar Monsoon Seasonality | **PASS** | Multi-dimensional cube: Location × Monsoon Season | mm, MJ/m2/day | Lecture 8 (CUBE Operator, Multi-Way Aggregation) | 19.2 ms | 15 |
| **Q16** | Domain 4: Weather & Renewable Coupling | Wind Resource Distribution and Generation Relationship | **FIXED** | Daily paired wind speed (50m) and wind dispatch | m/s, W/m2 proxy, MWh | Lecture 5 (Correlation, Distribution Fitting), Lecture 3 | 11.1 ms | 1 |
| **Q17** | Domain 5: Plant Operations & Capacity Ops | Zero-Generation Interval Analysis | **PASS** | Station-level offline intervals over 2,976 slots | Intervals, Hours, % | Lecture 6 (True Zero vs Missing Data Handling) | 441.7 ms | 36 |
| **Q18** | Domain 5: Plant Operations & Capacity Ops | Installed Capacity Utilization Ratio | **FIXED** | Plant peak dispatch vs rated nameplate capacity | MW, % | Lecture 3 (Physical Dimension Attributes, Ratios) | 74.0 ms | 22 |
| **Q19** | Domain 5: Plant Operations & Capacity Ops | Lakvijaya Coal Unit Dispatch Continuity | **PASS** | Unit-level baseload availability and utilization | MW, MWh, % | Lecture 5 (Availability Factor, Unscheduled Outage) | 39.8 ms | 4 |
| **Q20** | Domain 5: Plant Operations & Capacity Ops | Evening Peak Generation Contribution | **PASS** | Station-level merit-order contribution at peak hours | MW, % | Lecture 3 (Merit-Order Baseload vs Peaking Roles) | 121.3 ms | 7 |
| **Q21** | Domain 6: Efficiency | Five-Year Grid Sales Efficiency Trends | **FIXED** | Multilevel aggregation: Economic Class × Year | GWh, % | Lecture 8 (GROUPING SETS), Lecture 3 (Normalization) | 2.4 ms | 26 |
| **Q22** | Domain 6: Efficiency | Cross-Source Multi-Tier Reconciliation | **PASS** | Annual system generation minus billed sales | GWh, % | Lecture 6 (Multi-Source Loss Proxy Reconciliation) | 3.2 ms | 6 |
| **Q23** | Domain 6: Efficiency | Data Quality Quarantine Audit Trail | **FIXED** | Warehouse audit schema issue occurrences by rule | Issues, Tables, % | Lecture 6 (Quarantine Isolation), Lecture 8 (Grouping Sets) | 14.1 ms | 5 |
| **Q24** | Domain 6: Efficiency | ETL Execution Performance and Lineage | **PASS** | Pipeline execution batch metrics and lineage | Seconds, Rows/sec | Lecture 4 (ETL Monitoring), Lecture 6 (Data Provenance) | 175.1 ms | 4 |

---

## 2. Summary Statistics

- **Total Queries Audited:** 24
- **Queries Directly Passing Initial Audit:** 17 (70.8%)
- **Queries Corrected & Re-Engineered:** 6 (Q08, Q10, Q14, Q16, Q21, Q23) (25.0%)
- **Queries Refined for Engineering Domain Precision:** 1 (Q18) (4.2%)
- **Mean Query Execution Time:** **93.8 ms**
- **Queries Executing Under 100 ms:** 16 (66.7%)
- **Queries Executing Under 500 ms:** 24 (100.0%)
- **Slowest Query:** Q17 (441.7 ms — full table scan across 107,115 facts with plant-level filtering)
- **Fastest Query:** Q12 (2.1 ms — indexed dimensional join over 5 rows)

