---
name: etl-development
description: >-
  Provides procedures for building idempotent Extract, Transform, Load (ETL) pipelines,
  incremental batch processing, error handling, dead-letter quarantine, and audit logging.
  Use when creating or debugging ETL loaders and warehouse loading scripts.
---

# ETL Development Skill

## When to Use This Skill
Use this skill when developing, refactoring, or running ETL pipelines in `src/etl/` that load data from staging files or APIs into PostgreSQL warehouse tables.

## ETL Development Procedure

### 1. Extract Phase
1. Load verified staging files or fetch incremental API records.
2. Verify batch metadata (batch ID, source file checksum, record count).
3. Ensure the extract operation is read-only and does not mutate source data.

### 2. Transform Phase
1. Map source business keys to warehouse surrogate dimension keys:
   - Perform dimension lookups against cached or staged `dim_*` tables.
   - If an unknown business key is encountered, route the record to quarantine or assign a predefined `UNKNOWN` dimension member (`id = -1`).
2. Format measures and calculate derived metrics (e.g. Capacity Factor, Hydro Storage Percentage).
3. Validate row-level constraints before loading.

### 3. Load Phase (Idempotency Standard)
1. Load into PostgreSQL staging table first:
   ```sql
   CREATE TEMP TABLE tmp_stage_generation AS SELECT * FROM fact_daily_generation WITH NO DATA;
   ```
2. Bulk copy data using `psycopg` `copy()` API for maximum ingestion throughput.
3. Merge staged data into the target fact table using `INSERT ... ON CONFLICT`:
   ```sql
   INSERT INTO fact_daily_generation (date_id, plant_id, fuel_id, energy_mwh, peak_mw, created_at)
   SELECT date_id, plant_id, fuel_id, energy_mwh, peak_mw, CURRENT_TIMESTAMP
   FROM tmp_stage_generation
   ON CONFLICT (date_id, plant_id)
   DO UPDATE SET
       energy_mwh = EXCLUDED.energy_mwh,
       peak_mw = EXCLUDED.peak_mw,
       updated_at = CURRENT_TIMESTAMP;
   ```
4. Never use bare `INSERT INTO` without conflict resolution on natural grain keys.

### 4. Error Handling & Quarantine
1. Wrap the entire batch in a database transaction (`with connection.transaction():`).
2. If an unrecoverable failure occurs, roll back the transaction completely.
3. Log errors to `etl_pipeline_log` table with timestamp, batch ID, error message, and stack trace.
4. Export rejected records to `data/staging/quarantine/<batch_id>_rejected.csv`.

## Expected Outputs
- Populated fact and dimension records in PostgreSQL
- Completed execution record in `etl_execution_log`
- Quarantine files for rejected records (if any)

## Verification Steps
1. Run idempotency test: Execute the exact same ETL script twice sequentially. Confirm row counts and table checksums remain identical.
2. Run `pytest tests/integration/test_etl_pipeline.py`.
3. Check execution logs in PostgreSQL:
   ```sql
   SELECT * FROM etl_execution_log ORDER BY started_at DESC LIMIT 5;
   ```
