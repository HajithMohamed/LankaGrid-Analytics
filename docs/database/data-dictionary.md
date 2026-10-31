# Complete Warehouse Data Dictionary (PostgreSQL 18)

Generated and verified directly against the live **PostgreSQL 18.6** catalog (`sl_grid_warehouse`) across all **40 base and partitioned tables** (`public.schema_migrations` + 39 warehouse tables across `raw`, `ref`, `audit`, `dw`, `staging`, and `etl`).

**Catalog Totals Verified**: `40` tables (`39` in warehouse schemas + `public.schema_migrations`), `514` documented columns (100% column coverage).

> [!IMPORTANT]
> **Unit & Nullability Governance**: Across all tables, instantaneous active power and capacity use `MW`, integrated electrical energy uses `MWh` ($1\text{ GWh} = 1{,}000\text{ MWh}$), and missing source measurements are stored as SQL `NULL` (never `0`).

## Schema: `public`

### `public.schema_migrations` (TABLE)
- **Defined in**: [001_bootstrap.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/001_bootstrap.sql)
- **Grain**: One row per applied sequential forward SQL migration script.
- **Supported Business Functionality / Questions**: Which schema migrations have been applied, when were they executed, and do their normalized LF SHA-256 checksums match disk?

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `version` | `VARCHAR(255)` | `NOT NULL` | PK | N/A (categorical/text) | Migration Runner (`scripts/migrate.py`) | Unique sequential migration identifier (e.g. `001_bootstrap`, `005_dimensions`). |
| 2 | `description` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Migration Runner (`scripts/migrate.py`) | Detailed human-readable explanation of the entity or rule. |
| 3 | `applied_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Migration Runner (`scripts/migrate.py`) | Timestamp when the migration was committed to PostgreSQL. |
| 4 | `checksum` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Migration Runner (`scripts/migrate.py`) | Normalized LF SHA-256 hex digest of the SQL migration file verifying immutability. |
| 5 | `execution_ms` | `INTEGER` | `NULL` | — | milliseconds (ms) | Migration Runner (`scripts/migrate.py`) | Elapsed wall-clock execution duration of the migration script in milliseconds. |

## Schema: `raw`

### `raw.extracted_record` (TABLE)
- **Defined in**: [002_raw_source_registry.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/002_raw_source_registry.sql)
- **Grain**: One row per immutable JSONB record/row extracted from a source document within an ingestion batch.
- **Supported Business Functionality / Questions**: What exact raw cell/JSON payload existed at a given page/table/row locator before staging normalization?

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `raw_record_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 2 | `batch_id` | `BIGINT` | `NOT NULL` | FK -> `raw.ingestion_batch(batch_id)`, UQ | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key identifying the raw ingestion/extraction batch. |
| 3 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 4 | `source_row_locator` | `VARCHAR(128)` | `NOT NULL` | UQ | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Exact location within the raw file (e.g. `page=4:table=1:row=12` or JSON path). |
| 5 | `raw_payload` | `JSONB` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Unmodified JSONB key-value capture of the extracted source cells/fields. |
| 6 | `content_sha256` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | SHA-256 digest of the canonicalized `raw_payload` JSON. |
| 7 | `extracted_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Timestamp when the raw record was written. |

### `raw.ingestion_batch` (TABLE)
- **Defined in**: [002_raw_source_registry.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/002_raw_source_registry.sql)
- **Grain**: One row per parser extraction execution over a registered source document.
- **Supported Business Functionality / Questions**: When was a raw file parsed, using which parser version, and how many raw records were extracted?
- **Check Constraints**: `ck_raw_ingestion_batch_records_nonneg`: `CHECK ((records_extracted >= 0))`; `ck_raw_ingestion_batch_status`: `CHECK (((batch_status)::text = ANY ((ARRAY['STARTED'::character varying, 'EXTRACTED'::character varying, 'FAILED'::character varying, 'QUARANTINED'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `batch_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key identifying the raw ingestion/extraction batch. |
| 2 | `batch_code` | `VARCHAR(100)` | `NOT NULL` | UQ | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Unique business identifier for the extraction batch. |
| 3 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 4 | `extraction_method` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Parser/extractor identifier (e.g. `pdfplumber_table_v1`, `nasa_power_json_v1`). |
| 5 | `parser_version` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Semantic version of the extraction parser code. |
| 6 | `started_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Timestamp when the batch or ETL execution started. |
| 7 | `completed_at` | `TIMESTAMPTZ` | `NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Timestamp when the batch or ETL execution finished (`NULL` while running). |
| 8 | `batch_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Execution status (`STARTED`, `EXTRACTED`, `FAILED`, `QUARANTINED`). |
| 9 | `records_extracted` | `INTEGER` | `NOT NULL` | — | count (records) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Total raw records extracted and persisted into `raw.extracted_record`. |

### `raw.source_document` (TABLE)
- **Defined in**: [002_raw_source_registry.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/002_raw_source_registry.sql)
- **Grain**: One row per catalogued or downloaded raw source file/API response payload and revision.
- **Supported Business Functionality / Questions**: Which exact PDF/CSV/XLSX/JSON files in data/raw/ back warehouse facts, what are their SHA-256 hashes, and what reporting period do they cover?
- **Check Constraints**: `ck_raw_source_document_checksum_nonempty`: `CHECK ((length(btrim((sha256_checksum)::text)) >= 16))`; `ck_raw_source_document_format`: `CHECK (((file_format)::text = ANY ((ARRAY['PDF'::character varying, 'XLSX'::character varying, 'CSV'::character varying, 'JSON'::character varying, 'XML'::character varying, 'HTML'::character varying])::text[])))`; `ck_raw_source_document_period_order`: `CHECK ((reporting_period_end >= reporting_period_start))`; `ck_raw_source_document_period_type`: `CHECK (((reporting_period_type)::text = ANY ((ARRAY['INTERVAL_15MIN'::character varying, 'HOURLY'::character varying, 'DAILY'::character varying, 'MONTHLY'::character varying, 'QUARTERLY'::character varying, 'ANNUAL'::character varying, 'MULTI_YEAR'::character varying])::text[])))`; `ck_raw_source_document_size`: `CHECK (((file_size_bytes IS NULL) OR (file_size_bytes >= 0)))`; `ck_raw_source_document_status`: `CHECK (((acquisition_status)::text = ANY ((ARRAY['CATALOGUED_PENDING_DOWNLOAD'::character varying, 'DOWNLOADED_VERIFIED'::character varying, 'SYNTHETIC_FIXTURE'::character varying, 'QUARANTINED'::character varying, 'SUPERSEDED'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `source_document_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 2 | `source_system_id` | `INTEGER` | `NOT NULL` | FK -> `raw.source_system(source_system_id)` | Identifier (surrogate/key) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Surrogate primary key / foreign key for the upstream source provider. |
| 3 | `document_code` | `VARCHAR(100)` | `NOT NULL` | UQ | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Unique human-readable business code for the source document and reporting period. |
| 4 | `source_url` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Exact URL from which the document or API payload was retrieved. |
| 5 | `original_filename` | `VARCHAR(255)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Immutable original filename as published/downloaded. |
| 6 | `local_storage_path` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Relative repository path under `data/raw/` (or `tests/fixtures/` for synthetic test rows). |
| 7 | `file_format` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Controlled file container format (`PDF`, `XLSX`, `CSV`, `JSON`, `XML`, `HTML`). |
| 8 | `file_size_bytes` | `BIGINT` | `NULL` | — | bytes | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Exact byte length of the raw file on disk (`NULL` while pending acquisition). |
| 9 | `sha256_checksum` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | 64-hex-character SHA-256 file digest (`PENDING_ACQUISITION` only for catalogued un-downloaded entries). |
| 10 | `download_timestamp` | `TIMESTAMPTZ` | `NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Timezone-aware timestamp when the raw artifact was downloaded. |
| 11 | `publication_date` | `DATE` | `NULL` | — | ISO Calendar DATE | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Official publication or release date printed on the source report. |
| 12 | `reporting_period_type` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Temporal granularity covered by the source document. |
| 13 | `reporting_period_start` | `DATE` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Inclusive start date of the source document's coverage window. |
| 14 | `reporting_period_end` | `DATE` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Inclusive end date of the source document's coverage window. |
| 15 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 16 | `acquisition_status` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Lifecycle state (`CATALOGUED_PENDING_DOWNLOAD`, `DOWNLOADED_VERIFIED`, `SYNTHETIC_FIXTURE`, `QUARANTINED`, `SUPERSEDED`). |
| 17 | `created_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Audit timestamp when the record was initially created. |

### `raw.source_system` (TABLE)
- **Defined in**: [002_raw_source_registry.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/002_raw_source_registry.sql)
- **Grain**: One row per authoritative external data provider organization.
- **Supported Business Functionality / Questions**: Which official agencies provide warehouse data, via what portal/API mechanism, and under which default timezone?
- **Check Constraints**: `ck_raw_source_system_access`: `CHECK (((access_method)::text = ANY ((ARRAY['PORTAL_PDF'::character varying, 'REST_API_JSON'::character varying, 'PORTAL_XLSX'::character varying, 'PORTAL_CSV'::character varying, 'MANUAL_ARCHIVE'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `source_system_id` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Surrogate primary key / foreign key for the upstream source provider. |
| 2 | `source_code` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 3 | `source_name` | `VARCHAR(128)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Descriptive dataset/system title of the upstream provider. |
| 4 | `organization_name` | `VARCHAR(160)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Official legal name of the publishing institution. |
| 5 | `official_url` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Base official portal or API endpoint URL of the provider. |
| 6 | `default_timezone` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Default IANA timezone identifier for timestamps reported by this source (`Asia/Colombo`). |
| 7 | `access_method` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Controlled retrieval mechanism (`PORTAL_PDF`, `REST_API_JSON`, `PORTAL_XLSX`, `PORTAL_CSV`, `MANUAL_ARCHIVE`). |
| 8 | `is_active` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | `TRUE` when this record/rule is active for current ETL runs. |
| 9 | `created_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Ingestion Layer (`data/raw/manifest.json` & source file parsers) | Audit timestamp when the record was initially created. |

## Schema: `ref`

### `ref.data_quality_rule` (TABLE)
- **Defined in**: [003_reference_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/003_reference_tables.sql)
- **Grain**: One row per automated Lecture 6 / domain data quality rule.
- **Supported Business Functionality / Questions**: Which validation rules block warehouse promotion vs issue warnings across the 13 required DQ issue classifications?
- **Check Constraints**: `ck_ref_dq_rule_classification`: `CHECK (((issue_classification)::text = ANY ((ARRAY['MISSING_VALUE'::character varying, 'DUPLICATE'::character varying, 'INCORRECT_DATA_TYPE'::character varying, 'INVALID_MEASUREMENT'::character varying, 'STATISTICAL_OUTLIER'::character varying, 'UNIT_INCONSISTENCY'::character varying, 'NAMING_INCONSISTENCY'::character varying, 'MISSING_REPORTING_INTERVAL'::character varying, 'UNMATCHED_DIMENSION'::character varying, 'CONFLICTING_SOURCE_VALUE'::character varying, 'INCOMPATIBLE_REPORTING_GRANULARITY'::character varying, 'UNSUPPORTED_CALCULATION'::character varying, 'PARSING_FAILURE'::character varying])::text[])))`; `ck_ref_dq_rule_severity`: `CHECK (((default_severity)::text = ANY ((ARRAY['CRITICAL'::character varying, 'ERROR'::character varying, 'WARNING'::character varying, 'INFO'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `rule_code` | `VARCHAR(48)` | `NOT NULL` | PK | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Unique identifier for the automated data quality validation rule. |
| 2 | `rule_name` | `VARCHAR(128)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Concise human-readable title of the validation check. |
| 3 | `issue_classification` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | One of the 13 standardized Lecture 6 / warehouse data quality issue categories. |
| 4 | `target_domain` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Warehouse domain governed by the rule (`DISPATCH`, `GENERATION`, `CAPACITY`, `SALES`, `WEATHER`, `CROSS_SOURCE`, `ALL`). |
| 5 | `default_severity` | `VARCHAR(16)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Default alert severity (`CRITICAL`, `ERROR`, `WARNING`, `INFO`). |
| 6 | `blocks_warehouse_load` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | `TRUE` if violating rows must be quarantined rather than promoted to `dw.fact_*`. |
| 7 | `rule_expression_summary` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Formal specification of the predicate or check enforced by the rule. |
| 8 | `is_active` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | `TRUE` when this record/rule is active for current ETL runs. |
| 9 | `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Audit timestamp automatically maintained on `UPDATE` by trigger `etl.fn_trg_touch_updated_at()`. |

### `ref.energy_source_mapping` (TABLE)
- **Defined in**: [003_reference_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/003_reference_tables.sql)
- **Grain**: One row per provider-specific fuel/energy label mapped to a canonical energy source code and effective date.
- **Supported Business Functionality / Questions**: How do raw labels like 'Major Hydro', 'Thermal-Oil', or 'Mini Hydro (NCRE)' map to dw.dim_energy_source?
- **Check Constraints**: `ck_ref_esm_dates`: `CHECK (((effective_to IS NULL) OR (effective_to >= effective_from)))`; `ck_ref_esm_verification_status`: `CHECK (((verification_status)::text = ANY ((ARRAY['VERIFIED'::character varying, 'PENDING_EVIDENCE'::character varying, 'REJECTED'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `mapping_id` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Surrogate primary key for `energy_source_mapping`. |
| 2 | `source_code` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 3 | `raw_source_label` | `VARCHAR(128)` | `NOT NULL` | UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Exact fuel or generation category text appearing in upstream CEB/PUCSL reports. |
| 4 | `canonical_energy_source_code` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Target standardized code in `dw.dim_energy_source`. |
| 5 | `effective_from` | `DATE` | `NOT NULL` | UQ | ISO Calendar DATE | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Inclusive SCD Type 2 / mapping start date. |
| 6 | `effective_to` | `DATE` | `NULL` | — | ISO Calendar DATE | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Inclusive SCD Type 2 / mapping end date (`NULL` = currently active). |
| 7 | `verification_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Governance status (`VERIFIED`, `PENDING_EVIDENCE`, `REJECTED`); triggers enforce non-empty evidence when `VERIFIED`. |
| 8 | `verification_evidence` | `TEXT` | `NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Documentary citation proving why an alias/label maps to the canonical entity. |
| 9 | `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Audit timestamp automatically maintained on `UPDATE` by trigger `etl.fn_trg_touch_updated_at()`. |

### `ref.metric_mapping` (TABLE)
- **Defined in**: [003_reference_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/003_reference_tables.sql)
- **Grain**: One row per upstream source field/parameter name mapped to a canonical warehouse metric.
- **Supported Business Functionality / Questions**: Which canonical metric and unit correspond to NASA POWER 'ALLSKY_SFC_SW_DWN' or CEB Digest 'Billed Sales (GWh)'?
- **Check Constraints**: `ck_ref_metric_mapping_status`: `CHECK (((verification_status)::text = ANY ((ARRAY['VERIFIED'::character varying, 'PENDING_EVIDENCE'::character varying, 'REJECTED'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `metric_mapping_id` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Surrogate primary key for `metric_mapping`. |
| 2 | `source_code` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 3 | `source_field_name` | `VARCHAR(128)` | `NOT NULL` | UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Exact column header or API parameter code in the source dataset. |
| 4 | `canonical_metric_code` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Target standardized `metric_code` in `dw.dim_metric`. |
| 5 | `source_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Unit of measure in which the upstream field is originally reported. |
| 6 | `verification_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Governance status (`VERIFIED`, `PENDING_EVIDENCE`, `REJECTED`); triggers enforce non-empty evidence when `VERIFIED`. |
| 7 | `notes` | `TEXT` | `NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Supplementary governance or mapping notes. |
| 8 | `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Audit timestamp automatically maintained on `UPDATE` by trigger `etl.fn_trg_touch_updated_at()`. |

### `ref.plant_alias` (TABLE)
- **Defined in**: [003_reference_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/003_reference_tables.sql)
- **Grain**: One row per source-specific power station name/alias and effective start date.
- **Supported Business Functionality / Questions**: Which station name spellings (e.g. 'Lakvijaya Coal' vs 'Norochcholai') have verified evidence to resolve to the same canonical plant?
- **Check Constraints**: `ck_ref_plant_alias_dates`: `CHECK (((effective_to IS NULL) OR (effective_to >= effective_from)))`; `ck_ref_plant_alias_status`: `CHECK (((verification_status)::text = ANY ((ARRAY['VERIFIED'::character varying, 'PENDING_EVIDENCE'::character varying, 'REJECTED'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `alias_id` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Surrogate primary key for `plant_alias`. |
| 2 | `source_code` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 3 | `alias_name` | `VARCHAR(160)` | `NOT NULL` | UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Exact station or region spelling found in upstream source documents. |
| 4 | `canonical_plant_code` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Target standardized `plant_code` in `dw.dim_power_plant`. |
| 5 | `effective_from` | `DATE` | `NOT NULL` | UQ | ISO Calendar DATE | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Inclusive SCD Type 2 / mapping start date. |
| 6 | `effective_to` | `DATE` | `NULL` | — | ISO Calendar DATE | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Inclusive SCD Type 2 / mapping end date (`NULL` = currently active). |
| 7 | `verification_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Governance status (`VERIFIED`, `PENDING_EVIDENCE`, `REJECTED`); triggers enforce non-empty evidence when `VERIFIED`. |
| 8 | `verification_evidence` | `TEXT` | `NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Documentary citation proving why an alias/label maps to the canonical entity. |
| 9 | `verified_by` | `VARCHAR(80)` | `NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Engineer or reviewer identifier who verified the plant alias. |
| 10 | `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Audit timestamp automatically maintained on `UPDATE` by trigger `etl.fn_trg_touch_updated_at()`. |

### `ref.region_alias` (TABLE)
- **Defined in**: [003_reference_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/003_reference_tables.sql)
- **Grain**: One row per source geographic or CEB distribution division label.
- **Supported Business Functionality / Questions**: How do source geographic strings map to verified ISO 3166-2:LK provinces or CEB distribution regions?
- **Check Constraints**: `ck_ref_region_alias_status`: `CHECK (((verification_status)::text = ANY ((ARRAY['VERIFIED'::character varying, 'PENDING_EVIDENCE'::character varying, 'REJECTED'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `region_alias_id` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Surrogate primary key for `region_alias`. |
| 2 | `source_code` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 3 | `alias_name` | `VARCHAR(128)` | `NOT NULL` | UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Exact station or region spelling found in upstream source documents. |
| 4 | `canonical_region_code` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Target standardized `region_code` in `dw.dim_region`. |
| 5 | `verification_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Governance status (`VERIFIED`, `PENDING_EVIDENCE`, `REJECTED`); triggers enforce non-empty evidence when `VERIFIED`. |
| 6 | `verification_evidence` | `TEXT` | `NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Documentary citation proving why an alias/label maps to the canonical entity. |
| 7 | `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Audit timestamp automatically maintained on `UPDATE` by trigger `etl.fn_trg_touch_updated_at()`. |

### `ref.reporting_period_type` (TABLE)
- **Defined in**: [003_reference_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/003_reference_tables.sql)
- **Grain**: One row per controlled temporal reporting granularity.
- **Supported Business Functionality / Questions**: What minimum/maximum day span is valid for DAILY, MONTHLY, QUARTERLY, and ANNUAL records so granularities are never conflated?
- **Check Constraints**: `ck_ref_period_day_bounds`: `CHECK ((max_days >= min_days))`; `ck_ref_period_min_days`: `CHECK ((min_days >= 0))`; `ck_ref_period_nominal_minutes`: `CHECK (((nominal_minutes IS NULL) OR (nominal_minutes > 0)))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | PK | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 2 | `period_type_name` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Human-readable reporting granularity name. |
| 3 | `nominal_minutes` | `INTEGER` | `NULL` | — | minutes | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Nominal duration in minutes for sub-daily/daily periods (`15`, `60`, `1440`; `NULL` for variable-length calendar months/years). |
| 4 | `min_days` | `INTEGER` | `NOT NULL` | — | days | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Minimum inclusive day span permitted for this period granularity. |
| 5 | `max_days` | `INTEGER` | `NOT NULL` | — | days | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Maximum inclusive day span permitted for this period granularity. |
| 6 | `is_subdaily` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | `TRUE` for sub-daily operational intervals (`INTERVAL_15MIN`, `HOURLY`). |
| 7 | `description` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Detailed human-readable explanation of the entity or rule. |
| 8 | `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Audit timestamp automatically maintained on `UPDATE` by trigger `etl.fn_trg_touch_updated_at()`. |

### `ref.source_precedence` (TABLE)
- **Defined in**: [003_reference_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/003_reference_tables.sql)
- **Grain**: One row per business domain, reporting granularity, and authoritative source ranking.
- **Supported Business Functionality / Questions**: When CEB Statistical Digests and PUCSL operational reports differ, which source is authoritative for sub-daily vs annual analysis?
- **Check Constraints**: `ck_ref_source_precedence_rank`: `CHECK ((precedence_rank >= 1))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `precedence_id` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Surrogate primary key for the source precedence rule. |
| 2 | `business_domain` | `VARCHAR(48)` | `NOT NULL` | UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Analytical domain (`DISPATCH`, `GENERATION`, `CAPACITY`, `SALES`, `WEATHER`, `SYSTEM_DEMAND`). |
| 3 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.reporting_period_type(period_type_code)`, UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 4 | `authoritative_source_code` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Primary trusted source code for the given domain and granularity. |
| 5 | `secondary_source_code` | `VARCHAR(32)` | `NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Secondary source provider code in the comparison (must differ from `primary_source_code`). |
| 6 | `precedence_rank` | `SMALLINT` | `NOT NULL` | — | ordinal rank (1 = highest) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Priority rank (`1` denotes primary authoritative source). |
| 7 | `rationale` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Domain justification explaining why this source takes precedence at this granularity. |
| 8 | `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Audit timestamp automatically maintained on `UPDATE` by trigger `etl.fn_trg_touch_updated_at()`. |

### `ref.unit` (TABLE)
- **Defined in**: [003_reference_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/003_reference_tables.sql)
- **Grain**: One row per controlled physical, meteorological, or economic unit of measure.
- **Supported Business Functionality / Questions**: Which units represent instantaneous power (MW) versus integrated energy (MWh/GWh), and which unit is canonical in the warehouse?
- **Check Constraints**: `ck_ref_unit_dimension`: `CHECK (((measurement_dimension)::text = ANY ((ARRAY['POWER'::character varying, 'ENERGY'::character varying, 'CAPACITY'::character varying, 'IRRADIANCE_POWER'::character varying, 'IRRADIANCE_ENERGY'::character varying, 'TEMPERATURE'::character varying, 'SPEED'::character varying, 'LENGTH'::character varying, 'VOLUME'::character varying, 'PERCENTAGE'::character varying, 'CURRENCY'::character varying, 'COUNT'::character varying, 'FREQUENCY'::character varying, 'DIMENSIONLESS'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `unit_code` | `VARCHAR(24)` | `NOT NULL` | PK | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Canonical short identifier for the unit of measure (e.g. `MW`, `MWh`, `GWh`, `LKR`). |
| 2 | `unit_name` | `VARCHAR(80)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Full physical or economic unit name. |
| 3 | `unit_symbol` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Standard display symbol (`MW`, `MWh`, `°C`, `kWh/m²/day`). |
| 4 | `measurement_dimension` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Physical dimension class (`POWER`, `ENERGY`, `CAPACITY`, `TEMPERATURE`, etc.) preventing illegal cross-dimension conversions. |
| 5 | `is_canonical_warehouse_unit` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | `TRUE` if this unit is the standardized storage unit for its physical dimension in `dw`. |
| 6 | `description` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Detailed human-readable explanation of the entity or rule. |
| 7 | `created_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Audit timestamp when the record was initially created. |
| 8 | `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Audit timestamp automatically maintained on `UPDATE` by trigger `etl.fn_trg_touch_updated_at()`. |

### `ref.unit_conversion` (TABLE)
- **Defined in**: [003_reference_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/003_reference_tables.sql)
- **Grain**: One row per directed conversion factor from a source unit to a target unit.
- **Supported Business Functionality / Questions**: What exact multiplier converts GWh or kWh to MWh, and which conversions require explicit time-interval integration (MW -> MWh)?
- **Check Constraints**: `ck_ref_unit_conv_multiplier_pos`: `CHECK ((multiplier > (0)::numeric))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `conversion_id` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Surrogate primary key of the unit conversion rule. |
| 2 | `from_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)`, UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Source unit code prior to normalization. |
| 3 | `to_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)`, UQ | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Target unit code after normalization. |
| 4 | `multiplier` | `NUMERIC(20, 10)` | `NOT NULL` | — | dimensionless ratio | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Multiplicative scale factor (`target = (source * multiplier) + additive_offset`). |
| 5 | `additive_offset` | `NUMERIC(20, 10)` | `NOT NULL` | — | target unit offset | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Additive offset applied after scaling (e.g. Kelvin/Celsius conversions; `0` for linear energy/power scales). |
| 6 | `requires_interval_hours` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | `TRUE` when converting instantaneous power (`MW`) to energy (`MWh`), requiring multiplication by `interval_duration_minutes / 60`. |
| 7 | `formula_description` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Explicit mathematical conversion formula for audit transparency. |
| 8 | `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Curated Reference Seed (`scripts/seed_reference.py`) from CEB, PUCSL, NASA POWER & ISO standards | Audit timestamp automatically maintained on `UPDATE` by trigger `etl.fn_trg_touch_updated_at()`. |

## Schema: `audit`

### `audit.data_quality_issue` (TABLE)
- **Defined in**: [004_audit_and_quality_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/004_audit_and_quality_tables.sql)
- **Grain**: One row per detected data quality violation linked to its staging record and raw source provenance.
- **Supported Business Functionality / Questions**: Which records were quarantined or flagged under each of the 13 DQ classifications, what were their raw values, and who resolved them?
- **Check Constraints**: `ck_audit_dq_issue_classification`: `CHECK (((issue_classification)::text = ANY ((ARRAY['MISSING_VALUE'::character varying, 'DUPLICATE'::character varying, 'INCORRECT_DATA_TYPE'::character varying, 'INVALID_MEASUREMENT'::character varying, 'STATISTICAL_OUTLIER'::character varying, 'UNIT_INCONSISTENCY'::character varying, 'NAMING_INCONSISTENCY'::character varying, 'MISSING_REPORTING_INTERVAL'::character varying, 'UNMATCHED_DIMENSION'::character varying, 'CONFLICTING_SOURCE_VALUE'::character varying, 'INCOMPATIBLE_REPORTING_GRANULARITY'::character varying, 'UNSUPPORTED_CALCULATION'::character varying, 'PARSING_FAILURE'::character varying])::text[])))`; `ck_audit_dq_issue_severity`: `CHECK (((severity)::text = ANY ((ARRAY['CRITICAL'::character varying, 'ERROR'::character varying, 'WARNING'::character varying, 'INFO'::character varying])::text[])))`; `ck_audit_dq_issue_status`: `CHECK (((issue_status)::text = ANY ((ARRAY['unresolved'::character varying, 'quarantined'::character varying, 'accepted'::character varying, 'corrected'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `issue_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Surrogate primary key of the recorded data quality issue. |
| 2 | `etl_run_id` | `BIGINT` | `NULL` | FK -> `audit.etl_run(etl_run_id)` | Identifier (surrogate/key) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Surrogate key identifying the exact ETL execution run in `audit.etl_run`. |
| 3 | `source_document_id` | `BIGINT` | `NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 4 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 5 | `staging_table_name` | `VARCHAR(80)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Fully qualified staging table where the issue was detected. |
| 6 | `staging_record_ref` | `VARCHAR(128)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Primary key / natural locator of the offending staging row. |
| 7 | `rule_code` | `VARCHAR(48)` | `NOT NULL` | FK -> `ref.data_quality_rule(rule_code)` | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Unique identifier for the automated data quality validation rule. |
| 8 | `issue_classification` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | One of the 13 standardized Lecture 6 / warehouse data quality issue categories. |
| 9 | `severity` | `VARCHAR(16)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Recorded issue severity (`CRITICAL`, `ERROR`, `WARNING`, `INFO`). |
| 10 | `original_value` | `TEXT` | `NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Unmodified offending string/numeric value as extracted from the source (`NULL` if missing). |
| 11 | `suggested_normalized_value` | `TEXT` | `NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Optional deterministic remediation candidate (never auto-overwrites raw data). |
| 12 | `detected_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Timestamp when the validation gate recorded the issue. |
| 13 | `issue_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Governance lifecycle state (`unresolved`, `quarantined`, `accepted`, `corrected`). |
| 14 | `resolved_by` | `VARCHAR(80)` | `NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Reviewer who adjudicated the issue (mandatory when `accepted` or `corrected`, enforced by trigger). |
| 15 | `resolved_at` | `TIMESTAMPTZ` | `NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Timestamp when the issue resolution was recorded. |
| 16 | `resolution_justification` | `TEXT` | `NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Documented domain rationale for accepting or correcting a flagged record. |

### `audit.etl_run` (TABLE)
- **Defined in**: [004_audit_and_quality_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/004_audit_and_quality_tables.sql)
- **Grain**: One row per ETL validation, reference promotion, warehouse load, or reconciliation execution.
- **Supported Business Functionality / Questions**: Did a batch succeed, fail, roll back, or quarantine rows, and how many rows were read/inserted/updated/quarantined?
- **Check Constraints**: `ck_audit_etl_run_ins`: `CHECK ((rows_inserted >= 0))`; `ck_audit_etl_run_quar`: `CHECK ((rows_quarantined >= 0))`; `ck_audit_etl_run_read`: `CHECK ((rows_read >= 0))`; `ck_audit_etl_run_status`: `CHECK (((run_status)::text = ANY ((ARRAY['RUNNING'::character varying, 'SUCCEEDED'::character varying, 'FAILED'::character varying, 'ROLLED_BACK'::character varying, 'PARTIAL_QUARANTINE'::character varying])::text[])))`; `ck_audit_etl_run_upd`: `CHECK ((rows_updated >= 0))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `etl_run_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Surrogate key identifying the exact ETL execution run in `audit.etl_run`. |
| 2 | `pipeline_name` | `VARCHAR(100)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Logical ETL pipeline or stored procedure name. |
| 3 | `target_schema` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Destination PostgreSQL schema targeted by the run. |
| 4 | `target_table` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Destination table targeted by the run. |
| 5 | `source_document_id` | `BIGINT` | `NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 6 | `batch_id` | `BIGINT` | `NULL` | FK -> `raw.ingestion_batch(batch_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key identifying the raw ingestion/extraction batch. |
| 7 | `run_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Outcome of the ETL run (`RUNNING`, `SUCCEEDED`, `FAILED`, `ROLLED_BACK`, `PARTIAL_QUARANTINE`). |
| 8 | `started_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Timestamp when the batch or ETL execution started. |
| 9 | `completed_at` | `TIMESTAMPTZ` | `NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Timestamp when the batch or ETL execution finished (`NULL` while running). |
| 10 | `rows_read` | `INTEGER` | `NOT NULL` | — | count (rows) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Number of input rows inspected during the ETL run. |
| 11 | `rows_inserted` | `INTEGER` | `NOT NULL` | — | count (rows) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Number of rows inserted into the target table. |
| 12 | `rows_updated` | `INTEGER` | `NOT NULL` | — | count (rows) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Number of existing rows idempotently updated (`ON CONFLICT DO UPDATE`). |
| 13 | `rows_quarantined` | `INTEGER` | `NOT NULL` | — | count (rows) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Number of invalid rows held in staging quarantine and logged to `audit.data_quality_issue`. |
| 14 | `error_message` | `TEXT` | `NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Captured exception diagnostic when `run_status` is `FAILED` or `ROLLED_BACK`. |
| 15 | `invoked_by` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | PostgreSQL role/user that executed the ETL run. |

### `audit.reconciliation_case` (TABLE)
- **Defined in**: [004_audit_and_quality_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/004_audit_and_quality_tables.sql)
- **Grain**: One row per cross-source comparison of a compatible metric, entity scope, unit, and reporting period.
- **Supported Business Functionality / Questions**: What is the exact MWh and percentage variance between CEB and PUCSL for the same reporting period, and is it within tolerance (<=1%)?
- **Check Constraints**: `ck_audit_reconciliation_dates`: `CHECK ((period_end_date >= period_start_date))`; `ck_audit_reconciliation_distinct_sources`: `CHECK (((primary_source_code)::text <> (secondary_source_code)::text))`; `ck_audit_reconciliation_status`: `CHECK (((reconciliation_status)::text = ANY ((ARRAY['OPEN'::character varying, 'WITHIN_TOLERANCE'::character varying, 'CONFLICT_FLAGGED'::character varying, 'RESOLVED_PRIMARY'::character varying, 'RESOLVED_SECONDARY'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `reconciliation_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Surrogate primary key of the cross-source reconciliation case. |
| 2 | `etl_run_id` | `BIGINT` | `NULL` | FK -> `audit.etl_run(etl_run_id)` | Identifier (surrogate/key) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Surrogate key identifying the exact ETL execution run in `audit.etl_run`. |
| 3 | `metric_code` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Canonical metric identifier (e.g. `PLANT_DISPATCH_MW`, `GEN_ENERGY_MWH`, `SALES_ENERGY_MWH`, `SOLAR_GHI_KWH_M2_DAY`). |
| 4 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.reporting_period_type(period_type_code)` | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 5 | `period_start_date` | `DATE` | `NOT NULL` | — | ISO Calendar DATE | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Inclusive start date of the reporting period. |
| 6 | `period_end_date` | `DATE` | `NOT NULL` | — | ISO Calendar DATE | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Inclusive end date of the reporting period. |
| 7 | `entity_scope_code` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Entity scope compared (`NATIONAL`, plant code, fuel code, or sector code). |
| 8 | `unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Canonical short identifier for the unit of measure (e.g. `MW`, `MWh`, `GWh`, `LKR`). |
| 9 | `primary_source_code` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Authoritative source provider code in the comparison. |
| 10 | `primary_value` | `NUMERIC(18, 4)` | `NOT NULL` | — | metric unit (unit_code) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Standardized numeric value reported by the primary source. |
| 11 | `secondary_source_code` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Secondary source provider code in the comparison (must differ from `primary_source_code`). |
| 12 | `secondary_value` | `NUMERIC(18, 4)` | `NOT NULL` | — | metric unit (unit_code) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Standardized numeric value reported by the secondary source. |
| 13 | `absolute_variance` | `NUMERIC(18, 4)` | `NULL` | GENERATED STORED | metric unit (unit_code) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Stored generated column `ABS(primary_value - secondary_value)`. |
| 14 | `pct_variance` | `NUMERIC(10, 4)` | `NULL` | — | pct (%) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Absolute percentage difference relative to `primary_value` (`NULL` if `primary_value = 0`). |
| 15 | `reconciliation_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Adjudication state (`OPEN`, `WITHIN_TOLERANCE`, `CONFLICT_FLAGGED`, `RESOLVED_PRIMARY`, `RESOLVED_SECONDARY`). |
| 16 | `authoritative_source_chosen` | `VARCHAR(32)` | `NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Source code selected for downstream reporting after reconciliation. |
| 17 | `resolution_notes` | `TEXT` | `NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Audit notes explaining the reconciliation variance (e.g. gross vs net boundary or billing lag). |
| 18 | `created_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Audit timestamp when the record was initially created. |

### `audit.record_lineage` (TABLE)
- **Defined in**: [004_audit_and_quality_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/004_audit_and_quality_tables.sql)
- **Grain**: One row per promoted warehouse fact record linked back to staging and raw source locators.
- **Supported Business Functionality / Questions**: Which exact staging row ID and raw PDF/JSON record produced a given warehouse fact primary key?

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `lineage_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Surrogate primary key of the record-level lineage entry. |
| 2 | `etl_run_id` | `BIGINT` | `NOT NULL` | FK -> `audit.etl_run(etl_run_id)` | Identifier (surrogate/key) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Surrogate key identifying the exact ETL execution run in `audit.etl_run`. |
| 3 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 4 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 5 | `staging_table` | `VARCHAR(80)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Source staging table from which the warehouse record was promoted. |
| 6 | `staging_row_id` | `BIGINT` | `NOT NULL` | — | Identifier (surrogate/key) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Surrogate primary key of the source row in the staging table. |
| 7 | `target_dw_table` | `VARCHAR(80)` | `NOT NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Target dimensional/fact table in `dw`. |
| 8 | `target_dw_pk` | `BIGINT` | `NOT NULL` | — | Identifier (surrogate/key) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Surrogate primary key assigned in the target `dw` table. |
| 9 | `transformation_notes` | `TEXT` | `NULL` | — | N/A (categorical/text) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Summary of unit conversions or derivations applied during promotion. |
| 10 | `recorded_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Automated DQ & Reconciliation Engine (`etl.sp_validate_*`, `etl.sp_record_reconciliation`) | Timestamp when the lineage link was recorded. |

## Schema: `dw`

### `dw.dim_consumption_sector` (TABLE)
- **Defined in**: [005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)
- **Grain**: One row per official CEB/PUCSL electricity tariff consumer category (9 verified categories).
- **Supported Business Functionality / Questions**: Supports electricity demand/sales breakdown across Domestic, Industrial, General Purpose, Hotel, Government, Religious, Street Lighting, LECO, and All Sectors.

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `sector_key` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Surrogate dimension key for `dw.dim_consumption_sector`. |
| 2 | `sector_code` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Canonical tariff sector code (`DOMESTIC`, `INDUSTRIAL`, `GENERAL_PURPOSE`, `HOTEL`, `GOVERNMENT`, `RELIGIOUS`, `STREET_LIGHTING`, `BULK_LECO`). |
| 3 | `sector_name` | `VARCHAR(100)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Official consumer tariff category name. |
| 4 | `tariff_group` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | PUCSL tariff schedule family (`D`, `I`, `GP`, `H`, `GV`, `R`, `SL`, `BS`). |
| 5 | `is_aggregate_bucket` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | `TRUE` if the sector represents a bulk/aggregate distribution licensee (`BULK_LECO`). |
| 6 | `source_classification` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Publishing tariff classification authority. |

### `dw.dim_date` (TABLE)
- **Defined in**: [005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)
- **Grain**: One row per calendar day (2019-01-01 through 2026-12-31 seeded; 2,922 days).
- **Supported Business Functionality / Questions**: Enables calendar rollups by ISO week, month, quarter, year, weekend vs weekday, and Sri Lanka's four meteorological monsoon seasons.
- **Check Constraints**: `ck_dim_date_dom`: `CHECK (((day_of_month >= 1) AND (day_of_month <= 31)))`; `ck_dim_date_dow`: `CHECK (((day_of_week_iso >= 1) AND (day_of_week_iso <= 7)))`; `ck_dim_date_doy`: `CHECK (((day_of_year >= 1) AND (day_of_year <= 366)))`; `ck_dim_date_monsoon`: `CHECK (((sl_monsoon_season)::text = ANY ((ARRAY['NORTHEAST_MONSOON'::character varying, 'FIRST_INTER_MONSOON'::character varying, 'SOUTHWEST_MONSOON'::character varying, 'SECOND_INTER_MONSOON'::character varying])::text[])))`; `ck_dim_date_month`: `CHECK (((month_number >= 1) AND (month_number <= 12)))`; `ck_dim_date_quarter`: `CHECK (((quarter_number >= 1) AND (quarter_number <= 4)))`; `ck_dim_date_woy`: `CHECK (((week_of_year_iso >= 1) AND (week_of_year_iso <= 53)))`; `ck_dim_date_year`: `CHECK (((calendar_year >= 1990) AND (calendar_year <= 2100)))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `date_key` | `INTEGER` | `NOT NULL` | PK | YYYYMMDD integer key | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | Smart integer calendar key in `YYYYMMDD` format (e.g. `20240115`). |
| 2 | `calendar_date` | `DATE` | `NOT NULL` | UQ | ISO Calendar DATE | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | Exact SQL `DATE` value. |
| 3 | `day_of_month` | `SMALLINT` | `NOT NULL` | — | calendar day (1-31) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | Day number within the calendar month (`1`–`31`). |
| 4 | `day_of_year` | `SMALLINT` | `NOT NULL` | — | calendar day (1-366) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | Ordinal day within the calendar year (`1`–`366`). |
| 5 | `day_of_week_iso` | `SMALLINT` | `NOT NULL` | — | ISO weekday (1=Mon..7=Sun) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | ISO-8601 weekday (`1` = Monday through `7` = Sunday). |
| 6 | `day_name` | `VARCHAR(12)` | `NOT NULL` | — | N/A (categorical/text) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | English weekday name (`Monday`–`Sunday`). |
| 7 | `is_weekend` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | `TRUE` for Saturday and Sunday. |
| 8 | `week_of_year_iso` | `SMALLINT` | `NOT NULL` | — | ISO week (1-53) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | ISO-8601 week number (`1`–`53`). |
| 9 | `month_number` | `SMALLINT` | `NOT NULL` | — | calendar month (1-12) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | Calendar month number (`1`–`12`). |
| 10 | `month_name` | `VARCHAR(12)` | `NOT NULL` | — | N/A (categorical/text) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | English month name (`January`–`December`). |
| 11 | `year_month` | `CHAR(7)` | `NOT NULL` | — | N/A (categorical/text) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | Formatted year-month label (`YYYY-MM`). |
| 12 | `quarter_number` | `SMALLINT` | `NOT NULL` | — | calendar quarter (1-4) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | Calendar quarter (`1`–`4`). |
| 13 | `quarter_name` | `CHAR(2)` | `NOT NULL` | — | N/A (categorical/text) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | Quarter label (`Q1`–`Q4`). |
| 14 | `calendar_year` | `SMALLINT` | `NOT NULL` | — | calendar year (YYYY) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | Four-digit Gregorian calendar year. |
| 15 | `sl_monsoon_season` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Deterministic ISO-8601 Calendar + Dept. of Meteorology SL Monsoon Classification | Sri Lanka meteorological hydro-climate season (`NORTHEAST_MONSOON`, `FIRST_INTER_MONSOON`, `SOUTHWEST_MONSOON`, `SECOND_INTER_MONSOON`). |

### `dw.dim_energy_source` (TABLE)
- **Defined in**: [005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)
- **Grain**: One row per standardized electricity generation technology / fuel category (9 verified categories).
- **Supported Business Functionality / Questions**: Supports renewable vs thermal share, Major Hydro vs NCRE breakdown, indigenous vs imported fuel dependence, and dispatchable mix.

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `energy_source_key` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Surrogate dimension key for `dw.dim_energy_source`. |
| 2 | `energy_source_code` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Canonical fuel/technology code (e.g. `MAJOR_HYDRO`, `COAL`, `THERMAL_OIL`, `SOLAR_UTILITY`, `WIND`). |
| 3 | `energy_category` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | High-level generation family (`Hydro`, `Thermal`, `Renewable_NCRE`, `Storage`, `Other`). |
| 4 | `fuel_type` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Underlying primary energy carrier (`Water`, `Coal`, `Fuel Oil / Diesel / Naphtha`, `Solar_PV`, `Wind`, `Biomass`). |
| 5 | `reporting_classification` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Official CEB/PUCSL reporting roll-up bucket (`Conventional Hydro`, `Thermal Coal`, `Thermal Oil`, `NCRE`). |
| 6 | `is_renewable` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | `TRUE` for renewable energy sources (Major Hydro, Mini Hydro, Solar, Wind, Biomass). |
| 7 | `is_dispatchable` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | `TRUE` if output can be controlled/dispatched on demand by System Control. |
| 8 | `is_indigenous` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | `TRUE` for domestic primary energy resources (water, solar, wind, local biomass); `FALSE` for imported coal/oil. |

### `dw.dim_interval` (TABLE)
- **Defined in**: [005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)
- **Grain**: One row per sub-daily dispatch slot (96 x 15-minute slots + 24 x 60-minute slots = 120 rows).
- **Supported Business Functionality / Questions**: Enables intraday load-curve profiling and Sri Lanka Time-of-Use (TOU) tariff block analysis (OFF_PEAK, DAY, PEAK).
- **Check Constraints**: `ck_dim_interval_duration`: `CHECK ((duration_minutes = ANY (ARRAY[15, 60])))`; `ck_dim_interval_hour`: `CHECK (((hour_of_day >= 0) AND (hour_of_day <= 23)))`; `ck_dim_interval_index`: `CHECK (((interval_index >= 1) AND (interval_index <= 96)))`; `ck_dim_interval_tou_block`: `CHECK (((tariff_time_block)::text = ANY ((ARRAY['OFF_PEAK'::character varying, 'DAY'::character varying, 'PEAK'::character varying])::text[])))`; `ck_dim_interval_type`: `CHECK (((interval_type)::text = ANY ((ARRAY['15MIN'::character varying, 'HOURLY'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `interval_key` | `INTEGER` | `NOT NULL` | PK | surrogate slot key | Deterministic Sub-Daily Clock Grid + PUCSL/CEB TOU Tariff Schedule | Surrogate key for sub-daily slot (`1`–`96` for 15-min slots; `101`–`124` for hourly slots). |
| 2 | `interval_type` | `VARCHAR(20)` | `NOT NULL` | UQ | N/A (categorical/text) | Deterministic Sub-Daily Clock Grid + PUCSL/CEB TOU Tariff Schedule | Sub-daily slot resolution (`15MIN` or `HOURLY`). |
| 3 | `interval_index` | `SMALLINT` | `NOT NULL` | UQ | slot index (1-96) | Deterministic Sub-Daily Clock Grid + PUCSL/CEB TOU Tariff Schedule | 1-based sequential slot number within the 24-hour day (`1`–`96` or `1`–`24`). |
| 4 | `start_time` | `TIME WITHOUT TIME ZONE` | `NOT NULL` | — | Local Time (Asia/Colombo) | Deterministic Sub-Daily Clock Grid + PUCSL/CEB TOU Tariff Schedule | Inclusive Sri Lanka Standard Time (`UTC+05:30`) slot start time. |
| 5 | `end_time` | `TIME WITHOUT TIME ZONE` | `NOT NULL` | — | Local Time (Asia/Colombo) | Deterministic Sub-Daily Clock Grid + PUCSL/CEB TOU Tariff Schedule | Slot end time in Sri Lanka Standard Time. |
| 6 | `duration_minutes` | `SMALLINT` | `NOT NULL` | — | minutes (15 or 60) | Deterministic Sub-Daily Clock Grid + PUCSL/CEB TOU Tariff Schedule | Slot width in minutes (`15` or `60`). |
| 7 | `hour_of_day` | `SMALLINT` | `NOT NULL` | — | hour (0-23) | Deterministic Sub-Daily Clock Grid + PUCSL/CEB TOU Tariff Schedule | 0-based clock hour (`0`–`23`). |
| 8 | `tariff_time_block` | `VARCHAR(20)` | `NOT NULL` | — | N/A (categorical/text) | Deterministic Sub-Daily Clock Grid + PUCSL/CEB TOU Tariff Schedule | Sri Lanka PUCSL/CEB Time-of-Use tariff block (`OFF_PEAK` 22:30–05:30, `DAY` 05:30–18:30, `PEAK` 18:30–22:30). |

### `dw.dim_metric` (TABLE)
- **Defined in**: [005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)
- **Grain**: One row per canonical physical/economic metric definition (14 seeded metrics).
- **Supported Business Functionality / Questions**: Governs metric semantics, canonical units, gross vs net boundaries, additivity across time/entities, and comparability groups.
- **Check Constraints**: `ck_dim_metric_agg`: `CHECK (((aggregation_behavior)::text = ANY ((ARRAY['SUM'::character varying, 'AVG'::character varying, 'MIN'::character varying, 'MAX'::character varying, 'NON_ADDITIVE'::character varying, 'SEMI_ADDITIVE_PERIOD_END'::character varying])::text[])))`; `ck_dim_metric_boundary`: `CHECK (((generation_boundary)::text = ANY ((ARRAY['GROSS'::character varying, 'NET'::character varying, 'AUXILIARY'::character varying, 'NOT_APPLICABLE'::character varying])::text[])))`; `ck_dim_metric_class`: `CHECK (((measurement_class)::text = ANY ((ARRAY['POWER'::character varying, 'ENERGY'::character varying, 'CAPACITY'::character varying, 'COUNT'::character varying, 'CURRENCY'::character varying, 'PERCENTAGE'::character varying, 'METEOROLOGICAL'::character varying, 'STORAGE'::character varying, 'RATIO'::character varying])::text[])))`; `ck_dim_metric_nature`: `CHECK (((value_nature)::text = ANY ((ARRAY['REPORTED'::character varying, 'ESTIMATED'::character varying, 'DERIVED'::character varying, 'AUDITED_FINAL'::character varying, 'PROVISIONAL'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `metric_key` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Surrogate dimension key for `dw.dim_metric`. |
| 2 | `metric_code` | `VARCHAR(48)` | `NOT NULL` | UQ | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Canonical metric identifier (e.g. `PLANT_DISPATCH_MW`, `GEN_ENERGY_MWH`, `SALES_ENERGY_MWH`, `SOLAR_GHI_KWH_M2_DAY`). |
| 3 | `metric_name` | `VARCHAR(128)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Full descriptive name of the physical or economic metric. |
| 4 | `business_domain` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Analytical domain (`DISPATCH`, `GENERATION`, `CAPACITY`, `SALES`, `WEATHER`, `SYSTEM_DEMAND`). |
| 5 | `measurement_class` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Measurement type (`POWER`, `ENERGY`, `CAPACITY`, `COUNT`, `CURRENCY`, `PERCENTAGE`, `METEOROLOGICAL`, `STORAGE`, `RATIO`). |
| 6 | `canonical_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Standardized unit code in which this metric is stored in `dw`. |
| 7 | `generation_boundary` | `VARCHAR(20)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Electrical measurement boundary (`GROSS` at generator terminals, `NET` sent out to grid, `AUXILIARY`, or `NOT_APPLICABLE`). |
| 8 | `value_nature` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Epistemic status of the quantity (`REPORTED`, `ESTIMATED`, `DERIVED`, `AUDITED_FINAL`, `PROVISIONAL`, `REVISED`, `MISSING`). |
| 9 | `aggregation_behavior` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Permitted OLAP aggregation function (`SUM`, `AVG`, `MIN`, `MAX`, `NON_ADDITIVE`, `SEMI_ADDITIVE_PERIOD_END`). |
| 10 | `is_summable_across_time` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | `TRUE` only if values can be summed across consecutive time periods (e.g. `MWh` is `TRUE`; `MW` power and capacity are `FALSE`). |
| 11 | `is_summable_across_entities` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | `TRUE` if values can be summed across disjoint plants/sectors at the same time point. |
| 12 | `comparability_group` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Equivalence key required by cross-source reconciliation to prevent comparing incompatible metrics. |
| 13 | `definition_notes` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Authoritative engineering definition and aggregation caveats. |

### `dw.dim_power_plant` (TABLE)
- **Defined in**: [005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)
- **Grain**: One row per SCD Type 2 version of a verified power station, hydro complex, or reported NCRE aggregate category (32 seeded entities).
- **Supported Business Functionality / Questions**: Supports plant-level generation, dispatch, complex-level hydro analysis (Mahaweli, Laxapana, Samanala), CEB vs IPP/SPP ownership, and historical plant attribute changes.
- **Check Constraints**: `ck_dim_power_plant_effective_dates`: `CHECK (((effective_to IS NULL) OR (effective_to >= effective_from)))`; `ck_dim_power_plant_lat`: `CHECK (((latitude_deg IS NULL) OR ((latitude_deg >= 5.80000) AND (latitude_deg <= 10.00000))))`; `ck_dim_power_plant_level`: `CHECK (((entity_level)::text = ANY ((ARRAY['PLANT'::character varying, 'UNIT'::character varying, 'COMPLEX'::character varying, 'AGGREGATE_CATEGORY'::character varying])::text[])))`; `ck_dim_power_plant_lon`: `CHECK (((longitude_deg IS NULL) OR ((longitude_deg >= 79.40000) AND (longitude_deg <= 82.00000))))`; `ck_dim_power_plant_operator`: `CHECK (((operator_type)::text = ANY ((ARRAY['CEB'::character varying, 'IPP'::character varying, 'SPP'::character varying, 'AGGREGATE'::character varying, 'MIXED'::character varying])::text[])))`; `ck_dim_power_plant_verification`: `CHECK (((verification_status)::text = ANY ((ARRAY['VERIFIED'::character varying, 'AGGREGATE_REPORTED'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `plant_key` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Surrogate SCD Type 2 primary/foreign key for `dw.dim_power_plant`. |
| 2 | `plant_code` | `VARCHAR(48)` | `NOT NULL` | UQ | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Natural identifier for the power plant, complex, or reported category (e.g. `LAKVIJAYA`, `VICTORIA`, `NCRE_SOLAR_AGG`). |
| 3 | `plant_name` | `VARCHAR(160)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Verified station or reporting category name. |
| 4 | `entity_level` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Granularity of the generation entity (`PLANT`, `UNIT`, `COMPLEX`, `AGGREGATE_CATEGORY`). |
| 5 | `operator_type` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Ownership/operating regime (`CEB`, `IPP`, `SPP`, `AGGREGATE`, `MIXED`). |
| 6 | `energy_source_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_energy_source(energy_source_key)` | Identifier (surrogate/key) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Surrogate dimension key for `dw.dim_energy_source`. |
| 7 | `region_key` | `INTEGER` | `NULL` | FK -> `dw.dim_region(region_key)` | Identifier (surrogate/key) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Surrogate dimension key for `dw.dim_region`. |
| 8 | `hydro_complex` | `VARCHAR(64)` | `NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Hydrological cascade complex (`Mahaweli`, `Laxapana`, `Samanala`, `Other Hydro`; `NULL` for non-hydro). |
| 9 | `latitude_deg` | `NUMERIC(8, 5)` | `NULL` | — | degrees North (WGS84) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Verified WGS84 latitude within Sri Lanka (`5.80`–`10.00` °N; `NULL` for national aggregate buckets). |
| 10 | `longitude_deg` | `NUMERIC(8, 5)` | `NULL` | — | degrees East (WGS84) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Verified WGS84 longitude within Sri Lanka (`79.40`–`82.00` °E; `NULL` for national aggregate buckets). |
| 11 | `verification_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Governance status (`VERIFIED`, `PENDING_EVIDENCE`, `REJECTED`); triggers enforce non-empty evidence when `VERIFIED`. |
| 12 | `effective_from` | `DATE` | `NOT NULL` | UQ | ISO Calendar DATE | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Inclusive SCD Type 2 / mapping start date. |
| 13 | `effective_to` | `DATE` | `NULL` | — | ISO Calendar DATE | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Inclusive SCD Type 2 / mapping end date (`NULL` = currently active). |
| 14 | `is_current` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | `TRUE` for the active SCD Type 2 row of `plant_code` (enforced via partial unique index). |

### `dw.dim_region` (TABLE)
- **Defined in**: [005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)
- **Grain**: One row per verified geographic/distribution region (National LK, 9 ISO provinces, 4 CEB distribution regions = 14 rows).
- **Supported Business Functionality / Questions**: Supports national and verified provincial/distribution-region rollups without unverified locations.
- **Check Constraints**: `ck_dim_region_level`: `CHECK (((region_level)::text = ANY ((ARRAY['NATIONAL'::character varying, 'PROVINCE'::character varying, 'DISTRICT'::character varying, 'CEB_DISTRIBUTION_REGION'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `region_key` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Surrogate dimension key for `dw.dim_region`. |
| 2 | `region_code` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Verified region identifier (`LK`, `LK-1`..`LK-9`, `CEB_R1`..`CEB_R4`). |
| 3 | `region_name` | `VARCHAR(100)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Official administrative province, national, or CEB distribution region name. |
| 4 | `region_level` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Hierarchy level (`NATIONAL`, `PROVINCE`, `DISTRICT`, `CEB_DISTRIBUTION_REGION`). |
| 5 | `iso_code` | `VARCHAR(16)` | `NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | ISO 3166-1 / ISO 3166-2:LK code where applicable (`NULL` for CEB operational distribution regions). |
| 6 | `parent_region_key` | `INTEGER` | `NULL` | FK -> `dw.dim_region(region_key)` | Identifier (surrogate/key) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Self-referencing foreign key to parent region (`LK` national root has `NULL`). |
| 7 | `source_standard` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Authoritative standard defining this region (`ISO 3166-2:LK` or `CEB Distribution Division Structure`). |

### `dw.dim_source_system` (TABLE)
- **Defined in**: [005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)
- **Grain**: One row per upstream source system in the dimensional layer (CEB, PUCSL, NASA_POWER).
- **Supported Business Functionality / Questions**: Slices warehouse facts by regulatory vs utility vs satellite meteorological provider.
- **Check Constraints**: `ck_dim_source_system_cat`: `CHECK (((source_category)::text = ANY ((ARRAY['UTILITY_STATISTICAL'::character varying, 'REGULATORY_OPERATIONAL'::character varying, 'SATELLITE_METEOROLOGICAL'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `source_system_key` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Surrogate dimension key for `dw.dim_source_system`. |
| 2 | `source_code` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 3 | `source_name` | `VARCHAR(128)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Descriptive dataset/system title of the upstream provider. |
| 4 | `organization_name` | `VARCHAR(160)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Official legal name of the publishing institution. |
| 5 | `source_category` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Domain classification (`UTILITY_STATISTICAL`, `REGULATORY_OPERATIONAL`, `SATELLITE_METEOROLOGICAL`). |
| 6 | `official_portal_url` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Official publication portal or API documentation URL. |
| 7 | `default_time_zone` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Default IANA timezone identifier for timestamps reported by this source. |
| 8 | `typical_granularity` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | Primary reporting cadence published by this source. |
| 9 | `is_active` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Conformed Reference Seed (`scripts/seed_reference.py`) & Verified Source Metadata | `TRUE` when this record/rule is active for current ETL runs. |

### `dw.dim_weather_location` (TABLE)
- **Defined in**: [005_dimensions.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/005_dimensions.sql)
- **Grain**: One row per verified Sri Lanka meteorological grid sampling point bounded to island coordinates (6 seeded energy zones).
- **Supported Business Functionality / Questions**: Links hydro catchments (Victoria, Laxapana), wind corridors (Mannar, Puttalam), solar hubs (Hambantota), and Colombo load center to NASA POWER weather.
- **Check Constraints**: `ck_dim_weather_location_lat`: `CHECK (((latitude_deg >= 5.80000) AND (latitude_deg <= 10.00000)))`; `ck_dim_weather_location_lon`: `CHECK (((longitude_deg >= 79.40000) AND (longitude_deg <= 82.00000)))`; `ck_dim_weather_location_res`: `CHECK ((spatial_resolution_deg > (0)::numeric))`; `ck_dim_weather_location_zone`: `CHECK (((energy_zone_type)::text = ANY ((ARRAY['HYDRO_CATCHMENT'::character varying, 'WIND_CORRIDOR'::character varying, 'SOLAR_HUB'::character varying, 'THERMAL_HUB'::character varying, 'LOAD_CENTER'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `weather_location_key` | `INTEGER` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | NASA POWER Grid Coordinates + CEB Hydro/Renewable Zone Definitions | Surrogate dimension key for `dw.dim_weather_location`. |
| 2 | `location_code` | `VARCHAR(48)` | `NOT NULL` | UQ | N/A (categorical/text) | NASA POWER Grid Coordinates + CEB Hydro/Renewable Zone Definitions | Canonical sampling point code (e.g. `LK_CASTLEREAGH_HYDRO`, `LK_MANNAR_WIND`). |
| 3 | `location_name` | `VARCHAR(128)` | `NOT NULL` | — | N/A (categorical/text) | NASA POWER Grid Coordinates + CEB Hydro/Renewable Zone Definitions | Descriptive name of the Sri Lanka meteorological sampling location. |
| 4 | `energy_zone_type` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | NASA POWER Grid Coordinates + CEB Hydro/Renewable Zone Definitions | Grid relevance of the weather location (`HYDRO_CATCHMENT`, `WIND_CORRIDOR`, `SOLAR_HUB`, `THERMAL_HUB`, `LOAD_CENTER`). |
| 5 | `region_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_region(region_key)` | Identifier (surrogate/key) | NASA POWER Grid Coordinates + CEB Hydro/Renewable Zone Definitions | Surrogate dimension key for `dw.dim_region`. |
| 6 | `latitude_deg` | `NUMERIC(8, 5)` | `NOT NULL` | — | degrees North (WGS84) | NASA POWER Grid Coordinates + CEB Hydro/Renewable Zone Definitions | Verified WGS84 latitude within Sri Lanka (`5.80`–`10.00` °N; `NULL` for national aggregate buckets). |
| 7 | `longitude_deg` | `NUMERIC(8, 5)` | `NOT NULL` | — | degrees East (WGS84) | NASA POWER Grid Coordinates + CEB Hydro/Renewable Zone Definitions | Verified WGS84 longitude within Sri Lanka (`79.40`–`82.00` °E; `NULL` for national aggregate buckets). |
| 8 | `elevation_m` | `NUMERIC(7, 2)` | `NULL` | — | meters above sea level (m) | NASA POWER Grid Coordinates + CEB Hydro/Renewable Zone Definitions | Site elevation above mean sea level in meters. |
| 9 | `spatial_resolution_deg` | `NUMERIC(5, 3)` | `NOT NULL` | — | degrees grid resolution | NASA POWER Grid Coordinates + CEB Hydro/Renewable Zone Definitions | NASA POWER grid cell spatial resolution in degrees (default `0.500`). |
| 10 | `source_provider` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | NASA POWER Grid Coordinates + CEB Hydro/Renewable Zone Definitions | Meteorological data provider (`NASA_POWER`). |

### `dw.fact_capacity_period` (TABLE)
- **Defined in**: [007_facts_capacity_and_sales.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/007_facts_capacity_and_sales.sql)
- **Grain**: One installed/dependable capacity record per plant/category, metric, effective reporting period, source system, and dataset revision (semi-additive).
- **Supported Business Functionality / Questions**: Answers: Installed vs dependable capacity evolution (MW) over time; renewable capacity additions; verified plant capacity factors ONLY when joined on matching reporting periods and boundaries.
- **Check Constraints**: `ck_fact_capacity_dates`: `CHECK ((effective_end_date_key >= effective_start_date_key))`; `ck_fact_capacity_dependable_le_installed`: `CHECK (((installed_capacity_mw IS NULL) OR (dependable_capacity_mw IS NULL) OR (dependable_capacity_mw <= installed_capacity_mw)))`; `ck_fact_capacity_nonneg`: `CHECK ((((installed_capacity_mw IS NULL) OR (installed_capacity_mw >= (0)::numeric)) AND ((dependable_capacity_mw IS NULL) OR (dependable_capacity_mw >= (0)::numeric)) AND ((unit_count IS NULL) OR (unit_count >= 0))))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `capacity_fact_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Surrogate primary key for `dw.fact_capacity_period`. |
| 2 | `plant_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_power_plant(plant_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Surrogate SCD Type 2 primary/foreign key for `dw.dim_power_plant`. |
| 3 | `energy_source_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_energy_source(energy_source_key)` | Identifier (surrogate/key) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Surrogate dimension key for `dw.dim_energy_source`. |
| 4 | `metric_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_metric(metric_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Surrogate dimension key for `dw.dim_metric`. |
| 5 | `source_system_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_source_system(source_system_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Surrogate dimension key for `dw.dim_source_system`. |
| 6 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.reporting_period_type(period_type_code)`, UQ | N/A (categorical/text) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 7 | `effective_start_date_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_date(date_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Start date key (`YYYYMMDD`) of the period for which this capacity rating applies. |
| 8 | `effective_end_date_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_date(date_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | End date key (`YYYYMMDD`) of the period for which this capacity rating applies. |
| 9 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 10 | `installed_capacity_mw` | `NUMERIC(12, 4)` | `NULL` | — | MW (Megawatts, nameplate capacity) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Rated nameplate generating capacity in `MW` (semi-additive: never sum across time). |
| 11 | `dependable_capacity_mw` | `NUMERIC(12, 4)` | `NULL` | — | MW (Megawatts, effective/dependable capacity) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Effective/dependable capacity in `MW` (`<= installed_capacity_mw` enforced by CHECK constraint). |
| 12 | `unit_count` | `SMALLINT` | `NULL` | — | count (generating units) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Number of generating units commissioned at the station during the period. |
| 13 | `reported_source_value` | `NUMERIC(14, 4)` | `NULL` | — | source unit (reported_unit_code) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Exact numeric value before unit conversion (e.g. original `GWh` figure in CEB Digest). |
| 14 | `reported_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | CEB Statistical Digest Plant Capacity Tables & PUCSL Plant Lists via `staging.stg_plant_capacity` | Original unit of measure printed in the source document. |
| 15 | `is_current_revision` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | `TRUE` for the latest active source publication revision of this natural grain; superseded revisions are marked `FALSE` to prevent double-counting. |
| 16 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 17 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 18 | `etl_run_id` | `BIGINT` | `NOT NULL` | FK -> `audit.etl_run(etl_run_id)` | Identifier (surrogate/key) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Surrogate key identifying the exact ETL execution run in `audit.etl_run`. |
| 19 | `loaded_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Timezone-aware timestamp when the fact row was promoted into `dw`. |

### `dw.fact_dispatch_interval` (PARTITIONED TABLE)
- **Defined in**: [006_facts_generation_and_dispatch.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/006_facts_generation_and_dispatch.sql)
- **Grain**: One verified sub-daily dispatch/demand observation per reporting entity, date, interval slot, metric, source system, and dataset revision (range-partitioned by date_key).
- **Supported Business Functionality / Questions**: Answers: What is the 15-minute intraday dispatch curve by plant/fuel? How does evening peak (18:30-22:30) compare to daytime solar trough? What is integrated MWh from 15-min MW?
- **Check Constraints**: `ck_fact_dispatch_derived_energy_physics`: `CHECK (((is_energy_derived = false) OR (active_power_mw IS NULL) OR (derived_energy_mwh IS NULL) OR (abs((derived_energy_mwh - (active_power_mw * ((interval_duration_minutes)::numeric / 60.0)))) <= 0.01)))`; `ck_fact_dispatch_duration`: `CHECK ((interval_duration_minutes = ANY (ARRAY[15, 30, 60])))`; `ck_fact_dispatch_missing_is_null`: `CHECK ((((value_status)::text <> 'MISSING'::text) OR ((active_power_mw IS NULL) AND (derived_energy_mwh IS NULL))))`; `ck_fact_dispatch_power_nonneg`: `CHECK ((((value_status)::text = 'PUMPING_LOAD'::text) OR (((active_power_mw IS NULL) OR (active_power_mw >= (0)::numeric)) AND ((derived_energy_mwh IS NULL) OR (derived_energy_mwh >= (0)::numeric)))))`; `ck_fact_dispatch_value_status`: `CHECK (((value_status)::text = ANY ((ARRAY['REPORTED'::character varying, 'ESTIMATED'::character varying, 'DERIVED'::character varying, 'MISSING'::character varying, 'PUMPING_LOAD'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `dispatch_fact_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Surrogate identity column (composite PK `(dispatch_fact_id, date_key)` required by PostgreSQL range partitioning). |
| 2 | `date_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_date(date_key)`, PK, UQ | YYYYMMDD integer key | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Smart integer calendar key in `YYYYMMDD` format (e.g. `20240115`). |
| 3 | `interval_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_interval(interval_key)`, UQ | surrogate slot key | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Surrogate key for sub-daily slot (`1`–`96` for 15-min slots; `101`–`124` for hourly slots). |
| 4 | `plant_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_power_plant(plant_key)`, UQ | Identifier (surrogate/key) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Surrogate SCD Type 2 primary/foreign key for `dw.dim_power_plant`. |
| 5 | `energy_source_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_energy_source(energy_source_key)` | Identifier (surrogate/key) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Surrogate dimension key for `dw.dim_energy_source`. |
| 6 | `metric_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_metric(metric_key)`, UQ | Identifier (surrogate/key) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Surrogate dimension key for `dw.dim_metric`. |
| 7 | `source_system_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_source_system(source_system_key)`, UQ | Identifier (surrogate/key) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Surrogate dimension key for `dw.dim_source_system`. |
| 8 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 9 | `original_timestamp` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Timezone-aware observation timestamp preserved in `Asia/Colombo` (`UTC+05:30`). |
| 10 | `time_standard` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Documented time standard of the observation (`Asia/Colombo (UTC+05:30)` or `LST / UTC+05:30`). |
| 11 | `interval_duration_minutes` | `SMALLINT` | `NOT NULL` | — | minutes (15, 30, or 60) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Exact dispatch interval duration in minutes (`15`, `30`, or `60`). |
| 12 | `active_power_mw` | `NUMERIC(12, 4)` | `NULL` | — | MW (Megawatts, instantaneous/average active power) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Instantaneous/interval-average active power in `MW` (`NULL` when missing; `0` = verified zero output/outage). |
| 13 | `derived_energy_mwh` | `NUMERIC(12, 4)` | `NULL` | — | MWh (Megawatt-hours, integrated energy) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Integrated interval energy in `MWh` (`active_power_mw * duration / 60`), populated only when reported or physics-verified. |
| 14 | `is_energy_derived` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | `TRUE` when `derived_energy_mwh` was computed from `active_power_mw` rather than directly printed in the source. |
| 15 | `reported_value` | `NUMERIC(14, 4)` | `NULL` | — | source unit (reported_unit_code) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Unconverted numeric measurement in `reported_unit_code`. |
| 16 | `reported_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Original unit of measure printed in the source document. |
| 17 | `value_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | PUCSL / CEB System Control 15-min & Hourly Dispatch Reports via `staging.stg_dispatch_observation` | Observation status (`REPORTED`, `ESTIMATED`, `DERIVED`, `MISSING`, `PUMPING_LOAD`). |
| 18 | `is_current_revision` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | `TRUE` for the latest active source publication revision of this natural grain; superseded revisions are marked `FALSE` to prevent double-counting. |
| 19 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 20 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 21 | `etl_run_id` | `BIGINT` | `NOT NULL` | FK -> `audit.etl_run(etl_run_id)` | Identifier (surrogate/key) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Surrogate key identifying the exact ETL execution run in `audit.etl_run`. |
| 22 | `loaded_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Timezone-aware timestamp when the fact row was promoted into `dw`. |

### `dw.fact_electricity_sales` (TABLE)
- **Defined in**: [007_facts_capacity_and_sales.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/007_facts_capacity_and_sales.sql)
- **Grain**: One billed electricity sales/consumption record per region, tariff sector, metric, reporting period, source system, and dataset revision.
- **Supported Business Functionality / Questions**: Answers: Sectoral electricity consumption shares (MWh), consumer account growth, tariff revenue (LKR), and average consumption per account.
- **Check Constraints**: `ck_fact_sales_dates`: `CHECK ((period_end_date_key >= period_start_date_key))`; `ck_fact_sales_missing_null`: `CHECK ((((value_nature)::text <> 'MISSING'::text) OR (energy_sold_mwh IS NULL)))`; `ck_fact_sales_nature`: `CHECK (((value_nature)::text = ANY ((ARRAY['REPORTED'::character varying, 'ESTIMATED'::character varying, 'PROVISIONAL'::character varying, 'AUDITED_FINAL'::character varying, 'MISSING'::character varying])::text[])))`; `ck_fact_sales_nonneg`: `CHECK ((((energy_sold_mwh IS NULL) OR (energy_sold_mwh >= (0)::numeric)) AND ((consumer_account_count IS NULL) OR (consumer_account_count >= 0)) AND ((revenue_lkr IS NULL) OR (revenue_lkr >= (0)::numeric))))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `sales_fact_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Surrogate primary key for `dw.fact_electricity_sales`. |
| 2 | `region_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_region(region_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Surrogate dimension key for `dw.dim_region`. |
| 3 | `sector_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_consumption_sector(sector_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Surrogate dimension key for `dw.dim_consumption_sector`. |
| 4 | `metric_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_metric(metric_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Surrogate dimension key for `dw.dim_metric`. |
| 5 | `source_system_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_source_system(source_system_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Surrogate dimension key for `dw.dim_source_system`. |
| 6 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.reporting_period_type(period_type_code)`, UQ | N/A (categorical/text) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 7 | `period_start_date_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_date(date_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Inclusive start date key (`YYYYMMDD`) referencing `dw.dim_date`. |
| 8 | `period_end_date_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_date(date_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Inclusive end date key (`YYYYMMDD`) referencing `dw.dim_date`. |
| 9 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 10 | `energy_sold_mwh` | `NUMERIC(14, 4)` | `NULL` | — | MWh (Megawatt-hours) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Billed electricity consumption/sales in `MWh` (`NULL` if missing; distinct from gross generation due to T&D losses). |
| 11 | `consumer_account_count` | `BIGINT` | `NULL` | — | count (consumer accounts) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Active billed consumer accounts at period end (`NULL` when not reported). |
| 12 | `revenue_lkr` | `NUMERIC(18, 2)` | `NULL` | — | LKR (Sri Lankan Rupees) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Billed electricity tariff revenue in `LKR` (`NULL` when not published in source table). |
| 13 | `reported_energy_value` | `NUMERIC(16, 4)` | `NULL` | — | source unit (reported_energy_unit_code) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Original unconverted billed energy figure (e.g. `GWh` in CEB Digest). |
| 14 | `reported_energy_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Original unit code of `reported_energy_value`. |
| 15 | `value_nature` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | CEB Statistical Digest Sales/Tariff Tables & PUCSL Reports via `staging.stg_electricity_sales` | Epistemic status of the quantity (`REPORTED`, `ESTIMATED`, `DERIVED`, `AUDITED_FINAL`, `PROVISIONAL`, `REVISED`, `MISSING`). |
| 16 | `is_current_revision` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | `TRUE` for the latest active source publication revision of this natural grain; superseded revisions are marked `FALSE` to prevent double-counting. |
| 17 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 18 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 19 | `etl_run_id` | `BIGINT` | `NOT NULL` | FK -> `audit.etl_run(etl_run_id)` | Identifier (surrogate/key) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Surrogate key identifying the exact ETL execution run in `audit.etl_run`. |
| 20 | `loaded_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Timezone-aware timestamp when the fact row was promoted into `dw`. |

### `dw.fact_generation_period` (TABLE)
- **Defined in**: [006_facts_generation_and_dispatch.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/006_facts_generation_and_dispatch.sql)
- **Grain**: One periodic electricity generation measurement per plant/category, metric, explicit period_type_code (DAILY/MONTHLY/ANNUAL), start/end dates, source system, and dataset revision.
- **Supported Business Functionality / Questions**: Answers: Monthly/annual generation mix (MWh) by fuel and plant; hydro vs thermal seasonal shifts across monsoon seasons; year-over-year generation growth without conflating daily and annual rows.
- **Check Constraints**: `ck_fact_gen_period_boundary`: `CHECK (((generation_boundary)::text = ANY ((ARRAY['GROSS'::character varying, 'NET'::character varying, 'AUXILIARY'::character varying])::text[])))`; `ck_fact_gen_period_daily_exact`: `CHECK ((((period_type_code)::text <> 'DAILY'::text) OR (period_start_date_key = period_end_date_key)))`; `ck_fact_gen_period_date_order`: `CHECK ((period_end_date_key >= period_start_date_key))`; `ck_fact_gen_period_missing_null`: `CHECK ((((value_nature)::text <> 'MISSING'::text) OR (generation_mwh IS NULL)))`; `ck_fact_gen_period_nature`: `CHECK (((value_nature)::text = ANY ((ARRAY['REPORTED'::character varying, 'ESTIMATED'::character varying, 'PROVISIONAL'::character varying, 'AUDITED_FINAL'::character varying, 'MISSING'::character varying])::text[])))`; `ck_fact_gen_period_non_negative`: `CHECK (((((generation_boundary)::text = 'AUXILIARY'::text) OR (generation_mwh IS NULL) OR (generation_mwh >= (0)::numeric)) AND ((peak_generation_mw IS NULL) OR (peak_generation_mw >= (0)::numeric))))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `generation_fact_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Surrogate primary key for `dw.fact_generation_period`. |
| 2 | `plant_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_power_plant(plant_key)`, UQ | Identifier (surrogate/key) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Surrogate SCD Type 2 primary/foreign key for `dw.dim_power_plant`. |
| 3 | `energy_source_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_energy_source(energy_source_key)` | Identifier (surrogate/key) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Surrogate dimension key for `dw.dim_energy_source`. |
| 4 | `metric_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_metric(metric_key)`, UQ | Identifier (surrogate/key) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Surrogate dimension key for `dw.dim_metric`. |
| 5 | `source_system_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_source_system(source_system_key)`, UQ | Identifier (surrogate/key) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Surrogate dimension key for `dw.dim_source_system`. |
| 6 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.reporting_period_type(period_type_code)`, UQ | N/A (categorical/text) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 7 | `period_start_date_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_date(date_key)`, UQ | Identifier (surrogate/key) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Inclusive start date key (`YYYYMMDD`) referencing `dw.dim_date`. |
| 8 | `period_end_date_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_date(date_key)`, UQ | Identifier (surrogate/key) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Inclusive end date key (`YYYYMMDD`) referencing `dw.dim_date`. |
| 9 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 10 | `generation_mwh` | `NUMERIC(14, 4)` | `NULL` | — | MWh (Megawatt-hours) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Normalized electrical energy generated during the period in `MWh` (`NULL` if missing; never mixed across period types). |
| 11 | `peak_generation_mw` | `NUMERIC(12, 4)` | `NULL` | — | MW (Megawatts) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Optional peak active power (`MW`) recorded during the period (never summed with `generation_mwh`). |
| 12 | `reported_source_value` | `NUMERIC(16, 4)` | `NULL` | — | source unit (reported_unit_code) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Exact numeric value before unit conversion (e.g. original `GWh` figure in CEB Digest). |
| 13 | `reported_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Original unit of measure printed in the source document. |
| 14 | `generation_boundary` | `VARCHAR(16)` | `NOT NULL` | — | N/A (categorical/text) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Electrical measurement boundary (`GROSS` at generator terminals, `NET` sent out to grid, `AUXILIARY`, or `NOT_APPLICABLE`). |
| 15 | `value_nature` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | PUCSL Daily/Monthly Generation Reports & CEB Statistical Digests via `staging.stg_generation_report` | Epistemic status of the quantity (`REPORTED`, `ESTIMATED`, `DERIVED`, `AUDITED_FINAL`, `PROVISIONAL`, `REVISED`, `MISSING`). |
| 16 | `is_current_revision` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | `TRUE` for the latest active source publication revision of this natural grain; superseded revisions are marked `FALSE` to prevent double-counting. |
| 17 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 18 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 19 | `etl_run_id` | `BIGINT` | `NOT NULL` | FK -> `audit.etl_run(etl_run_id)` | Identifier (surrogate/key) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Surrogate key identifying the exact ETL execution run in `audit.etl_run`. |
| 20 | `loaded_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Timezone-aware timestamp when the fact row was promoted into `dw`. |

### `dw.fact_published_metric` (TABLE)
- **Defined in**: [008_facts_weather_and_published.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/008_facts_weather_and_published.sql)
- **Grain**: One officially published aggregate headline statistic per metric, period, optional scope (region/energy source/sector), source system, and dataset revision.
- **Supported Business Functionality / Questions**: Answers: Official historical system peak demand (MW), transmission/distribution loss %, annual CEB vs PUCSL headline totals, and revision history — strictly isolated from bottom-up plant sums.
- **Check Constraints**: `ck_fact_pub_dates`: `CHECK ((period_end_date_key >= period_start_date_key))`; `ck_fact_pub_nature`: `CHECK (((value_nature)::text = ANY ((ARRAY['REPORTED'::character varying, 'ESTIMATED'::character varying, 'PROVISIONAL'::character varying, 'AUDITED_FINAL'::character varying, 'REVISED'::character varying, 'MISSING'::character varying])::text[])))`; `ck_fact_pub_standalone_guard`: `CHECK ((is_standalone_published_aggregate = true))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `published_fact_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Surrogate primary key for `dw.fact_published_metric`. |
| 2 | `metric_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_metric(metric_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Surrogate dimension key for `dw.dim_metric`. |
| 3 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.reporting_period_type(period_type_code)`, UQ | N/A (categorical/text) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 4 | `period_start_date_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_date(date_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Inclusive start date key (`YYYYMMDD`) referencing `dw.dim_date`. |
| 5 | `period_end_date_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_date(date_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Inclusive end date key (`YYYYMMDD`) referencing `dw.dim_date`. |
| 6 | `region_key` | `INTEGER` | `NULL` | FK -> `dw.dim_region(region_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Surrogate dimension key for `dw.dim_region`. |
| 7 | `energy_source_key` | `INTEGER` | `NULL` | FK -> `dw.dim_energy_source(energy_source_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Surrogate dimension key for `dw.dim_energy_source`. |
| 8 | `sector_key` | `INTEGER` | `NULL` | FK -> `dw.dim_consumption_sector(sector_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Surrogate dimension key for `dw.dim_consumption_sector`. |
| 9 | `source_system_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_source_system(source_system_key)`, UQ | Identifier (surrogate/key) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Surrogate dimension key for `dw.dim_source_system`. |
| 10 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 11 | `standardized_value` | `NUMERIC(18, 4)` | `NULL` | — | canonical unit (standardized_unit_code) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Normalized headline metric value in `standardized_unit_code` (`NULL` when `value_nature = 'MISSING'`). |
| 12 | `standardized_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Canonical warehouse unit code for the published metric. |
| 13 | `published_value` | `NUMERIC(18, 4)` | `NULL` | — | published unit (published_unit_code) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Exact headline aggregate figure printed in the official publication. |
| 14 | `published_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Unit code printed in the official publication. |
| 15 | `value_nature` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Epistemic status of the quantity (`REPORTED`, `ESTIMATED`, `DERIVED`, `AUDITED_FINAL`, `PROVISIONAL`, `REVISED`, `MISSING`). |
| 16 | `publication_table_ref` | `VARCHAR(128)` | `NULL` | — | N/A (categorical/text) | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Source table/page citation (e.g. `CEB Statistical Digest 2023 Table 4.1`). |
| 17 | `is_standalone_published_aggregate` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | CEB Statistical Digests & PUCSL Official Summary Tables via `staging.stg_published_statistic` | Safety guard (`ALWAYS TRUE`) reminding analysts never to sum this table with bottom-up plant/dispatch facts. |
| 18 | `is_current_revision` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | `TRUE` for the latest active source publication revision of this natural grain; superseded revisions are marked `FALSE` to prevent double-counting. |
| 19 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 20 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 21 | `etl_run_id` | `BIGINT` | `NOT NULL` | FK -> `audit.etl_run(etl_run_id)` | Identifier (surrogate/key) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Surrogate key identifying the exact ETL execution run in `audit.etl_run`. |
| 22 | `loaded_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Timezone-aware timestamp when the fact row was promoted into `dw`. |

### `dw.fact_weather_daily` (TABLE)
- **Defined in**: [008_facts_weather_and_published.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/008_facts_weather_and_published.sql)
- **Grain**: One daily meteorological parameter observation per weather sampling location, calendar date, metric, source system, and dataset revision.
- **Supported Business Functionality / Questions**: Answers: How does catchment rainfall (mm/day) drive hydro output? How does Mannar/Puttalam wind speed (m/s) or Hambantota GHI (kWh/m2/day) correlate with renewable generation?
- **Check Constraints**: `ck_fact_weather_missing_null`: `CHECK ((((is_missing = true) AND (standardized_value IS NULL)) OR (is_missing = false)))`; `ck_fact_weather_physical_bounds`: `CHECK (((standardized_value IS NULL) OR ((((source_variable_name)::text = ANY ((ARRAY['ALLSKY_SFC_SW_DWN'::character varying, 'CLRSKY_SFC_SW_DWN'::character varying, 'PRECTOTCORR'::character varying, 'WS10M'::character varying, 'WS50M'::character varying])::text[])) AND (standardized_value >= (0)::numeric)) OR (((source_variable_name)::text = 'RH2M'::text) AND ((standardized_value >= (0)::numeric) AND (standardized_value <= (100)::numeric))) OR (((source_variable_name)::text ~~ 'T2M%'::text) AND ((standardized_value >= ('-20'::integer)::numeric) AND (standardized_value <= (60)::numeric))) OR (((source_variable_name)::text <> ALL ((ARRAY['ALLSKY_SFC_SW_DWN'::character varying, 'CLRSKY_SFC_SW_DWN'::character varying, 'PRECTOTCORR'::character varying, 'WS10M'::character varying, 'WS50M'::character varying, 'RH2M'::character varying])::text[])) AND ((source_variable_name)::text !~~ 'T2M%'::text)))))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `weather_fact_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Surrogate primary key for `dw.fact_weather_daily`. |
| 2 | `date_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_date(date_key)`, UQ | YYYYMMDD integer key | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Smart integer calendar key in `YYYYMMDD` format (e.g. `20240115`). |
| 3 | `weather_location_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_weather_location(weather_location_key)`, UQ | Identifier (surrogate/key) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Surrogate dimension key for `dw.dim_weather_location`. |
| 4 | `metric_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_metric(metric_key)`, UQ | Identifier (surrogate/key) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Surrogate dimension key for `dw.dim_metric`. |
| 5 | `source_system_key` | `INTEGER` | `NOT NULL` | FK -> `dw.dim_source_system(source_system_key)`, UQ | Identifier (surrogate/key) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Surrogate dimension key for `dw.dim_source_system`. |
| 6 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | UQ | N/A (categorical/text) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 7 | `source_variable_name` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Exact NASA POWER parameter identifier (`ALLSKY_SFC_SW_DWN`, `PRECTOTCORR`, `T2M`, `WS10M`, `WS50M`, `RH2M`). |
| 8 | `standardized_value` | `NUMERIC(14, 5)` | `NULL` | — | canonical unit (standardized_unit_code) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Validated meteorological measurement in `standardized_unit_code` (`NULL` when `is_missing = TRUE`). |
| 9 | `standardized_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Canonical warehouse unit code for this weather parameter. |
| 10 | `original_reported_value` | `NUMERIC(14, 5)` | `NULL` | — | original unit (original_unit_code) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Raw numeric value returned by NASA POWER (may contain `-999` sentinel when `is_missing = TRUE`). |
| 11 | `original_unit_code` | `VARCHAR(24)` | `NOT NULL` | FK -> `ref.unit(unit_code)` | N/A (categorical/text) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Unit code returned by the upstream meteorological dataset. |
| 12 | `missing_value_code` | `VARCHAR(32)` | `NULL` | — | N/A (categorical/text) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Source missing-value sentinel detected (e.g. `'-999'` or `'NA'`). |
| 13 | `is_missing` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | `TRUE` when the source reported a missing sentinel; enforces `standardized_value IS NULL`. |
| 14 | `time_standard` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | NASA POWER Daily Agroclimatology/Renewable Energy API via `staging.stg_weather_observation` | Documented time standard of the observation (`Asia/Colombo (UTC+05:30)` or `LST / UTC+05:30`). |
| 15 | `is_current_revision` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | `TRUE` for the latest active source publication revision of this natural grain; superseded revisions are marked `FALSE` to prevent double-counting. |
| 16 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 17 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 18 | `etl_run_id` | `BIGINT` | `NOT NULL` | FK -> `audit.etl_run(etl_run_id)` | Identifier (surrogate/key) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Surrogate key identifying the exact ETL execution run in `audit.etl_run`. |
| 19 | `loaded_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | ETL Runtime (`etl` procedures / `src/etl/batch_loader.py`) | Timezone-aware timestamp when the fact row was promoted into `dw`. |

## Schema: `staging`

### `staging.stg_dispatch_observation` (TABLE)
- **Defined in**: [009_staging_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql)
- **Grain**: One staged sub-daily dispatch record extracted from a raw batch prior to validation/promotion.
- **Supported Business Functionality / Questions**: Holds raw text and parsed MW/timestamp values for dispatch observations, retaining quarantined rows with validation notes.
- **Check Constraints**: `ck_stg_dispatch_status`: `CHECK (((validation_status)::text = ANY ((ARRAY['pending'::character varying, 'valid'::character varying, 'quarantined'::character varying, 'loaded'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `stg_dispatch_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Surrogate primary key of staging table `stg_dispatch_observation`. |
| 2 | `batch_id` | `BIGINT` | `NOT NULL` | FK -> `raw.ingestion_batch(batch_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key identifying the raw ingestion/extraction batch. |
| 3 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 4 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 5 | `source_code` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 6 | `raw_entity_name` | `VARCHAR(160)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `entity_name` preserved prior to type conversion. |
| 7 | `raw_timestamp_text` | `VARCHAR(64)` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `timestamp_text` preserved prior to type conversion. |
| 8 | `parsed_timestamp` | `TIMESTAMPTZ` | `NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `timestamp` (`NULL` on parse failure or missing). |
| 9 | `interval_duration_minutes` | `SMALLINT` | `NOT NULL` | — | minutes (15, 30, or 60) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Exact dispatch interval duration in minutes (`15`, `30`, or `60`). |
| 10 | `raw_power_text` | `VARCHAR(64)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `power_text` preserved prior to type conversion. |
| 11 | `parsed_power_mw` | `NUMERIC(12, 4)` | `NULL` | — | MW (Megawatts) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `power_mw` (`NULL` on parse failure or missing). |
| 12 | `reported_unit_code` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Original unit of measure printed in the source document. |
| 13 | `metric_code` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Canonical metric identifier (e.g. `PLANT_DISPATCH_MW`, `GEN_ENERGY_MWH`, `SALES_ENERGY_MWH`, `SOLAR_GHI_KWH_M2_DAY`). |
| 14 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 15 | `validation_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Staging lifecycle state (`pending`, `valid`, `quarantined`, `loaded`). |
| 16 | `validation_notes` | `TEXT` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Diagnostic message recorded by `etl.sp_validate_*` when a row is quarantined. |
| 17 | `staged_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Timestamp when the row was inserted into staging. |

### `staging.stg_electricity_sales` (TABLE)
- **Defined in**: [009_staging_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql)
- **Grain**: One staged electricity sales/consumption record extracted from CEB/PUCSL tables.
- **Supported Business Functionality / Questions**: Holds raw sector/region labels, energy sold, consumer counts, and revenue prior to warehouse promotion.
- **Check Constraints**: `ck_stg_sales_status`: `CHECK (((validation_status)::text = ANY ((ARRAY['pending'::character varying, 'valid'::character varying, 'quarantined'::character varying, 'loaded'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `stg_sales_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Surrogate primary key of staging table `stg_electricity_sales`. |
| 2 | `batch_id` | `BIGINT` | `NOT NULL` | FK -> `raw.ingestion_batch(batch_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key identifying the raw ingestion/extraction batch. |
| 3 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 4 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 5 | `source_code` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 6 | `raw_region_name` | `VARCHAR(128)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `region_name` preserved prior to type conversion. |
| 7 | `raw_sector_name` | `VARCHAR(128)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `sector_name` preserved prior to type conversion. |
| 8 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 9 | `period_start_date` | `DATE` | `NULL` | — | ISO Calendar DATE | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Inclusive start date of the reporting period. |
| 10 | `period_end_date` | `DATE` | `NULL` | — | ISO Calendar DATE | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Inclusive end date of the reporting period. |
| 11 | `raw_energy_sold_text` | `VARCHAR(64)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `energy_sold_text` preserved prior to type conversion. |
| 12 | `parsed_energy_sold` | `NUMERIC(16, 4)` | `NULL` | — | source unit (reported_unit_code) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `energy_sold` (`NULL` on parse failure or missing). |
| 13 | `reported_unit_code` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Original unit of measure printed in the source document. |
| 14 | `parsed_consumer_count` | `BIGINT` | `NULL` | — | count (consumer accounts) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `consumer_count` (`NULL` on parse failure or missing). |
| 15 | `parsed_revenue_lkr` | `NUMERIC(18, 2)` | `NULL` | — | LKR (Sri Lankan Rupees) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `revenue_lkr` (`NULL` on parse failure or missing). |
| 16 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 17 | `validation_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Staging lifecycle state (`pending`, `valid`, `quarantined`, `loaded`). |
| 18 | `validation_notes` | `TEXT` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Diagnostic message recorded by `etl.sp_validate_*` when a row is quarantined. |
| 19 | `staged_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Timestamp when the row was inserted into staging. |

### `staging.stg_generation_report` (TABLE)
- **Defined in**: [009_staging_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql)
- **Grain**: One staged periodic generation record extracted from PUCSL or CEB reports.
- **Supported Business Functionality / Questions**: Holds raw plant/category labels, period dates, and reported energy values (MWh/GWh) before alias resolution and unit normalization.
- **Check Constraints**: `ck_stg_gen_status`: `CHECK (((validation_status)::text = ANY ((ARRAY['pending'::character varying, 'valid'::character varying, 'quarantined'::character varying, 'loaded'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `stg_generation_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Surrogate primary key of staging table `stg_generation_report`. |
| 2 | `batch_id` | `BIGINT` | `NOT NULL` | FK -> `raw.ingestion_batch(batch_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key identifying the raw ingestion/extraction batch. |
| 3 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 4 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 5 | `source_code` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 6 | `raw_plant_name` | `VARCHAR(160)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `plant_name` preserved prior to type conversion. |
| 7 | `raw_energy_category` | `VARCHAR(80)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `energy_category` preserved prior to type conversion. |
| 8 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 9 | `period_start_date` | `DATE` | `NULL` | — | ISO Calendar DATE | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Inclusive start date of the reporting period. |
| 10 | `period_end_date` | `DATE` | `NULL` | — | ISO Calendar DATE | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Inclusive end date of the reporting period. |
| 11 | `raw_generation_text` | `VARCHAR(64)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `generation_text` preserved prior to type conversion. |
| 12 | `parsed_generation_value` | `NUMERIC(16, 4)` | `NULL` | — | source unit (reported_unit_code) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `generation_value` (`NULL` on parse failure or missing). |
| 13 | `raw_peak_mw_text` | `VARCHAR(64)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `peak_mw_text` preserved prior to type conversion. |
| 14 | `parsed_peak_mw` | `NUMERIC(12, 4)` | `NULL` | — | MW (Megawatts) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `peak_mw` (`NULL` on parse failure or missing). |
| 15 | `reported_unit_code` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Original unit of measure printed in the source document. |
| 16 | `generation_boundary` | `VARCHAR(16)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Electrical measurement boundary (`GROSS` at generator terminals, `NET` sent out to grid, `AUXILIARY`, or `NOT_APPLICABLE`). |
| 17 | `value_nature` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Epistemic status of the quantity (`REPORTED`, `ESTIMATED`, `DERIVED`, `AUDITED_FINAL`, `PROVISIONAL`, `REVISED`, `MISSING`). |
| 18 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 19 | `validation_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Staging lifecycle state (`pending`, `valid`, `quarantined`, `loaded`). |
| 20 | `validation_notes` | `TEXT` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Diagnostic message recorded by `etl.sp_validate_*` when a row is quarantined. |
| 21 | `staged_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Timestamp when the row was inserted into staging. |

### `staging.stg_plant_capacity` (TABLE)
- **Defined in**: [009_staging_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql)
- **Grain**: One staged power plant installed/dependable capacity record.
- **Supported Business Functionality / Questions**: Holds raw plant capacity strings and parsed MW/unit counts prior to check-constraint validation.
- **Check Constraints**: `ck_stg_cap_status`: `CHECK (((validation_status)::text = ANY ((ARRAY['pending'::character varying, 'valid'::character varying, 'quarantined'::character varying, 'loaded'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `stg_capacity_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Surrogate primary key of staging table `stg_plant_capacity`. |
| 2 | `batch_id` | `BIGINT` | `NOT NULL` | FK -> `raw.ingestion_batch(batch_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key identifying the raw ingestion/extraction batch. |
| 3 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 4 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 5 | `source_code` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 6 | `raw_plant_name` | `VARCHAR(160)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `plant_name` preserved prior to type conversion. |
| 7 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 8 | `effective_start_date` | `DATE` | `NULL` | — | ISO Calendar DATE | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Inclusive start date of the staged plant capacity rating. |
| 9 | `effective_end_date` | `DATE` | `NULL` | — | ISO Calendar DATE | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Inclusive end date of the staged plant capacity rating. |
| 10 | `raw_installed_mw_text` | `VARCHAR(64)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `installed_mw_text` preserved prior to type conversion. |
| 11 | `parsed_installed_mw` | `NUMERIC(12, 4)` | `NULL` | — | MW (Megawatts) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `installed_mw` (`NULL` on parse failure or missing). |
| 12 | `parsed_dependable_mw` | `NUMERIC(12, 4)` | `NULL` | — | MW (Megawatts) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `dependable_mw` (`NULL` on parse failure or missing). |
| 13 | `parsed_unit_count` | `SMALLINT` | `NULL` | — | count (generating units) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `unit_count` (`NULL` on parse failure or missing). |
| 14 | `reported_unit_code` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Original unit of measure printed in the source document. |
| 15 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 16 | `validation_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Staging lifecycle state (`pending`, `valid`, `quarantined`, `loaded`). |
| 17 | `validation_notes` | `TEXT` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Diagnostic message recorded by `etl.sp_validate_*` when a row is quarantined. |
| 18 | `staged_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Timestamp when the row was inserted into staging. |

### `staging.stg_published_statistic` (TABLE)
- **Defined in**: [009_staging_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql)
- **Grain**: One staged standalone published aggregate statistic from official digests/reports.
- **Supported Business Functionality / Questions**: Stages headline annual/monthly published totals and table references for dw.fact_published_metric and cross-source reconciliation.
- **Check Constraints**: `ck_stg_pub_status`: `CHECK (((validation_status)::text = ANY ((ARRAY['pending'::character varying, 'valid'::character varying, 'quarantined'::character varying, 'loaded'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `stg_published_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Surrogate primary key of staging table `stg_published_statistic`. |
| 2 | `batch_id` | `BIGINT` | `NOT NULL` | FK -> `raw.ingestion_batch(batch_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key identifying the raw ingestion/extraction batch. |
| 3 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 4 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 5 | `source_code` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 6 | `metric_code` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Canonical metric identifier (e.g. `PLANT_DISPATCH_MW`, `GEN_ENERGY_MWH`, `SALES_ENERGY_MWH`, `SOLAR_GHI_KWH_M2_DAY`). |
| 7 | `period_type_code` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Controlled reporting granularity code (`INTERVAL_15MIN`, `HOURLY`, `DAILY`, `MONTHLY`, `QUARTERLY`, `ANNUAL`). |
| 8 | `period_start_date` | `DATE` | `NULL` | — | ISO Calendar DATE | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Inclusive start date of the reporting period. |
| 9 | `period_end_date` | `DATE` | `NULL` | — | ISO Calendar DATE | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Inclusive end date of the reporting period. |
| 10 | `raw_region_code` | `VARCHAR(32)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `region_code` preserved prior to type conversion. |
| 11 | `raw_energy_source_code` | `VARCHAR(32)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `energy_source_code` preserved prior to type conversion. |
| 12 | `raw_sector_code` | `VARCHAR(32)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `sector_code` preserved prior to type conversion. |
| 13 | `raw_published_text` | `VARCHAR(64)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `published_text` preserved prior to type conversion. |
| 14 | `parsed_published_value` | `NUMERIC(18, 4)` | `NULL` | — | published unit (published_unit_code) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `published_value` (`NULL` on parse failure or missing). |
| 15 | `published_unit_code` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unit code printed in the official publication. |
| 16 | `value_nature` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Epistemic status of the quantity (`REPORTED`, `ESTIMATED`, `DERIVED`, `AUDITED_FINAL`, `PROVISIONAL`, `REVISED`, `MISSING`). |
| 17 | `publication_table_ref` | `VARCHAR(128)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Source table/page citation (e.g. `CEB Statistical Digest 2023 Table 4.1`). |
| 18 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 19 | `validation_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Staging lifecycle state (`pending`, `valid`, `quarantined`, `loaded`). |
| 20 | `validation_notes` | `TEXT` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Diagnostic message recorded by `etl.sp_validate_*` when a row is quarantined. |
| 21 | `staged_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Timestamp when the row was inserted into staging. |

### `staging.stg_weather_observation` (TABLE)
- **Defined in**: [009_staging_tables.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/009_staging_tables.sql)
- **Grain**: One staged daily meteorological parameter observation from NASA POWER JSON/CSV extracts.
- **Supported Business Functionality / Questions**: Preserves raw parameter values including NASA missing-value sentinels (-999) before NULL normalization.
- **Check Constraints**: `ck_stg_weather_status`: `CHECK (((validation_status)::text = ANY ((ARRAY['pending'::character varying, 'valid'::character varying, 'quarantined'::character varying, 'loaded'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `stg_weather_id` | `BIGINT` | `NOT NULL` | PK, IDENTITY | Identifier (surrogate/key) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Surrogate primary key of staging table `stg_weather_observation`. |
| 2 | `batch_id` | `BIGINT` | `NOT NULL` | FK -> `raw.ingestion_batch(batch_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key identifying the raw ingestion/extraction batch. |
| 3 | `source_document_id` | `BIGINT` | `NOT NULL` | FK -> `raw.source_document(source_document_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate identifier tracing records to the exact immutable file in `data/raw/`. |
| 4 | `raw_record_id` | `BIGINT` | `NULL` | FK -> `raw.extracted_record(raw_record_id)` | Identifier (surrogate/key) | Raw Provenance Registry (`raw.source_document` / `raw.extracted_record`) | Surrogate key referencing the exact immutable JSONB envelope in `raw.extracted_record`. |
| 5 | `source_code` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Short canonical provider code (`CEB`, `PUCSL`, `NASA_POWER`). |
| 6 | `location_code` | `VARCHAR(48)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Canonical sampling point code (e.g. `LK_CASTLEREAGH_HYDRO`, `LK_MANNAR_WIND`). |
| 7 | `observation_date` | `DATE` | `NULL` | — | ISO Calendar DATE | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Calendar date of the staged meteorological observation. |
| 8 | `source_variable_name` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Exact NASA POWER parameter identifier (`ALLSKY_SFC_SW_DWN`, `PRECTOTCORR`, `T2M`, `WS10M`, `WS50M`, `RH2M`). |
| 9 | `raw_value_text` | `VARCHAR(64)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unparsed source string for `value_text` preserved prior to type conversion. |
| 10 | `parsed_value` | `NUMERIC(14, 5)` | `NULL` | — | original unit (original_unit_code) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Typed value parsed from raw staging input for `value` (`NULL` on parse failure or missing). |
| 11 | `original_unit_code` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Unit code returned by the upstream meteorological dataset. |
| 12 | `missing_value_code` | `VARCHAR(32)` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Source missing-value sentinel detected (e.g. `'-999'` or `'NA'`). |
| 13 | `dataset_revision` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Source publication revision label (`v1`, `provisional`, `audited_2024`, etc.). |
| 14 | `validation_status` | `VARCHAR(24)` | `NOT NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Staging lifecycle state (`pending`, `valid`, `quarantined`, `loaded`). |
| 15 | `validation_notes` | `TEXT` | `NULL` | — | N/A (categorical/text) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Diagnostic message recorded by `etl.sp_validate_*` when a row is quarantined. |
| 16 | `staged_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Source Extraction Parsers (PUCSL PDF/CSV, CEB Digest tables, NASA POWER JSON) | Timestamp when the row was inserted into staging. |

## Schema: `etl`

### `etl.scheduled_job_registry` (TABLE)
- **Defined in**: [017_scheduler_metadata.sql](file:///c:/Fullstack%20development%20course/Data%20Ware%20House%20Project/database/migrations/017_scheduler_metadata.sql)
- **Grain**: One row per declarative scheduled maintenance/refresh job.
- **Supported Business Functionality / Questions**: Documents cron schedule, SQL command, and optional execution mode (manual, external scheduler, or pg_cron) without MySQL CREATE EVENT syntax.
- **Check Constraints**: `ck_etl_sched_mechanism`: `CHECK (((execution_mechanism)::text = ANY ((ARRAY['EXTERNAL_OR_PG_CRON'::character varying, 'MANUAL_ONLY'::character varying, 'PG_CRON'::character varying])::text[])))`

| # | Column | Data Type | Nullability | Keys / Constraints | Unit of Measure | Source Lineage | Description |
|---|---|---|---|---|---|---|---|
| 1 | `job_code` | `VARCHAR(64)` | `NOT NULL` | PK | N/A (categorical/text) | Database Maintenance Metadata (`017_scheduler_metadata.sql`) | Unique identifier for the scheduled maintenance job. |
| 2 | `job_name` | `VARCHAR(128)` | `NOT NULL` | — | N/A (categorical/text) | Database Maintenance Metadata (`017_scheduler_metadata.sql`) | Descriptive title of the scheduled operation. |
| 3 | `cron_schedule` | `VARCHAR(64)` | `NOT NULL` | — | N/A (categorical/text) | Database Maintenance Metadata (`017_scheduler_metadata.sql`) | Standard 5-field cron schedule expression. |
| 4 | `sql_command` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Database Maintenance Metadata (`017_scheduler_metadata.sql`) | Exact PostgreSQL command invoked by the external scheduler or `pg_cron`. |
| 5 | `execution_mechanism` | `VARCHAR(32)` | `NOT NULL` | — | N/A (categorical/text) | Database Maintenance Metadata (`017_scheduler_metadata.sql`) | Permitted scheduler mechanism (`EXTERNAL_OR_PG_CRON`, `MANUAL_ONLY`, `PG_CRON`). |
| 6 | `is_enabled` | `BOOLEAN` | `NOT NULL` | — | Boolean flag | Database Maintenance Metadata (`017_scheduler_metadata.sql`) | `FALSE` by default in Phase 1 so scheduling stays strictly optional. |
| 7 | `last_manual_or_scheduled_run` | `TIMESTAMPTZ` | `NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Database Maintenance Metadata (`017_scheduler_metadata.sql`) | Timestamp of most recent execution. |
| 8 | `description` | `TEXT` | `NOT NULL` | — | N/A (categorical/text) | Database Maintenance Metadata (`017_scheduler_metadata.sql`) | Detailed human-readable explanation of the entity or rule. |
| 9 | `created_at` | `TIMESTAMPTZ` | `NOT NULL` | — | ISO-8601 TIMESTAMPTZ (UTC+05:30) | Database Maintenance Metadata (`017_scheduler_metadata.sql`) | Audit timestamp when the record was initially created. |

