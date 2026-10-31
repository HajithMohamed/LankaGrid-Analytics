-- =============================================================================
-- Migration: 006_facts_generation_and_dispatch.sql
-- Purpose  : Create range-partitioned dw.fact_dispatch_interval (with yearly
--            partitions) and dw.fact_generation_period.
-- Rollback : DROP TABLE IF EXISTS dw.fact_generation_period,
--            dw.fact_dispatch_interval CASCADE;
-- =============================================================================

-- Fact A: Sub-Daily Grid Dispatch Observations (Range-Partitioned by date_key)
CREATE TABLE dw.fact_dispatch_interval (
    dispatch_fact_id BIGINT GENERATED ALWAYS AS IDENTITY,
    date_key INTEGER NOT NULL
        CONSTRAINT fk_fact_dispatch_date REFERENCES dw.dim_date (date_key),
    interval_key INTEGER NOT NULL
        CONSTRAINT fk_fact_dispatch_interval REFERENCES dw.dim_interval (interval_key),
    plant_key INTEGER NOT NULL
        CONSTRAINT fk_fact_dispatch_plant REFERENCES dw.dim_power_plant (plant_key),
    energy_source_key INTEGER NOT NULL
        CONSTRAINT fk_fact_dispatch_energy_source REFERENCES dw.dim_energy_source (energy_source_key),
    metric_key INTEGER NOT NULL
        CONSTRAINT fk_fact_dispatch_metric REFERENCES dw.dim_metric (metric_key),
    source_system_key INTEGER NOT NULL
        CONSTRAINT fk_fact_dispatch_source_system REFERENCES dw.dim_source_system (source_system_key),
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    original_timestamp TIMESTAMPTZ NOT NULL,
    time_standard VARCHAR(32) NOT NULL DEFAULT 'Asia/Colombo (UTC+05:30)',
    interval_duration_minutes SMALLINT NOT NULL
        CONSTRAINT ck_fact_dispatch_duration CHECK (interval_duration_minutes IN (15, 30, 60)),
    active_power_mw NUMERIC(12, 4),
    derived_energy_mwh NUMERIC(12, 4),
    is_energy_derived BOOLEAN NOT NULL DEFAULT FALSE,
    reported_value NUMERIC(14, 4),
    reported_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_dispatch_reported_unit REFERENCES ref.unit (unit_code),
    value_status VARCHAR(24) NOT NULL DEFAULT 'REPORTED'
        CONSTRAINT ck_fact_dispatch_value_status
        CHECK (value_status IN ('REPORTED', 'ESTIMATED', 'DERIVED', 'MISSING', 'PUMPING_LOAD')),
    is_current_revision BOOLEAN NOT NULL DEFAULT TRUE,
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_fact_dispatch_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_fact_dispatch_raw_record REFERENCES raw.extracted_record (raw_record_id),
    etl_run_id BIGINT NOT NULL
        CONSTRAINT fk_fact_dispatch_etl_run REFERENCES audit.etl_run (etl_run_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_fact_dispatch_interval PRIMARY KEY (dispatch_fact_id, date_key),
    CONSTRAINT uq_fact_dispatch_interval_grain UNIQUE (
        date_key,
        interval_key,
        plant_key,
        metric_key,
        source_system_key,
        dataset_revision
    ),
    CONSTRAINT ck_fact_dispatch_power_nonneg CHECK (
        value_status = 'PUMPING_LOAD'
        OR (
            (active_power_mw IS NULL OR active_power_mw >= 0)
            AND (derived_energy_mwh IS NULL OR derived_energy_mwh >= 0)
        )
    ),
    CONSTRAINT ck_fact_dispatch_missing_is_null CHECK (
        value_status <> 'MISSING'
        OR (active_power_mw IS NULL AND derived_energy_mwh IS NULL)
    ),
    CONSTRAINT ck_fact_dispatch_derived_energy_physics CHECK (
        is_energy_derived = FALSE
        OR active_power_mw IS NULL
        OR derived_energy_mwh IS NULL
        OR ABS(derived_energy_mwh - (active_power_mw * (interval_duration_minutes::NUMERIC / 60.0))) <= 0.01
    )
) PARTITION BY RANGE (date_key);

COMMENT ON TABLE dw.fact_dispatch_interval IS
    'Grain: One verified dispatch/demand observation per reporting entity, sub-daily interval, metric, and source revision. Range-partitioned by date_key.';

CREATE TABLE dw.fact_dispatch_interval_y2023
    PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20230101) TO (20240101);

CREATE TABLE dw.fact_dispatch_interval_y2024
    PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20240101) TO (20250101);

CREATE TABLE dw.fact_dispatch_interval_y2025
    PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20250101) TO (20260101);

CREATE TABLE dw.fact_dispatch_interval_y2026
    PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20260101) TO (20270101);

CREATE TABLE dw.fact_dispatch_interval_default
    PARTITION OF dw.fact_dispatch_interval
    DEFAULT;

-- Fact B: Periodic Electricity Generation (Daily / Monthly / Annual Explicitly Separated)
CREATE TABLE dw.fact_generation_period (
    generation_fact_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_fact_generation_period PRIMARY KEY,
    plant_key INTEGER NOT NULL
        CONSTRAINT fk_fact_gen_period_plant REFERENCES dw.dim_power_plant (plant_key),
    energy_source_key INTEGER NOT NULL
        CONSTRAINT fk_fact_gen_period_energy_source REFERENCES dw.dim_energy_source (energy_source_key),
    metric_key INTEGER NOT NULL
        CONSTRAINT fk_fact_gen_period_metric REFERENCES dw.dim_metric (metric_key),
    source_system_key INTEGER NOT NULL
        CONSTRAINT fk_fact_gen_period_source_system REFERENCES dw.dim_source_system (source_system_key),
    period_type_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_gen_period_type REFERENCES ref.reporting_period_type (period_type_code),
    period_start_date_key INTEGER NOT NULL
        CONSTRAINT fk_fact_gen_period_start_date REFERENCES dw.dim_date (date_key),
    period_end_date_key INTEGER NOT NULL
        CONSTRAINT fk_fact_gen_period_end_date REFERENCES dw.dim_date (date_key),
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    generation_mwh NUMERIC(14, 4),
    peak_generation_mw NUMERIC(12, 4),
    reported_source_value NUMERIC(16, 4),
    reported_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_gen_period_unit REFERENCES ref.unit (unit_code),
    generation_boundary VARCHAR(16) NOT NULL DEFAULT 'GROSS'
        CONSTRAINT ck_fact_gen_period_boundary CHECK (generation_boundary IN ('GROSS', 'NET', 'AUXILIARY')),
    value_nature VARCHAR(24) NOT NULL DEFAULT 'REPORTED'
        CONSTRAINT ck_fact_gen_period_nature
        CHECK (value_nature IN ('REPORTED', 'ESTIMATED', 'PROVISIONAL', 'AUDITED_FINAL', 'MISSING')),
    is_current_revision BOOLEAN NOT NULL DEFAULT TRUE,
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_fact_gen_period_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_fact_gen_period_raw_record REFERENCES raw.extracted_record (raw_record_id),
    etl_run_id BIGINT NOT NULL
        CONSTRAINT fk_fact_gen_period_etl_run REFERENCES audit.etl_run (etl_run_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_fact_generation_period_grain UNIQUE (
        plant_key,
        metric_key,
        period_type_code,
        period_start_date_key,
        period_end_date_key,
        source_system_key,
        dataset_revision
    ),
    CONSTRAINT ck_fact_gen_period_date_order CHECK (period_end_date_key >= period_start_date_key),
    CONSTRAINT ck_fact_gen_period_daily_exact CHECK (
        period_type_code <> 'DAILY' OR period_start_date_key = period_end_date_key
    ),
    CONSTRAINT ck_fact_gen_period_non_negative CHECK (
        (generation_boundary = 'AUXILIARY' OR generation_mwh IS NULL OR generation_mwh >= 0)
        AND (peak_generation_mw IS NULL OR peak_generation_mw >= 0)
    ),
    CONSTRAINT ck_fact_gen_period_missing_null CHECK (
        value_nature <> 'MISSING' OR generation_mwh IS NULL
    )
);

COMMENT ON TABLE dw.fact_generation_period IS
    'Grain: One periodic generation measurement per plant/category, metric, reporting period (DAILY/MONTHLY/ANNUAL), and source revision.';
