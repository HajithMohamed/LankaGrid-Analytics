-- =============================================================================
-- Migration: 003_reference_tables.sql
-- Purpose  : Create controlled reference definitions, unit conversions, alias
--            mappings, data-quality rule registry, and source precedence tables.
-- Rollback : DROP TABLE IF EXISTS ref.source_precedence, ref.data_quality_rule,
--            ref.metric_mapping, ref.region_alias, ref.plant_alias,
--            ref.energy_source_mapping, ref.reporting_period_type,
--            ref.unit_conversion, ref.unit CASCADE;
-- =============================================================================

CREATE TABLE ref.unit (
    unit_code VARCHAR(24)
        CONSTRAINT pk_ref_unit PRIMARY KEY,
    unit_name VARCHAR(80) NOT NULL,
    unit_symbol VARCHAR(24) NOT NULL,
    measurement_dimension VARCHAR(32) NOT NULL
        CONSTRAINT ck_ref_unit_dimension
        CHECK (measurement_dimension IN (
            'POWER',
            'ENERGY',
            'CAPACITY',
            'IRRADIANCE_POWER',
            'IRRADIANCE_ENERGY',
            'TEMPERATURE',
            'SPEED',
            'LENGTH',
            'VOLUME',
            'PERCENTAGE',
            'CURRENCY',
            'COUNT',
            'FREQUENCY',
            'DIMENSIONLESS'
        )),
    is_canonical_warehouse_unit BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ref.unit IS
    'Controlled physical and economic units separating instantaneous power (MW) from integrated energy (MWh/GWh).';

CREATE TABLE ref.unit_conversion (
    conversion_id INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_ref_unit_conversion PRIMARY KEY,
    from_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_ref_unit_conv_from REFERENCES ref.unit (unit_code),
    to_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_ref_unit_conv_to REFERENCES ref.unit (unit_code),
    multiplier NUMERIC(20, 10) NOT NULL
        CONSTRAINT ck_ref_unit_conv_multiplier_pos CHECK (multiplier > 0),
    additive_offset NUMERIC(20, 10) NOT NULL DEFAULT 0,
    requires_interval_hours BOOLEAN NOT NULL DEFAULT FALSE,
    formula_description TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ref_unit_conversion_pair UNIQUE (from_unit_code, to_unit_code)
);

COMMENT ON TABLE ref.unit_conversion IS
    'Deterministic conversion factors between compatible units; requires_interval_hours guards power-to-energy integration.';

CREATE TABLE ref.reporting_period_type (
    period_type_code VARCHAR(24)
        CONSTRAINT pk_ref_reporting_period_type PRIMARY KEY,
    period_type_name VARCHAR(64) NOT NULL,
    nominal_minutes INTEGER
        CONSTRAINT ck_ref_period_nominal_minutes CHECK (nominal_minutes IS NULL OR nominal_minutes > 0),
    min_days INTEGER NOT NULL
        CONSTRAINT ck_ref_period_min_days CHECK (min_days >= 0),
    max_days INTEGER NOT NULL,
    is_subdaily BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_ref_period_day_bounds CHECK (max_days >= min_days)
);

COMMENT ON TABLE ref.reporting_period_type IS
    'Controlled reporting granularities preventing daily, monthly, and annual totals from being conflated.';

CREATE TABLE ref.energy_source_mapping (
    mapping_id INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_ref_energy_source_mapping PRIMARY KEY,
    source_code VARCHAR(32) NOT NULL,
    raw_source_label VARCHAR(128) NOT NULL,
    canonical_energy_source_code VARCHAR(32) NOT NULL,
    effective_from DATE NOT NULL DEFAULT DATE '2000-01-01',
    effective_to DATE,
    verification_status VARCHAR(24) NOT NULL
        CONSTRAINT ck_ref_esm_verification_status
        CHECK (verification_status IN ('VERIFIED', 'PENDING_EVIDENCE', 'REJECTED')),
    verification_evidence TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ref_energy_source_mapping UNIQUE (source_code, raw_source_label, effective_from),
    CONSTRAINT ck_ref_esm_dates CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

COMMENT ON TABLE ref.energy_source_mapping IS
    'Maps provider-specific fuel/category labels from CEB and PUCSL reports to canonical dw.dim_energy_source codes.';

CREATE TABLE ref.plant_alias (
    alias_id INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_ref_plant_alias PRIMARY KEY,
    source_code VARCHAR(32) NOT NULL,
    alias_name VARCHAR(160) NOT NULL,
    canonical_plant_code VARCHAR(48) NOT NULL,
    effective_from DATE NOT NULL DEFAULT DATE '2000-01-01',
    effective_to DATE,
    verification_status VARCHAR(24) NOT NULL
        CONSTRAINT ck_ref_plant_alias_status
        CHECK (verification_status IN ('VERIFIED', 'PENDING_EVIDENCE', 'REJECTED')),
    verification_evidence TEXT,
    verified_by VARCHAR(80),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ref_plant_alias UNIQUE (source_code, alias_name, effective_from),
    CONSTRAINT ck_ref_plant_alias_dates CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

COMMENT ON TABLE ref.plant_alias IS
    'Evidence-gated power station alias resolution table; unverified name matches remain PENDING_EVIDENCE.';

CREATE TABLE ref.region_alias (
    region_alias_id INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_ref_region_alias PRIMARY KEY,
    source_code VARCHAR(32) NOT NULL,
    alias_name VARCHAR(128) NOT NULL,
    canonical_region_code VARCHAR(32) NOT NULL,
    verification_status VARCHAR(24) NOT NULL
        CONSTRAINT ck_ref_region_alias_status
        CHECK (verification_status IN ('VERIFIED', 'PENDING_EVIDENCE', 'REJECTED')),
    verification_evidence TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ref_region_alias UNIQUE (source_code, alias_name)
);

COMMENT ON TABLE ref.region_alias IS
    'Maps source geographic and CEB distribution division strings to verified ISO/CEB region codes.';

CREATE TABLE ref.metric_mapping (
    metric_mapping_id INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_ref_metric_mapping PRIMARY KEY,
    source_code VARCHAR(32) NOT NULL,
    source_field_name VARCHAR(128) NOT NULL,
    canonical_metric_code VARCHAR(48) NOT NULL,
    source_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_ref_metric_mapping_unit REFERENCES ref.unit (unit_code),
    verification_status VARCHAR(24) NOT NULL
        CONSTRAINT ck_ref_metric_mapping_status
        CHECK (verification_status IN ('VERIFIED', 'PENDING_EVIDENCE', 'REJECTED')),
    notes TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ref_metric_mapping UNIQUE (source_code, source_field_name)
);

COMMENT ON TABLE ref.metric_mapping IS
    'Maps exact source column/parameter names (e.g. NASA ALLSKY_SFC_SW_DWN, PUCSL Daily MWh) to canonical dw.dim_metric codes.';

CREATE TABLE ref.data_quality_rule (
    rule_code VARCHAR(48)
        CONSTRAINT pk_ref_data_quality_rule PRIMARY KEY,
    rule_name VARCHAR(128) NOT NULL,
    issue_classification VARCHAR(48) NOT NULL
        CONSTRAINT ck_ref_dq_rule_classification
        CHECK (issue_classification IN (
            'MISSING_VALUE',
            'DUPLICATE',
            'INCORRECT_DATA_TYPE',
            'INVALID_MEASUREMENT',
            'STATISTICAL_OUTLIER',
            'UNIT_INCONSISTENCY',
            'NAMING_INCONSISTENCY',
            'MISSING_REPORTING_INTERVAL',
            'UNMATCHED_DIMENSION',
            'CONFLICTING_SOURCE_VALUE',
            'INCOMPATIBLE_REPORTING_GRANULARITY',
            'UNSUPPORTED_CALCULATION',
            'PARSING_FAILURE'
        )),
    target_domain VARCHAR(48) NOT NULL,
    default_severity VARCHAR(16) NOT NULL
        CONSTRAINT ck_ref_dq_rule_severity
        CHECK (default_severity IN ('CRITICAL', 'ERROR', 'WARNING', 'INFO')),
    blocks_warehouse_load BOOLEAN NOT NULL DEFAULT TRUE,
    rule_expression_summary TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE ref.data_quality_rule IS
    'Catalogue of automated validation rules covering all 13 Lecture 6 & warehouse data quality classifications.';

CREATE TABLE ref.source_precedence (
    precedence_id INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_ref_source_precedence PRIMARY KEY,
    business_domain VARCHAR(48) NOT NULL,
    period_type_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_ref_source_precedence_period
        REFERENCES ref.reporting_period_type (period_type_code),
    authoritative_source_code VARCHAR(32) NOT NULL,
    secondary_source_code VARCHAR(32),
    precedence_rank SMALLINT NOT NULL
        CONSTRAINT ck_ref_source_precedence_rank CHECK (precedence_rank >= 1),
    rationale TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ref_source_precedence UNIQUE (business_domain, period_type_code, authoritative_source_code)
);

COMMENT ON TABLE ref.source_precedence IS
    'Documents authoritative source hierarchy per domain and granularity (e.g. PUCSL for 15-min dispatch; CEB Digest for annual sales).';
