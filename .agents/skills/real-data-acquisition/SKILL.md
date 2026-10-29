---
name: real-data-acquisition
description: >-
  Provides procedures for authentic data source discovery, source URL and publication verification,
  file download, SHA-256 checksum verification, immutable raw storage, and metadata manifest recording.
  Use when retrieving historical electricity grid or meteorological datasets from CEB, PUCSL, or NASA POWER.
---

# Real Data Acquisition Skill

## When to Use This Skill
Use this skill when identifying, downloading, verifying, and indexing historical electricity datasets from the Ceylon Electricity Board (CEB), Public Utilities Commission of Sri Lanka (PUCSL), or NASA POWER API.

## Acquisition Procedure

### Step 1: Official Source Discovery & Inspection
1. Query official portals:
   - CEB Official Statistics: [https://ceb.lk/](https://ceb.lk/)
   - PUCSL Daily Generation & Dispatch Reports: [https://www.pucsl.gov.lk/daily-generation-reports-2/](https://www.pucsl.gov.lk/daily-generation-reports-2/)
   - NASA POWER API: [https://power.larc.nasa.gov/docs/services/api/temporal/daily/](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
2. Verify HTTP headers (Content-Type, Content-Length, Last-Modified) using `HEAD` requests before initiating large downloads.
3. Validate that the dataset matches the target historical period (primary focus: calendar year 2024).

### Step 2: Download & Immutable Storage
1. Save retrieved files directly to `data/raw/<provider>/<reporting_year>/` with their original filenames.
2. Under no circumstances edit, format, or clean raw files in `data/raw/`. They are immutable historical evidence.
3. In Phase 0 and CI, keep sample fixtures under `tests/fixtures/` and record full file manifests in `data/raw/manifest.json`.

### Step 3: Checksum Computation & Metadata Recording
1. Compute the SHA-256 cryptographic hash of every downloaded file:
   ```bash
   python scripts/compute_checksum.py data/raw/path/to/file.pdf
   ```
2. Append the record to `data/raw/manifest.json`:
   ```json
   {
     "file_id": "pucsl_gen_2024_01_15",
     "source_provider": "PUCSL",
     "source_url": "https://www.pucsl.gov.lk/wp-content/uploads/2024/01/Daily-Generation-Report-15-01-2024.pdf",
     "original_filename": "Daily-Generation-Report-15-01-2024.pdf",
     "local_path": "data/raw/pucsl/2024/Daily-Generation-Report-15-01-2024.pdf",
     "retrieval_timestamp": "2026-10-29T10:00:00+05:30",
     "reporting_period": "2024-01-15",
     "file_format": "PDF",
     "file_size_bytes": 284192,
     "sha256_checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
     "time_zone": "Asia/Colombo",
     "data_granularity": "Daily Plant Total & 15-min Dispatch",
     "units_contained": ["MW", "MWh", "GWh"]
   }
   ```

### Step 4: Provenance Documentation
1. Update `docs/data_sources/source-inventory.md`.
2. Fill out `docs/data_sources/source-profiling-template.md` for any newly introduced data source format.

## Expected Outputs
- Immutable raw data file in `data/raw/`
- Validated entry in `data/raw/manifest.json`
- Source profiling entry in `docs/data_sources/`

## Verification Steps
1. Run `python scripts/verify_manifest.py` to assert that all files registered in `manifest.json` match their SHA-256 hashes.
2. Confirm URL accessibility and document any HTTP redirects or archival mirrors.
