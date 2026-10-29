# ADR-001: Kimball Fact Constellation Architecture, 7-Schema Segregation, and PostgreSQL 18 Physical Design

- **Status**: Accepted
- **Date**: 2026-10-29
- **Deciders**: National Grid Warehouse Architecture Team

## Context
Sri Lanka's electricity sector datasets span heterogeneous providers (CEB, PUCSL, NASA POWER), temporal resolutions (`15-minute` operational dispatch, `daily` plant generation and weather, `monthly`/`annual` tariff sales and audited digests), and physical measurement classes (`MW` power, `MWh`/`GWh` energy, `MW` semi-additive capacity, meteorological variables, and non-additive loss percentages).

Forcing all measurements into a single denormalized table or a single star schema would either mix incompatible grains (risking 4x power-vs-energy errors and daily-vs-annual double-counting) or fabricate artificial regional/plant splits where sources only publish aggregates. Conversely, an operational 3NF OLTP schema would complicate multi-dimensional OLAP slicing and time-series rollups.

## Decision
1. **Kimball Fact Constellation (Galaxy Schema) in `dw`**:
   - Implement six purpose-built fact tables (`fact_dispatch_interval`, `fact_generation_period`, `fact_capacity_period`, `fact_electricity_sales`, `fact_weather_daily`, `fact_published_metric`) sharing nine conformed dimensions (`dim_date`, `dim_interval`, `dim_power_plant`, `dim_energy_source`, `dim_region`, `dim_consumption_sector`, `dim_weather_location`, `dim_metric`, `dim_source_system`).
2. **Seven Segregated PostgreSQL Schemas**:
   - Separate `raw`, `staging`, `ref`, `dw`, `mart`, `audit`, and `etl` so provenance records, quarantined staging data, reference mappings, core dimensional tables, analytical views, quality logs, and procedural code have explicit ownership and privilege boundaries.
3. **Range Partitioning Only Where Justified**:
   - Range-partition `dw.fact_dispatch_interval` by `date_key` (`y2023`–`y2026` + `default`) because 96 daily intervals across dozens of entities yield millions of time-series rows queried by date windows. Keep reference and lower-volume periodic tables unpartitioned to avoid catalog overhead.
4. **PostgreSQL 18 `UNIQUE NULLS NOT DISTINCT` for Optional Scope Grains**:
   - Use `UNIQUE NULLS NOT DISTINCT` on `dw.fact_published_metric` so national-level metrics with `NULL` sector/energy-source keys still enforce strict grain uniqueness without inventing dummy dimension rows.

## Consequences
- **Positive**: Eliminates mixed-grain summation hazards, preserves full `raw -> staging -> dw` lineage, supports sub-2ms partition-pruned dispatch lookups, and enforces least-privilege security (`grid_admin`, `grid_etl`, `grid_analyst`).
- **Trade-offs**: Requires ETL loaders ([batch_loader.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/etl/batch_loader.py) and [012_procedures.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/012_procedures.sql)) to resolve conformed surrogate keys and respect `period_type_code` and `is_current_revision` predicates.
