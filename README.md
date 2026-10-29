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

## Quick Start
1. Copy `.env.example` to `.env` and configure local database credentials:
   ```bash
   cp .env.example .env
   ```
2. Start the PostgreSQL 18 container:
   ```bash
   docker compose up -d
   ```
3. Run test suites:
   ```bash
   pytest tests/
   ```

## License
Academic coursework project. All rights reserved.
