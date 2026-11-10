# Advanced PostgreSQL Engineering & Analytical Features

## Overview

The GridLens data warehouse utilizes advanced features of PostgreSQL 18 / Supabase Managed PostgreSQL to perform complex time-series analytics, multi-dimensional hierarchical aggregations, automated data quality enforcement, and high-performance partition pruning.

---

## 1. Common Table Expressions (CTEs) & Modular SQL

Complex analytical queries in GridLens rely on CTEs (`WITH` clauses) to isolate intermediate data preparation, unit conversions, and dimensional joins before executing analytical aggregations.

### Example: Fuel Mix Contribution with CTEs ([`Q01`](../../database/queries/phase3/01_member1_generation_mix_and_dispatch.sql))
```sql
WITH daily_plant_energy AS (
    SELECT
        f.date_key,
        d.calendar_date,
        d.day_name,
        p.plant_name,
        fuel.energy_category,
        fuel.is_renewable,
        SUM(f.derived_energy_mwh) AS plant_daily_mwh
    FROM dw.fact_dispatch_interval f
    JOIN dw.dim_date d ON f.date_key = d.date_key
    JOIN dw.dim_power_plant p ON f.plant_key = p.plant_key
    JOIN dw.dim_energy_source fuel ON f.energy_source_key = fuel.energy_source_key
    GROUP BY f.date_key, d.calendar_date, d.day_name, p.plant_name, fuel.energy_category, fuel.is_renewable
)
SELECT * FROM daily_plant_energy;
```

---

## 2. Advanced Window Functions

Window functions perform calculations across sets of table rows related to the current query row without collapsing rows into a single output.

### A. Temporal Ramp Rate Derivatives via `LAG()` ([`Q06`](../../database/queries/phase3/02_member2_demand_peaks_and_load_factor.sql))
Calculates interval-to-interval power ramp rates ($\frac{dMW}{dt}$) across 15-minute telemetry intervals:

```sql
SELECT
    f.original_timestamp,
    p.plant_name,
    f.active_power_mw,
    LAG(f.active_power_mw, 1) OVER (
        PARTITION BY f.plant_key
        ORDER BY f.original_timestamp
    ) AS prev_power_mw,
    (f.active_power_mw - LAG(f.active_power_mw, 1) OVER (
        PARTITION BY f.plant_key
        ORDER BY f.original_timestamp
    )) / 15.0 AS ramp_rate_mw_per_min
FROM dw.fact_dispatch_interval f
JOIN dw.dim_power_plant p ON f.plant_key = p.plant_key;
```

### B. Moving Averages via Window Framing ([`Q02`](../../database/queries/phase3/01_member1_generation_mix_and_dispatch.sql))
Smoothes daily renewable penetration rates using a 7-day centered moving average window:

```sql
AVG(renewable_share_pct) OVER (
    ORDER BY dispatch_date
    ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
) AS renewable_share_7d_ma
```

### C. Plant Ranking via `DENSE_RANK()` ([`Q07`](../../database/queries/phase3/02_member2_demand_peaks_and_load_factor.sql))
Ranks generating stations by capacity factor and coefficient of variation ($CV$) to classify plants into baseload, intermediate, and peaking regimes.

---

## 3. Multi-Dimensional Aggregations: `ROLLUP`, `CUBE`, and `GROUPING SETS`

PostgreSQL OLAP extensions allow computing multiple aggregation levels in a single query pass.

### A. Hierarchical Aggregation with `ROLLUP` ([`Q01`](../../database/queries/phase3/01_member1_generation_mix_and_dispatch.sql))
Generates subtotals across Fuel Category &rarr; Specific Fuel Type &rarr; Grand Total:

```sql
SELECT
    COALESCE(fuel.energy_category, 'TOTAL_GRID') AS energy_category,
    COALESCE(fuel.fuel_type, 'SUBTOTAL') AS fuel_type,
    SUM(f.derived_energy_mwh) AS total_generation_mwh
FROM dw.fact_dispatch_interval f
JOIN dw.dim_energy_source fuel ON f.energy_source_key = fuel.energy_source_key
GROUP BY ROLLUP (fuel.energy_category, fuel.fuel_type);
```

### B. Cross-Dimensional Combinations with `CUBE` ([`Q15`](../../database/queries/phase3/04_member4_weather_hydro_and_solar_impact.sql))
Evaluates all possible combinations of rainfall intensity tiers, provinces, and seasons.

### C. Customized Aggregation Slices with `GROUPING SETS` ([`Q21`](../../database/queries/phase3/06_member6_data_quality_and_reconciliation.sql))
Computes commercial sales metrics simultaneously grouped by `(year, customer_class)`, `(year, province)`, and `(year)`.

---

## 4. Stored Procedures & Transaction Control

PostgreSQL 11+ stored procedures (`CREATE PROCEDURE`) support explicit transactional commit and rollback boundaries.

### A. Data Quality Staging Validation ([`018_real_data_etl_procedures.sql`](../../database/migrations/018_real_data_etl_procedures.sql))
Procedure `etl.sp_validate_staged_dispatch()` verifies range boundaries, checks nameplate ratings, and isolates unmapped plant aliases into `audit.data_quality_issue` without terminating the batch.

### B. Materialized Mart Maintenance ([`015_views_and_materialized_marts.sql`](../../database/migrations/015_views_and_materialized_marts.sql) & [`021_phase3_analytical_marts.sql`](../../database/migrations/021_phase3_analytical_marts.sql))
Procedures `etl.sp_refresh_mart_views(FALSE)` and `mart.sp_refresh_analytical_marts(FALSE)` refresh all 5 pre-aggregated analytical views across the warehouse:

```sql
CALL etl.sp_refresh_mart_views(FALSE);
CALL mart.sp_refresh_analytical_marts(FALSE);
-- Refreshes:
--   1. mart.mv_monthly_generation_summary
--   2. mart.mv_annual_energy_mix
--   3. mart.mv_monthly_sales_summary
--   4. mart.mv_daily_dispatch_by_source
--   5. mart.mv_monthly_weather_summary
```

---

## 5. Declarative Table Partitioning & Performance

The high-volume dispatch telemetry fact table (`dw.fact_dispatch_interval`) contains millions of potential intervals.

- **Partition Key:** `RANGE (date_key)` with composite primary key `(dispatch_fact_id, date_key)`.
- **Partition Pruning:** When queries filter on `date_key` ranges, the PostgreSQL query planner eliminates unneeded yearly child partitions (`y2020`..`y2023`, `y2025`..`y2030`) via partition pruning, executing queries exclusively against target partitions in tens of milliseconds.
- **Foreign Key Indexing:** All surrogate foreign keys (`date_key`, `plant_key`, `energy_source_key`) have explicit B-tree indexes to optimize star-schema joins.

