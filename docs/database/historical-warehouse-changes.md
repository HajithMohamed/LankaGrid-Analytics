# Database Schema Evolution — Phase 2.2 Historical Expansion

## 1. Context & Governance Standards

In strict accordance with project rules (`.agents/rules/postgresql.md` and `.agents/rules/database-migration/SKILL.md`):
- **Immutability of Applied Migrations**: Migrations `001` through `018` were already applied and are strictly immutable.
- **Controlled Forward Migrations**: All schema modifications, partitioning additions, dimensional expansions, and procedure alignments are governed by sequential forward migrations:
  - **Migration 019**: `database/migrations/019_historical_partitions_and_entities.sql` (Rollback: `rollbacks/019_historical_partitions_and_entities_rollback.sql`)
  - **Migration 020**: `database/migrations/020_dispatch_reporting_date_fix_and_reconciliation.sql` (Rollback: `rollbacks/020_dispatch_reporting_date_fix_and_reconciliation_rollback.sql`)
- **PostgreSQL 18 Target**: Verified on container `sl_grid_warehouse_db` (`postgres:18-alpine` running on port 5433).

---

## 2. Migration 019 Architecture & Components

### 2.1 Forward Range Partitioning for Sub-Daily Dispatch (`dw.fact_dispatch_interval`)

The primary fact table for 15-minute dispatch (`dw.fact_dispatch_interval`) is range-partitioned on `date_key`.
Migration 019 added dedicated historical yearly partitions for 2020, 2021, and 2022:

```sql
CREATE TABLE IF NOT EXISTS dw.fact_dispatch_interval_y2020 PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20200101) TO (20210101);

CREATE TABLE IF NOT EXISTS dw.fact_dispatch_interval_y2021 PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20210101) TO (20220101);

CREATE TABLE IF NOT EXISTS dw.fact_dispatch_interval_y2022 PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20220101) TO (20230101);
```

**Partition Pruning Verification**:
`EXPLAIN (FORMAT JSON)` confirms partition pruning: querying a date range in 2024 scans exclusively `fact_dispatch_interval_y2024`, completely skipping earlier years.

### 2.2 Conformed Dimension Expansion (`dw.dim_consumption_sector`)

Added conformed sector `BULK_LECO` to isolate Lanka Electricity Company bulk sales from CEB retail sales categories, ensuring audited sales reconciliation without double-counting.

### 2.3 Initial Stored Procedure Hardening
Hardened initial stored procedures: `etl.sp_validate_staged_dispatch`, `etl.sp_validate_staged_sales`, `etl.sp_load_electricity_sales`, and `etl.sp_load_weather_daily`.

---

## 3. Migration 020 Architecture & Remediation Components

Migration 020 resolves critical structural defects in dispatch date derivation, partition leakage, procedure integrity, and meteorological metadata.

### 3.1 Dispatch Reporting Date & Slot Staging (`staging.stg_dispatch_observation`)

In PUCSL spreadsheets, interval slot 96 represents 23:45–24:00 SLST. Because Python timestamps convert 24:00 to `next_day 00:00:00+05:30`, deriving `date_key` from the timestamp alone incorrectly assigned slot 96 to $D+1$ (e.g. March 1 slot 96 became March 2; March 31 slot 96 spilled into April 1).

Migration 020 alters `staging.stg_dispatch_observation`:
```sql
ALTER TABLE staging.stg_dispatch_observation
    ADD COLUMN IF NOT EXISTS reporting_date DATE,
    ADD COLUMN IF NOT EXISTS interval_slot_number SMALLINT;
```

### 3.2 High-Performance Lookup Indexes
To optimize batch staging and extraction lookups across 100,000+ row loads:
```sql
CREATE INDEX IF NOT EXISTS idx_stg_dispatch_batch_lookup
    ON staging.stg_dispatch_observation (batch_id, validation_status);

CREATE INDEX IF NOT EXISTS idx_extracted_record_dispatch_lookup
    ON raw.extracted_record (source_document_id, record_type_code, status);
```

### 3.3 Hardened `etl.sp_load_dispatch_interval`
1. **Reporting Date & Slot Assignment**:
   Resolves `date_key` directly from `rec.reporting_date` (or `(rec.parsed_timestamp - INTERVAL '1 day')::DATE` when slot is 96 and timestamp is `00:00:00`).
   Resolves `interval_key` directly from `rec.interval_slot_number` (1..96).
2. **Partitioned Table System Column Resolution**:
   PostgreSQL disallows retrieving system column `(xmax = 0)` in `RETURNING` clauses on partitioned tables. Migration 020 pre-checks record existence:
   ```sql
   SELECT fdi.dispatch_fact_id INTO v_existing_fact_id
     FROM dw.fact_dispatch_interval fdi
    WHERE fdi.date_key = v_date_key
      AND fdi.interval_key = v_interval_key
      AND fdi.plant_key = v_plant_key
      AND fdi.dataset_revision = rec.dataset_revision
    LIMIT 1;
   ```
   Counts inserts/updates explicitly and uses `RETURNING dispatch_fact_id INTO v_fact_id`.
3. **Audit Lineage Columns**:
   Corrects `audit.record_lineage` columns to canonical schema (`staging_table`, `staging_row_id`, `target_dw_table`, `target_dw_pk`, `transformation_notes`).

### 3.4 Hardened `etl.sp_load_weather_daily`
1. **Time Standard Metadata**: Stores `time_standard = 'LST'` (Local Solar Time) as declared in NASA POWER API headers.
2. **Conformed Metric Alignment**: Maps source parameter codes (`T2M`, `RH2M`, `WS10M`, `WS50M`, `PRECTOTCORR`, `ALLSKY_SFC_SW_DWN`) to verified canonical metric keys in `dw.dim_metric` (`AIR_TEMP_2M_C`, `REL_HUMIDITY_2M_PCT`, etc.).
3. **Physical Unit Conversion**: Standardizes solar insolation from $\text{kWh/m}^2/\text{day}$ to $\text{MJ/m}^2/\text{day}$ ($\times 3.600000$).

### 3.5 Auditable DML Data Repairs
Migration 020 executes idempotent data repairs on existing warehouse facts:
```sql
-- Repair displaced interval 96 facts
UPDATE dw.fact_dispatch_interval fdi
   SET date_key = (SELECT dd.date_key FROM dw.dim_date dd WHERE dd.calendar_date = ((fdi.original_timestamp AT TIME ZONE 'Asia/Colombo') - INTERVAL '1 day')::DATE)
 WHERE fdi.interval_key = 96
   AND fdi.date_key = (SELECT dd.date_key FROM dw.dim_date dd WHERE dd.calendar_date = (fdi.original_timestamp AT TIME ZONE 'Asia/Colombo')::DATE);

-- Standardize weather time standard metadata
UPDATE dw.fact_weather_daily
   SET time_standard = 'LST'
 WHERE time_standard <> 'LST' OR time_standard IS NULL;
```

---

## 4. Rollback Strategy

Each migration maintains a reversible rollback script:
- To roll back Migration 020:
  ```bash
  python scripts/migrate.py down --target 019
  ```
  Applies `database/migrations/rollbacks/020_dispatch_reporting_date_fix_and_reconciliation_rollback.sql`.
- To roll back Migration 019:
  ```bash
  python scripts/migrate.py down --target 018
  ```
  Applies `database/migrations/rollbacks/019_historical_partitions_and_entities_rollback.sql`.
