-- =============================================================================
-- Migration: 002_raw_source_registry.sql
-- Purpose  : Create provenance-aware raw source system, document, batch, and
--            extracted record registry tables in the raw schema.
-- Rollback : DROP TABLE IF EXISTS raw.extracted_record, raw.ingestion_batch,
--            raw.source_document, raw.source_system CASCADE;
-- =============================================================================

CREATE TABLE raw.source_system (
    source_system_id INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_raw_source_system PRIMARY KEY,
    source_code VARCHAR(32) NOT NULL
        CONSTRAINT uq_raw_source_system_code UNIQUE,
    source_name VARCHAR(128) NOT NULL,
    organization_name VARCHAR(160) NOT NULL,
    official_url TEXT NOT NULL,
    default_timezone VARCHAR(64) NOT NULL DEFAULT 'Asia/Colombo',
    access_method VARCHAR(32) NOT NULL
        CONSTRAINT ck_raw_source_system_access
        CHECK (access_method IN ('PORTAL_PDF', 'REST_API_JSON', 'PORTAL_XLSX', 'PORTAL_CSV', 'MANUAL_ARCHIVE')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE raw.source_system IS
    'Authoritative registry of upstream electricity and meteorological data providers (CEB, PUCSL, NASA POWER).';

CREATE TABLE raw.source_document (
    source_document_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_raw_source_document PRIMARY KEY,
    source_system_id INTEGER NOT NULL
        CONSTRAINT fk_raw_source_document_system
        REFERENCES raw.source_system (source_system_id),
    document_code VARCHAR(100) NOT NULL
        CONSTRAINT uq_raw_source_document_code UNIQUE,
    source_url TEXT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    local_storage_path TEXT NOT NULL,
    file_format VARCHAR(24) NOT NULL
        CONSTRAINT ck_raw_source_document_format
        CHECK (file_format IN ('PDF', 'XLSX', 'CSV', 'JSON', 'XML', 'HTML')),
    file_size_bytes BIGINT
        CONSTRAINT ck_raw_source_document_size
        CHECK (file_size_bytes IS NULL OR file_size_bytes >= 0),
    sha256_checksum VARCHAR(64) NOT NULL
        CONSTRAINT ck_raw_source_document_checksum_nonempty
        CHECK (LENGTH(BTRIM(sha256_checksum)) >= 16),
    download_timestamp TIMESTAMPTZ,
    publication_date DATE,
    reporting_period_type VARCHAR(24) NOT NULL
        CONSTRAINT ck_raw_source_document_period_type
        CHECK (reporting_period_type IN ('INTERVAL_15MIN', 'HOURLY', 'DAILY', 'MONTHLY', 'QUARTERLY', 'ANNUAL', 'MULTI_YEAR')),
    reporting_period_start DATE NOT NULL,
    reporting_period_end DATE NOT NULL,
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    acquisition_status VARCHAR(32) NOT NULL
        CONSTRAINT ck_raw_source_document_status
        CHECK (acquisition_status IN (
            'CATALOGUED_PENDING_DOWNLOAD',
            'DOWNLOADED_VERIFIED',
            'SYNTHETIC_FIXTURE',
            'QUARANTINED',
            'SUPERSEDED'
        )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_raw_source_document_period_order
        CHECK (reporting_period_end >= reporting_period_start)
);

COMMENT ON TABLE raw.source_document IS
    'Immutable file/document provenance metadata linking filesystem files in data/raw/ to warehouse records via SHA-256.';

CREATE TABLE raw.ingestion_batch (
    batch_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_raw_ingestion_batch PRIMARY KEY,
    batch_code VARCHAR(100) NOT NULL
        CONSTRAINT uq_raw_ingestion_batch_code UNIQUE,
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_raw_ingestion_batch_document
        REFERENCES raw.source_document (source_document_id),
    extraction_method VARCHAR(64) NOT NULL,
    parser_version VARCHAR(32) NOT NULL DEFAULT '0.1.0',
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    batch_status VARCHAR(24) NOT NULL
        CONSTRAINT ck_raw_ingestion_batch_status
        CHECK (batch_status IN ('STARTED', 'EXTRACTED', 'FAILED', 'QUARANTINED')),
    records_extracted INTEGER NOT NULL DEFAULT 0
        CONSTRAINT ck_raw_ingestion_batch_records_nonneg
        CHECK (records_extracted >= 0)
);

COMMENT ON TABLE raw.ingestion_batch IS
    'Execution batch tracking raw parser extraction runs over registered source documents.';

CREATE TABLE raw.extracted_record (
    raw_record_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_raw_extracted_record PRIMARY KEY,
    batch_id BIGINT NOT NULL
        CONSTRAINT fk_raw_extracted_record_batch
        REFERENCES raw.ingestion_batch (batch_id),
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_raw_extracted_record_document
        REFERENCES raw.source_document (source_document_id),
    source_row_locator VARCHAR(128) NOT NULL,
    raw_payload JSONB NOT NULL,
    content_sha256 VARCHAR(64) NOT NULL,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_raw_extracted_record_locator
        UNIQUE (batch_id, source_row_locator)
);

COMMENT ON TABLE raw.extracted_record IS
    'Immutable raw JSONB envelope of every extracted row/cell block with exact page/table/line locator.';
