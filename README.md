# National Electricity Grid Analytics Data Warehouse — Sri Lanka

## Overview
An academic data warehouse engineering project modeling and analyzing historical electricity generation, dispatch, capacity, consumption, and solar/meteorological data for the Sri Lankan national grid.

## Architecture & Technology Stack
- **Database Target**: PostgreSQL 18 on Docker
- **Modeling Paradigm**: Kimball Dimensional Architecture (Star / Fact Constellation)
- **Data Engineering**: Python 3.12+, Psycopg 3, Pandas, PyPDF, PDFPlumber
- **Testing & Quality**: Pytest, Mypy (strict typing), Ruff, Automated Quarantine Quality Gates

## Repository Structure
```
├── .agents/              # Agent rules, workflows, and governance skills
├── config/               # Application configuration files
├── data/                 # Raw and staging data directories (immutable provenance)
│   ├── raw/              # Official CEB, PUCSL, NASA POWER downloads with manifest.json
│   ├── staging/          # Normalized interim records
│   └── processed/        # Validated datasets ready for dimensional warehouse
├── database/             # PostgreSQL schema, migrations, queries, and seeds
│   ├── migrations/       # Numbered sequential forward migrations
│   ├── queries/          # Business and analytical OLAP queries
│   └── seeds/            # Initial dimension reference data
├── docs/                 # Project documentation and specifications
│   ├── architecture/     # System overview and dimensional bus matrix
│   ├── assignment/       # Academic deliverables and requirements tracking
│   ├── data_sources/     # Data source inventory and profiling notes
│   ├── database/         # Schema data dictionaries and ERDs
│   ├── team/             # Team allocations and member responsibilities
│   └── testing/          # Test strategy and execution reports
├── scripts/              # Migration runners, database initialization, and utilities
├── src/                  # Core application source code
│   ├── common/           # Configuration, logging, and database connection pools
│   ├── etl/              # Idempotent batch extract-transform-load pipelines
│   ├── ingestion/        # Official source parsers and manifest validators
│   ├── preprocessing/    # Data cleaning, deduplication, and outlier detection
│   └── validation/       # Quarantine quality gates and integrity assertions
└── tests/                # Test suites
    ├── data_quality/     # Data quality assertions and quarantine evaluation
    ├── fixtures/         # Small, representative synthetic test fixtures
    ├── integration/      # PostgreSQL connection and migration integration tests
    └── unit/             # Parser, manifest, config, and preprocessing unit tests
```

## Quick Start (Phase 1 — PostgreSQL 18 Warehouse Foundation)
1. Copy [.env.example](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.env.example) to `.env` and configure local database credentials (set `POSTGRES_PORT=5433` if port `5432` is already used on the host):
   ```powershell
   Copy-Item .env.example .env
   ```
2. Start the PostgreSQL 18 container:
   ```powershell
   docker compose up -d postgres --wait
   ```
3. Apply sequential migrations (`001`–`017`), configure role credentials from `.env`, and seed verified static reference data:
   ```powershell
   .\.venv\Scripts\python.exe scripts/migrate.py up
   .\.venv\Scripts\python.exe scripts/migrate.py configure-roles
   .\.venv\Scripts\python.exe scripts/seed_reference.py
   ```
4. Run automated TDD test suites and full database verification:
   ```powershell
   .\.venv\Scripts\pytest.exe -v --cov=src --cov=scripts
   .\.venv\Scripts\python.exe scripts/verify_database.py
   ```

## Key Phase 1 Documentation
- [System Architecture Overview](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/architecture/system-overview.md) & [Dimensional Bus Matrix](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/architecture/dimensional-bus-matrix.md)
- [Fact Constellation & Schema ERDs](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/database/erd-fact-constellation.md) & [Complete Data Dictionary (514 Columns)](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/database/data-dictionary.md)
- [PostgreSQL 18 Setup & Migration Guide](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/database/postgresql-setup-and-migration-guide.md) & [Phase 1 Verification Report](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docs/testing/phase-1-verification-report.md)

## License
Academic coursework project. All rights reserved.
