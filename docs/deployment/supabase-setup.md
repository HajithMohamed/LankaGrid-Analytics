# Supabase Setup & Environment Configuration Guide

## Prerequisites

- Python 3.12+ with virtual environment installed.
- Node.js 22+ and `pnpm`.
- Active Supabase project credentials.

---

## 1. Environment Configuration

### Root Python Environment (`.env`)
Create or edit your local `.env` file in the repository root:

```bash
# Managed Supabase Cloud Connection String
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.leormbswimbnpixkkbbu.supabase.co:5432/postgres

# Mandatory Transport Security
POSTGRES_SSLMODE=require

# Operational Paths
DATA_RAW_DIR=data/raw
DATA_STAGING_DIR=data/staging
DATA_PROCESSED_DIR=data/processed
```

> [!CAUTION]
> Never commit real database passwords to Git. The `.env` and `web/.env.local` files are tracked in `.gitignore`.

### Next.js Dashboard Environment (`web/.env.local`)
Create or edit `web/.env.local`:

```bash
# Managed Supabase Connection
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.leormbswimbnpixkkbbu.supabase.co:5432/postgres

# Dashboard Data Source Mode:
# 'hybrid'   - Queries Supabase live; falls back to snapshots if offline.
# 'live'     - Requires live connection to Supabase.
# 'snapshot' - Strictly offline static snapshots.
DATA_SOURCE_MODE=hybrid

QUERY_STATEMENT_TIMEOUT_MS=10000
MAX_QUERY_ROWS_LIMIT=5000
NODE_ENV=development
```

---

## 2. One-Command Supabase Migration & Ingestion

Run the dedicated Supabase migration runner:

```powershell
python scripts/migrate_supabase.py
```

This single command will:
1. Validate connectivity and TLS encryption with your Supabase project.
2. Apply migrations `001` through `022` in sequential transactional order.
3. Seed all 13 conformed dimension and reference tables idempotently.
4. Load verified authentic historical facts (CEB 5-year sales, NASA 5-year weather, PUCSL dispatch).
5. Refresh all 5 analytical materialized views in `mart`.
6. Print a comprehensive health and inventory report.

---

## 3. Useful CLI Commands

### Non-Destructive Health Audit
```powershell
python scripts/migrate_supabase.py --verify-only
```

### Dry-Run Schema Preview
```powershell
python scripts/migrate_supabase.py --dry-run
```

### Apply Schema Only (Skip Large Datasets)
```powershell
python scripts/migrate_supabase.py --skip-data
```

### Run Next.js Dashboard against Supabase
```powershell
pnpm --dir web dev
```
Navigate to `http://localhost:3000` to interact with live Supabase analytical queries.

