---
trigger: always_on
description: PostgreSQL 18 standards, schema migration policies, and SQL conventions
---
# PostgreSQL Standards & Migration Rules

## Schema & Migration Integrity
1. **Migrations Are Mandatory**:
   - All schema changes must be declared in numbered, sequential migration files under `database/migrations/` (e.g. `001_bootstrap.sql`, `002_create_dim_date.sql`).
   - Every forward migration must have a clear corresponding rollback strategy or teardown path.
2. **Immutability of Applied Migrations**:
   - NEVER modify a migration file that has already been executed or committed to `development` or `main`.
   - Bug fixes, schema alterations, or index modifications require a new sequential migration.
3. **Database Version Target**:
   - PostgreSQL 18 on Docker. Ensure all DDL and queries use modern, standard PostgreSQL syntax.

## SQL Naming & Conventions
- Lowercase with snake_case for all table names, column names, indexes, views, and schemas.
- Dimension tables: Prefix with `dim_` (e.g., `dim_power_plant`, `dim_date`, `dim_fuel_type`).
- Fact tables: Prefix with `fact_` (e.g., `fact_daily_generation`, `fact_dispatch_15min`).
- Staging tables: Prefix with `stg_` in dedicated `staging` schema.
- Explicit constraints: Always name primary keys (`pk_<table>`), foreign keys (`fk_<table>_<ref_table>`), unique constraints (`uq_<table>_<cols>`), and check constraints (`ck_<table>_<condition>`).

## Performance & Indexing
- Primary keys must have surrogate integer/bigint keys.
- Foreign keys in fact tables referencing dimensions must be indexed.
- Use explicit date/timestamp types: `TIMESTAMPTZ` for absolute moments in time, `DATE` for calendar dates.
- Avoid `SELECT *` in production analytical queries; project required columns explicitly.
- Verify all analytical queries with `EXPLAIN (ANALYZE, BUFFERS)`.
