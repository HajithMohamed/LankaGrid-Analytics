# ETL Pipeline Architecture & Design Principles

## 1. Principles of the GridLens Pipeline

The GridLens Extract, Transform, Load (ETL) pipeline adheres to enterprise data engineering standards:

1. **Cryptographic Provenance**: Every raw file downloaded from CEB, PUCSL, or NASA POWER is fingerprinted using SHA-256 and registered in `data/raw/manifest.json` and `raw.source_document`.
2. **Idempotence**: Running any ingestion, staging, or fact-loading script multiple times produces the exact same database state without duplicate rows.
3. **No Silent Drops**: Records that fail range validation or contain unknown plant aliases are quarantined into `audit.data_quality_issue` with explicit error codes for subsequent remediation.
4. **Physical Integrity**: Power ($MW$) is never confused with Energy ($MWh$). Converting 15-minute dispatch power to energy follows:
   $$\text{MWh} = \text{MW} \times 0.25\text{ hours}$$
5. **Missing Value Semantics**: $0\text{ MW}$ indicates a real plant outage or zero generation; missing telemetry is explicitly stored as `NULL`.

---

## 2. Pipeline Modules

- `src/ingestion/`: Source-specific parsers for CEB Statistical Digest PDFs, PUCSL 15-minute Excel sheets, and NASA POWER JSON APIs.
- `src/preprocessing/`: Normalization of timestamps to Asia/Colombo (`UTC+05:30`), unit conversions to $MW$ and $MWh$, and alias harmonization against `ref.plant_alias`.
- `src/etl/real_data_loader.py`: Core transactional loader managing `raw`, `staging`, `dw`, and `audit` schema transitions.
- `src/etl/incremental_refresher.py`: Automated change detection and scheduled incremental updates.
- `scripts/refresh_warehouse.py`: CLI driver for on-demand or automated execution.

