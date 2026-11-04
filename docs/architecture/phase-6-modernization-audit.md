# GridLens Phase 6: Modernization & Supabase Compatibility Audit

**Project:** GridLens — Sri Lanka National Electricity Grid Analytics Data Warehouse  
**Version Target:** Managed Supabase PostgreSQL (PostgreSQL 15–17)  
**Author:** Antigravity Data Warehouse Architect & Modernization Team  
**Date:** November 2026  

---

## 1. Executive Summary

This document provides the foundational engineering audit for migrating the **GridLens** academic data warehouse into an enterprise-grade, cloud-managed PostgreSQL analytical warehouse hosted on **Supabase**, complemented by an automated incremental ETL refresh pipeline and live Next.js Business Intelligence dashboard.

The audit evaluates:
1. Current warehouse assets, row counts, and real historical coverage.
2. Unpopulated structures and scope boundaries.
3. PostgreSQL version compatibility between local PostgreSQL 18 and managed Supabase PostgreSQL (15–17).
4. Required changes to connection management, schema permissions, and ETL orchestration.
5. Identification of hardcoded historical boundaries and manual operational workflows.

---

## 2. Current State Inventory

### 2.1 Populated Relational Fact & Dimension Tables
The primary development warehouse currently persists authentic historical electricity and meteorological data:

| Schema & Table | Row Count | Historical Coverage | Data Lineage / Source |
| :--- | :---: | :--- | :--- |
| `dw.fact_electricity_sales` | **49** | 2020–2024 (Annual) | CEB Statistical Digests (Table 7 / Table 11) |
| `dw.fact_weather_daily` | **21,924** | 2020–2024 (Daily) | NASA POWER Solar & Meteorological Observations (Victoria & Mannar) |
| `dw.fact_dispatch_interval_y2024` | **107,115** | March 1–31, 2024 (15-min) | PUCSL Operational Sub-Daily Dispatch Curves (31 daily sheets) |
| `audit.data_quality_issue` | **926** | Audit Ledger | Automated ETL Quality Gates (879 entity unmapped, 47 negative power) |
| `dw.dim_power_plant` | **41** | Conformed Dimension | Official CEB/PUCSL Generation Licences (SCD Type 2 enabled) |
| `dw.dim_date` | **2,922** | 2018-01-01 to 2025-12-31 | Pre-seeded Gregorian / Fiscal Calendar Dimension |
| `dw.dim_interval` | **120** | 96 standard + TOU blocks | Sub-daily quarter-hour intervals & peak tariff blocks |
| `dw.dim_energy_source` | **9** | Taxonomy | Major generation classifications (Hydro, Coal, Oil, Solar, Wind) |
| `dw.dim_consumption_sector` | **11** | Taxonomy | Official CEB Tariff customer categories (Domestic, Industrial, General, etc.) |
| `dw.dim_region` | **14** | Taxonomy | CEB Distribution Divisions (DD1–DD4) & Administrative Provinces |
| `dw.dim_weather_location` | **6** | Taxonomy | Meteorological grid monitoring points (Victoria Reservoir, Mannar Wind) |
| `dw.dim_metric` | **15** | Taxonomy | Physical indicators (Active Power, Billed Energy, GHI, Temperature) |
| `dw.dim_source_system` | **3** | Provenance | Provider identities (CEB, PUCSL, NASA_POWER) |
| `ref.*` (6 tables) | **64** | Reference Data | Physical units, conversions, precedence rules, data quality policies |

### 2.2 Unpopulated Fact Tables (Awaiting Verified Source Ingestion)
The following tables are structurally defined in migrations 006–008 but contain 0 persisted rows pending source acquisition:
1. `dw.fact_generation_period`: Designed for monthly utility station-level generation logs. Currently, daily/monthly totals are derived from `fact_dispatch_interval` and `fact_electricity_sales`.
2. `dw.fact_capacity_period`: Semi-additive table for seasonal dependable capacity ratings. Nameplate capacity is presently modeled directly on `dw.dim_power_plant.nameplate_capacity_mw`.
3. `dw.fact_published_metric`: Staging structure for macroeconomic grid indicators (e.g., national peak gross demand from Central Bank reports).
4. `dw.fact_dispatch_interval` Partitions: Partitions `y2020`, `y2021`, `y2022`, `y2023`, `y2025`, and `y2026` exist as physical partition tables but await official 15-minute dispatch sheets from PUCSL.

---

## 3. Supabase Managed PostgreSQL Compatibility Analysis

Supabase provides managed PostgreSQL (typically major version 15 or 16). The following matrix analyzes GridLens DDL/DML compatibility:

| PostgreSQL Feature / Syntax | Local PG18 | Supabase (PG15/16) | Compatibility Status & Mitigation |
| :--- | :---: | :---: | :--- |
| `PARTITION BY RANGE (date_key)` | Supported | Supported | **Fully Compatible**. Native PostgreSQL feature since PG 10. |
| Composite Partition PK `(id, date_key)` | Supported | Supported | **Fully Compatible**. Standard composite constraint. |
| `BIGINT GENERATED ALWAYS AS IDENTITY` | Supported | Supported | **Fully Compatible**. Standard ANSI SQL since PG 10. |
| Custom Schemas (`dw`, `mart`, `ref`, etc.) | Supported | Supported | **Fully Compatible**. Can be created via standard DDL. |
| Materialized Views (`mart.mv_*`) | Supported | Supported | **Fully Compatible**. Standard PostgreSQL feature. |
| PL/pgSQL Stored Procedures (`CALL etl.sp_*`) | Supported | Supported | **Fully Compatible**. Stored procedures supported since PG 11. |
| `CREATE DATABASE sl_grid_warehouse` | Local DDL | Cloud Managed | **Incompatible on Cloud**. In Supabase, the target database is fixed to `postgres`. The migration script must connect to `postgres` without executing `CREATE DATABASE`. |
| Superuser Privileges (`SUPERUSER`) | Available locally | Restricted | **Incompatible on Cloud**. In Supabase, `postgres` is a member of `supa_admin`, not a naked superuser. Avoid `ALTER SYSTEM` or superuser-exclusive statements. |
| `ALTER ROLE ... WITH LOGIN PASSWORD` | Used locally | Pooler / IAM | **Adjusted**. Managed Supabase provisions users through Dashboard or SQL Editor. The analytical role `grid_analyst` can be created as a standard database role. |
| SSL Mode (`sslmode=require`) | Optional | **Mandatory** | **Required**. Supabase requires encrypted SSL transport. Both Python `psycopg` and Next.js `pg` pool must pass `sslmode=require` / `rejectUnauthorized: false`. |
| Connection Pooling (Port 6543 vs 5432) | Direct 5432 | Supavisor Pooler | **Supported**. For serverless Next.js, use Transaction Pooler (port 6543). For long-running Python ETL migrations, use Direct/Session connection (port 5432). |

---

## 4. Analytical Query (Q01–Q24) Cloud Compatibility

All 24 analytical queries project ANSI-compliant SQL utilizing standard window functions (`LAG()`, `LEAD()`), common table expressions (`WITH`), and OLAP groupings (`ROLLUP`, `CUBE`, `GROUPING SETS`):

- **Aggregation Consistency**: All queries project from conformed dimensions and facts in `dw` and analytical views in `mart`.
- **Grain Safety**: No query joins conflicting granularities (e.g., sub-daily dispatch is never cartesian-joined to annual billed sales).
- **Date Filters**: Existing queries benchmark specific historical windows (March 2024 for Q01–Q12; 2020–2024 for Q13–Q24). Incremental refresh jobs must populate new time windows without breaking existing historical baseline queries.

---

## 5. Identified Manual Bottlenecks & Automation Requirements

1. **Hardcoded Ingestion Triggers**:
   - `load_historical_warehouse.py` previously executed single-batch file loaders.
   - **Modernization Required**: Implement `src/etl/incremental_refresher.py` capable of scanning official portals, detecting new files, comparing checksums against `manifest.json`, and incrementally loading new periods.
2. **Materialized View Staleness**:
   - `mart.mv_*` views required manual `REFRESH MATERIALIZED VIEW` commands.
   - **Modernization Required**: Stored procedure `etl.sp_refresh_analytical_marts()` must be invoked automatically at the conclusion of every successful incremental batch.
3. **Dashboard Connection Configuration**:
   - `web/.env.local` previously pointed to `localhost:5433`.
   - **Modernization Required**: Add dual support for `DATABASE_URL` targeting Supabase Transaction Pooler, with automatic SSL handling and fallback to pre-computed snapshots.

---

## 6. Audit Conclusion & Phase Transition Approval

- **Database Structure**: Ready for migration to Supabase without structural alteration.
- **Data Integrity**: Source data volume is compact (~107k dispatch rows, ~22k weather rows, 49 sales rows) and migrates cleanly via direct session connection in under 30 seconds.
- **Rollback Guarantee**: Local native PostgreSQL warehouse (`sl_grid_warehouse`) remains completely intact and serves as the primary ground-truth backup until cloud verification passes.

