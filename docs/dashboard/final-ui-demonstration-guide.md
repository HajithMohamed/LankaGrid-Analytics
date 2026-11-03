# GridLens — University Evaluation & Final UI Demonstration Guide

**Project:** GridLens — Sri Lanka National Electricity Grid Analytics Data Warehouse  
**Target Audience:** Academic Evaluators, External Reviewers, Data Warehouse Examination Committee  
**Institution:** University of Ruhuna, Faculty of Technology, Department of ICT  
**Framework:** Next.js 16 App Router, React 19, TypeScript, Tailwind CSS v4  
**Database:** PostgreSQL 18 on Docker (Kimball Fact Constellation Architecture)  
**Branch:** `fix/phase-5-dashboard-accuracy-and-demo`  

---

## 1. Quick Start & Demonstration Setup

### 1.1 Development Server Execution
To demonstrate the application with full Premium White styling and avoid any cached bundler conflicts:

```bash
# 1. Clean any stale cache artifacts
cd web
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue

# 2. Run the Next.js development server
pnpm run dev
# Application will be accessible at http://localhost:3000
```

Alternatively, to run the pre-built, production-optimized build:
```bash
cd web
pnpm run build
pnpm start
```

### 1.2 Dual Execution Modes
GridLens is engineered for dual execution environments:
1. **Live PostgreSQL 18 Mode**: When the Docker PostgreSQL 18 container is active (`docker compose up -d`), TopNav displays a green indicator **"PostgreSQL 18 Connected"**, and queries execute directly against live partitioned tables and materialized views using least-privilege `grid_analyst` credentials.
2. **Historical Snapshot Mode**: If running in an offline or portable presentation setting without Docker, the application automatically falls back to verified historical snapshots (`web/public/data/snapshots/Q01-Q24.json`), indicated by an amber badge **"Historical Snapshot Active"**. All data points remain 100% authentic and verified.

---

## 2. Step-by-Step Evaluator Walkthrough (8 Pages)

### Page 1: Executive Overview (`/`)
* **Core Academic Focus**: Multi-source national energy synthesis, dynamic filtering, physical unit discipline (MW vs MWh).
* **Demonstration Actions**:
  1. **Examine Key Metrics**: Point out the March 2024 generation figures (Lakvijaya Coal: 595,524.50 MWh, Oil: 387,450.75 MWh, Major Hydro: 321,595.50 MWh) and 2024 annual billed sales (15,190.50 GWh).
  2. **Demonstrate Dynamic Year Filtering**:
     - Change the **Sales year** dropdown from `2020–2024 (All)` to `2022`.
     - Observe the dynamic KPI card automatically update to **"2022 billed electricity sales: 14,520.00 GWh"**.
     - Notice the **Sales by Economic Sector** table filter to calendar year 2022 with exact sectoral breakdown (Productive: 7,541.00 GWh / 51.94%, Residential: 5,044.00 GWh).
     - Notice the **"Reset"** button appear next to the filter dropdown.
  3. **Interactive Trend Chart**: Click on any point on the SVG trend line (e.g., year 2021). The chart highlights that year, displays a 15,214 GWh callout, and filters the table. Click **"Show all years"** to reset.
  4. **Data Coverage Telemetry**: Scroll to the bottom to demonstrate the automated Kimball schema inventory (6 facts, 9 conformed dimensions, 107k dispatch rows, 21k weather rows, 49 sales rows).

---

### Page 2: Generation Mix & Renewables (`/generation`)
* **Lead Researcher**: Member 1
* **Demonstrated Queries**: Q01, Q02, Q03, Q04
* **Academic Highlights**:
  - **Q01 Donut Breakdown**: Lakvijaya Coal represents 42.56% of March 2024 dispatch, thermal oil represents 27.69%, and major hydro represents 22.98%.
  - **Q02 7-Day Moving Average**: Showcases SQL window framing `AVG() OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)` tracking daily renewable volatility.
  - **Q03 Capacity Factors**: Evaluates plant utilization against rated nameplate capacity over 744 operating hours (Lakvijaya Coal operated at an exceptional 89.44% capacity factor).
  - **Q04 TOU Tariff Buckets**: Demonstrates conditional aggregation across Day (05:30–18:30), Peak (18:30–22:30), and Off-Peak (22:30–05:30) windows.

---

### Page 3: Dispatch & Grid Dynamics (`/dispatch`)
* **Lead Researcher**: Member 2
* **Demonstrated Queries**: Q05, Q06, Q07, Q08
* **Academic Highlights**:
  - **Q05 96-Interval Diurnal Load Curves**: Compares average weekday demand against weekend demand across the 96 daily 15-minute intervals. Peak national demand consistently occurs at 19:30 (Interval 78).
  - **Q06 Maximum Ramp Rate**: Showcases SQL `LAG()` window function tracking 15-minute system velocity. Authoritative maximum upward ramp rate is **141.00 MW on March 17, 2024 at 18:30**, driven by rapid peaker synchronization for the evening peak.
  - **Q07 Baseload vs Peaker Volatility**: Demonstrates statistical profiling using Coefficient of Variation ($CV = \sigma / \mu$). Lakvijaya shows minimal volatility ($CV = 9.8\%$), whereas thermal diesel peakers exhibit extreme volatility ($CV > 120\%$).
  - **Q08 Telemetry Reconciliation**: Compares 15-minute integrated MWh with published daily log sheets.

---

### Page 4: Consumer Demand & Tariff Analytics (`/sales`)
* **Lead Researcher**: Member 3
* **Demonstrated Queries**: Q09, Q10, Q11, Q12
* **Academic Highlights**:
  - **Q09 Sectoral Sales Matrix**: Five-year longitudinal evolution (2020–2024) across industrial, commercial, domestic, and LECO bulk sectors.
  - **Q10 Hotel Sector Post-Crisis Rebound**: Highlights post-2022 tourism recovery with an audited **+83.94% YoY sales surge** in the hospitality sector in 2023.
  - **Q11 Household Consumption Density**: Demonstrates per-account intensity analysis ($kWh / \text{account} / \text{month}$), revealing how tariff revisions in 2022–2023 compressed domestic household demand.
  - **Q12 Franchise Distribution Share**: Compares LECO bulk franchise distribution against direct CEB retail supply.

---

### Page 5: Weather & Renewable Potential (`/weather`)
* **Lead Researcher**: Member 4
* **Demonstrated Queries**: Q13, Q14, Q15, Q16
* **Academic Highlights**:
  - **Q13 Solar Insolation**: Converts NASA POWER all-sky surface irradiance into Peak Sun Hours (PSH/day), comparing Victoria Dam catchment with the Mannar Dry Zone corridor.
  - **Q14 Temperature-Demand Correlation**: Demonstrates bivariate statistical correlation `CORR(max_temp_c, dispatch_gwh)` to quantify air conditioning and cooling demand elasticity.
  - **Q15 Monsoon Hydrological CUBE**: Showcases advanced SQL `GROUP BY CUBE (calendar_year, monsoon_season, location_name)` for multi-dimensional precipitation profiling.
  - **Q16 Wind Speed Power Curve**: Joins NASA POWER 50-meter hub-height wind speed telemetry with actual dispatched wind park generation in Mannar.

---

### Page 6: Plant Performance & Operational Outages (`/plants`)
* **Lead Researcher**: Member 5
* **Demonstrated Queries**: Q17, Q18, Q19, Q20
* **Academic Highlights**:
  - **Q17 Zero-Dispatch Availability**: Quantifies station availability rates across 2,976 March 2024 intervals. Identifies scheduled maintenance outages vs standby reserve plants.
  - **Q18 Peak Dispatch vs Nameplate**: Derating analysis identifying thermal stations operating below original nameplate capacity.
  - **Q19 Lakvijaya Baseload Reliability**: 24-hour dispatch area chart tracking continuous 900 MW baseload generation from Sri Lanka's sole coal-fired station.
  - **Q20 Thermal Peaker Merit Order**: Chronological ramp-up order of diesel/fuel oil reciprocating engines during the 18:30–22:30 evening window.

---

### Page 7: Data Quality & Cross-Source Audit (`/data-quality`)
* **Lead Researcher**: Member 6
* **Demonstrated Queries**: Q21, Q22, Q23, Q24
* **Academic Highlights**:
  - **Multi-Tier Reconciliation Rigor (Q22)**:
    - **Tier 1 (CEB Audited Sales)**: Reconciles five years of constituent customer categories against published control totals with **$\le 0.007\%$ maximum variance** (exact zero variance in 2021 and 2022).
    - **Tier 2 (PUCSL Daily Dispatch)**: Reconciles 15-minute telemetry (46,308 MWh) against published daily system control totals (48,223 MWh), with an audited variance of **3.971%**. Evaluators will appreciate the technical explanation: this variance reflects unmetered rooftop solar and mini-hydro generation (~4.2% of national mix) not captured by primary telemetry.
  - **Quarantine Anomaly Ledger (Q23)**:
    - Demonstrates ETL quality gates that isolated **926 malformed records** into `audit.data_quality_issue` without dropping them or corrupting warehouse fact tables.
    - Accurately categorized without subtotal double-counting: **879 Unmatched Entity Names (94.92%)** from historical PDF spelling variations and **47 Negative Active Power Outliers (5.08%)** from sensor telemetry noise.
  - **Audit Provenance Flow**: Explains how `audit.record_lineage` maps target warehouse fact records (`target_dw_table`, `target_dw_pk`) back to staging and SHA-256 raw archives.

---

### Page 8: Query & Analytics Explorer (`/query-explorer`)
* **Core Academic Focus**: Full schema transparency, SQL verification, and governed semantic modeling.
* **Demonstration Actions**:
  1. **Browse All 24 Queries**: Select queries across the 6 research domains.
  2. **Demonstrate OLAP Technique Banner**: For every query, highlight the explicit OLAP method banner (e.g. `GROUPING SETS` in Q21/Q23, `CUBE` in Q15, `LAG()` window function in Q06/Q10, window framing in Q02).
  3. **Toggle SQL Source**: Click **"SQL Source"** to view and copy the exact parameterized PostgreSQL query executing on the warehouse.
  4. **Demonstrate Governed Semantic Layer**:
     - Switch to the **"Semantic Layer (Governed)"** tab.
     - Choose a measure (e.g. `Electricity Generated (MWh)`) and a compatible dimension (e.g. `Energy Category`).
     - Point out the real-time Kimball grain compatibility indicator: **"Valid Kimball grain combination"**.
     - Click **"Run Semantic Aggregation"** to demonstrate Power BI-style controlled metric aggregation.
     - Select an incompatible pair (e.g. `Air Temperature` paired with `Generating Station`) to demonstrate automated grain validation blocking invalid queries.

---

## 3. Defense Talking Points & Q&A Preparation

| Potential Evaluator Question | Authoritative Architectural Answer |
| :--- | :--- |
| **"Why is the sales data annual while dispatch data is 15-minute intervals?"** | This is a core strength of Kimball Fact Constellation design. Fact tables model distinct business processes at their natural grains: `fact_dispatch_interval` has a 15-minute operational grain, while `fact_electricity_sales` has an annual billing grain. Conformed dimensions (`dim_date`, `dim_energy_source`) link them without artificial grain distortion. |
| **"Why does PUCSL dispatch telemetry show a ~3.97% variance in Q22?"** | In Sri Lanka's electricity grid, large utility power plants are telemetered in real time by the System Control Centre, but distributed rooftop solar PV and small non-conventional renewable energy (NCRE) mini-hydro feed into medium-voltage distribution networks without high-speed telemetry. PUCSL operating reports adjust for this unmetered ~4.2% contribution. GridLens explicitly audits this difference in Q22 rather than fabricating numbers. |
| **"How is SQL injection prevented in the Query Explorer and Semantic Layer?"** | GridLens enforces a strict closed semantic layer. Users can only select predefined measures and dimensions from a typed registry. SQL queries are executed via static parameterized definitions or controlled aggregations using `psycopg`/`pg` parameters, with zero dynamic SQL string interpolation. Database connections use least-privilege `grid_analyst` credentials with read-only transaction locks. |
| **"Why did you use GROUPING SETS in Q21 and Q23?"** | `GROUPING SETS` enables computing detail-level figures, intermediate category subtotals, and overall grand totals in a single unified database pass, dramatically reducing disk I/O and query execution time compared to multiple `UNION ALL` statements. |

