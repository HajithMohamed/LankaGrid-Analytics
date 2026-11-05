# End-to-End Data Pipeline & Architectural Flow

## Overview

The GridLens data warehouse operates an automated, idempotent multi-stage ELT pipeline designed to ingest, validate, conform, and expose electricity grid and meteorological data.

---

## Architectural Pipeline Diagram

```mermaid
flowchart TD
    subgraph Sources ["1. Official Data Sources"]
        S_CEB["Ceylon Electricity Board (CEB)<br/>Statistical Digest (PDF / XLSX)"]
        S_PUCSL["PUCSL System Operator<br/>15-Minute Dispatch Curves (XLSX)"]
        S_NASA["NASA POWER Meteorological API<br/>Solar, Temp, Wind, Rain (JSON)"]
    end

    subgraph RawZone ["2. Raw & Provenance Zone (raw)"]
        M_HASH["SHA-256 Checksum Verification<br/>manifest.json & source_document"]
        M_BATCH["raw.ingestion_batch<br/>Audit Registry"]
    end

    subgraph StagingZone ["3. Typed Staging & Preprocessing (staging)"]
        STG_CEB["stg_ceb_sales<br/>Provincial & Tariff Records"]
        STG_PUCSL["stg_pucsl_dispatch_interval<br/>15-Min Raw Generation MW"]
        STG_NASA["stg_nasa_weather_daily<br/>Raw Meteorological Nodes"]
    end

    subgraph ValidationZone ["4. Database Validation & Quality (etl / audit)"]
        VAL_PROC["etl.sp_validate_dispatch_staging()<br/>Boundary & Unit Consistency"]
        DQ_LEDGER["audit.data_quality_issue<br/>Quarantined Unmapped Records"]
        DQ_RUN["audit.etl_run<br/>Pipeline Execution Metrics"]
    end

    subgraph WarehouseZone ["5. Kimball Fact Constellation (dw)"]
        DIM_CONF["Conformed Dimensions<br/>dim_date, dim_plant, dim_fuel, etc."]
        FACT_DISP["dw.fact_dispatch_interval<br/>(Yearly Partitioned 107k+ Rows)"]
        FACT_SALES["dw.fact_electricity_sales<br/>(Audited 5-Year History)"]
        FACT_WEATH["dw.fact_weather_daily<br/>(21k+ Daily Observations)"]
    end

    subgraph MartZone ["6. Analytical Marts & Views (mart)"]
        PROC_REFRESH["etl.sp_refresh_analytical_marts()<br/>Automated Stored Procedure"]
        MV_DAILY["mart.mv_daily_system_summary"]
        MV_FUEL["mart.mv_monthly_fuel_mix"]
        MV_HOURLY["mart.mv_hourly_dispatch_pattern"]
    end

    subgraph ConsumptionZone ["7. Analytics & Dashboard (Next.js 16 / SQL)"]
        READ_POOL["Next.js PostgreSQL Pool<br/>SSL / TLS Session Connection"]
        SQL_24["24 Analytical SQL Queries<br/>Marts, CTEs, Window Functions"]
        WEB_UI["Interactive Web Dashboard<br/>Recharts, Tailwind CSS 4, React 19"]
    end

    Sources --> RawZone
    RawZone --> StagingZone
    StagingZone --> ValidationZone
    ValidationZone -->|Valid Rows| WarehouseZone
    ValidationZone -->|Anomalies & Unmapped| DQ_LEDGER
    WarehouseZone --> MartZone
    PROC_REFRESH --> MartZone
    MartZone --> ConsumptionZone
    WarehouseZone --> ConsumptionZone
```

---

## Detailed Data Processing Stages

### Stage 1 — Acquisition & Cryptographic Provenance
- Incoming source files from CEB, PUCSL, and NASA POWER are deposited in `data/raw/` with immutable filenames.
- SHA-256 cryptographic hashes are calculated immediately and checked against `data/raw/manifest.json`.
- Files are registered in `raw.source_document` with ingestion timestamps and reporting periods.

### Stage 2 — Staging & Format Normalization
- Parsers (`src/ingestion/`) convert PDFs, Excel sheets, and JSON streams into typed tabular records.
- Staging tables (`staging.stg_*`) preserve all original extracted strings alongside cast numeric equivalents to enable full auditability without silent drops.

### Stage 3 — Validation & Quarantine Defense
- Stored procedures (`etl.sp_validate_*`) execute validation checks:
  - Range boundaries ($MW \ge 0$, Solar Irradiance $\ge 0$).
  - Station name and alias resolution against `ref.plant_alias`.
  - Non-conforming or negative telemetry records are quarantined in `audit.data_quality_issue` with explicit error codes, while clean records advance into the warehouse.

### Stage 4 — Warehouse Transformation & Fact Loading
- Valid records are merged into conformed dimensions and fact tables using idempotent `ON CONFLICT DO UPDATE` or staging-partition swaps.
- High-volume facts (`fact_dispatch_interval`) route automatically to their respective yearly child partition based on UTC timestamp.

### Stage 5 — Analytical Mart Refresh
- `CALL etl.sp_refresh_analytical_marts();` refreshes pre-aggregated materialized views (`mart.mv_*`) concurrently where applicable, ensuring ultra-fast sub-second analytics.

### Stage 6 — Read-Only Dashboard Analytics
- The Next.js 16 full-stack web application connects over TLS/SSL using a dedicated read-only role or Supabase connection string.
- Analytical queries run with strict statement timeouts (5s to 10s) and leverage pre-aggregated marts and window functions.

