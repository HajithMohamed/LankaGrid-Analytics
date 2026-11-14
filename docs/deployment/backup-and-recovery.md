# Warehouse Backup, Recovery & Disaster Management

## Overview

As an analytical data warehouse, GridLens maintains strict data durability and immutability standards:
1. **Raw File Immutability:** Raw source files are stored in `data/raw/` with verified SHA-256 hashes recorded in `data/raw/manifest.json`.
2. **Schema Reproducibility:** The entire database schema can be rebuilt from scratch using sequential migrations `database/migrations/001–022`.
3. **Reference Seeding Idempotence:** Conformed dimensions and reference taxonomies are completely reproducible via `scripts/seed_reference.py`.
4. **Cloud Database Backups:** Supabase provides automated daily snapshots and point-in-time recovery (PITR).

---

## 1. Supabase Automated Backups

- **Daily Physical Backups:** Managed automatically by Supabase for production projects.
- **Point-in-Time Recovery (PITR):** Allows rolling back to any specific second in the event of an operational failure.

---

## 2. On-Demand Logical Backups (`pg_dump`)

To take an on-demand logical backup of the warehouse schemas:

```bash
# Export all 7 warehouse schemas
pg_dump "postgresql://postgres:[PASSWORD]@db.<project-ref>.supabase.co:5432/postgres" \
  --schema="raw" \
  --schema="staging" \
  --schema="ref" \
  --schema="dw" \
  --schema="mart" \
  --schema="audit" \
  --schema="etl" \
  --format=custom \
  --file="gridlens_backup_$(date +%Y%m%d_%H%M%S).dump"
```

---

## 3. Disaster Recovery & Clean Re-Provisioning

If the cloud database is ever corrupted or deleted, the full warehouse can be restored in minutes:

1. Provision a fresh PostgreSQL database or Supabase instance.
2. Set `DATABASE_URL` in `.env`.
3. Run the automated migration runner:
   ```bash
   python scripts/migrate_supabase.py
   ```
4. All schemas, reference taxonomies, historical facts, and materialized marts will be rebuilt from authenticated local assets with zero data loss.

