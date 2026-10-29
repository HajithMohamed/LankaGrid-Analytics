---
name: sql-query-validation
description: >-
  Provides procedures for validating analytical SQL queries, testing OLAP aggregations and joins,
  measuring query performance, and analyzing PostgreSQL execution plans with EXPLAIN (ANALYZE, BUFFERS).
  Use when writing, optimizing, or reviewing the 24 team business analytical queries.
---

# SQL Query Validation Skill

## When to Use This Skill
Use this skill when developing, validating, and benchmarking the 24 group project business queries (4 queries per team member) across generation, dispatch, capacity, sales, weather, and data quality domains.

## Validation Procedure

### 1. Correctness & Business Logic Verification
1. Verify analytical intent matches the project requirements:
   - Aggregations: `SUM`, `AVG`, `MIN`, `MAX`, `PERCENTILE_CONT`.
   - Window functions: `OVER (PARTITION BY ... ORDER BY ...)`, `LEAD`, `LAG`, rolling averages (e.g. 7-day moving average demand).
   - Time dimensions: Grouping by hour, day of week, seasonal monsoon period (Southwest vs Northeast monsoon).
2. Validate NULL handling in aggregations:
   - Ensure `AVG(column)` does not inadvertently treat NULL as 0.
   - Use `COALESCE` only where an explicit business default is intended.
3. Assert deterministic ordering with explicit `ORDER BY`.

### 2. Query Plan & Performance Analysis
1. Run `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)` on the query:
   ```sql
   EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
   SELECT
       d.year,
       f.fuel_category,
       SUM(g.energy_mwh) AS total_generation_mwh
   FROM fact_daily_generation g
   JOIN dim_date d ON g.date_id = d.date_id
   JOIN dim_fuel_type f ON g.fuel_id = f.fuel_id
   GROUP BY d.year, f.fuel_category
   ORDER BY d.year, total_generation_mwh DESC;
   ```
2. Inspect execution plan metrics:
   - Confirm proper index scans (Index Scan / Index Only Scan / Bitmap Heap Scan) on large fact tables instead of sequential scans on high-cardinality foreign keys.
   - Check buffer usage (shared hit vs read).
   - Ensure execution time is well within target threshold (< 200ms for analytical queries on indexed schemas).

### 3. Verification Test Suite Formulation
1. Create automated test in `tests/integration/test_analytical_queries.py`:
   - Seed test database with synthetic fixture data.
   - Execute query and assert exact expected returned rows, column data types, and values.
   - Verify performance threshold assertions.

## Expected Outputs
- SQL query file in `database/queries/member<N>_query<M>_<topic>.sql`
- Formatted EXPLAIN ANALYZE execution plan output in `docs/database/query-execution-plans.md`
- Automated integration test asserting query correctness

## Verification Steps
1. Execute query via test runner.
2. Confirm returned result matches mathematical ground truth on test fixture data.
3. Validate that execution plan avoids full table scans where foreign key indexes exist.
