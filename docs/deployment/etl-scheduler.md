# Automated ETL Scheduler & Orchestration Guide

## Overview

GridLens incorporates an automated incremental refresh system that detects new official source publications, performs cryptographic validation, stages raw records, updates fact tables idempotently, and refreshes pre-aggregated analytical marts.

---

## 1. Refresh Architecture

```
                  ┌──────────────────────┐
                  │ GitHub Actions Cron  │
                  │ (Daily 02:00 UTC)    │
                  └──────────┬───────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │ scripts/refresh_warehouse.py │
              └──────────────┬──────────────┘
                             │
     ┌───────────────────────┼───────────────────────┐
     ▼                       ▼                       ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  CEB Sales   │      │ NASA Weather │      │PUCSL Dispatch│
│ Incremental  │      │ Incremental  │      │ Incremental  │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             │
                             ▼
             ┌───────────────────────────────┐
             │  etl.sp_validate_* Staging    │
             │  & dw.fact_* Idempotent Load  │
             └───────────────┬───────────────┘
                             │
                             ▼
             ┌───────────────────────────────┐
             │ CALL sp_refresh_analytical_   │
             │          marts()              │
             └───────────────────────────────┘
```

---

## 2. GitHub Actions Automation

The scheduled workflow is located at `.github/workflows/scheduled-data-refresh.yml`.

### Schedule Cadence
- **Trigger:** Daily at 02:00 UTC (07:30 Asia/Colombo time).
- **Manual Trigger:** Available via GitHub Actions `workflow_dispatch` with parameter selection (`all`, `ceb`, `pucsl`, `nasa`).

### Secret Configuration
In your GitHub repository settings, configure:
- **`DATABASE_URL`**: `postgresql://postgres:[PASSWORD]@db.<project-ref>.supabase.co:5432/postgres`

---

## 3. Manual Local / Server Execution

To run the incremental refresher manually:

```powershell
# Refresh all eligible datasets and update marts
python scripts/refresh_warehouse.py

# Refresh only PUCSL dispatch
python scripts/refresh_warehouse.py --dataset pucsl

# Preview without applying mutations
python scripts/refresh_warehouse.py --dry-run

# Force re-ingestion of existing files
python scripts/refresh_warehouse.py --force
```

---

## 4. Pipeline Execution Logging

Every run of the incremental refresher records execution diagnostics into PostgreSQL:
- **`audit.etl_run`**: Pipeline name, started_at, completed_at, run_status (`SUCCEEDED`, `FAILED`, `PARTIAL_QUARANTINE`), rows_read, rows_inserted, rows_updated, rows_quarantined, error_message.
- **`audit.data_quality_issue`**: Row-level quarantined records with rule violation codes.

