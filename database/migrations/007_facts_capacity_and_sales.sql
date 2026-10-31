-- =============================================================================
-- Migration: 007_facts_capacity_and_sales.sql
-- Purpose  : Create dw.fact_capacity_period (semi-additive installed/dependable
--            capacity) and dw.fact_electricity_sales.
-- Rollback : DROP TABLE IF EXISTS dw.fact_electricity_sales,
--            dw.fact_capacity_period CASCADE;
-- =============================================================================

-- Fact C: Installed & Dependable Capacity by Effective Reporting Period
CREATE TABLE dw.fact_capacity_period (
    capacity_fact_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_fact_capacity_period PRIMARY KEY,
    plant_key INTEGER NOT NULL
        CONSTRAINT fk_fact_capacity_plant REFERENCES dw.dim_power_plant (plant_key),
    energy_source_key INTEGER NOT NULL
        CONSTRAINT fk_fact_capacity_energy_source REFERENCES dw.dim_energy_source (energy_source_key),
    metric_key INTEGER NOT NULL
        CONSTRAINT fk_fact_capacity_metric REFERENCES dw.dim_metric (metric_key),
    source_system_key INTEGER NOT NULL
        CONSTRAINT fk_fact_capacity_source_system REFERENCES dw.dim_source_system (source_system_key),
    period_type_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_capacity_period_type REFERENCES ref.reporting_period_type (period_type_code),
    effective_start_date_key INTEGER NOT NULL
        CONSTRAINT fk_fact_capacity_start_date REFERENCES dw.dim_date (date_key),
    effective_end_date_key INTEGER NOT NULL
        CONSTRAINT fk_fact_capacity_end_date REFERENCES dw.dim_date (date_key),
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    installed_capacity_mw NUMERIC(12, 4),
    dependable_capacity_mw NUMERIC(12, 4),
    unit_count SMALLINT,
    reported_source_value NUMERIC(14, 4),
    reported_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_capacity_unit REFERENCES ref.unit (unit_code),
    is_current_revision BOOLEAN NOT NULL DEFAULT TRUE,
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_fact_capacity_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_fact_capacity_raw_record REFERENCES raw.extracted_record (raw_record_id),
    etl_run_id BIGINT NOT NULL
        CONSTRAINT fk_fact_capacity_etl_run REFERENCES audit.etl_run (etl_run_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_fact_capacity_period_grain UNIQUE (
        plant_key,
        metric_key,
        period_type_code,
        effective_start_date_key,
        effective_end_date_key,
        source_system_key,
        dataset_revision
    ),
    CONSTRAINT ck_fact_capacity_dates CHECK (effective_end_date_key >= effective_start_date_key),
    CONSTRAINT ck_fact_capacity_nonneg CHECK (
        (installed_capacity_mw IS NULL OR installed_capacity_mw >= 0)
        AND (dependable_capacity_mw IS NULL OR dependable_capacity_mw >= 0)
        AND (unit_count IS NULL OR unit_count >= 0)
    ),
    CONSTRAINT ck_fact_capacity_dependable_le_installed CHECK (
        installed_capacity_mw IS NULL
        OR dependable_capacity_mw IS NULL
        OR dependable_capacity_mw <= installed_capacity_mw
    )
);

COMMENT ON TABLE dw.fact_capacity_period IS
    'Grain: One installed/dependable capacity observation per plant or category, effective reporting period, and source revision. Semi-additive: never sum across time.';

-- Fact D: Electricity Sales & Billed Consumption
CREATE TABLE dw.fact_electricity_sales (
    sales_fact_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_fact_electricity_sales PRIMARY KEY,
    region_key INTEGER NOT NULL
        CONSTRAINT fk_fact_sales_region REFERENCES dw.dim_region (region_key),
    sector_key INTEGER NOT NULL
        CONSTRAINT fk_fact_sales_sector REFERENCES dw.dim_consumption_sector (sector_key),
    metric_key INTEGER NOT NULL
        CONSTRAINT fk_fact_sales_metric REFERENCES dw.dim_metric (metric_key),
    source_system_key INTEGER NOT NULL
        CONSTRAINT fk_fact_sales_source_system REFERENCES dw.dim_source_system (source_system_key),
    period_type_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_sales_period_type REFERENCES ref.reporting_period_type (period_type_code),
    period_start_date_key INTEGER NOT NULL
        CONSTRAINT fk_fact_sales_start_date REFERENCES dw.dim_date (date_key),
    period_end_date_key INTEGER NOT NULL
        CONSTRAINT fk_fact_sales_end_date REFERENCES dw.dim_date (date_key),
    dataset_revision VARCHAR(32) NOT NULL DEFAULT 'v1',
    energy_sold_mwh NUMERIC(14, 4),
    consumer_account_count BIGINT,
    revenue_lkr NUMERIC(18, 2),
    reported_energy_value NUMERIC(16, 4),
    reported_energy_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_fact_sales_unit REFERENCES ref.unit (unit_code),
    value_nature VARCHAR(24) NOT NULL DEFAULT 'REPORTED'
        CONSTRAINT ck_fact_sales_nature
        CHECK (value_nature IN ('REPORTED', 'ESTIMATED', 'PROVISIONAL', 'AUDITED_FINAL', 'MISSING')),
    is_current_revision BOOLEAN NOT NULL DEFAULT TRUE,
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_fact_sales_document REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_fact_sales_raw_record REFERENCES raw.extracted_record (raw_record_id),
    etl_run_id BIGINT NOT NULL
        CONSTRAINT fk_fact_sales_etl_run REFERENCES audit.etl_run (etl_run_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_fact_electricity_sales_grain UNIQUE (
        region_key,
        sector_key,
        metric_key,
        period_type_code,
        period_start_date_key,
        period_end_date_key,
        source_system_key,
        dataset_revision
    ),
    CONSTRAINT ck_fact_sales_dates CHECK (period_end_date_key >= period_start_date_key),
    CONSTRAINT ck_fact_sales_nonneg CHECK (
        (energy_sold_mwh IS NULL OR energy_sold_mwh >= 0)
        AND (consumer_account_count IS NULL OR consumer_account_count >= 0)
        AND (revenue_lkr IS NULL OR revenue_lkr >= 0)
    ),
    CONSTRAINT ck_fact_sales_missing_null CHECK (
        value_nature <> 'MISSING' OR energy_sold_mwh IS NULL
    )
);

COMMENT ON TABLE dw.fact_electricity_sales IS
    'Grain: One billed electricity sales record at the published period, region (or National LK), tariff sector, and source revision.';
