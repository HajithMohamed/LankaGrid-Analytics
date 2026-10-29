---
trigger: always_on
description: Data engineering, ingestion provenance, unit safety, and pipeline idempotency
---
# Data Engineering Rules

## Unit Integrity & Physical Consistency
- **Active Power vs. Energy Output**:
  - Power (instantaneous capacity/demand) is measured in **MW** (Megawatts) or **kW**.
  - Energy (integrated generation/consumption over time) is measured in **MWh** (Megawatt-hours) or **GWh** ($1\text{ GWh} = 1{,}000\text{ MWh}$).
  - NEVER mix or aggregate MW and MWh.
  - If integrating 15-minute dispatch MW to MWh, the calculation is: $\text{MWh} = \text{MW} \times 0.25\text{ hours}$.
- **Never Treat Missing as Zero**:
  - A reading of $0\text{ MW}$ signifies complete plant outage or zero generation.
  - An omitted, unrecorded, or unparsed value is `NULL` (missing data), NOT zero.
  - Treating missing measurements as zero corrupts load curve aggregates, capacity factor calculations, and loss estimates.

## Provenance & Immutable Storage
- Official raw downloads from CEB, PUCSL, and NASA POWER must be placed in `data/raw/` with their original filenames preserved.
- Compute and verify a **SHA-256 checksum** immediately upon retrieval and record it in `data/raw/manifest.json`.
- Raw source files are read-only and immutable. Never alter raw files in-place.
- Record retrieval timestamp, exact source URL, HTTP status, and reporting period for every dataset.

## Idempotency & Fault Tolerance
- All ingestion, staging, and ETL pipeline jobs must be idempotent:
  - Running a job twice with the same inputs must produce the exact same database state without duplicate rows.
  - Use `ON CONFLICT (natural_keys...) DO UPDATE` or staging-table swap patterns.
- Do not silently delete or drop corrupted source data. Move malformed rows into quarantined rejected records tables with error codes for manual/automated inspection.
