---
name: postgresql-warehouse-design
description: >-
  Provides procedures for Kimball dimensional data warehouse modeling, fact table grain definition,
  conformed dimension design, star/constellation schemas, and relational constraint design in PostgreSQL.
  Use when designing or reviewing dimensional tables, schemas, and relational constraints.
---

# PostgreSQL Warehouse Design Skill

## When to Use This Skill
Use this skill when designing, reviewing, or refactoring dimensional schemas, defining fact grains, establishing conformed dimensions, or formulating physical PostgreSQL DDL constraints for the electricity grid data warehouse.

## Design Procedure

### Step 1: Business Process & Fact Grain Definition
1. Identify the core business process:
   - Plant-level daily power generation (`fact_daily_generation`)
   - 15-minute grid dispatch and demand balance (`fact_grid_dispatch_15min`)
   - Weather observations and solar irradiance (`fact_solar_weather_daily`)
   - Monthly electricity sales and consumer tariffs (`fact_monthly_sales`)
2. Formally declare the **grain** of each fact record:
   - Example: *One row represents the total energy generated (MWh) by a specific power plant unit on a specific calendar date.*
3. Ensure no mixed-grain records exist in the same fact table.

### Step 2: Conformed Dimensions Formulation
1. Identify shared dimensional entities across business processes:
   - `dim_date`: Calendar attributes (date, day of week, month, quarter, year, holiday flag, season).
   - `dim_time`: 15-minute interval dispatch intervals (00:00 to 23:45, peak/off-peak/day blocks).
   - `dim_power_plant`: Station name, operator (CEB vs IPP), technology, fuel type, commissioned year, rated capacity (MW), province, GPS coordinates.
   - `dim_fuel_type`: Primary fuel, category (Thermal, Hydro, Solar, Wind, Biomass), renewable classification.
   - `dim_grid_node`: Transmission substation, voltage level (220kV, 132kV, 33kV), grid region.
2. Ensure attribute names, surrogate key formats, and domain values are strictly uniform across all referencing facts.

### Step 3: Schema Architecture (Fact Constellation)
1. Map multiple fact tables to shared conformed dimensions.
2. Define surrogate keys using `INT GENERATED ALWAYS AS IDENTITY` or `BIGINT GENERATED ALWAYS AS IDENTITY`.
3. Retain natural business keys (`natural_plant_code`, `source_station_name`) for auditability and ETL idempotency.

### Step 4: PostgreSQL Physical Optimization & Constraints
1. Declare explicit constraints:
   - `PRIMARY KEY (surrogate_id)`
   - `FOREIGN KEY (dim_id) REFERENCES dim_*(dim_id)` with `NOT NULL` where appropriate
   - `CHECK` constraints on physical boundaries ($MW \ge 0$, $0 \le \text{Capacity Factor} \le 1.0$)
2. Create B-Tree indexes on all foreign key columns in fact tables.
3. Use `TIMESTAMPTZ` for time moments and `NUMERIC(12, 3)` for precise electrical measurements.

## Expected Outputs
- Dimensional Bus Matrix (`docs/architecture/dimensional-bus-matrix.md`)
- Physical DDL migration scripts in `database/migrations/`
- Data dictionary entries documenting every table and column

## Verification Steps
1. Verify that all foreign keys reference valid primary keys in conformed dimensions.
2. Confirm no circular dependencies exist between tables.
3. Validate grain uniqueness: ensure a unique index exists on the combination of dimension foreign keys representing the natural grain.
