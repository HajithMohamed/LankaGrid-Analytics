# Indexing & Partitioning Strategy (PostgreSQL 18.6)

## 1. Declarative Range Partitioning Evaluation & Design

Implemented in [006_facts_generation_and_dispatch.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/006_facts_generation_and_dispatch.sql):

### Why `dw.fact_dispatch_interval` Is Partitioned
- **Volume Calculation**: $96\text{ intervals/day} \times 365\text{ days} = 35{,}040\text{ intervals/year}$ per entity. Across $40\text{–}80$ generating units and dispatch categories, a 4-year archive spans **$5.6\text{M–}11.2\text{M}$ rows**.
- **Query Pattern**: Operational load-curve, peak-demand, and monsoon dispatch queries almost universally filter on calendar date windows (`date_key BETWEEN ...`).
- **Partition Key & Constraint Compliance**: Partitioned by `RANGE (date_key)` into yearly child tables (`fact_dispatch_interval_y2023`, `y2024`, `y2025`, `y2026`, plus `fact_dispatch_interval_default`). Both `pk_fact_dispatch_interval (dispatch_fact_id, date_key)` and `uq_fact_dispatch_interval_grain (date_key, interval_key, plant_key, metric_key, source_system_key, dataset_revision)` include `date_key` to satisfy PostgreSQL partitioned uniqueness rules.

### Why Reference & Monthly/Annual Tables Are NOT Partitioned
- `ref.*` (3–17 rows), `dw.dim_*` (3–2,922 rows), `dw.fact_capacity_period`, `dw.fact_electricity_sales`, and `dw.fact_published_metric` contain hundreds to tens of thousands of rows. Partitioning small tables adds planner and catalog overhead without scan reduction, so they remain standard heap tables with targeted B-Tree indexes.

---

## 2. Indexing Architecture ([010_indexes_and_partition_tuning.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/010_indexes_and_partition_tuning.sql))

| Index Family | Representative Indexes | Rationale |
|---|---|---|
| **Composite B-Tree on Fact FKs** | `idx_fact_dispatch_plant_date (plant_key, date_key)`, `idx_fact_gen_period_dates (period_type_code, period_start_date_key, period_end_date_key)` | Accelerates star-join dimension lookups and period range predicates. |
| **Partial Current-Revision B-Tree** | `idx_fact_dispatch_current_rev`, `idx_fact_gen_period_energy`, `idx_fact_sales_period_sector`, `idx_fact_weather_loc_metric` (`WHERE is_current_revision = TRUE`) | Excludes superseded dataset revisions from index pages, shrinking index footprint for standard analytical queries. |
| **BRIN (Block Range Indexes)** | `idx_brin_fact_dispatch_timestamp` on `original_timestamp`, `idx_brin_fact_weather_date` on `date_key` (`pages_per_range = 32`) | Chronologically ingested dispatch and daily weather rows exhibit strong physical page correlation; BRIN provides compact min/max block skipping at $<1\%$ of B-Tree storage cost. |
| **Unique Materialized View Indexes** | `uq_mv_monthly_generation_summary`, `uq_mv_annual_energy_mix`, `uq_mv_monthly_sales_summary` | Required by PostgreSQL to unlock non-blocking `REFRESH MATERIALIZED VIEW CONCURRENTLY`. |

---

## 3. Measured `EXPLAIN (ANALYZE, BUFFERS)` Verification on PostgreSQL 18.6

Captured via [verify_database.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/verify_database.py) over a rolled-back 2,880-row 15-minute dispatch benchmark in `sl_grid_warehouse_test`:

### Query 1: TOU Block Dispatch Aggregation with Partition Pruning + Partitioned B-Tree Index Scan
```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT di.tariff_time_block,
       COUNT(*) AS intervals_count,
       ROUND(AVG(fd.active_power_mw), 2) AS avg_dispatch_mw,
       ROUND(SUM(fd.derived_energy_mwh), 2) AS integrated_energy_mwh
FROM dw.fact_dispatch_interval fd
JOIN dw.dim_interval di ON di.interval_key = fd.interval_key
WHERE fd.date_key BETWEEN 20240101 AND 20240115
  AND fd.plant_key = (SELECT plant_key FROM dw.dim_power_plant WHERE plant_code = 'VICTORIA' AND is_current = TRUE)
  AND fd.is_current_revision = TRUE
GROUP BY di.tariff_time_block
ORDER BY di.tariff_time_block;
```

**Actual PostgreSQL 18.6 Plan Output**:
```text
GroupAggregate  (cost=13.06..13.10 rows=1 width=83) (actual time=1.241..1.408 rows=3.00 loops=1)
  Group Key: di.tariff_time_block
  Buffers: shared hit=925
  InitPlan 1
    ->  Seq Scan on dim_power_plant  (cost=0.00..1.48 rows=1 width=4) (actual time=0.004..0.007 rows=1.00 loops=1)
          Filter: (is_current AND ((plant_code)::text = 'VICTORIA'::text))
          Buffers: shared hit=1
  ->  Sort  (cost=12.98..12.99 rows=1 width=37) (actual time=1.090..1.142 rows=1440.00 loops=1)
        Sort Key: di.tariff_time_block
        Sort Method: quicksort  Memory: 99kB
        ->  Hash Join  (cost=8.31..12.97 rows=1 width=37) (actual time=0.702..0.830 rows=1440.00 loops=1)
              Hash Cond: (di.interval_key = fd.interval_key)
              ->  Seq Scan on dim_interval di  (cost=0.00..4.20 rows=120 width=9) (actual time=0.007..0.013 rows=120.00 loops=1)
              ->  Hash  (cost=8.30..8.30 rows=1 width=36) (actual time=0.687..0.687 rows=1440.00 loops=1)
                    ->  Index Scan using fact_dispatch_interval_y2024_plant_key_date_key_idx on fact_dispatch_interval_y2024 fd
                          (cost=0.28..8.30 rows=1 width=36) (actual time=0.027..0.494 rows=1440.00 loops=1)
                          Index Cond: ((plant_key = (InitPlan 1).col1) AND (date_key >= 20240101) AND (date_key <= 20240115))
                          Filter: is_current_revision
                          Index Searches: 1
Planning Time: 2.366 ms
Execution Time: 1.449 ms
```
**Key Observation**: PostgreSQL 18 pruned partitions `y2023`, `y2025`, `y2026`, and `default` at plan time, executed a single B-Tree `Index Scan` (`Index Searches: 1`) on `fact_dispatch_interval_y2024`, and completed in **1.449 ms** (`< 200 ms` target).

