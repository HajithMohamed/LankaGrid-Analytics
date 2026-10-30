# ETL Transaction Design & Fault-Tolerance Architecture

## 1. Three-Boundary Transaction Pattern

Implemented in [batch_loader.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/src/etl/batch_loader.py) and [012_procedures.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/012_procedures.sql), batch loads separate **audit envelope persistence** from **atomic data promotion** so that rollbacks leave zero partial warehouse rows while preserving full failure forensics:

```mermaid
sequenceDiagram
    participant Py as BatchLoader (Python)
    participant Raw as raw / staging
    participant DW as dw.fact_*
    participant Aud as audit.etl_run

    Note over Py,Aud: Boundary A — Audit Registration (Committed Immediately)
    Py->>Raw: Upsert raw.source_document & raw.ingestion_batch
    Py->>Aud: CALL etl.sp_start_etl_run(...) -> status = 'RUNNING'

    Note over Py,DW: Boundary B — Atomic Data Promotion (Single ACID Transaction)
    Py->>Raw: BEGIN; Insert raw.extracted_record & staging.stg_*
    Py->>Raw: CALL etl.sp_validate_staged_generation(...)
    alt Validation & Warehouse Constraints Pass
        Py->>DW: CALL etl.sp_load_generation_period(...) (UPSERT + Lineage)
        Py->>DW: COMMIT Boundary B
        Note over Py,Aud: Boundary C (Success) — Finalize Audit
        Py->>Aud: CALL etl.sp_finalize_etl_run(..., 'SUCCEEDED' / 'PARTIAL_QUARANTINE')
    else Unrecoverable Constraint / Runtime Error Mid-Batch
        Py->>DW: ROLLBACK Boundary B (0 partial fact rows survive!)
        Note over Py,Aud: Boundary C (Failure) — Preserve Audit Evidence
        Py->>Aud: CALL etl.sp_finalize_etl_run(..., 'ROLLED_BACK', error_message)
    end
```

---

## 2. Guarantees Verified by Automated Tests

Tested in [test_phase1_etl_transactions.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/tests/integration/test_phase1_etl_transactions.py):
1. **All-or-Nothing Fact Promotion**: When item 2 of a 2-row batch violates `ck_fact_gen_period_non_negative` (`-999.0 MWh`), item 1 (`1100.0 MWh`) is rolled back completely — `SELECT COUNT(*) FROM dw.fact_generation_period` for that document is `0`.
2. **Audit Evidence Survival**: Because `Boundary A` and `Boundary C` commit independently on an `autocommit=True` connection outside `Boundary B`, `audit.etl_run` retains `run_status = 'ROLLED_BACK'` and the exact PostgreSQL constraint diagnostic message.
3. **Strict Re-Execution Idempotency**: Re-running the same valid batch hits `ON CONFLICT ON CONSTRAINT uq_fact_generation_period_grain DO UPDATE`, updating timestamps/run IDs cleanly with zero duplicate fact rows.
4. **Concurrent MV Refresh Boundary**: `CALL etl.sp_refresh_mart_views(TRUE)` executes on a top-level `autocommit=True` session after `Boundary B` commits, satisfying PostgreSQL's requirement that `REFRESH MATERIALIZED VIEW CONCURRENTLY` run outside explicit multi-statement transaction blocks.

