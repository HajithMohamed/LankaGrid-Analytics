# National Electricity Grid Analytics Data Warehouse — Sri Lanka

## Overview
An academic data warehouse engineering project modeling and analyzing historical electricity generation, dispatch, capacity, consumption, and solar/meteorological data for the Sri Lankan national grid. Developed by a team of six undergraduate software engineers at the University of Ruhuna, Faculty of Technology, Department of ICT.

## Architecture & Technology Stack
- **Database Target**: PostgreSQL 18 (Local Native or Docker)
- **Modeling Paradigm**: Kimball Dimensional Architecture (Star / Fact Constellation)
- **Data Engineering**: Python 3.11+, Psycopg 3, Pandas, PyPDF, PDFPlumber
- **Testing & Quality**: Pytest, Mypy (strict typing), Ruff, Automated Quarantine Quality Gates
- **Frontend / BI**: Next.js 16 App Router, React 19, TypeScript, Tailwind CSS v4, Recharts

## Repository Structure
```
├── .agents/              # Agent rules, workflows, and governance skills
├── config/               # Application configuration files
├── data/                 # Raw and staging data directories (immutable provenance)
│   ├── raw/              # Official CEB, PUCSL, NASA POWER downloads with manifest.json
│   ├── staging/          # Normalized interim records
│   └── processed/        # Validated datasets ready for dimensional warehouse
├── database/             # PostgreSQL schema, migrations, queries, and seeds
│   ├── migrations/       # Sequential forward migrations (001 to 022)
│   ├── queries/          # 24 Analytical OLAP queries (Q01–Q24) across 6 domains
│   └── seeds/            # Initial dimension reference data
├── docs/                 # Project documentation and specifications
│   ├── architecture/     # System overview and dimensional bus matrix
│   ├── assignment/       # Academic deliverables and requirements tracking
│   ├── dashboard/        # BI dashboard guides, presentation notes, and UI audits
│   ├── data_sources/     # Data source inventory and profiling notes
│   ├── database/         # Schema dictionaries, ERDs, and local native setup guides
│   ├── team/             # Team allocations and member responsibilities
│   └── testing/          # Test strategy and execution reports
├── scripts/              # Migration runners, database initialization, and ETL loaders
├── src/                  # Core application source code
│   ├── common/           # Configuration, logging, and database connection pools
│   ├── etl/              # Idempotent batch extract-transform-load pipelines
│   ├── ingestion/        # Official source parsers and manifest validators
│   ├── preprocessing/    # Data cleaning, deduplication, and outlier detection
│   └── validation/       # Quarantine quality gates and integrity assertions
├── tests/                # Test suites
│   ├── data_quality/     # Data quality assertions and quarantine evaluation
│   ├── fixtures/         # Small, representative synthetic test fixtures
│   ├── integration/      # PostgreSQL connection and migration integration tests
│   └── unit/             # Parser, manifest, config, and preprocessing unit tests
└── web/                  # Next.js 16 light-mode Business Intelligence dashboard
```

---

## Quick Start Guidelines

You can run GridLens either using your **Local Native PostgreSQL (pgAdmin)** or using **Docker**.

### Detailed Guides:
- 📖 **Local Native PostgreSQL (No Docker Required)**: See [Local Native PostgreSQL Setup Guide](docs/database/local-native-postgresql-setup-guide.md).
- 📖 **UI Demonstration & Presentation Guide**: See [Final UI Demonstration Guide](docs/dashboard/final-ui-demonstration-guide.md).

---

### Path A: Local Native PostgreSQL (No Docker) — One-Command Setup

#### 1. Setup Python Virtual Environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# (If blocked by execution policy, run: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)
python -m pip install --upgrade pip
pip install -e .
pip install pytest pytest-cov ruff mypy
```

#### 2. Configure Local Database Credentials in `.env`:
```powershell
Copy-Item .env.example .env
```
Open `.env` in any text editor and set your local PostgreSQL credentials:
```ini
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sl_grid_warehouse
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_local_postgres_password
```

#### 3. Run the Automated One-Command Bootstrap:
```powershell
python scripts/bootstrap_local.py
```
This single command safely and automatically:
1. Validates your Python runtime (>= 3.11) and raw data assets.
2. Creates the target databases (`sl_grid_warehouse`, `sl_grid_warehouse_test`) if they do not exist (never drops existing data).
3. Applies all 22 sequential forward migrations with SHA-256 immutability verification.
4. Configures least-privilege database roles (`grid_etl`, `grid_analyst`).
5. Seeds 13 conformed dimension and reference tables idempotently.
6. Populates authentic historical data (CEB 5-yr sales, NASA POWER 5-yr weather, PUCSL dispatch) without duplicating existing records.
7. Performs a non-destructive read-only warehouse integrity verification across all 7 schemas and 5 materialized views.
8. Automatically generates and synchronizes `web/.env.local` for the Next.js Analytics Dashboard (`DATA_SOURCE_MODE=live`).

*Optional flags:*
- `python scripts/bootstrap_local.py --dry-run` : Preview planned actions without modifying anything.
- `python scripts/bootstrap_local.py --verify-only` : Run non-destructive verification without re-seeding or re-loading.
- `python scripts/bootstrap_local.py --skip-data` : Apply migrations and seeds, but skip large historical fact loads.

#### 4. Run the Automated Test Suite:
```powershell
pytest tests/unit tests/data_quality -v
```

#### 5. Run the Next.js Analytics Dashboard (`web/`):
```powershell
cd web
pnpm install
pnpm dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser. (Database connection is automatically configured by `bootstrap_local.py`).

---

### Path B: Docker Setup (Alternative)

```powershell
# 1. Configure .env
Copy-Item .env.example .env

# 2. Start PostgreSQL 18 container (defaults to port 5433 to avoid host conflicts)
docker compose up -d postgres --wait

# 3. Run migrations and ETL
python scripts/migrate.py up
python scripts/migrate.py configure-roles
python scripts/seed_reference.py
python scripts/load_historical_warehouse.py

# 4. Start Next.js dashboard
cd web
Copy-Item .env.example .env.local
pnpm install
pnpm run dev
```

---

## Physical Units & Domain Integrity
- **Active Power (MW)**: Instantaneous demand rate.
- **Energy (MWh / GWh)**: Integrated energy output ($1\text{ GWh} = 1{,}000\text{ MWh}$). $\text{MWh} = \text{MW} \times 0.25\text{ h}$ for 15-minute intervals.
- **Missing vs. Zero**: Missing observations are preserved as `NULL`. $0\text{ MW}$ indicates a real plant outage or shutdown.
- **Data Provenance**: Immutable raw archives stored in `data/raw/` with SHA-256 checksums recorded in `manifest.json`.

---

## Academic Documentation References
- [System Architecture Overview](docs/architecture/system-overview.md)
- [Dimensional Bus Matrix](docs/architecture/dimensional-bus-matrix.md)
- [Fact Constellation & Schema ERDs](docs/database/erd-fact-constellation.md)
- [Complete Data Dictionary](docs/database/data-dictionary.md)
- [Local Native PostgreSQL Setup Guide](docs/database/local-native-postgresql-setup-guide.md)
- [Final UI Demonstration & Evaluation Guide](docs/dashboard/final-ui-demonstration-guide.md)

## License
Academic coursework project. University of Ruhuna, Faculty of Technology, Department of ICT. All rights reserved.
