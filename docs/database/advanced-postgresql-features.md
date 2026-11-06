# Advanced PostgreSQL Engineering & Analytical Features

## Overview

The GridLens data warehouse utilizes advanced features of PostgreSQL 18 / Supabase Managed PostgreSQL to perform complex time-series analytics, multi-dimensional hierarchical aggregations, automated data quality enforcement, and high-performance partition pruning.

---

## 1. Common Table Expressions (CTEs) & Modular SQL

Complex analytical queries in GridLens rely on CTEs (`WITH` clauses) to isolate intermediate data preparation, unit conversions, and dimensional joins before executing analytical aggregations.

### Example: Fuel Mix Contribution with CTEs ([`Q01`](database/analytical_queries/q01_generation_mix_by_source.sql))
```sql
WITH daily_plant_energy AS (
    SELECT
        f.interval_timestamp_utc::date AS dispatch_date,
        d.day_name,
        p.plant_name,
        fuel.fuel_category,
        fuel.is_renewable,
        SUM(f.dispatch_energy_mwh) AS plant_daily_mwh
    FROM dw.fact_dispatch_interval f
    JOIN dw.dim_date d ON f.date_key = d.date_key
    JOIN dw.dim_power_plant p ON f.plant_key = p.power_plant_key
    JOIN dw.dim_energy_source fuel ON f.energy_source_key = fuel.energy_source_key
    GROUP BY d.calendar_date, d.day_name, p.plant_name, fuel.primary_category, fuel.source_name
)
SELECT * FROM daily_plant_energy;
```

---

## 2. Advanced Window Functions

Window functions perform calculations across sets of table rows related to the current query row without collapsing rows into a single output.

### A. Temporal Ramp Rate Derivatives via `LAG()` ([`Q06`](database/analytical_queries/q06_dispatch_ramp_rate_analysis.sql))
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
JOIN dw.dim_power_plant p ON f.plant_key = p.power_plant_key;
```

### B. Moving Averages via Window Framing ([`Q02`](database/analytical_queries/q02_renewable_vs_nonrenewable_daily_share.sql))
Smoothes daily renewable penetration rates using a 7-day centered moving average window:

```sql
AVG(renewable_share_pct) OVER (
    ORDER BY dispatch_date
    ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
) AS renewable_share_7d_ma
```

### C. Plant Ranking via `DENSE_RANK()` ([`Q07`](database/analytical_queries/q07_baseload_vs_peaking_behavior.sql))
Ranks generating stations by capacity factor and coefficient of variation ($CV$) to classify plants into baseload, intermediate, and peaking regimes.

---

## 3. Multi-Dimensional Aggregations: `ROLLUP`, `CUBE`, and `GROUPING SETS`

PostgreSQL OLAP extensions allow computing multiple aggregation levels in a single query pass.

### A. Hierarchical Aggregation with `ROLLUP` ([`Q01`](database/analytical_queries/q01_generation_mix_by_source.sql))
Generates subtotals across Fuel Category &rarr; Specific Fuel Type &rarr; Grand Total:

```sql
SELECT
    COALESCE(fuel.primary_category, 'TOTAL_GRID') AS primary_category,
    COALESCE(fuel.source_name, 'SUBTOTAL') AS source_name,
    SUM(f.derived_energy_mwh) AS total_generation_mwh
FROM dw.fact_dispatch_interval f
JOIN dw.dim_energy_source fuel ON f.energy_source_key = fuel.energy_source_key
GROUP BY ROLLUP (fuel.primary_category, fuel.source_name);
```

### B. Cross-Dimensional Combinations with `CUBE` ([`Q15`](database/analytical_queries/q15_hydro_catchment_rainfall_correlation.sql))
Evaluates all possible combinations of rainfall intensity tiers, provinces, and seasons.

### C. Customized Aggregation Slices with `GROUPING SETS` ([`Q21`](database/analytical_queries/q21_tariff_economic_shift.sql))
Computes commercial sales metrics simultaneously grouped by `(year, customer_class)`, `(year, province)`, and `(year)`.

---

## 4. Stored Procedures & Transaction Control

PostgreSQL 11+ stored procedures (`CREATE PROCEDURE`) support explicit transactional commit and rollback boundaries.

### A. Data Quality Staging Validation ([`018_real_data_etl_procedures.sql`](database/migrations/018_real_data_etl_procedures.sql))
Procedure `etl.sp_validate_dispatch_staging()` verifies range boundaries, checks nameplate ratings, and isolates unmapped plant aliases into `audit.data_quality_issue` without terminating the batch.

### B. Materialized Mart Maintenance ([`021_phase3_analytical_marts.sql`](database/migrations/021_phase3_analytical_marts.sql))
Procedure `etl.sp_refresh_analytical_marts()` refreshes all pre-aggregated analytical views in a single transactional invocation:

```sql
CREATE OR REPLACE PROCEDURE etl.sp_refresh_analytical_marts()
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW mart.mv_daily_system_summary;
    REFRESH MATERIALIZED VIEW mart.mv_monthly_fuel_mix;
    REFRESH MATERIALIZED VIEW mart.mv_hourly_dispatch_pattern;
    REFRESH MATERIALIZED VIEW mart.mv_station_efficiency_benchmarks;
    REFRESH MATERIALIZED VIEW mart.mv_weather_correlation_summary;
END;
$$;
```

---

## 5. Declarative Table Partitioning & Performance

The high-volume dispatch telemetry fact table (`dw.fact_dispatch_interval`) contains millions of potential intervals.

- **Partition Key:** `RANGE (interval_timestamp_utc)`.
- **Partition Pruning:** When queries filter on `date_id` or timestamp ranges, the PostgreSQL query planner eliminates unneeded yearly child partitions (`y2020`..`y2023`, `y2025`..`y2026`) via partition pruning, executing queries exclusively against `y2024` in tens of milliseconds.
- **Foreign Key Indexing:** All surrogate foreign keys (`date_id`, `plant_id`, `fuel_type_id`) have explicit B-tree indexes to optimize star-schema joins.

