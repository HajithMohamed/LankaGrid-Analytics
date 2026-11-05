# GridLens — National Electricity Grid Analytics Data Warehouse

[![CI Pipeline](https://github.com/HajithMohamed/LankaGrid-Analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/HajithMohamed/LankaGrid-Analytics/actions/workflows/ci.yml)
[![Scheduled Data Refresh](https://github.com/HajithMohamed/LankaGrid-Analytics/actions/workflows/scheduled-data-refresh.yml/badge.svg)](https://github.com/HajithMohamed/LankaGrid-Analytics/actions/workflows/scheduled-data-refresh.yml)
[![PostgreSQL 18](https://img.shields.io/badge/PostgreSQL-18-blue.svg)](https://www.postgresql.org/)
[![Supabase](https://img.shields.io/badge/Database-Supabase%20Managed%20PG-3ECF8E.svg)](https://supabase.com/)
[![Next.js 16](https://img.shields.io/badge/Frontend-Next.js%2016-black.svg)](https://nextjs.org/)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)

---

## 1. Title and Project Overview

**GridLens** is a production-grade, Kimball Fact Constellation analytical data warehouse modeling the physical operations, economic dispatch, commercial sales, and meteorological dependencies of the **National Electricity Grid of Sri Lanka**. 

The platform aggregates, conforms, and analyzes historical generation telemetry, transmission dispatch curves, provincial retail tariffs, and NASA satellite weather observations across Sri Lanka Standard Time (`UTC+05:30` / Asia/Colombo). Built on PostgreSQL 18 and Supabase Managed PostgreSQL, GridLens powers high-performance Online Analytical Processing (OLAP) and an interactive Next.js 16 analytics dashboard.

---

## 2. What GridLens Solves

Managing national electricity grids during renewable transitions poses major data challenges:
- **Data Fragmentation & Incompatible Formats:** Official grid reports are scattered across annual CEB statistical digests (PDF), daily PUCSL dispatch sheets (XLSX), and global meteorological APIs (JSON).
- **Physical vs. Commercial Discrepancies:** Active power rate ($MW$) is frequently confused with integrated electrical energy ($MWh$), corrupting load factors and grid loss evaluations.
- **Renewable Intermittency & Merit-Order Opacity:** Grid operators need clear visibility into how solar irradiance and rainfall correlate with hydro storage and thermal peaker plant utilization.
- **Unreliable Manual Aggregation:** Ad-hoc spreadsheet reporting risks silent data drops, double-counting bulk distributor sales (such as LECO), and obscuring unmapped plant aliases.

**GridLens delivers:**
1. A unified, Kimball Fact Constellation warehouse that standardizes all operational and commercial measurements.
2. Cryptographically verified raw data provenance (SHA-256) with zero fabricated or proxy data.
3. Automated quarantine gates that isolate anomalies without failing production batch loads.
4. Pre-aggregated analytical materialized views for sub-second business intelligence.

---

## 3. Architecture & High-Level System Flow

```mermaid
flowchart TD
    classDef src fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#f8fafc;
    classDef pipe fill:#0f172a,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef wh fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef app fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc;

    %% Data Sources
    S1["CEB Statistical Digest<br/>(Annual Billed Sales & Accounts)"]:::src
    S2["PUCSL Dispatch Curves<br/>(15-Minute SCADA Telemetry)"]:::src
    S3["NASA POWER Satellite API<br/>(Daily Solar & Weather Nodes)"]:::src

    %% Processing Pipeline
    P1["Raw Provenance Ledger<br/>(SHA-256 & manifest.json)"]:::pipe
    P2["Typed Staging Schema (staging)<br/>(stg_ceb_sales, stg_pucsl, stg_nasa)"]:::pipe
    P3["Validation Stored Procedures<br/>(etl.sp_validate_*, Range & Alias Checks)"]:::pipe
    P4["Audit Ledger & Quarantine<br/>(audit.data_quality_issue, audit.etl_run)"]:::pipe

    %% Warehouse Core
    W1["9 Conformed Dimensions (dw.dim_*)<br/>Date, Time, Plant (SCD2), Fuel, Substation..."]:::wh
    W2["6 Kimball Fact Tables (dw.fact_*)<br/>Dispatch (107k+), Sales, Weather (21k+)..."]:::wh
    W3["Analytical Marts (mart.mv_*)<br/>Pre-aggregated Materialized Views"]:::wh

    %% Consumption Layer
    A1["24 OLAP SQL Queries<br/>(Window Functions, CTEs, ROLLUP/CUBE)"]:::app
    A2["Next.js 16 BI Dashboard<br/>(React 19, Recharts, Tailwind CSS 4)"]:::app

    S1 --> P1
    S2 --> P1
    S3 --> P1
    P1 --> P2
    P2 --> P3
    P3 -->|Clean Records| W2
    P3 -->|Anomalies & Unmapped| P4
    W1 --> W2
    W2 --> W3
    W3 --> A1
    W3 --> A2
    W2 --> A2
```

---

## 4. Fact Tables & Why Each Exists

GridLens models **six dedicated fact tables** in the `dw` schema, each addressing a distinct physical or commercial process at its atomic grain:

| Fact Table | Physical / Business Grain | Primary Additivity | Current Rows in Warehouse | Core Analytical Value |
| :--- | :--- | :--- | :--- | :--- |
| **`dw.fact_dispatch_interval`** | 15-minute interval per generator / station | Semi-additive ($MW$) / Additive ($MWh$) | **107,115** (March 2024 partition) | Diurnal load curve profiling, ramp rate analysis, spinning reserves, and unit merit-order. |
| **`dw.fact_generation_period`** | Periodic gross & net generation per plant / fuel | Fully additive ($MWh$) | Structured for periodic loads | Audited plant sent-out energy, station auxiliary consumption rates, and net energy balance. |
| **`dw.fact_capacity_period`** | Plant dependable capacity & outages per period | Semi-additive ($MW$) | Structured for periodic loads | Nameplate capacity tracking, peak availability factors, and planned vs. forced outages. |
| **`dw.fact_electricity_sales`** | Annual / monthly billed sales per province per tariff class | Additive ($MWh$, $LKR$, accounts) | **49** (2020–2024 audited history) | Sectoral demand shifts, tariff revenue realization, and LECO bulk supply reconciliation. |
| **`dw.fact_weather_daily`** | Daily meteorological observation per grid node | Semi-additive / intensive physical rates | **21,924** (2020–2024 continuous daily) | Solar irradiance (PSH), rainfall correlation with hydro catchments, and cooling degree days. |
| **`dw.fact_published_metric`** | National benchmark metric per period | Non-additive / intensive percentages | Structured for periodic loads | Official published transmission loss %, distribution loss %, and system peak demand ($MW$). |

Detailed fact table definitions, additivity rules, and partition designs are documented in [docs/database/fact-tables.md](docs/database/fact-tables.md).

---

## 5. Dimension Tables & Hierarchies

Nine conformed dimensions provide uniform analytical drill-down and slicing across all fact tables:

1. **`dw.dim_date`**: Calendar hierarchy (Day &rarr; Month &rarr; Quarter &rarr; Year), day-of-week, statutory holidays, and Sri Lankan monsoon regimes (*Northeast*, *First Inter-Monsoon*, *Southwest*, *Second Inter-Monsoon*).
2. **`dw.dim_time_of_day`**: 96 discrete 15-minute intervals mapped to official CEB Time-of-Use (TOU) tariff bands (*Day Peak: 18:30–22:30*, *Day Off-Peak: 05:30–18:30*, *Night Off-Peak: 22:30–05:30*).
3. **`dw.dim_power_plant`**: Generation facilities with geographic coordinates, rated capacities, grid connection voltage, and **Kimball Slowly Changing Dimension (SCD) Type 2** historical tracking (`effective_from`, `effective_to`, `is_current`).
4. **`dw.dim_generation_unit`**: Granular turbine-generator units within multi-unit complexes (e.g. Lakvijaya Units 1–3, Victoria Units 1–3).
5. **`dw.dim_fuel_type`**: Primary and secondary fuel taxonomies (*Major Hydro, Coal, Auto Diesel, Heavy Fuel Oil, Naphtha, Solar, Wind, Biomass*) with IPCC carbon intensity factors.
6. **`dw.dim_grid_substation`**: High-voltage transmission nodes (220 kV and 132 kV) mapped to geographic coordinates for weather matching.
7. **`dw.dim_transmission_line`**: High-voltage corridor circuits, route lengths ($km$), nominal voltages ($kV$), and thermal ratings ($MVA$).
8. **`dw.dim_tariff_customer_class`**: Gazette tariff classes (*Domestic, Religious, Industrial, Hotel, General Purpose, Government, Street Lighting*).
9. **`dw.dim_administrative_area`**: 9 administrative provinces, 25 districts, and CEB Distribution Divisions (*DD1, DD2, DD3, DD4, LECO*).

Full dimensional attribute catalogs and hierarchy maps are available in [docs/database/dimension-tables.md](docs/database/dimension-tables.md) and [docs/architecture/fact-constellation.md](docs/architecture/fact-constellation.md).

---

## 6. Data Sources & Provenance

GridLens strictly enforces immutable provenance. Raw files are stored in `data/raw/` with cryptographic SHA-256 checksums registered in `data/raw/manifest.json`:

| Provider | Dataset Title | Format | Reporting Period | Official Source URL | Local Raw Path | SHA-256 Checksum |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **CEB** | Statistical Digest (5-Year Billed Sales) | PDF / XLSX | 2020–2024 | [ceb.lk Publications](https://ceb.lk/) | `data/raw/ceb/5yr/` | `b0af3107c2eb...` |
| **PUCSL** | 15-Minute Generation Dispatch Curves | XLSX | March 2024 (31 days) | [pucsl.gov.lk Reports](https://www.pucsl.gov.lk/) | `data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx` | `d40c7d9b1129...` |
| **PUCSL** | Daily Generation & Dispatch Report | PDF | 2024-12-29 | [pucsl.gov.lk Reports](https://www.pucsl.gov.lk/) | `data/raw/pucsl/2024/Generation-Report-29th-Dec-2024.pdf` | `bb10974c344b...` |
| **NASA POWER** | Surface Meteorology & Solar Resource | JSON | 2020–2024 (5 Years) | [power.larc.nasa.gov](https://power.larc.nasa.gov/) | `data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json` | `7a9e3341b527...` |

See [docs/data_sources/source-inventory.md](docs/data_sources/source-inventory.md) for complete profiling notes.

---

## 7. Historical Coverage, Boundaries & Limitations

GridLens guarantees total data honesty: **no missing values are fabricated as zero, and no proxy dates are synthesized**.

- **5-Year Billed Sales (2020–2024):** Complete multi-year history covering all 9 provinces and retail consumer classes (**49 audited records** in `fact_electricity_sales`).
- **5-Year Meteorological Data (2020–2024):** Complete continuous daily weather across all 7 strategic grid nodes (**21,924 records** in `fact_weather_daily`).
- **Sub-Daily 15-Minute Telemetry (March 2024):** Complete 31-day sub-daily telemetry (**107,115 records** in `fact_dispatch_interval_y2024`). Sub-daily records for other months are intentionally unpopulated pending official PUCSL release; partition pruning handles this transparently.
- **Physical Meaning of Zero vs. NULL:** $0\text{ MW}$ signifies an actual plant outage or zero generation (e.g., solar at night). Missing telemetry is recorded as `NULL` so capacity factors are never artificially depressed.
- **Double-Counting Prevention:** CEB retail sales and LECO bulk sales are segregated to ensure national demand totals remain statistically valid.

Refer to [docs/data_sources/coverage-and-limitations.md](docs/data_sources/coverage-and-limitations.md) for boundary explanations.

---

## 8. Advanced PostgreSQL Implementation

GridLens leverages advanced relational database engineering features in PostgreSQL 18:

1. **Common Table Expressions (CTEs):** Structured, readable query pipelines isolating unit conversions and aggregations ([`database/queries/q01_generation_mix_by_source.sql`](database/queries/q01_generation_mix_by_source.sql)).
2. **Window Functions (`LAG`, `AVG() OVER`, `DENSE_RANK`):** Calculates 15-minute ramp rates ($\frac{dMW}{dt}$), 7-day centered moving averages, and baseload screening ([`database/queries/q06_dispatch_ramp_rate_analysis.sql`](database/queries/q06_dispatch_ramp_rate_analysis.sql)).
3. **Multi-Dimensional Aggregations (`ROLLUP`, `CUBE`, `GROUPING SETS`):** Computes hierarchical subtotals and cross-dimensional summaries in a single execution plan ([`database/queries/q15_hydro_catchment_rainfall_correlation.sql`](database/queries/q15_hydro_catchment_rainfall_correlation.sql)).
4. **Stored Procedures with Transaction Control:** Procedure `etl.sp_validate_dispatch_staging()` isolates unmapped plant aliases into quarantine without failing batches; procedure `etl.sp_refresh_analytical_marts()` updates materialized views.
5. **Declarative Range Partitioning:** Table `dw.fact_dispatch_interval` uses annual partitioning (`y2020` to `y2026`). The query planner prunes irrelevant partitions to achieve sub-100ms execution times.

See [docs/database/advanced-postgresql-features.md](docs/database/advanced-postgresql-features.md) for code links and execution plans.

---

## 9. Modern Supabase Cloud Database Architecture

GridLens is fully compatible with **Supabase Managed PostgreSQL**, enabling low-latency cloud analytics and managed TLS/SSL connectivity:

- **Direct Session Connection (`5432`):** Used for DDL migrations, schema operations, and ETL ingestion jobs.
- **Transaction Connection Pooler (`6543`):** Provides Supavisor connection pooling for serverless analytical querying.
- **Transport Security:** Strict SSL/TLS enforcement (`sslmode=require`) in Python (`psycopg`) and Next.js (`pg` with `rejectUnauthorized: false`).
- **Connection String:**
  ```bash
  DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.leormbswimbnpixkkbbu.supabase.co:5432/postgres
  ```

Detailed cloud migration and setup instructions are in [docs/deployment/supabase-setup.md](docs/deployment/supabase-setup.md).

---

## 10. Automated Incremental Acquisition & Refresh

GridLens features an automated, idempotent data refresher:
- **Scheduler:** GitHub Actions workflow at [`.github/workflows/scheduled-data-refresh.yml`](.github/workflows/scheduled-data-refresh.yml) runs daily at 02:00 UTC (07:30 Asia/Colombo).
- **Change Detection:** Class `IncrementalWarehouseRefresher` ([`src/etl/incremental_refresher.py`](src/etl/incremental_refresher.py)) scans for new files, compares SHA-256 hashes against `raw.source_document`, and processes only new/revised periods.
- **Mart Refresh:** Automatically executes `CALL etl.sp_refresh_analytical_marts();` upon completing any batch ingestion.

Run the refresher on-demand:
```powershell
python scripts/refresh_warehouse.py --dataset all
```

See [docs/deployment/etl-scheduler.md](docs/deployment/etl-scheduler.md) for orchestration details.

---

## 11. Data Quality, Quarantine & Integrity Defense

The warehouse enforces Lecture 6 data preprocessing standards with automated defense gates:
1. **Quarantine Ledger (`audit.data_quality_issue`):** Rows with unknown station aliases or out-of-boundary values are quarantined with explicit rule codes (`ERR_UNMAPPED_STATION_ALIAS`, `ERR_NEGATIVE_DISPATCH_MW`).
2. **Batch Audit (`audit.etl_run`):** Every pipeline execution logs rows read, inserted, updated, and quarantined with timestamps and status.
3. **Cross-Source Reconciliation (`audit.reconciliation_case`):** Reconciles sub-daily Riemann integrated dispatch against audited monthly statistical digest totals.

---

## 12. 24 Analytical Queries Overview

The warehouse includes 24 verified analytical SQL queries organized across six operational domains:

- **Domain 1: Generation Mix & Renewables (Q01–Q04):** Monthly fuel mix (`ROLLUP`), 7-day smoothed renewable penetration, plant capacity factors, and Time-of-Use generation.
- **Domain 2: Grid Dispatch Dynamics (Q05–Q08):** Diurnal load curves (weekday vs. weekend), 15-minute ramp rates (`LAG`), baseload vs. peaking classification, and telemetry energy reconciliation.
- **Domain 3: Electricity Demand Dynamics (Q09–Q12):** 5-year provincial consumption trends, multi-year sector pivots, hotel sector recovery CAGR, and LECO bulk supply accounting.
- **Domain 4: Weather & Renewable Coupling (Q13–Q16):** Peak Sun Hours (PSH) solar availability, temperature vs. peak demand correlation, hydro catchment rainfall (`CUBE`), and wind power curves.
- **Domain 5: Plant Operations & Capacity (Q17–Q20):** Telemetry outage vs. zero-generation filtering, peak dispatch vs. nameplate ratings, Lakvijaya baseload continuity, and thermal merit-order dispatch.
- **Domain 6: Grid Efficiency & Quality (Q21–Q24):** Tariff class economic shifts (`GROUPING SETS`), transmission/distribution loss proxy, data quality quarantine audit, and ETL throughput benchmarks.

All queries are located in [`database/queries/`](database/queries/) and documented in [docs/analytics/phase-3-query-catalogue.md](docs/analytics/phase-3-query-catalogue.md).

---

## 13. Next.js 16 Analytics Dashboard

The frontend is a light-mode Business Intelligence dashboard built with **Next.js 16 App Router, React 19, TypeScript, Tailwind CSS 4, and Recharts**.

- **Hybrid Data Source Mode (`DATA_SOURCE_MODE=hybrid`):** Attempts live parameterized queries against PostgreSQL/Supabase; seamlessly falls back to pre-computed verified snapshots if the database is unreachable.
- **Live Mode (`DATA_SOURCE_MODE=live`):** Enforces live cloud queries with real-time query execution metrics and connection diagnostics.
- **Interactive Visualizations:** Diurnal load curves, solar PSH heatmaps, capacity factor distribution charts, and fuel mix area charts.

---

## 14. Quickstart: Local Native PostgreSQL Setup

Run the entire warehouse locally on Windows with one command:

```powershell
# 1. Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run one-command local bootstrap
python scripts/bootstrap_local.py
```

This single command:
- Connects to your local PostgreSQL instance on port `5432` or `5433`.
- Creates `sl_grid_warehouse` and `sl_grid_warehouse_test`.
- Applies migrations `001–022`.
- Seeds 13 conformed dimensions and reference tables.
- Ingests real historical datasets (CEB sales, NASA weather, PUCSL dispatch).
- Refreshes analytical materialized marts and synchronizes `web/.env.local`.

---

## 15. Quickstart: Supabase Cloud Setup

Provision the entire warehouse on Supabase with one command:

```powershell
# 1. Set your Supabase connection string in .env:
# DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.leormbswimbnpixkkbbu.supabase.co:5432/postgres

# 2. Run one-command Supabase migration runner
python scripts/migrate_supabase.py
```

Useful commands:
```powershell
# Non-destructive health and inventory audit
python scripts/migrate_supabase.py --verify-only

# Preview schema operations without writing
python scripts/migrate_supabase.py --dry-run

# Start Next.js dashboard against Supabase
pnpm --dir web dev
```
Navigate to `http://localhost:3000` to explore the live cloud data warehouse.

---

## 16. Running Analytical Queries & ETL

Execute analytical queries or incremental refresh jobs directly from the CLI:

```powershell
# Run a specific analytical query
python scripts/run_query.py Q01

# Execute incremental refresh for PUCSL dispatch
python scripts/refresh_warehouse.py --dataset pucsl

# Verify warehouse inventory across all schemas
python scripts/migrate_supabase.py --verify-only
```

---

## 17. Automated Testing Strategy

GridLens adheres to Test-Driven Development (TDD) across three automated test tiers:
- **Unit Tests (`tests/unit/`):** Fast in-memory tests verifying parsers, checksum calculation, configuration loading, and date transformations.
- **Data Quality Tests (`tests/data_quality/`):** Assertions on physical units, non-negative dispatch values, date ranges, and quarantine behavior.
- **Integration Tests (`tests/integration/`):** Live database connection, migration rollback, and transactional integrity tests.

Run the test suite:
```powershell
python -m pytest tests/unit tests/data_quality -v
```

---

## 18. Security, Roles & Least-Privilege Governance

The warehouse implements a defense-in-depth role matrix:
- **`grid_admin`:** Superuser/owner responsible for executing schema migrations and DDL.
- **`grid_etl`:** Data loader role with `SELECT`, `INSERT`, and `UPDATE` on staging, facts, and audit tables. Explicitly denied `DELETE` and `TRUNCATE` on production facts.
- **`grid_analyst`:** Strictly read-only role used by analytical consumers and the Next.js dashboard. Enforced session-level `SET default_transaction_read_only = on` and strict query statement timeouts (5s to 10s).
- **Zero Credentials in Git:** Passwords, database URLs, and API tokens are read exclusively from environment variables. `.env` and `web/.env.local` are tracked in `.gitignore`.

---

## 19. Repository Structure

```
├── .agents/                  # Agent rules and architecture skills
├── .github/                  # CI and scheduled refresh GitHub Actions
│   └── workflows/
│       ├── ci.yml            # Lint, typing, unit, and quality test pipeline
│       └── scheduled-data-refresh.yml # Daily automated warehouse refresh
├── data/                     # Immutable raw and staged data
│   ├── raw/                  # CEB, PUCSL, NASA POWER downloads with manifest.json
│   └── staging/              # Staged normalized records
├── database/                 # Database schema and analytical assets
│   ├── migrations/           # 22 sequential forward SQL migrations (001–022)
│   └── queries/              # 24 verified analytical OLAP SQL queries (Q01–Q24)
├── docs/                     # Living technical documentation
│   ├── architecture/         # System design, bus matrix, data flow, and ADRs
│   ├── data_sources/         # Source inventory, coverage boundaries, and profiling
│   ├── database/             # Fact tables, conformed dimensions, advanced SQL
│   ├── deployment/           # Supabase setup, migration plan, and scheduler
│   └── testing/              # Test strategy, verification checklists, and reports
├── scripts/                  # Operational CLI runners
│   ├── bootstrap_local.py    # One-command local native PostgreSQL bootstrap
│   ├── migrate_supabase.py   # One-command Supabase cloud migration & verify
│   ├── refresh_warehouse.py  # Automated incremental refresh CLI
│   ├── migrate.py            # Sequential migration runner
│   ├── seed_reference.py     # Idempotent reference dimension seeder
│   └── verify_database.py    # Comprehensive database audit runner
├── src/                      # Core Python application package
│   ├── common/               # Config, logging, and database connection pooling
│   ├── etl/                  # Real data loader and incremental refresher
│   ├── ingestion/            # Source parsers and manifest validators
│   ├── preprocessing/        # Data cleaning and unit normalization
│   └── validation/           # Quality assertions and quarantine filters
├── tests/                    # Automated test suites (60+ tests)
│   ├── unit/                 # In-memory unit tests
│   ├── data_quality/         # Domain constraint and quarantine tests
│   └── fixtures/             # Representative synthetic fixtures
└── web/                      # Next.js 16 BI analytics dashboard
    ├── src/app/              # Next.js App Router pages and API routes
    ├── src/components/       # Reusable UI cards, charts, and metrics
    └── src/lib/db/           # PostgreSQL connection client with Supabase TLS
```

---

## 20. Living Documentation Map

Explore comprehensive technical documentation:
- 📐 [Fact Constellation Architecture](docs/architecture/fact-constellation.md)
- 🔄 [End-to-End Data Flow Pipeline](docs/architecture/data-flow.md)
- 📊 [Fact Tables Specification](docs/database/fact-tables.md)
- 🏷️ [Conformed Dimensions Specification](docs/database/dimension-tables.md)
- ⚡ [Advanced PostgreSQL Engineering Features](docs/database/advanced-postgresql-features.md)
- 🌐 [Data Source Inventory & Provenance](docs/data_sources/source-inventory.md)
- 🔍 [Historical Coverage & Limitations](docs/data_sources/coverage-and-limitations.md)
- ☁️ [Supabase Cloud Setup Guide](docs/deployment/supabase-setup.md)
- 🚀 [Supabase Migration Plan](docs/deployment/supabase-migration-plan.md)
- ⏱️ [Automated ETL Scheduler Guide](docs/deployment/etl-scheduler.md)
- 🛡️ [Backup & Disaster Recovery Plan](docs/deployment/backup-and-recovery.md)
- 💻 [Local Native PostgreSQL Setup Guide](docs/database/local-native-postgresql-setup-guide.md)
- 📋 [Analytical Query Catalogue (Q01–Q24)](docs/analytics/phase-3-query-catalogue.md)

---

## 21. Engineering Standards & Contributions

- **Branching Strategy:** Feature branches (`feature/*`, `fix/*`) branch from `development`. Changes merge into `development` through reviewed Pull Requests. Direct commits to `main` are strictly prohibited.
- **Commit Messages:** Follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- **Code Formatting:** Python code is formatted with [Ruff](https://github.com/astral-sh/ruff) and checked with [Mypy](https://mypy-lang.org/) in strict mode. Frontend code is formatted with Prettier and checked with ESLint.
- **Continuous Integration:** Every push and pull request triggers GitHub Actions validating linting, strict typing, unit tests, and data quality assertions.
