# GridLens Live Technical Demonstration Guide
## National Electricity Grid Analytics Data Warehouse — Sri Lanka

**Document Reference:** `docs/demo/live-demonstration-guide.md`  
**Target Audience:** Academic Evaluators, Lecturers, Industrial Reviewers  
**Execution Environment:** Windows / Linux / macOS with Docker Desktop, Python 3.11+, and PostgreSQL 18  
**Demonstration Time:** 15–20 Minutes  

---

## 1. Demonstration Overview & Objectives

This guide provides an end-to-end walkthrough for conducting a live, reproducible demonstration of the **GridLens** data warehouse. 

By following this guide, you will demonstrate:
1. **Containerized Database Health:** Verifying PostgreSQL 18 running in Docker with schemas `dw`, `stg`, `mart`, and `audit`.
2. **Schema & Migration Governance:** Showing the strict, sequential forward migration runner and SHA-256 tracking.
3. **ETL Pipeline Execution & Lineage:** Running the automated loaders and verifying quarantine isolation.
4. **Analytical Marts & Stored Procedures:** Demonstrating concurrent materialized view refresh.
5. **Interactive Execution of Key Analytical Queries:** Executing high-impact queries live across the 6 team member domains.
6. **Visual Insights & Generated Charts:** Reviewing the publication-quality charts generated from warehouse outputs.

---

## 2. Environment Verification & Startup (2 Minutes)

### Step 2.1: Start PostgreSQL 18 Docker Container
Verify Docker Desktop is running and launch the warehouse container:

```bash
docker compose up -d db
```

Verify that the container is healthy and listening on port 5433:

```bash
docker compose ps
# Expected: sl_grid_warehouse_db running on 0.0.0.0:5433->5432/tcp
```

### Step 2.2: Verify Python Virtual Environment
Activate the environment and verify installed dependencies:

```bash
# On Windows
.venv\Scripts\activate

# On Linux/macOS
source .venv/bin/activate

# Verify Python version and key packages
python --version
# Expected: Python 3.11+
python -c "import psycopg, pandas, matplotlib; print('Core dependencies OK')"
```

---

## 3. Schema Migrations & Database Architecture Demo (3 Minutes)

### Step 3.1: Demonstrate Migration Discovery & Idempotency
Run the custom migration runner to demonstrate that all 21 schema migrations are discovered and verified:

```bash
python scripts/migrate.py status
```

**Presenter Speaking Point:**
> *"Our database schema is governed entirely via immutable forward migrations. Every SQL file has an SHA-256 checksum recorded in `public.schema_migrations`. If a file is modified after deployment, the migration runner halts execution to prevent silent schema corruption."*

### Step 3.2: Inspect Multi-Schema Isolation
Connect via `psql` or database IDE to inspect the schema layout:

```bash
docker exec -it sl_grid_warehouse_db psql -U grid_admin -d sl_grid_warehouse -c "\dn"
```

**Expected Schemas Displayed:**
- `public` (System tables, migration tracking)
- `stg` (Staging schema for raw incoming files)
- `dw` (Kimball dimensional warehouse core: 8 conformed dimensions + 4 fact tables)
- `mart` (Pre-aggregated materialized views for high-speed executive dashboards)
- `audit` (ETL batch logs, record-level lineage, quarantined records)

---

## 4. Pipeline Execution & Data Quality Demo (3 Minutes)

### Step 4.1: Run Full Test Suite (Red-Green TDD Evidence)
Demonstrate automated test verification across unit, integration, data quality, and analytics tests:

```bash
pytest tests/unit tests/data_quality tests/integration/test_migrations.py tests/analytics -v
```

**Expected Result:**
```
============================== 74 passed in ~4 minutes ==============================
```

### Step 4.2: Inspect Data Quality Quarantine Isolation (Lecture 6)
Demonstrate that anomalies (such as negative active power readings from the Colombo Harbour Barge plant) were not discarded or fabricated, but isolated into `audit.quarantine_records`:

```bash
docker exec -it sl_grid_warehouse_db psql -U grid_analyst -d sl_grid_warehouse -c "
SELECT rule_code, severity, COUNT(*) AS issue_count, 
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_share
FROM audit.quarantine_records
GROUP BY rule_code, severity;
"
```

**Expected Output:**
```
       rule_code        | severity | issue_count | pct_share 
------------------------+----------+-------------+-----------
 DQ_DIM_UNMATCHED_ENTITY| WARNING  |         879 |     94.92
 DQ_GEN_NEGATIVE_OUTPUT | ERROR    |          47 |      5.08
```

---

## 5. Live Analytical Queries Demonstration (7 Minutes)

Execute selected queries representing the key lecture concepts directly from the CLI or database tool:

### Demo Query 1: Generation Mix with ROLLUP (Member 1 — Query Q01)
Demonstrates multi-level hierarchical aggregation in a single query:

```bash
docker exec -it sl_grid_warehouse_db psql -U grid_analyst -d sl_grid_warehouse -f database/queries/phase3/member_01_generation/Q01.sql
```

**Presenter Highlights:**
- **National Dispatched Total:** 1,399,337.00 MWh (~1.40 TWh) in March 2024.
- **Thermal Coal Dominance:** Lakvijaya Units 1–3 generated 595,524.50 MWh (42.56%).
- **Clean Subtotals:** `ROLLUP` produces source-level, category-level, and grand total in one scan.

---

### Demo Query 2: SCADA Ramping Derivatives with LAG (Member 2 — Query Q06)
Demonstrates window functions calculating 15-minute ramp rates and rate-of-change velocity:

```bash
docker exec -it sl_grid_warehouse_db psql -U grid_analyst -d sl_grid_warehouse -f database/queries/phase3/member_02_dispatch/Q06.sql
```

**Presenter Highlights:**
- **Maximum System Surge:** **+141.00 MW** (+9.40 MW/min) occurring systematically at 18:30 (Interval 75).
- **Physical Explanation:** Solar generation drops to zero while domestic lighting and appliance loads spike simultaneously.

---

### Demo Query 3: Telemetry-to-Published Reconciliation (Member 2 — Query Q08)
Demonstrates exact reconciliation of SCADA discrete Riemann integration against audited settlement sheets:

```bash
docker exec -it sl_grid_warehouse_db psql -U grid_analyst -d sl_grid_warehouse -f database/queries/phase3/member_02_dispatch/Q08.sql
```

**Presenter Highlights:**
- **Telemetered Sum:** 46,308.00 MWh vs Published Benchmark: 48,223.00 MWh.
- **Net Scope Variance:** Exactly 1,915.00 MWh (3.97%).
- **Physical Traceability:** Coal matches within +0.04% (+8.75 MWh) and Major Hydro within +0.05% (+5.10 MWh). The entire variance is explained by distributed rooftop solar (+1,728.20 MWh) and 33kV embedded mini-hydro (+302.80 MWh).

---

### Demo Query 4: Five-Year Sectoral Shift & Tourism Rebound (Member 3 — Query Q10)
Demonstrates multi-year pivot and compound annual growth rate (CAGR):

```bash
docker exec -it sl_grid_warehouse_db psql -U grid_analyst -d sl_grid_warehouse -f database/queries/phase3/member_03_sales/Q10.sql
```

**Presenter Highlights:**
- **Hotel Sector:** Surged from 193.00 GWh (2020) to 355.00 GWh (2024) — **+83.94% growth (16.46% CAGR)**, reflecting post-crisis tourism recovery.
- **Domestic Contraction:** Decreased from 5,090.00 GWh to 4,701.00 GWh (-7.64%) due to steep tariff restructuring.

---

### Demo Query 5: Wind Resource Coupling via Pearson Correlation (Member 4 — Query Q16)
Demonstrates in-database statistical correlation between NASA 50m wind speed and utility dispatch:

```bash
docker exec -it sl_grid_warehouse_db psql -U grid_analyst -d sl_grid_warehouse -f database/queries/phase3/member_04_weather/Q16.sql
```

**Presenter Highlights:**
- **Strong Empirical Coupling:** Linear correlation $r = +0.7143$, cubic wind energy proxy $r(v^3) = +0.7132$.
- **Validation:** Proves satellite meteorological reanalysis can reliably proxy grid generation without local anemometers.

---

### Demo Query 6: Advanced Multi-Level GROUPING SETS (Member 6 — Query Q21)
Demonstrates selective OLAP subtotals across economic consumer classes:

```bash
docker exec -it sl_grid_warehouse_db psql -U grid_analyst -d sl_grid_warehouse -f database/queries/phase3/member_06_grid_efficiency/Q21.sql
```

**Presenter Highlights:**
- Productive economic share expanded from 50.35% (2020) to 55.64% (2024).
- Executed in 2.4 ms via `GROUPING SETS`.

---

## 6. Generated Visualizations & Export Artifacts Demo (2 Minutes)

Execute the export and visualization runner:

```bash
python scripts/execute_phase3_queries.py
python scripts/generate_phase3_charts.py
```

Inspect the generated charts in `results/phase3/charts/`:
1. `chart_01_generation_mix_march_2024.png`: Donut chart of national technology shares.
2. `chart_02_renewable_daily_share_march_2024.png`: Daily renewable trajectory with 7-day centered moving average.
3. `chart_03_dispatch_curve_weekday_vs_weekend.png`: 96-interval diurnal load curves showing the 235 MW weekend drop.
4. `chart_04_five_year_sales_trends.png`: 5-year sectoral sales evolution.
5. `chart_05_solar_irradiance_victoria_vs_mannar.png`: Monthly solar profiles showing pre-monsoon peaks.
6. `chart_06_tou_generation_contribution.png`: Stacked bar chart of Daytime vs Evening Peak vs Off-Peak generation.

---

## 7. Demonstration Wrap-Up & Evaluator Takeaways (1 Minute)

Key architectural highlights to conclude:
1. **Zero Data Fabrication:** Every number matches official PUCSL, CEB, and NASA publications.
2. **PostgreSQL 18 Mastery:** Declarative partitioning, concurrency-safe materialized views, ROLLUP, CUBE, GROUPING SETS, and Pearson correlation.
3. **Reproducibility:** 100% automated via Docker, migrations, scripts, and Pytest.

