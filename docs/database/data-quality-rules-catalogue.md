# Data-Quality Rules & Cross-Source Reconciliation Catalogue

Implemented in [003_reference_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/003_reference_tables.sql), [004_audit_and_quality_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/004_audit_and_quality_tables.sql), and seeded via [seed_reference.py](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/scripts/seed_reference.py).

---

## 1. Complete Catalogue of the 13 Seeded Data-Quality Rules (`ref.data_quality_rule`)

| Rule Code | Issue Classification | Target Domain | Default Severity | Blocks Load? | Rule Logic & Handling Policy |
|---|---|---|---|---|---|
| `DQ_GEN_MISSING_ENERGY` | `MISSING_VALUE` | `GENERATION` | `WARNING` | `TRUE` | Detects `NULL` or sentinels (`-`, `N/A`, `-999`). Preserves `NULL` — **never substitutes `0`**. |
| `DQ_EXACT_OR_GRAIN_DUPLICATE` | `DUPLICATE` | `ALL` | `ERROR` | `TRUE` | Flags duplicate rows on identical `(entity, period, metric, source, revision)`. |
| `DQ_NUMERIC_TYPE_PARSE_ERROR` | `INCORRECT_DATA_TYPE` | `ALL` | `ERROR` | `TRUE` | Quarantines unparseable non-numeric tokens that are not registered missing sentinels. |
| `DQ_GEN_NEGATIVE_OUTPUT` | `INVALID_MEASUREMENT` | `GENERATION` | `ERROR` | `TRUE` | Rejects negative power/energy ($<0$) for non-pumping / non-auxiliary entities. |
| `DQ_STATISTICAL_IQR_ZSCORE` | `STATISTICAL_OUTLIER` | `DISPATCH` | `WARNING` | `FALSE` | Flags readings $> 1.05 \times P_{\text{installed}}$ or outside $[Q_1 - 1.5\text{IQR}, Q_3 + 1.5\text{IQR}]$ for review. |
| `DQ_UNIT_DIMENSIONAL_MISMATCH` | `UNIT_INCONSISTENCY` | `ALL` | `CRITICAL` | `TRUE` | Blocks incompatible unit pairs (e.g., `MW` into `MWh` without explicit interval hours). |
| `DQ_PLANT_NAMING_VARIANT` | `NAMING_INCONSISTENCY` | `GENERATION` | `WARNING` | `TRUE` | Quarantines variant plant spellings until a `VERIFIED` entry with evidence exists in `ref.plant_alias`. |
| `DQ_DISPATCH_MISSING_SLOT` | `MISSING_REPORTING_INTERVAL` | `DISPATCH` | `WARNING` | `FALSE` | Logs missing 15-minute slots when a daily dispatch curve has $<96$ intervals. |
| `DQ_DIM_UNMATCHED_ENTITY` | `UNMATCHED_DIMENSION` | `ALL` | `ERROR` | `TRUE` | Quarantines staging records whose business key fails conformed dimension lookup. |
| `DQ_CROSS_SOURCE_VARIANCE` | `CONFLICTING_SOURCE_VALUE` | `RECONCILIATION` | `WARNING` | `FALSE` | Logs cross-source discrepancies (CEB vs. PUCSL) exceeding percentage tolerance. |
| `DQ_PERIOD_GRANULARITY_MISMATCH` | `INCOMPATIBLE_REPORTING_GRANULARITY` | `ALL` | `CRITICAL` | `TRUE` | Rejects period start/end dates that violate declared `period_type_code` (e.g., annual range tagged `DAILY`). |
| `DQ_UNSUPPORTED_CAPACITY_FACTOR` | `UNSUPPORTED_CALCULATION` | `CAPACITY` | `ERROR` | `TRUE` | Blocks derived ratios when capacity and generation periods or boundaries are incompatible. |
| `DQ_PDF_TABLE_PARSE_FAILURE` | `PARSING_FAILURE` | `INGESTION` | `CRITICAL` | `TRUE` | Logs structural table extraction failures without silently dropping source documents. |

---

## 2. Issue Lifecycle & Non-Destructive Audit Policy

Every issue recorded in `audit.data_quality_issue` transitions through four controlled statuses:
- `unresolved` — Newly detected anomaly awaiting triage.
- `quarantined` — Blocked from `dw.fact_*` promotion while retained intact in `staging.stg_*`.
- `accepted` — Engineering reviewer confirmed value is valid domain behavior (e.g., scheduled outage `NULL`); trigger `trg_audit_dq_issue_resolution` requires `resolved_by` and `resolution_justification`.
- `corrected` — Superseded by a verified parser rule or upstream revision with documented `resolved_by`, `resolution_justification`, and auto-stamped `resolved_at`.

---

## 3. Cross-Source Reconciliation Rules (`audit.reconciliation_case` & `ref.source_precedence`)

1. **Compatibility Preconditions**: `etl.sp_record_reconciliation_case` verifies via `etl.fn_validate_reporting_period` and `dw.dim_metric` that both sources share the exact same `metric_code` (hence identical gross/net boundary), `period_type_code`, `period_start_date`, `period_end_date`, and `unit_code`.
2. **Authoritative Precedence (`ref.source_precedence`)**:
   - **15-Minute Dispatch & Daily Station Generation**: `PUCSL` (CEB System Control operational reports) is rank 1.
   - **Monthly & Annual Generation, Provincial/Tariff Sales & Revenue**: `CEB` (Statistical Digest) is rank 1.
   - **Daily Meteorology**: `NASA_POWER` is rank 1.
3. **Both Values Preserved**: Neither source record is deleted or overwritten; variances above threshold are surfaced in `mart.vw_conflicting_source_metrics` as `CONFLICT_FLAGGED`.
