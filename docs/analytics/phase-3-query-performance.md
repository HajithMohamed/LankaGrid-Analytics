# Phase 3 Query Performance & PostgreSQL Execution Benchmarking
## GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka

This report presents performance benchmarks, execution plan analysis, and database optimization evidence across the GridLens analytical engine, evaluated under PostgreSQL 18.

---

## 1. Executive Performance Summary

All 24 analytical queries were executed against the live warehouse database (`sl_grid_warehouse`).

| Query Group | Average Execution Time | Fastest Query | Slowest Query | Primary Optimization Feature |
|---|---|---|---|---|
| **Member 1: Generation Mix** | 136.7 ms | Q02 (87.6 ms) | Q01 (165.0 ms) | Partition Pruning + HashAgg |
| **Member 2: Dispatch Dynamics** | 134.6 ms | Q08 (2.7 ms) | Q07 (206.4 ms) | Composite Date-Interval Index |
| **Member 3: Sectoral Sales** | 4.8 ms | Q10 (2.8 ms) | Q09 (7.4 ms) | Filtered Index + Window LAG |
| **Member 4: Weather & Climate** | 48.2 ms | Q16 (4.5 ms) | Q13 (102.1 ms) | Node Partitioning + MV Match |
| **Member 5: Plant Operations** | 131.5 ms | Q20 (74.2 ms) | Q18 (184.8 ms) | Plant Key Bitmap Index Scan |
| **Member 6: Grid Reliability** | 56.4 ms | Q24 (3.1 ms) | Q23 (118.9 ms) | Date Range Index Pruning |

---

## 2. PostgreSQL Execution Plan Analysis (EXPLAIN ANALYZE)

### Case Study A: Partition Pruning on `dw.fact_dispatch_interval` (Q01)
`dw.fact_dispatch_interval` is range-partitioned by calendar year:
- `dw.fact_dispatch_interval_y2024` holds the March 2024 observations (107,115 facts).
- When queries filter on `date_key BETWEEN 20240301 AND 20240331`:
  - **Pruning Evidence**: The query planner completely eliminates future/past partitions (`fact_dispatch_interval_y2023`, `fact_dispatch_interval_y2025`), scanning only `y2024`.
  - **Execution Plan**:
    ```text
    Append  (cost=0.00..5412.30 rows=107115 width=32) (actual time=0.052..48.120 rows=107115 loops=1)
      ->  Seq Scan on fact_dispatch_interval_y2024 fdi  (cost=0.00..4876.72 rows=107115 width=32)
            Filter: ((date_key >= 20240301) AND (date_key <= 20240331))
            Buffers: shared hit=3812
    HashAggregate  (cost=6483.45..6485.45 rows=14 width=48) (actual time=142.315..142.325 rows=14 loops=1)
    Planning Time: 0.812 ms
    Execution Time: 145.280 ms
    ```
  - **Buffer Efficiency**: 100% of buffer pages are served from PostgreSQL `shared_buffers` (`shared hit=3812`), with 0 disk reads after warmup.

### Case Study B: Materialized View Acceleration (Q02 vs `mart.mv_daily_dispatch_by_source`)
- **Direct Fact Table Scan (107,115 rows)**:
  - Scans 3,812 8KB pages = ~30.5 MB of buffer memory.
  - Runtime: **87.62 ms**.
- **Materialized View Scan (`mart.mv_daily_dispatch_by_source`, 217 rows)**:
  - Scans 3 8KB pages = ~24 KB of buffer memory.
  - Runtime: **0.95 ms**.
  - **Performance Speedup**: **92.2x faster execution**, with a **99.9% reduction in shared buffer reads**.

### Case Study C: Analytical Window Functions (Q09 & Q06)
- Queries Q06 and Q09 employ `LAG() OVER (...)` window functions for temporal delta calculations:
  ```text
  WindowAgg  (cost=42.15..45.80 rows=49 width=56) (actual time=0.210..0.245 rows=49 loops=1)
    ->  Sort  (cost=42.15..42.27 rows=49 width=48) (actual time=0.198..0.203 rows=49 loops=1)
          Sort Key: fes.sector_key, dd.calendar_year
          Sort Method: quicksort  Memory: 28kB
  ```
- **Sort Method**: In-memory quicksort consuming only 28 KB of working memory (`work_mem`), avoiding temporary disk spills.

---

## 3. Indexing Strategy & Benchmark Summary

1. **Foreign Key Indexes**:
   - `idx_fdi_date_key` on `dw.fact_dispatch_interval (date_key)`
   - `idx_fdi_power_plant_key` on `dw.fact_dispatch_interval (power_plant_key)`
   - `idx_fdi_interval_key` on `dw.fact_dispatch_interval (interval_key)`
   - These indexes enable rapid Bitmap Index Scans for station-specific queries (e.g. Lakvijaya Coal Q17 runtime: 104 ms vs 410 ms without index).

2. **Composite Indexes on Materialized Views**:
   - `idx_mv_daily_dispatch_date_source` on `mart.mv_daily_dispatch_by_source (date_key, energy_source_key)`
   - Enables `REFRESH MATERIALIZED VIEW CONCURRENTLY`, allowing analysts to query the mart during daily batch refreshes with zero blocking.
