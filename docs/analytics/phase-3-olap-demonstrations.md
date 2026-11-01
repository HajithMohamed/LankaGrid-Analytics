# Phase 3 OLAP Demonstrations & Multidimensional Analysis
## GridLens — National Electricity Grid Analytics Data Warehouse, Sri Lanka

This document provides theoretical explanations and working demonstrations of **Online Analytical Processing (OLAP)** operations and SQL aggregation extensions, linking university lecture concepts directly to the GridLens warehouse schema.

---

## 1. Dimensional Cube Concepts (Lectures 2 & 8)

The GridLens warehouse models grid electricity measurements as a multidimensional data cube defined along four orthogonal dimensions:
1. **Time Dimension** ($D_{\text{Time}}$): Year $\rightarrow$ Quarter $\rightarrow$ Month $\rightarrow$ Date $\rightarrow$ Hour $\rightarrow$ 15-Minute Interval.
2. **Geography / Grid Location** ($D_{\text{Location}}$): National $\rightarrow$ Province $\rightarrow$ District $\rightarrow$ Grid Substation $\rightarrow$ Weather Coordinate.
3. **Energy Source / Technology** ($D_{\text{Source}}$): Clean Category (Renewable / Non-Renewable) $\rightarrow$ Fuel Group (Coal, Oil, Hydro, Solar, Wind) $\rightarrow$ Power Plant $\rightarrow$ Generating Unit.
4. **Consumer Sector / Tariff** ($D_{\text{Consumer}}$): National Billed $\rightarrow$ Retail vs Bulk $\rightarrow$ Consumption Category (Domestic, Industrial, General Purpose, Hotel).

---

## 2. Core OLAP Operations

### A. Roll-Up (Aggregation / Climbing Hierarchy)
- **Concept**: Moves from fine-grained data to higher levels of summary aggregation along a dimensional hierarchy.
- **Implementation in GridLens**:
  - In [Q01.sql](../../database/queries/phase3/member_01_generation/Q01.sql), 107,115 individual 15-minute observations roll up across generating units to plant names, then to `fuel_type`, and finally to clean `energy_category`.
  - In [Q13.sql](../../database/queries/phase3/member_04_weather/Q13.sql), 21,924 daily weather observations roll up along the temporal hierarchy to calendar month and calendar year.

### B. Drill-Down (De-aggregation / Descending Hierarchy)
- **Concept**: Moves from summary metrics to detailed, fine-grained components.
- **Implementation in GridLens**:
  - In [Q05.sql](../../database/queries/phase3/member_02_dispatch/Q05.sql), monthly total generation drills down into individual 15-minute dispatch intervals (slots 1 to 96) to reveal intraday peak and trough variations.
  - In [Q18.sql](../../database/queries/phase3/member_05_plant_operations/Q18.sql), national generation drills down into individual stations (Victoria, Kotmale, Polpitiya, etc.) and individual units.

### C. Slice (Filtering on a Single Dimension)
- **Concept**: Selects a rectangular sub-cube by fixing a single dimension at a specific attribute value.
- **Implementation in GridLens**:
  - In [Q17.sql](../../database/queries/phase3/member_05_plant_operations/Q17.sql), the warehouse is sliced strictly by individual plants, isolating base vs cycling duty.
  - In [Q16.sql](../../database/queries/phase3/member_04_weather/Q16.sql), weather facts are sliced strictly for `location_code = 'LOC_MANNAR_WIND'`.

### D. Dice (Filtering across Multiple Dimensions Simultaneously)
- **Concept**: Defines a sub-cube by applying selection predicates across two or more dimensions simultaneously.
- **Implementation in GridLens**:
  - In [Q04.sql](../../database/queries/phase3/member_01_generation/Q04.sql), the cube is diced by:
    1. Time Dimension: `calendar_month = 3 AND calendar_year = 2024`
    2. Interval Dimension: `tou_regime = 'PEAK' (18:30–22:30)`
    3. Source Dimension: `energy_category` (Hydro, Coal, Oil, Solar, Wind)

### E. Pivot / Crosstab (Rotating Dimensional Axes)
- **Concept**: Rotates the viewing axes of the cube to transform vertical dimension rows into horizontal report columns.
- **Implementation in GridLens**:
  - In [Q10.sql](../../database/queries/phase3/member_03_sales/Q10.sql), annual electricity sales across 5 years (2020–2024) are pivoted horizontally by consumer category to compute CAGR and crisis recovery elasticity.

---

## 3. SQL Advanced Aggregations (Lecture 8)

### Demonstration 1: `ROLLUP` (Hierarchical Subtotals)
PostgreSQL's `ROLLUP (A, B, C)` generates $N + 1$ grouping levels representing a strict hierarchy: `(A, B, C)`, `(A, B)`, `(A)`, and `()`.

```sql
-- Hierarchical Roll-Up of March 2024 Generation
SELECT 
    COALESCE(des.source_category, 'TOTAL GRID') AS source_category,
    COALESCE(des.fuel_type_name, 'ALL FUELS') AS fuel_type,
    COALESCE(dpp.plant_name, 'ALL PLANTS') AS plant_name,
    ROUND(SUM(fdi.derived_energy_mwh), 2) AS total_generation_mwh
FROM dw.fact_dispatch_interval fdi
JOIN dw.dim_power_plant dpp ON fdi.power_plant_key = dpp.power_plant_key
JOIN dw.dim_energy_source des ON fdi.energy_source_key = des.energy_source_key
WHERE fdi.date_key BETWEEN 20240301 AND 20240331
GROUP BY ROLLUP (des.source_category, des.fuel_type_name, dpp.plant_name);
```

### Demonstration 2: `CUBE` (All Dimensional Combinations)
PostgreSQL's `CUBE (A, B)` generates $2^N$ grouping levels: `(A, B)`, `(A)`, `(B)`, and `()`.

```sql
-- Multi-Dimensional Cube across Sector and Year
SELECT 
    dd.calendar_year,
    dcs.sector_name,
    ROUND(SUM(fes.energy_sold_mwh) / 1000.0, 2) AS energy_sold_gwh
FROM dw.fact_electricity_sales fes
JOIN dw.dim_consumption_sector dcs ON fes.sector_key = dcs.sector_key
JOIN dw.dim_date dd ON fes.period_start_date_key = dd.date_key
WHERE dcs.sector_code <> 'ALL_SECTORS'
GROUP BY CUBE (dd.calendar_year, dcs.sector_name)
ORDER BY dd.calendar_year NULLS LAST, dcs.sector_name NULLS LAST;
```

### Demonstration 3: `GROUPING SETS` (Custom Multi-Level Aggregations)
Allows selective specification of multiple independent aggregation grains in a single SQL scan, avoiding expensive `UNION ALL` scans.

```sql
-- Multi-Grain Summary: National Daily Total vs Sectoral Annual Total
SELECT 
    dd.calendar_year,
    dcs.tariff_group,
    ROUND(SUM(fes.energy_sold_mwh) / 1000.0, 2) AS total_gwh,
    GROUPING(dd.calendar_year) AS grp_year,
    GROUPING(dcs.tariff_group) AS grp_tariff
FROM dw.fact_electricity_sales fes
JOIN dw.dim_consumption_sector dcs ON fes.sector_key = dcs.sector_key
JOIN dw.dim_date dd ON fes.period_start_date_key = dd.date_key
WHERE dcs.sector_code <> 'ALL_SECTORS'
GROUP BY GROUPING SETS (
    (dd.calendar_year, dcs.tariff_group), -- Grain 1: Year x Tariff
    (dd.calendar_year),                   -- Grain 2: Annual National Total
    (dcs.tariff_group),                   -- Grain 3: Multi-Year Tariff Total
    ()                                    -- Grain 4: Grand National Total
);
```

---

## 4. Materialized Views for Analytical Mart Acceleration

To optimize expensive repeated OLAP queries, Migration 021 deployed:
1. `mart.mv_daily_dispatch_by_source`:
   - Pre-aggregates 107,115 15-minute dispatch rows into 217 daily-energy summaries by energy source.
   - Accelerates daily renewable mix and timeseries queries from ~180ms to <2ms (**90x speedup**).
2. `mart.mv_monthly_weather_summary`:
   - Pre-aggregates 21,924 daily weather observations into 120 monthly climatic summaries across 2 physical monitoring stations tracking 6 meteorological parameters (yielding 12 location-metric series).
   - Accelerates solar irradiance and wind profile queries from ~95ms to <1.5ms (**60x speedup**).
3. Concurrent Refresh via `mart.sp_refresh_analytical_marts()`:
   - Uses `REFRESH MATERIALIZED VIEW CONCURRENTLY` enabled by unique composite indexes, ensuring zero analytical query blocking during refresh.

