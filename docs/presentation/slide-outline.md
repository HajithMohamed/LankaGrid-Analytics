# GridLens Academic Presentation Slide Deck Outline (24 Slides)
## National Electricity Grid Analytics Data Warehouse — Sri Lanka

**Document Reference:** `docs/presentation/slide-outline.md`  
**Target Duration:** 20–25 Minutes (Six Presenters, ~3.5 Minutes per Member)  
**Audience:** Academic Examination Panel, Data Warehousing Professors, External Industry Assessors  

---

## Slide Structure & Master Agenda

```
+--------------------------------------------------------------------------------------------------+
| SLIDE  1: Title Slide & Project Overview (GridLens — National Electricity Grid Analytics)        |
| SLIDE  2: Academic Motivation, Research Objectives & Sri Lankan Energy Crisis Context            |
+--------------------------------------------------------------------------------------------------+
| MEMBER 1: GENERATION MIX, RENEWABLE ENERGY PENETRATION & BASELOAD TRANSITION                     |
| SLIDE  3: Architectural Context & Kimball Fact Grain: 15-Minute Generation Measurements          |
| SLIDE  4: Query Q01 & Q02: National Generation Mix via ROLLUP & 7-Day Centered Moving Averages   |
| SLIDE  5: Query Q03 & Q04: Plant Capacity Factors, Nameplate Boundaries & TOU Peaking Dynamics   |
| SLIDE  6: Member 1 Key Insights, Policy Takeaways & Transition to Member 2                       |
+--------------------------------------------------------------------------------------------------+
| MEMBER 2: GRID DISPATCH DYNAMICS, HIGH-FREQUENCY RAMPING & TELEMETRY RECONCILIATION              |
| SLIDE  7: SCADA 15-Minute Telemetry Architecture & Fact Grain Partitioning Strategy               |
| SLIDE  8: Query Q05 & Q06: Diurnal Load Curves (Weekday vs Weekend) & First-Derivative Ramping   |
| SLIDE  9: Query Q07 & Q08: Baseload vs Peaker Classification (CV) & Exact SCADA Reconciliation    |
| SLIDE 10: Member 2 Key Insights, Grid Stability Implications & Transition to Member 3            |
+--------------------------------------------------------------------------------------------------+
| MEMBER 3: ELECTRICITY DEMAND DYNAMICS, SECTORAL SHIFTS & TARIFF RESTRUCTURING IMPACTS            |
| SLIDE 11: Five-Year Audited Billed Sales Modeling & Conformed Customer/Tariff Dimensions         |
| SLIDE 12: Query Q09 & Q10: 5-Year Sector Trajectories & Post-Crisis Tourism Rebound (+83.94%)    |
| SLIDE 13: Query Q11 & Q12: Household Consumption Contraction & LECO Bulk Supply Decoupling       |
| SLIDE 14: Member 3 Key Insights, Tariff Elasticity Findings & Transition to Member 4             |
+--------------------------------------------------------------------------------------------------+
| MEMBER 4: WEATHER, METEOROLOGICAL COUPLING & SOLAR/WIND RESOURCE POTENTIAL                       |
| SLIDE 15: NASA POWER Satellite Reanalysis Ingestion, LST Timezone Alignment & Station Topography |
| SLIDE 16: Query Q13 & Q14: 5-Year Solar Irradiance Profiles (PSH) & Temperature Correlation      |
| SLIDE 17: Query Q15 & Q16: Monsoon Rainfall Hypercube (CUBE) & In-Database Wind Coupling (r=0.71) |
| SLIDE 18: Member 4 Key Insights, Renewable Siting Recommendations & Transition to Member 5       |
+--------------------------------------------------------------------------------------------------+
| MEMBER 5: POWER PLANT OPERATIONS, CAPACITY AVAILABILITY & DISPATCH MERIT-ORDER                   |
| SLIDE 19: Operational Dimension Modeling: Nameplate Boundaries, Heat Engines & Hydro Dynamics    |
| SLIDE 20: Query Q17 & Q18: Zero-Generation Sentinel Filtering & Peak-to-Nameplate Ratios         |
| SLIDE 21: Query Q19 & Q20: Lakvijaya Coal 100% Baseload Continuity & Evening Peak Merit-Order    |
| SLIDE 22: Member 5 Key Insights, Generation Bottleneck Diagnostics & Transition to Member 6      |
+--------------------------------------------------------------------------------------------------+
| MEMBER 6: GRID EFFICIENCY, AUDIT PROVENANCE, DATA QUALITY & PERFORMANCE BENCHMARKING              |
| SLIDE 23: Data Governance Architecture: Quarantine Isolation, Lineage & Loss Proxies (Q21-Q24)   |
| SLIDE 24: PostgreSQL 18 Performance Summary, Academic Contributions & Project Conclusion         |
+--------------------------------------------------------------------------------------------------+
```

---

## Detailed Slide Content Specifications

### Slide 1: Title Slide & Project Overview
- **Header:** GridLens: National Electricity Grid Analytics Data Warehouse — Sri Lanka.
- **Sub-header:** A Kimball Dimensional Warehouse Modeling 5 Years of Power Generation, Sectoral Demand, SCADA Telemetry, and Satellite Meteorological Observations.
- **Team:** Six Undergraduate Software Engineers.
- **Technology Stack:** PostgreSQL 18 (Docker), Python 3.14, Pytest, SQL:1999 OLAP.
- **Visual:** High-level system architecture badge + National Grid summary diagram.

### Slide 2: Academic Motivation & Domain Context
- **Problem Statement:** Sri Lanka's electricity sector faces unprecedented trilemma pressures: high fossil fuel import costs, severe economic crisis tariff shocks (2022–2023), and an aggressive national mandate for 70% renewable electricity by 2030.
- **Academic Purpose:** Bridging the gap between raw, fragmented operational data (PUCSL SCADA Excel files, CEB statistical PDFs, NASA POWER APIs) and unified dimensional intelligence using Kimball methodology.
- **Key Deliverables:** 8 conformed dimensions, 4 fact tables, 2 analytical marts, 24 business queries, 101 automated tests.

---

### Member 1: Generation Mix & Renewables (Slides 3–6)
- **Slide 3:** *Dimensional Modeling of Generation Facts.* Defining the fact grain of `dw.fact_dispatch_interval` ($[T, S, P]$: Time $\times$ Source $\times$ Plant). Unit integrity rules ($MW \ne MWh$).
- **Slide 4:** *National Generation Mix & Daily Renewable Penetration (Q01 & Q02).* Demonstrating `ROLLUP` hierarchical subtotals: Coal (42.56%, 595,524.50 MWh), Oil (27.69%, 387,450.75 MWh), Hydro (22.98%, 321,595.50 MWh). Daily renewable share variation (27.13% to 34.68%, mean 29.75%) with 7-day centered moving average chart.
- **Slide 5:** *Plant Capacity Factors & Time-of-Use Peaking (Q03 & Q04).* Distinguishing official capacity factors (Coal: 88.74%–89.15%, Kelanitissa CC: 82.43%) from observed peak utilization proxies. Evening Peak (18:30–22:30) hydro surge to 32.40% and total solar cessation (0.00%).
- **Slide 6:** *Member 1 Conclusions.* Transition to Member 2 on how sub-hourly SCADA dispatch accommodates these diurnal swings.

---

### Member 2: Grid Dispatch Dynamics & Ramping (Slides 7–10)
- **Slide 7:** *SCADA 15-Minute Telemetry Architecture.* Ingestion of 2,976 intervals per station across March 2024. Declarative range partitioning on `date_key` to accelerate 96-slot profile scans.
- **Slide 8:** *Diurnal Load Curves & Operational Ramping Stress (Q05 & Q06).* Comparing weekday (peak 2,476.32 MW at 19:15) vs weekend (peak 2,241.18 MW, a 9.50% drop). In-database first derivatives via `LAG()` identifying national maximum ramp stress: **+141.00 MW (+9.40 MW/min)** at 18:30 (Interval 75).
- **Slide 9:** *Baseload vs Peaker Screening & Telemetry Reconciliation (Q07 & Q08).* Coefficient of variation ($CV$) screening: Lakvijaya Coal ($CV = 0.09$, baseload) vs Kotmale ($CV = 0.94$, peaker). Mathematical proof of the 3.97% (1,915.00 MWh) telemetry-to-published variance (rooftop solar +1,728.20 MWh, mini hydro +302.80 MWh; coal and hydro within 0.05%).
- **Slide 10:** *Member 2 Conclusions.* Grid stability implications and transition to Member 3 on consumer demand driving these curves.

---

### Member 3: Electricity Demand & Customer Dynamics (Slides 11–14)
- **Slide 11:** *Five-Year Billed Sales Modeling.* Conformed modeling of `dim_tariff_sector` and `dim_customer_class` across 2020–2024. Preventing double-counting between CEB retail and LECO bulk sales.
- **Slide 12:** *Five-Year Trajectories & Tourism Rebound (Q09 & Q10).* Audited sales data: National billed sales grew from 14,287 GWh (2020) to 15,190.5 GWh (2024). Tourism rebound: Hotel sales expanded from 193.00 GWh to 355.00 GWh (**+83.94% growth, +16.46% CAGR**).
- **Slide 13:** *Residential Demand Contraction & Bulk Supply Decoupling (Q11 & Q12).* Domestic consumption contracted by -7.64% (5,090 GWh to 4,701 GWh) due to tariff hikes, with monthly household intensity dropping from 71.3 to 62.4 kWh. LECO bulk supply remaining steady at 10.67%–11.23% share.
- **Slide 14:** *Member 3 Conclusions.* Structural economic transition toward productive sectors and transition to Member 4 on weather impacts.

---

### Member 4: Weather & Renewable Coupling (Slides 15–18)
- **Slide 15:** *Satellite Meteorological Reanalysis Ingestion.* NASA POWER 5-year daily weather facts (21,924 rows). Date-aligned fact constellation joins with grid dispatch facts.
- **Slide 16:** *Solar Irradiance Profiles & Temperature In-Database Correlation (Q13 & Q14).* Mannar (5.16 PSH/day) vs Victoria Catchment (5.09 PSH/day). In-database Pearson correlation showing near-zero correlation between non-urban station temperatures and peak dispatch ($r = +0.0083$), but mild positive correlation with daily energy ($r = +0.1248$).
- **Slide 17:** *Monsoon Seasonality CUBE & Wind Resource Coupling (Q15 & Q16).* Multi-dimensional `CUBE` across location $\times$ monsoon season (16,929.50 mm total rain, 63.54% at Victoria). Strong empirical coupling between satellite 50m wind speed and utility wind generation ($r = +0.7143$, $r(v^3) = +0.7132$).
- **Slide 18:** *Member 4 Conclusions.* Validation of satellite reanalysis for renewable resource planning; transition to Member 5 on physical plant capacities.

---

### Member 5: Plant Operations & Capacity Performance (Slides 19–22)
- **Slide 19:** *Operational Plant Dimensioning.* Modeling nameplate ratings, fuel types, and physical heat engines in `dim_power_plant`.
- **Slide 20:** *Sentinel vs Zero Interval Filtering & Capacity Envelopes (Q17 & Q18).* Handling $0.0\text{ MW}$ as physical shutdowns rather than missing values. 10 plants delivered $\ge 95\%$ of nameplate rating; empirical exceedances catalogued objectively (Polpitiya 116.0%, West Coast 107.0%).
- **Slide 21:** *Baseload Continuity & Evening Peak Merit-Order (Q19 & Q20).* Lakvijaya Coal generated 595,524.50 MWh with 100.0% duty cycle across all 3 units (0 forced outages). Evening peak dispatch share: Coal (39.67%), Major Hydro (32.40%), Thermal Oil (23.19%).
- **Slide 22:** *Member 5 Conclusions.* Thermal baseload reliability vs hydro peaking flexibility; transition to Member 6 on grid efficiency and warehouse engineering.

---

### Member 6: Grid Efficiency, Audit Provenance & QA (Slides 23–24)
- **Slide 23:** *Efficiency Trends, Loss Proxies & Data Quality (Q21–Q24).* `GROUPING SETS` demonstrating productive economic share expansion (50.35% to 55.64%). Multi-tier loss proxy reconciliation confirming 8.8% to 9.6% transmission & distribution losses. Quarantine isolation: 926 records isolated and reconciled to 100.00%.
- **Slide 24:** *PostgreSQL 18 Performance, Architecture Highlights & Conclusion.* 24 queries executing in mean 93.8 ms (100% under 500 ms). 101 automated tests passing. Declarative partitioning, concurrency-safe materialized views, complete lineage audit trail. Final project summary and Q&A open.

