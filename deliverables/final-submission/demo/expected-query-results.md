# Master Expected Query Results Reference (Q01–Q24)
## National Electricity Grid Analytics Data Warehouse — Sri Lanka (GridLens)

**Document Reference:** `docs/demo/expected-query-results.md`  
**Purpose:** Official benchmark reference for live system demonstration, manual query auditing, and student presentation reference.  
**Database Target:** PostgreSQL 18 (`sl_grid_warehouse`)  
**All metrics verified against authentic warehouse tables and official source publications.**  

---

## 1. Master Query Reference Table

| Query ID | Member & Domain | Query Title | Key Analytical Output Numbers | Rows | Typical Runtime | Lecture Theory & Concept |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **Q01** | Member 1: Generation | Generation Mix by Energy Source | Total: 1,399,337.00 MWh; Coal: 595,524.50 MWh (42.56%); Oil: 387,450.75 MWh (27.69%); Hydro: 321,595.50 MWh (22.98%); NCRE: 94,766.25 MWh (6.77%). | 14 | 360–600 ms | Lecture 8 (`ROLLUP` hierarchy), Lecture 3 (Fact grain). |
| **Q02** | Member 1: Generation | Renewable vs Non-Renewable Daily Share | Mean Renewable Share: 29.75%; Low: 27.13% (March 18); High: 34.68% (March 31); 7-day centered moving average smoothed. | 31 | 40–55 ms | Lecture 5 (Centered moving average window functions). |
| **Q03** | Member 1: Generation | Plant Capacity Factor Analysis | Lakvijaya Coal units: 88.74%–89.15% CF; Kelanitissa CC: 82.43% CF; Victoria Hydro: 38.15% CF; Kotmale Hydro: 12.21% CF. | 20 | 120–150 ms | Lecture 3 (Non-additive ratios), Lecture 6 (Boundary ratings). |
| **Q04** | Member 1: Generation | Peak Daytime Off-Peak Contribution | Evening Peak (18:30–22:30): Hydro surges to 32.40% (vs 20.95% Day); Solar drops to 0.00%; Coal supplies 39.67%. | 7 | 100–120 ms | Lecture 3 (Time-of-Use TOU dimensional slicing). |
| **Q05** | Member 2: Dispatch | Daily Dispatch Curves Weekday vs Weekend | Weekday peak: 2,476.32 MW (Slot 77, 19:15); Weekend peak: 2,241.18 MW (9.50% reduction); Baseload night trough: 1,280–1,340 MW. | 96 | 90–130 ms | Lecture 5 (Diurnal load curve profiling across 96 slots). |
| **Q06** | Member 2: Dispatch | Dispatch Ramp Rate Analysis | Max system surge: +141.00 MW (+9.40 MW/min) on Sunday, March 17 at 18:30 (Slot 75); Steepest drop: -122.40 MW at 22:45. | 25 | 105–125 ms | Lecture 5 (`LAG` window functions, discrete first derivatives). |
| **Q07** | Member 2: Dispatch | Baseload vs Peaking Plant Behavior | Lakvijaya Coal: Availability 100.0%, $CV = 0.09$ (Baseload); Kotmale: $CV = 0.94$, 43.8% avail; Upper Kotmale: $CV = 1.39$ (Peaking). | 30 | 140–160 ms | Lecture 5 (Coefficient of variation $CV$, operational screening). |
| **Q08** | Member 2: Dispatch | Telemetry to Published Energy Reconciliation | Telemetered: 46,308.00 MWh; Published (Sheet 01.03): 48,223.00 MWh; Variance: +1,915.00 MWh (3.97%); Solar: +1,728.20 MWh; Mini Hydro: +302.80 MWh. | 8 | 10–18 ms | Lecture 6 (Source conflict resolution), Lecture 5 (Residuals). |
| **Q09** | Member 3: Demand | Five-Year Sectoral Electricity Sales Trends | Billed total: 14,287 GWh (2020) to 15,190.5 GWh (2024); Domestic: 5,090 GWh to 4,701 GWh; Industrial: 4,164 GWh to 4,622 GWh. | 44 | 12–18 ms | Lecture 1 (Time-variant history), Lecture 5 (YoY trends). |
| **Q10** | Member 3: Demand | Sectoral Consumption Shifts Across Historical Periods | Hotel Sector: 193.00 GWh (2020) to 355.00 GWh (2024) (+83.94% gain, +16.46% CAGR); Domestic: -7.64% drop (-1.97% CAGR). | 9 | 4–7 ms | Lecture 5 (Compound annual growth rate CAGR, economic shocks). |
| **Q11** | Member 3: Demand | Average Consumption per Customer Account | Domestic intensity: 71.3 kWh/acct/mo (2021) dropping to 62.4 kWh (2023) following tariff hikes; Hotel intensity: 2,890 to 4,460 kWh/acct/mo. | 39 | 2–5 ms | Lecture 3 (Non-additive vs semi-additive measures). |
| **Q12** | Member 3: Demand | LECO Bulk Supply vs Direct CEB Sales | LECO bulk purchases: 1,539 to 1,633 GWh/year (10.67% to 11.23% share of national consumption); CEB retail: 12,614.5 to 13,581 GWh. | 5 | 1–3 ms | Lecture 3 (Avoiding double-counting, franchise partitioning). |
| **Q13** | Member 4: Weather | Five-Year Solar Irradiance Profiles | Mannar: 18.57 MJ/m²/day (5.16 PSH/day); Victoria Catchment: 18.31 MJ/m²/day (5.09 PSH/day); Pre-monsoon peak in March–April (5.8–6.4 PSH). | 10 | 25–45 ms | Lecture 3 (Solar energy unit conversion: $1\text{ PSH} = 3.6\text{ MJ/m}^2$). |
| **Q14** | Member 4: Weather | Temperature and Grid Demand Correlation | Two-station mean temp vs peak dispatch: $r = +0.0083$ (near zero); Two-station mean temp vs daily total energy: $r = +0.1248$ (mild positive). | 1 | 65–90 ms | Lecture 5 (In-database Pearson correlation `CORR`). |
| **Q15** | Member 4: Weather | Rainfall and Solar Monsoon Seasonality | 5-year total rainfall: 16,929.50 mm; Victoria: 10,757.20 mm (63.54%, Second Inter-Monsoon peak 3,421.10 mm); Mannar: 6,172.30 mm (36.46%). | 15 | 12–20 ms | Lecture 8 (`CUBE` multi-way dimensional cross-tabulation). |
| **Q16** | Member 4: Weather | Wind Resource Distribution & Generation Relationship | Mean 50m wind speed: 5.37 m/s (2.90–7.73 m/s); Linear correlation with wind dispatch: $r = +0.7143$; Cubic correlation: $r(v^3) = +0.7132$. | 1 | 10–15 ms | Lecture 5 (Physical resource coupling, aerodynamic wind power). |
| **Q17** | Member 5: Plant Ops | Zero-Generation Interval Analysis | Lakvijaya Units 1–3: 0 offline intervals (100% duty cycle); Victoria Hydro: 114 offline intervals (96.2% duty); Bowatenna: 2,723 offline (8.5% duty). | 36 | 350–450 ms | Lecture 6 (True zero vs missing data sentinel preservation). |
| **Q18** | Member 5: Plant Ops | Installed Capacity Utilization Ratio | 10 stations delivered $\ge 95\%$ of nameplate rating; 6 stations recorded dispatch exceeding reference ratings (Polpitiya 116.0%, West Coast 107.0%). | 22 | 70–90 ms | Lecture 3 (Physical dimension attributes, capacity envelopes). |
| **Q19** | Member 5: Plant Ops | Lakvijaya Coal Unit Dispatch Continuity | Unit 1: 198,478.00 MWh; Unit 2: 198,973.00 MWh; Unit 3: 198,073.50 MWh; Total: 595,524.50 MWh with 0 forced outages across 744 hours. | 4 | 35–45 ms | Lecture 5 (Availability factor, forced outage tracking). |
| **Q20** | Member 5: Plant Ops | Evening Peak Generation Contribution | Evening Peak (18:30–22:30): Coal provides 39.67%, Major Hydro 32.40%, Thermal Oil 23.19%; Gas Turbines: 0.00% (reserve). | 7 | 105–125 ms | Lecture 3 (Merit-order ranking, fast-ramping peaker roles). |
| **Q21** | Member 6: Efficiency | Five-Year Grid Sales Efficiency Trends | Productive economic share expanded from 50.35% (7,194 GWh) in 2020 to 55.64% (8,452.5 GWh) in 2024; Domestic share contracted from 35.63% to 30.95%. | 26 | 2–5 ms | Lecture 8 (`GROUPING SETS` multi-level aggregation). |
| **Q22** | Member 6: Efficiency | Cross-Source Multi-Tier Reconciliation | 5-year transmission & distribution loss proxy: 8.8% to 9.6% across 2020–2024; consistent with audited CEB regulatory statistics. | 6 | 2–5 ms | Lecture 6 (Multi-source integration, residual loss proxies). |
| **Q23** | Member 6: Efficiency | Data Quality Quarantine Audit Trail | Total issues: 926 (100.00%); Unmatched entities: 879 (94.92%); Negative measurements: 47 (5.08%); All rules reconcile to 100.00%. | 5 | 14–22 ms | Lecture 6 (Quarantine isolation), Lecture 8 (Grouping sets). |
| **Q24** | Member 6: Efficiency | ETL Execution Performance & Lineage | 273,452 source records processed; 228,145 audit lineage rows; Dispatch loader: 405.3 rows/sec; Weather loader: 532.3 rows/sec. | 4 | 160–200 ms | Lecture 4 (ETL performance monitoring, row-level lineage). |

---

## 2. Integrity Assertion Checklist for Demonstrators

When demonstrating the queries to professors or reviewers, highlight the following **4 non-negotiable data warehouse truths**:
1. **Physical Energy Balance (Q01, Q08, Q22):** $E_{\text{net}} = \int P(t) dt$. Active power (MW) is instantaneous; electrical energy (MWh) is integrated over time. $1\text{ MWh} = 0.25\text{ h} \times 1\text{ MW}$ in 15-minute intervals.
2. **True Zero vs Missing Data (Q17, Q23):** $0.0\text{ MW}$ is a physical plant shutdown/offline interval. `NULL` is an omitted/unrecorded transmission slot. Treating missing values as zero is strictly prohibited.
3. **No Double Counting in Sales (Q09, Q10, Q12, Q21):** Total national billed electricity consumption equals CEB retail sales plus LECO bulk supply. Adding LECO consumer accounts on top of bulk supply is invalid and prevented in `dw.fact_electricity_sales`.
4. **Transparent Scope Reconciliations (Q08):** SCADA transmission meters measure high-voltage bulk dispatch (46,308 MWh). Utility settlement sheets include untelemetered low-voltage rooftop solar and 33kV mini-hydro (48,223 MWh). The 3.97% gap is a physical boundary difference, not telemetry data loss.

