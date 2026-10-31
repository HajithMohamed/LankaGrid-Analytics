-- =============================================================================
-- Migration: 009_staging_tables.sql
-- Purpose  : Create typed, source-traceable staging tables for all six data
--            streams. Malformed rows remain in staging with quarantine status.
-- Rollback : DROP TABLE IF EXISTS staging.stg_published_statistic,
--            staging.stg_weather_observation, staging.stg_plant_capacity,
--            staging.stg_electricity_sales, staging.stg_generation_report,
--            staging.stg_dispatch_observation CASCADE;
-- =============================================================================

CREATE TABLE staging.stg_dispatch_observation (
    stg_dispatch_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_stg_dispatch_observation PRIMARY KEY,
    batch_id BIGINT NOT NULL
        CONSTRAINT fk_stg_dispatch_batch REFERENCES raw.ingestion_batch (batch_id),
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_stg_dispatch_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_stg_dispatch_raw_record REFERENCES raw.extracted_record (raw_record_id),
    source_code VARCHAR(32) NOT NULL,
    raw_entity_name VARCHAR(160) NOT NULL,
    raw_timestamp_text VARCHAR(64) NOT NULL,
    parsed_timestamp TIMESTAMPTZ,
    interval_duration_minutes SMALLINT NOT NULL DEFAULT 15,
    raw_power_text VARCHAR(64),
    parsed_power_mw NUMERIC(12, 4),
    reported_unit_code VARCHAR(24) NOT NULL DEFAULT 'MW',
    metric_code VARCHAR(48) NOT NULL DEFAULT 'PLANT_DISPATCH_MW',
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    validation_status VARCHAR(24) NOT NULL DEFAULT 'pending'
        CONSTRAINT ck_stg_dispatch_status CHECK (validation_status IN ('pending', 'valid', 'quarantined', 'loaded')),
    validation_notes TEXT,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE staging.stg_generation_report (
    stg_generation_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_stg_generation_report PRIMARY KEY,
    batch_id BIGINT NOT NULL
        CONSTRAINT fk_stg_gen_batch REFERENCES raw.ingestion_batch (batch_id),
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_stg_gen_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_stg_gen_raw_record REFERENCES raw.extracted_record (raw_record_id),
    source_code VARCHAR(32) NOT NULL,
    raw_plant_name VARCHAR(160) NOT NULL,
    raw_energy_category VARCHAR(80),
    period_type_code VARCHAR(24) NOT NULL,
    period_start_date DATE,
    period_end_date DATE,
    raw_generation_text VARCHAR(64),
    parsed_generation_value NUMERIC(16, 4),
    raw_peak_mw_text VARCHAR(64),
    parsed_peak_mw NUMERIC(12, 4),
    reported_unit_code VARCHAR(24) NOT NULL,
    generation_boundary VARCHAR(16) NOT NULL DEFAULT 'GROSS',
    value_nature VARCHAR(24) NOT NULL DEFAULT 'REPORTED',
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    validation_status VARCHAR(24) NOT NULL DEFAULT 'pending'
        CONSTRAINT ck_stg_gen_status CHECK (validation_status IN ('pending', 'valid', 'quarantined', 'loaded')),
    validation_notes TEXT,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE staging.stg_electricity_sales (
    stg_sales_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_stg_electricity_sales PRIMARY KEY,
    batch_id BIGINT NOT NULL
        CONSTRAINT fk_stg_sales_batch REFERENCES raw.ingestion_batch (batch_id),
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_stg_sales_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_stg_sales_raw_record REFERENCES raw.extracted_record (raw_record_id),
    source_code VARCHAR(32) NOT NULL,
    raw_region_name VARCHAR(128) NOT NULL DEFAULT 'LK',
    raw_sector_name VARCHAR(128) NOT NULL,
    period_type_code VARCHAR(24) NOT NULL,
    period_start_date DATE,
    period_end_date DATE,
    raw_energy_sold_text VARCHAR(64),
    parsed_energy_sold NUMERIC(16, 4),
    reported_unit_code VARCHAR(24) NOT NULL,
    parsed_consumer_count BIGINT,
    parsed_revenue_lkr NUMERIC(18, 2),
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    validation_status VARCHAR(24) NOT NULL DEFAULT 'pending'
        CONSTRAINT ck_stg_sales_status CHECK (validation_status IN ('pending', 'valid', 'quarantined', 'loaded')),
    validation_notes TEXT,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE staging.stg_plant_capacity (
    stg_capacity_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_stg_plant_capacity PRIMARY KEY,
    batch_id BIGINT NOT NULL
        CONSTRAINT fk_stg_cap_batch REFERENCES raw.ingestion_batch (batch_id),
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_stg_cap_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_stg_cap_raw_record REFERENCES raw.extracted_record (raw_record_id),
    source_code VARCHAR(32) NOT NULL,
    raw_plant_name VARCHAR(160) NOT NULL,
    period_type_code VARCHAR(24) NOT NULL,
    effective_start_date DATE,
    effective_end_date DATE,
    raw_installed_mw_text VARCHAR(64),
    parsed_installed_mw NUMERIC(12, 4),
    parsed_dependable_mw NUMERIC(12, 4),
    parsed_unit_count SMALLINT,
    reported_unit_code VARCHAR(24) NOT NULL DEFAULT 'MW',
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    validation_status VARCHAR(24) NOT NULL DEFAULT 'pending'
        CONSTRAINT ck_stg_cap_status CHECK (validation_status IN ('pending', 'valid', 'quarantined', 'loaded')),
    validation_notes TEXT,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE staging.stg_weather_observation (
    stg_weather_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_stg_weather_observation PRIMARY KEY,
    batch_id BIGINT NOT NULL
        CONSTRAINT fk_stg_weather_batch REFERENCES raw.ingestion_batch (batch_id),
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_stg_weather_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_stg_weather_raw_record REFERENCES raw.extracted_record (raw_record_id),
    source_code VARCHAR(32) NOT NULL DEFAULT 'NASA_POWER',
    location_code VARCHAR(48) NOT NULL,
    observation_date DATE,
    source_variable_name VARCHAR(64) NOT NULL,
    raw_value_text VARCHAR(64),
    parsed_value NUMERIC(14, 5),
    original_unit_code VARCHAR(24) NOT NULL,
    missing_value_code VARCHAR(32),
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    validation_status VARCHAR(24) NOT NULL DEFAULT 'pending'
        CONSTRAINT ck_stg_weather_status CHECK (validation_status IN ('pending', 'valid', 'quarantined', 'loaded')),
    validation_notes TEXT,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE staging.stg_published_statistic (
    stg_published_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_stg_published_statistic PRIMARY KEY,
    batch_id BIGINT NOT NULL
        CONSTRAINT fk_stg_pub_batch REFERENCES raw.ingestion_batch (batch_id),
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_stg_pub_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_stg_pub_raw_record REFERENCES raw.extracted_record (raw_record_id),
    source_code VARCHAR(32) NOT NULL,
    metric_code VARCHAR(48) NOT NULL,
    period_type_code VARCHAR(24) NOT NULL,
    period_start_date DATE,
    period_end_date DATE,
    raw_region_code VARCHAR(32),
    raw_energy_source_code VARCHAR(32),
    raw_sector_code VARCHAR(32),
    raw_published_text VARCHAR(64),
    parsed_published_value NUMERIC(18, 4),
    published_unit_code VARCHAR(24) NOT NULL,
    value_nature VARCHAR(24) NOT NULL DEFAULT 'REPORTED',
    publication_table_ref VARCHAR(128),
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    validation_status VARCHAR(24) NOT NULL DEFAULT 'pending'
        CONSTRAINT ck_stg_pub_status CHECK (validation_status IN ('pending', 'valid', 'quarantined', 'loaded')),
    validation_notes TEXT,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
