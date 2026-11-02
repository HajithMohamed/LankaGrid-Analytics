# GridLens: National Electricity Grid Analytics Data Warehouse — Final Academic Deliverables

## Academic Group Project Submission Package
- **Institution:** University of Ruhuna
- **Faculty:** Faculty of Technology
- **Department:** Department of Information and Communication Technology (ICT)
- **Course:** CS4032 Advanced Data Warehousing
- **Project Title:** GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka
- **Repository:** `https://github.com/HajithMohamed/LankaGrid-Analytics`
- **Database Engine:** PostgreSQL 18 on Docker (Service `postgres`, container `sl_grid_warehouse_db`, port 5433)
- **Programming Language & Tools:** Python 3.14, Psycopg 3, Pandas, Pytest, Ruff, Docker Compose
- **Academic Team:** Six Undergraduate Software Engineers

---

## 1. Executive Summary & Data Coverage

The GridLens data warehouse models and analyzes historical generation, transmission dispatch, sectoral electricity sales, and satellite meteorological observations for the Sri Lankan national power grid. The dimensional model follows Ralph Kimball's dimensional architecture (Fact Constellation) and complies with the data warehousing concepts from Lectures 1 through 8.

### Real Data Coverage & Boundaries (Zero Fabrication Policy):
- **High-Frequency SCADA Dispatch Telemetry:** 107,115 atomic 15-minute dispatch facts covering the complete month of **March 1–31, 2024** (744 consecutive hours) across 25 major grid generation stations, sourced from official PUCSL transmission dispatch logs (*15-Minutes-Report-31-Mar2024.xlsx*).
- **Five-Year Sectoral Electricity Demand:** Audited electricity sales and consumer account figures across 10 tariff sectors spanning **2020 to 2024** (49 facts), sourced from official Ceylon Electricity Board (CEB) *Statistical Digests*.
- **Five-Year Satellite Meteorological Observations:** Daily surface solar irradiance, air temperature, precipitation, and 50m wind speed spanning **2020 to 2024** (21,924 facts), sourced from the NASA POWER satellite reanalysis API across two critical grid nodes (`LOC_VICTORIA_CATCHMENT` and `LOC_MANNAR_WIND`).
- **Physical Integrity & Zero-Value Distinction:** $0.00\text{ MW}$ signifies physical shutdown/reserve; missing telemetry is explicitly preserved as `NULL`. No synthetic or fabricated measurements exist in the warehouse.

---

## 2. Master Deliverables Directory

This `deliverables/final-submission/` directory contains the official academic deliverables:

| Document File | Title & Description | Primary Audience |
| :--- | :--- | :--- |
| **`01-final-academic-implementation-report.md`** | **Comprehensive Academic Implementation Report (10 Chapters):** Full project technical specification covering problem motivation, Kimball bus matrix, 8-schema layout, 9 conformed dimensions, 6 fact tables, Lecture 6 data preprocessing, 24 analytical queries with verified SQL outputs, and academic conclusions. | Academic Evaluators & Lecturers |
| **`02-advanced-database-concepts-and-optimization.md`** | **Advanced Database Concepts & Optimization Reference:** In-depth documentation of PostgreSQL 18 declarative yearly range partitioning, concurrency-safe materialized views, transaction-safe migration runner with SHA-256 integrity, window functions (`LAG()`), and OLAP aggregation operators (`ROLLUP`, `CUBE`, `GROUPING SETS`). | Database Specialists & Reviewers |
| **`03-live-demonstration-guide.md`** | **Live Technical Demonstration Guide (15–20 Mins):** Step-by-step reproducible runbook to demonstrate container startup, migration verification, data quality quarantine audit, and live query execution across all 6 member domains. | Examination Panel & Demonstrators |
| **`04-academic-presentation-slide-deck.md`** | **Academic Presentation Slide Deck Outline (24 Slides):** Detailed slide structure, diagrams, speaking allocations, and timing covering all 6 team members (~3.5 mins each). | Presentation Assessors |
| **`05-member-presentation-speaking-notes.md`** | **Member-by-Member Presentation Speaking Scripts:** Precise, academically rigorous talking points for all 6 members with exact figures, physical justifications, and smooth transitions. | Student Presenters |
| **`06-technical-defense-q-and-a.md`** | **Technical Examination Questions & Defense Reference (24 Q&A):** 4 advanced technical questions and answers per member covering Kimball architecture, SQL:1999 OLAP operators, PostgreSQL internals, and grid physics. | Oral Defense Panel |
| **`07-verified-database-schema-inventory.md`** | **Authoritative Physical Schema Inventory:** Exact reflection of all 8 database schemas, 9 dimensions, 6 facts, yearly partitions, views, indexes, triggers, and procedures running in PostgreSQL 18. | Technical Auditors |
| **`08-deliverables-verification-and-audit-report.md`** | **Phase 4 Verification & Quality Gate Audit Report:** Evidence of 100% test pass rate (101 automated tests), Ruff linter/formatter compliance, and static typing verification. | QA & Assessment Panel |

---

## 3. Physical Database Architecture Summary

The PostgreSQL 18 database (`sl_grid_warehouse`) contains **8 isolated schemas**:
1. `raw`: Immutable raw ingested records and file provenance manifests (`raw.source_document`, `raw.extracted_record`).
2. `staging`: Normalized staging tables for raw incoming data (`staging.stg_pucsl_15min_dispatch`, `staging.stg_ceb_annual_sales`, `staging.stg_nasa_daily_weather`).
3. `ref`: Standard lookup entities, conformed codes, and data quality validation rules (`ref.data_quality_rule`, `ref.power_station_lookup`).
4. `dw`: Kimball dimensional warehouse core:
   - **9 Conformed Dimensions:** `dim_date`, `dim_interval`, `dim_source_system`, `dim_energy_source`, `dim_region`, `dim_consumption_sector`, `dim_power_plant`, `dim_weather_location`, `dim_metric`.
   - **6 Fact Tables:** `fact_dispatch_interval` (declaratively partitioned by yearly ranges: `y2020` to `y2026` + `default`), `fact_generation_period`, `fact_capacity_period`, `fact_electricity_sales`, `fact_weather_daily`, `fact_published_metric`.
5. `etl`: Stored procedures for idempotent pipeline transformation and loading (`etl.sp_load_dispatch_facts`, `etl.sp_load_sales_facts`, `etl.sp_load_weather_facts`).
6. `mart`: High-speed pre-aggregated materialized views (`mart.mv_daily_dispatch_by_source`, `mart.mv_monthly_weather_summary`).
7. `audit`: Operational governance, execution batch logs, row-level lineage (`audit.record_lineage`, 272,526 rows), and quarantine issue tracking (`audit.data_quality_issue`, 926 rows).
8. `public`: Database bootstrap and schema migration audit register (`public.schema_migrations`, 21 applied migrations).

---

## 4. Visual Diagrams & Analytical Charts

All diagrams and charts are accessible in the repository:
- **Mermaid Architecture Diagrams (`docs/diagrams/`):**
  - `system-architecture.mmd`: End-to-end ingestion, staging, dimensional warehouse, and analytical marts.
  - `fact-constellation.mmd`: Real Kimball model showing all 9 dimensions and 6 facts with authentic keys.
  - `etl-workflow.mmd`: Idempotent extraction, quarantine validation, loading, and audit lineage.
  - `schema-architecture.mmd`: Physical 8-schema layout and isolation boundaries.
  - `advanced-database-workflow.mmd`: Yearly range partitioning, static/runtime pruning, and concurrent materialized view refresh.
  - `analytical-query-architecture.mmd`: Mapping of 24 queries across 6 members to underlying warehouse facts.
- **Publication-Ready Matplotlib Charts (`results/phase3/charts/`):**
  - `chart_01_generation_mix_march_2024.png`: Donut chart of national generation mix (Coal 42.56%, Oil 27.69%, Hydro 22.98%, NCRE 6.77%).
  - `chart_02_renewable_daily_share_march_2024.png`: 31-day renewable penetration trajectory with 7-day centered moving average.
  - `chart_03_dispatch_curve_weekday_vs_weekend.png`: 96-interval diurnal load curves showing 235 MW weekend drop.
  - `chart_04_five_year_sales_trends.png`: Five-year sectoral sales evolution and hotel tourism rebound (+83.94%).
  - `chart_05_solar_irradiance_victoria_vs_mannar.png`: Monthly solar profiles showing pre-monsoon peaks (5.8–6.4 PSH).
  - `chart_06_tou_generation_contribution.png`: Stacked bar chart of Daytime vs Evening Peak vs Off-Peak generation.

---

## 5. Verification & Reproducibility Protocol

To reproduce the warehouse and verify all deliverables locally:

```bash
# 1. Start PostgreSQL 18 container
docker compose up -d postgres

# 2. Run automated test suite (Unit, Data Quality, Integration, Analytics)
pytest tests/unit tests/data_quality tests/integration tests/analytics -v

# 3. Verify static code quality
python -m ruff check .
python -m ruff format --check .
python -m mypy src scripts tests/analytics

# 4. Execute all 24 analytical queries and regenerate charts
python scripts/execute_phase3_queries.py
python scripts/generate_phase3_charts.py
```

### Note on File Formats & Document Export:
All academic deliverables are maintained in standard GitHub Flavored Markdown (`.md`) with embedded LaTeX math (KaTeX) and Mermaid syntax. Because binary conversion utilities (`pandoc`, `libreoffice`) are not present in this runtime environment, these documents represent the authoritative, lossless primary format. They can be rendered directly in GitHub, Antigravity IDE, Visual Studio Code, or exported to PDF/DOCX using standard markdown tools.

