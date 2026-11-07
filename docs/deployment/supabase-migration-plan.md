# Supabase Managed PostgreSQL Migration Plan

## 1. Executive Summary

This document specifies the migration plan for transitioning the GridLens National Electricity Grid Analytics Data Warehouse from local native PostgreSQL onto **Supabase Managed PostgreSQL**.

Migrating to Supabase provides:
- High-availability cloud-hosted PostgreSQL with automated point-in-time backups.
- Global low-latency access for team members and analytical consumers.
- Native SSL/TLS session and connection pooling.
- Seamless compatibility with Next.js dashboard deployments on Vercel.

---

## 2. Target Cloud Environment

- **Host:** `db.<project-ref>.supabase.co`
- **Default Database:** `postgres`
- **Admin User:** `postgres`
- **Standard Direct Port:** `5432` (Session Mode / DDL Migrations)
- **Transaction Pooler Port:** `6543` (Prepared statements disabled / high concurrency)
- **Transport Security:** Mandatory TLS/SSL (`sslmode=require`)
- **Node.js TLS Certificate Handling:** `rejectUnauthorized: false` for managed cloud certificates.

---

## 3. Migration Execution Stages

### Stage 1 — Configuration & Authentication
1. Configure environment variables in `.env` and `web/.env.local`:
   ```bash
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.<project-ref>.supabase.co:5432/postgres
   ```
2. Verify network connectivity via `python scripts/migrate_supabase.py --verify-only`.

### Stage 2 — Dry-Run Schema Inspection
1. Run pre-flight dry-run check:
   ```bash
   python scripts/migrate_supabase.py --dry-run
   ```
2. Inspect discovered migrations (001 through 022) and target schemas (`raw`, `staging`, `ref`, `dw`, `mart`, `audit`, `etl`).

### Stage 3 — Schema Provisioning & Dimension Seeding
1. Execute sequential forward migrations:
   ```bash
   python scripts/migrate_supabase.py --skip-data
   ```
   - Automatically records migration hashes in `public.schema_migrations`.
   - Seeds conformed dimensions and static taxonomies into `ref.*` and `dw.dim_*`.

### Stage 4 — Historical Fact Data Ingestion
1. Ingest authentic historical datasets:
   ```bash
   python scripts/migrate_supabase.py
   ```
   - CEB Billed Electricity Sales (2020–2024: 49 records)
   - NASA POWER Meteorological Observations (2020–2024: 21,924 records)
   - PUCSL Sub-Daily Generation Dispatch Curves (March 2024: 107,115 records)
2. Refresh analytical materialized views via stored procedure `etl.sp_refresh_analytical_marts()`.

### Stage 5 — Validation & Verification Audit
1. Execute post-migration audit:
   ```bash
   python scripts/migrate_supabase.py --verify-only
   ```
2. Run test queries and confirm Next.js dashboard connectivity.

