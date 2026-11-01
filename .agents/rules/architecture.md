---
trigger: always_on
description: Architectural constraints, Kimball dimensional modeling guidelines, and phase boundaries
---
# Architecture Rules

## Phase Governance
- **Current Phase: Phase 3 (Business Intelligence, Advanced OLAP and Historical Data Analysis).**
- Phase 0 foundation, Phase 1 dimensional schema, Phase 2 real-data ETL, and Phase 3 Business Analytics are authorized.
- Do NOT build frontend applications (no React, Next.js, Spring Boot, etc.) or machine-learning forecasting until Phase 3 is approved.
- Never advance to a subsequent phase without explicit user approval.

## Dimensional Modeling Standards (Kimball Architecture)
- When modeling in later phases:
  - Distinguish Fact tables (measurements, events, transactions) from Dimension tables (context, attributes, hierarchies).
  - Define explicit fact grain before writing any DDL or ETL.
  - Enforce conformed dimensions across different business processes (Date/Time, Power Station, Fuel Type, Grid Substation/Region).
  - Use surrogate primary keys (`BIGINT GENERATED ALWAYS AS IDENTITY` or `INT`) for dimension warehouse identifiers.
  - Retain natural / business keys from source providers for auditing and idempotent UPSERTs.
  - Employ Star and Fact Constellation schemas rather than 3NF or overly denormalized single tables.

## Component Decoupling
- Ingestion (`src/ingestion`): Downloads and archives immutable raw source files and records metadata manifests.
- Preprocessing (`src/preprocessing`): Parses raw data, normalizes timestamps and units, identifies anomalies, and outputs clean staging structures.
- ETL (`src/etl`): Loads staging data into relational staging and transforms into dimensional facts and dimensions idempotently.
- Validation (`src/validation`): Executes schema checks, integrity assertions, and data quality metrics.
