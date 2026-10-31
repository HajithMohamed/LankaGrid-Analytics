-- =============================================================================
-- Migration: 008_facts_weather_and_published.sql
-- Purpose  : Create dw.fact_weather_daily (NASA POWER meteorological parameters)
--            and dw.fact_published_metric (standalone official statistics).
-- Rollback : DROP TABLE IF EXISTS dw.fact_published_metric,
--            dw.fact_weather_daily CASCADE;
-- =============================================================================

-- Fact E: Daily Meteorological Observations per Parameter & Location
CREATE TABLE dw.fact_weather_daily (
    weather_fact_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_fact_weather_daily PRIMARY KEY,
    date_key INTEGER NOT NULL
        CONSTRAINT fk_fact_weather_date REFERENCES dw.dim_date (date_key),
    weather_location_key INTEGER NOT NULL
        CONSTRAINT fk_fact_weather_location REFERENCES dw.dim_weather_location (weather_location_key),
    metric_key INTEGER NOT NULL
        CONSTRAINT fk_fact_weather_metric REFERENCES dw.dim_metric (metric_key),
    source_system_key INTEGER NOT NULL
        CONSTRAINT fk_fact_weather_source_system REFERENCES dw.dim_source_system (source_system_key),
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    source_variable_name VARCHAR(64) NOT NULL,
    standardized_value NUMERIC(14, 5),
    standardized_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_weather_std_unit REFERENCES ref.unit (unit_code),
    original_reported_value NUMERIC(14, 5),
    original_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_weather_orig_unit REFERENCES ref.unit (unit_code),
    missing_value_code VARCHAR(32),
    is_missing BOOLEAN NOT NULL DEFAULT FALSE,
    time_standard VARCHAR(32) NOT NULL DEFAULT 'LST / UTC+05:30',
    is_current_revision BOOLEAN NOT NULL DEFAULT TRUE,
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_fact_weather_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_fact_weather_raw_record REFERENCES raw.extracted_record (raw_record_id),
    etl_run_id BIGINT NOT NULL
        CONSTRAINT fk_fact_weather_etl_run REFERENCES audit.etl_run (etl_run_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_fact_weather_daily_grain UNIQUE (
        date_key,
        weather_location_key,
        metric_key,
        source_system_key,
        dataset_revision
    ),
    CONSTRAINT ck_fact_weather_missing_null CHECK (
        (is_missing = TRUE AND standardized_value IS NULL)
        OR (is_missing = FALSE)
    ),
    CONSTRAINT ck_fact_weather_physical_bounds CHECK (
        standardized_value IS NULL
        OR (
            (source_variable_name IN ('ALLSKY_SFC_SW_DWN', 'CLRSKY_SFC_SW_DWN', 'PRECTOTCORR', 'WS10M', 'WS50M') AND standardized_value >= 0)
            OR (source_variable_name = 'RH2M' AND standardized_value BETWEEN 0 AND 100)
            OR (source_variable_name LIKE 'T2M%' AND standardized_value BETWEEN -20 AND 60)
            OR (source_variable_name NOT IN ('ALLSKY_SFC_SW_DWN', 'CLRSKY_SFC_SW_DWN', 'PRECTOTCORR', 'WS10M', 'WS50M', 'RH2M') AND source_variable_name NOT LIKE 'T2M%')
        )
    )
);

COMMENT ON TABLE dw.fact_weather_daily IS
    'Grain: One daily meteorological parameter per verified Sri Lanka sampling location and source revision. Preserves NASA missing sentinels (-999) without storing 0.';

-- Fact F: Standalone Published Aggregate Metrics (Reconciliation & Historical Benchmarks)
CREATE TABLE dw.fact_published_metric (
    published_fact_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_fact_published_metric PRIMARY KEY,
    metric_key INTEGER NOT NULL
        CONSTRAINT fk_fact_pub_metric REFERENCES dw.dim_metric (metric_key),
    period_type_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_pub_period_type REFERENCES ref.reporting_period_type (period_type_code),
    period_start_date_key INTEGER NOT NULL
        CONSTRAINT fk_fact_pub_start_date REFERENCES dw.dim_date (date_key),
    period_end_date_key INTEGER NOT NULL
        CONSTRAINT fk_fact_pub_end_date REFERENCES dw.dim_date (date_key),
    region_key INTEGER
        CONSTRAINT fk_fact_pub_region REFERENCES dw.dim_region (region_key),
    energy_source_key INTEGER
        CONSTRAINT fk_fact_pub_energy_source REFERENCES dw.dim_energy_source (energy_source_key),
    sector_key INTEGER
        CONSTRAINT fk_fact_pub_sector REFERENCES dw.dim_consumption_sector (sector_key),
    source_system_key INTEGER NOT NULL
        CONSTRAINT fk_fact_pub_source_system REFERENCES dw.dim_source_system (source_system_key),
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    standardized_value NUMERIC(18, 4),
    standardized_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_pub_std_unit REFERENCES ref.unit (unit_code),
    published_value NUMERIC(18, 4),
    published_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_pub_orig_unit REFERENCES ref.unit (unit_code),
    value_nature VARCHAR(24) NOT NULL
        CONSTRAINT ck_fact_pub_nature
        CHECK (value_nature IN ('REPORTED', 'ESTIMATED', 'PROVISIONAL', 'AUDITED_FINAL', 'REVISED', 'MISSING')),
    publication_table_ref VARCHAR(128),
    is_standalone_published_aggregate BOOLEAN NOT NULL DEFAULT TRUE
        CONSTRAINT ck_fact_pub_standalone_guard CHECK (is_standalone_published_aggregate = TRUE),
    is_current_revision BOOLEAN NOT NULL DEFAULT TRUE,
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_fact_pub_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_fact_pub_raw_record REFERENCES raw.extracted_record (raw_record_id),
    etl_run_id BIGINT NOT NULL
        CONSTRAINT fk_fact_pub_etl_run REFERENCES audit.etl_run (etl_run_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_fact_published_metric_grain UNIQUE NULLS NOT DISTINCT (
        metric_key,
        period_type_code,
        period_start_date_key,
        period_end_date_key,
        region_key,
        energy_source_key,
        sector_key,
        source_system_key,
        dataset_revision
    ),
    CONSTRAINT ck_fact_pub_dates CHECK (period_end_date_key >= period_start_date_key)
);

COMMENT ON TABLE dw.fact_published_metric IS
    'Grain: One officially published aggregate metric per scope, reporting period, and source revision. Never sum together with fact_dispatch_interval or fact_generation_period.';
