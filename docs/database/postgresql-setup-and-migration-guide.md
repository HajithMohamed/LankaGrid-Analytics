# PostgreSQL 18 Setup, Migration Execution & Scheduler Guide

## 1. Environment & Docker Setup

### Prerequisites
- Docker Desktop (Compose v2+)
- Python 3.12+ with `uv` or `venv`

### Configuration Steps
1. Create a local `.env` from [.env.example](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/.env.example):
   ```powershell
   Copy-Item .env.example .env
   ```
   > [!NOTE]
   > If another PostgreSQL service already occupies host port `5432`, set `POSTGRES_PORT=5433` in `.env`. Both [docker-compose.yml](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docker-compose.yml) and `DatabaseConfig.from_env()` in [config.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/common/config.py) automatically honor `POSTGRES_PORT`.

2. Start the **PostgreSQL 18** (`postgres:18-alpine`) container:
   ```powershell
   docker compose up -d postgres --wait
   ```
   *Note on PostgreSQL 18 Volume Layout*: Official `postgres:18+` Docker images use major-version cluster subdirectories under `/var/lib/postgresql` (`postgres_data:/var/lib/postgresql` in [docker-compose.yml](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/docker-compose.yml)), and [init-db.sh](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/init-db.sh) automatically initializes both `sl_grid_warehouse` and `sl_grid_warehouse_test`.

---

## 2. Migration Execution Guide ([migrate.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/migrate.py))

All 17 forward SQL migrations live in `database/migrations/` (`001_bootstrap.sql` through `017_scheduler_metadata.sql`) and are tracked in `public.schema_migrations` with normalized LF SHA-256 checksums.

```powershell
# 1. Inspect migration status (APPLIED vs PENDING)
.\.venv\Scripts\python.exe scripts/migrate.py status

# 2. Apply all pending migrations to primary database (sl_grid_warehouse)
.\.venv\Scripts\python.exe scripts/migrate.py up

# 3. Bind login passwords for grid_etl and grid_analyst from .env (zero secrets in SQL)
.\.venv\Scripts\python.exe scripts/migrate.py configure-roles

# 4. Seed verified reference and conformed dimension data idempotently
.\.venv\Scripts\python.exe scripts/seed_reference.py

# 5. Run full clean-room verification & SQL assertion suite
.\.venv\Scripts\python.exe scripts/verify_database.py
```

### Clean Teardown / Rollback (Development & Test Environments Only)
To reset an isolated test or local development database to an empty state before re-applying `001`–`017`, use [rollback_all_phase1.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/rollbacks/rollback_all_phase1.sql). Never modify an already-committed forward migration file; introduce schema changes via `018_<action>.sql`.

---

## 3. Scheduled Operations & Manual Refresh Guide ([017_scheduler_metadata.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/017_scheduler_metadata.sql))

PostgreSQL does **not** use MySQL `CREATE EVENT` syntax. Recurring maintenance jobs are catalogued in `etl.scheduled_job_registry` and remain **disabled/optional (`is_enabled = FALSE`)** in Phase 1:

- **Manual Refresh Execution** (recommended after ETL loads):
  ```sql
  -- Execute in an autocommit session:
  CALL etl.sp_refresh_mart_views(TRUE);
  ```
- **External Scheduler Option** (Linux `cron`, Windows Task Scheduler, or GitHub Actions / Airflow):
  ```powershell
  docker exec sl_grid_warehouse_db psql -U grid_admin -d sl_grid_warehouse -c "CALL etl.sp_refresh_mart_views(TRUE);"
  ```
- **Optional `pg_cron` Extension**: Check availability via `SELECT etl.fn_detect_pg_cron_available();`. On custom PostgreSQL images with `shared_preload_libraries = 'pg_cron'`, jobs in `etl.scheduled_job_registry` map directly to `cron.schedule(job_code, cron_schedule, sql_command)`.
