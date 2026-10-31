# Database Schema Evolution — Phase 2.2 Historical Expansion

## 1. Context & Governance Standards

In strict accordance with project rules (`.agents/rules/postgresql.md` and `.agents/rules/database-migration/SKILL.md`):
- **Immutability of Applied Migrations**: Migrations `001` through `018` were already applied and are strictly immutable.
- **Controlled Forward Migration**: All database alterations, partition additions, conformed dimension expansions, and stored procedure alignments for Phase 2.2 are implemented in:
  - Forward Migration: `database/migrations/019_historical_partitions_and_entities.sql`
  - Reversible Rollback: `database/migrations/019_historical_partitions_and_entities_rollback.sql`
- **PostgreSQL 18 Target**: Verified on container `sl_grid_warehouse_db` (`postgres:18-alpine` running on port 5433).

---

## 2. Migration 019 Architecture & Components

### 2.1 Forward Range Partitioning for Sub-Daily Dispatch (`dw.fact_dispatch_interval`)

The primary fact table for 15-minute dispatch (`dw.fact_dispatch_interval`) is range-partitioned on `date_key`.
Prior to Phase 2.2, partitions existed for 2023, 2024, and 2025 (`006_facts_generation_and_dispatch.sql`).

Migration 019 adds dedicated historical yearly partitions for 2020, 2021, and 2022:

```sql
CREATE TABLE IF NOT EXISTS dw.fact_dispatch_interval_y2020 PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20200101) TO (20210101);

CREATE TABLE IF NOT EXISTS dw.fact_dispatch_interval_y2021 PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20210101) TO (20220101);

CREATE TABLE IF NOT EXISTS dw.fact_dispatch_interval_y2022 PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20220101) TO (20230101);
```

**Verification Evidence (Partition Pruning)**:
PostgreSQL execution engine prunes all non-matching partitions when querying temporal bounds.
Verified via `EXPLAIN (FORMAT JSON)`:
```sql
EXPLAIN (FORMAT JSON)
SELECT date_key, interval_key, active_power_mw
FROM dw.fact_dispatch_interval
WHERE date_key BETWEEN 20240101 AND 20240131;
```
Result: Only `fact_dispatch_interval_y2024` is included in the query plan; `fact_dispatch_interval_y2020`, `_y2021`, `_y2022`, `_y2023`, and `_y2025` are pruned completely.

---

### 2.2 Conformed Dimension Expansion (`dw.dim_consumption_sector`)

In CEB audited statistical digests, retail sales are disaggregated into standard consumer categories, while bulk sales to the distribution franchisee (Lanka Electricity Company) are audited separately as *"Bulk Supply to LECO"*.

To prevent conflating retail sales with franchise bulk delivery:
1. Migration 019 seeds the conformed sector:
   - `sector_code`: `'BULK_LECO'`
   - `sector_name`: `'Bulk Supply to Lanka Electricity Company (LECO)'`
   - `is_residential`: `FALSE`
   - `is_productive_use`: `TRUE`
2. `ref.energy_source_mapping` and parser rules associate LECO line items with `BULK_LECO`.

---

### 2.3 Stored Procedure Hardening & Schema Alignment

Migration 019 replaces and hardens four core transactional stored procedures in the `etl` schema:

1. `etl.sp_validate_staged_dispatch(p_batch_id BIGINT)`:
   - Aligns with real staging primary key `stg_dispatch_id`.
   - Reconciles plant name aliases against `ref.plant_alias` and `dw.dim_power_plant`.
   - Validates energy conservation: checks that $| \text{derived\_energy\_mwh} - (\text{active\_power\_mw} \times 0.25) | \le 0.05$.
   - Quarantines invalid records into `staging.stg_quarantined_record` with error code `'DISPATCH_ENERGY_INCONSISTENT'` or `'UNKNOWN_PLANT_NAME'`.
   - Marks clean rows as `'valid'`.

2. `etl.sp_validate_staged_sales(p_batch_id BIGINT)`:
   - Aligns with staging primary key `stg_sales_id`.
   - Maps tariff sector names to `dw.dim_consumption_sector`.
   - Ensures non-negative sales volumes ($GWh \ge 0$).
   - Flags aggregated totals (e.g. `"Total"`, `"System Total"`) to prevent double-counting.

3. `etl.sp_load_electricity_sales(p_batch_id BIGINT)`:
   - Idempotently promotes valid staged sales records into `dw.fact_electricity_sales`.
   - Uses `ON CONFLICT (sector_key, period_type_code, effective_start_date_key, effective_end_date_key, source_system_key, dataset_revision) DO UPDATE` to ensure idempotent execution.

4. `etl.sp_load_weather_daily(p_batch_id BIGINT)`:
   - Aligns with staging primary key `stg_weather_id`.
   - Promotes staged meteorological observations into `dw.fact_weather_daily`.
   - Performs physical unit conversion: converts native solar irradiance ($\text{kWh/m}^2/\text{day}$) to canonical warehouse units ($\text{MJ/m}^2/\text{day}$) using factor $3.600000$.
   - Preserves both original reported values and canonical standardized values.

---

## 3. Rollback Procedure

To roll back Migration 019 safely:

```bash
python scripts/migrate.py down --target 018
```

The corresponding rollback script `database/migrations/019_historical_partitions_and_entities_rollback.sql` cleanly drops the historical partitions and removes the `BULK_LECO` dimension row without affecting earlier warehouse objects.
