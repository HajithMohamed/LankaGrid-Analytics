-- =============================================================================
-- Migration: 005_dimensions.sql
-- Purpose  : Create all nine conformed dimensions for the Kimball Fact
--            Constellation schema in dw.
-- Rollback : DROP TABLE IF EXISTS dw.dim_metric, dw.dim_weather_location,
--            dw.dim_power_plant, dw.dim_consumption_sector, dw.dim_region,
--            dw.dim_energy_source, dw.dim_source_system, dw.dim_interval,
--            dw.dim_date CASCADE;
-- =============================================================================

-- 1. Calendar Date Dimension
CREATE TABLE dw.dim_date (
    date_key INTEGER
        CONSTRAINT pk_dim_date PRIMARY KEY,
    calendar_date DATE NOT NULL
        CONSTRAINT uq_dim_date_calendar_date UNIQUE,
    day_of_month SMALLINT NOT NULL
        CONSTRAINT ck_dim_date_dom CHECK (day_of_month BETWEEN 1 AND 31),
    day_of_year SMALLINT NOT NULL
        CONSTRAINT ck_dim_date_doy CHECK (day_of_year BETWEEN 1 AND 366),
    day_of_week_iso SMALLINT NOT NULL
        CONSTRAINT ck_dim_date_dow CHECK (day_of_week_iso BETWEEN 1 AND 7),
    day_name VARCHAR(12) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    week_of_year_iso SMALLINT NOT NULL
        CONSTRAINT ck_dim_date_woy CHECK (week_of_year_iso BETWEEN 1 AND 53),
    month_number SMALLINT NOT NULL
        CONSTRAINT ck_dim_date_month CHECK (month_number BETWEEN 1 AND 12),
    month_name VARCHAR(12) NOT NULL,
    year_month CHAR(7) NOT NULL,
    quarter_number SMALLINT NOT NULL
        CONSTRAINT ck_dim_date_quarter CHECK (quarter_number BETWEEN 1 AND 4),
    quarter_name CHAR(2) NOT NULL,
    calendar_year SMALLINT NOT NULL
        CONSTRAINT ck_dim_date_year CHECK (calendar_year BETWEEN 1990 AND 2100),
    sl_monsoon_season VARCHAR(32) NOT NULL
        CONSTRAINT ck_dim_date_monsoon
        CHECK (sl_monsoon_season IN (
            'NORTHEAST_MONSOON',
            'FIRST_INTER_MONSOON',
            'SOUTHWEST_MONSOON',
            'SECOND_INTER_MONSOON'
        ))
);

COMMENT ON TABLE dw.dim_date IS
    'Conformed calendar date dimension with ISO calendar hierarchies and Sri Lanka meteorological monsoon seasons.';

-- 2. Sub-Daily Time / Dispatch Interval Dimension
CREATE TABLE dw.dim_interval (
    interval_key INTEGER
        CONSTRAINT pk_dim_interval PRIMARY KEY,
    interval_type VARCHAR(20) NOT NULL
        CONSTRAINT ck_dim_interval_type CHECK (interval_type IN ('15MIN', 'HOURLY')),
    interval_index SMALLINT NOT NULL
        CONSTRAINT ck_dim_interval_index CHECK (interval_index BETWEEN 1 AND 96),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    duration_minutes SMALLINT NOT NULL
        CONSTRAINT ck_dim_interval_duration CHECK (duration_minutes IN (15, 60)),
    hour_of_day SMALLINT NOT NULL
        CONSTRAINT ck_dim_interval_hour CHECK (hour_of_day BETWEEN 0 AND 23),
    tariff_time_block VARCHAR(20) NOT NULL
        CONSTRAINT ck_dim_interval_tou_block CHECK (tariff_time_block IN ('OFF_PEAK', 'DAY', 'PEAK')),
    CONSTRAINT uq_dim_interval_type_idx UNIQUE (interval_type, interval_index)
);

COMMENT ON TABLE dw.dim_interval IS
    'Conformed sub-daily interval dimension (96 x 15-min and 24 x 60-min slots) aligned to Sri Lanka TOU blocks.';

-- 3. Source System Dimension
CREATE TABLE dw.dim_source_system (
    source_system_key INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_dim_source_system PRIMARY KEY,
    source_code VARCHAR(32) NOT NULL
        CONSTRAINT uq_dim_source_system_code UNIQUE,
    source_name VARCHAR(128) NOT NULL,
    organization_name VARCHAR(160) NOT NULL,
    source_category VARCHAR(48) NOT NULL
        CONSTRAINT ck_dim_source_system_cat
        CHECK (source_category IN ('UTILITY_STATISTICAL', 'REGULATORY_OPERATIONAL', 'SATELLITE_METEOROLOGICAL')),
    official_portal_url TEXT NOT NULL,
    default_time_zone VARCHAR(64) NOT NULL DEFAULT 'Asia/Colombo',
    typical_granularity VARCHAR(64) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE dw.dim_source_system IS
    'Conformed provider dimension identifying CEB, PUCSL, and NASA POWER lineage across all warehouse facts.';

-- 4. Energy Source & Fuel Classification Dimension
CREATE TABLE dw.dim_energy_source (
    energy_source_key INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_dim_energy_source PRIMARY KEY,
    energy_source_code VARCHAR(32) NOT NULL
        CONSTRAINT uq_dim_energy_source_code UNIQUE,
    energy_category VARCHAR(48) NOT NULL,
    fuel_type VARCHAR(48) NOT NULL,
    reporting_classification VARCHAR(64) NOT NULL,
    is_renewable BOOLEAN NOT NULL,
    is_dispatchable BOOLEAN NOT NULL,
    is_indigenous BOOLEAN NOT NULL
);

COMMENT ON TABLE dw.dim_energy_source IS
    'Conformed generation technology and fuel taxonomy matching verified CEB and PUCSL reporting classifications.';

-- 5. Geographic & CEB Distribution Region Dimension
CREATE TABLE dw.dim_region (
    region_key INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_dim_region PRIMARY KEY,
    region_code VARCHAR(32) NOT NULL
        CONSTRAINT uq_dim_region_code UNIQUE,
    region_name VARCHAR(100) NOT NULL,
    region_level VARCHAR(32) NOT NULL
        CONSTRAINT ck_dim_region_level
        CHECK (region_level IN ('NATIONAL', 'PROVINCE', 'DISTRICT', 'CEB_DISTRIBUTION_REGION')),
    iso_code VARCHAR(16),
    parent_region_key INTEGER
        CONSTRAINT fk_dim_region_parent REFERENCES dw.dim_region (region_key),
    source_standard VARCHAR(64) NOT NULL
);

COMMENT ON TABLE dw.dim_region IS
    'Verified Sri Lanka administrative (ISO-3166-2:LK) and CEB distribution divisions; contains zero unverified locations.';

-- 6. Electricity Consumption / Tariff Sector Dimension
CREATE TABLE dw.dim_consumption_sector (
    sector_key INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_dim_consumption_sector PRIMARY KEY,
    sector_code VARCHAR(32) NOT NULL
        CONSTRAINT uq_dim_consumption_sector_code UNIQUE,
    sector_name VARCHAR(100) NOT NULL,
    tariff_group VARCHAR(48) NOT NULL,
    is_aggregate_bucket BOOLEAN NOT NULL DEFAULT FALSE,
    source_classification VARCHAR(64) NOT NULL
);

COMMENT ON TABLE dw.dim_consumption_sector IS
    'Official CEB and PUCSL electricity consumer tariff categories (Domestic, Industrial, General Purpose, Hotel, etc.).';

-- 7. Power Plant / Generation Entity Dimension (SCD Type 2)
CREATE TABLE dw.dim_power_plant (
    plant_key INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_dim_power_plant PRIMARY KEY,
    plant_code VARCHAR(48) NOT NULL,
    plant_name VARCHAR(160) NOT NULL,
    entity_level VARCHAR(24) NOT NULL
        CONSTRAINT ck_dim_power_plant_level
        CHECK (entity_level IN ('PLANT', 'UNIT', 'COMPLEX', 'AGGREGATE_CATEGORY')),
    operator_type VARCHAR(32) NOT NULL
        CONSTRAINT ck_dim_power_plant_operator
        CHECK (operator_type IN ('CEB', 'IPP', 'SPP', 'AGGREGATE', 'MIXED')),
    energy_source_key INTEGER NOT NULL
        CONSTRAINT fk_dim_power_plant_energy_source
        REFERENCES dw.dim_energy_source (energy_source_key),
    region_key INTEGER
        CONSTRAINT fk_dim_power_plant_region
        REFERENCES dw.dim_region (region_key),
    hydro_complex VARCHAR(64),
    latitude_deg NUMERIC(8, 5)
        CONSTRAINT ck_dim_power_plant_lat
        CHECK (latitude_deg IS NULL OR (latitude_deg BETWEEN 5.80000 AND 10.00000)),
    longitude_deg NUMERIC(8, 5)
        CONSTRAINT ck_dim_power_plant_lon
        CHECK (longitude_deg IS NULL OR (longitude_deg BETWEEN 79.40000 AND 82.00000)),
    verification_status VARCHAR(24) NOT NULL
        CONSTRAINT ck_dim_power_plant_verification
        CHECK (verification_status IN ('VERIFIED', 'AGGREGATE_REPORTED')),
    effective_from DATE NOT NULL DEFAULT DATE '2000-01-01',
    effective_to DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_dim_power_plant_scd2 UNIQUE (plant_code, effective_from),
    CONSTRAINT ck_dim_power_plant_effective_dates
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

CREATE UNIQUE INDEX uq_dim_power_plant_current
    ON dw.dim_power_plant (plant_code)
    WHERE is_current = TRUE;

COMMENT ON TABLE dw.dim_power_plant IS
    'SCD Type 2 generation entity dimension supporting individual units, power stations, hydro complexes, and reported NCRE aggregate categories.';

-- 8. Meteorological Sampling Location Dimension
CREATE TABLE dw.dim_weather_location (
    weather_location_key INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_dim_weather_location PRIMARY KEY,
    location_code VARCHAR(48) NOT NULL
        CONSTRAINT uq_dim_weather_location_code UNIQUE,
    location_name VARCHAR(128) NOT NULL,
    energy_zone_type VARCHAR(32) NOT NULL
        CONSTRAINT ck_dim_weather_location_zone
        CHECK (energy_zone_type IN ('HYDRO_CATCHMENT', 'WIND_CORRIDOR', 'SOLAR_HUB', 'THERMAL_HUB', 'LOAD_CENTER')),
    region_key INTEGER NOT NULL
        CONSTRAINT fk_dim_weather_location_region
        REFERENCES dw.dim_region (region_key),
    latitude_deg NUMERIC(8, 5) NOT NULL
        CONSTRAINT ck_dim_weather_location_lat
        CHECK (latitude_deg BETWEEN 5.80000 AND 10.00000),
    longitude_deg NUMERIC(8, 5) NOT NULL
        CONSTRAINT ck_dim_weather_location_lon
        CHECK (longitude_deg BETWEEN 79.40000 AND 82.00000),
    elevation_m NUMERIC(7, 2),
    spatial_resolution_deg NUMERIC(5, 3) NOT NULL DEFAULT 0.500
        CONSTRAINT ck_dim_weather_location_res CHECK (spatial_resolution_deg > 0),
    source_provider VARCHAR(32) NOT NULL DEFAULT 'NASA_POWER'
);

COMMENT ON TABLE dw.dim_weather_location IS
    'Verified Sri Lanka meteorological grid sampling points bounded strictly to island coordinates.';

-- 9. Canonical Metric Dictionary Dimension
CREATE TABLE dw.dim_metric (
    metric_key INTEGER GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_dim_metric PRIMARY KEY,
    metric_code VARCHAR(48) NOT NULL
        CONSTRAINT uq_dim_metric_code UNIQUE,
    metric_name VARCHAR(128) NOT NULL,
    business_domain VARCHAR(48) NOT NULL,
    measurement_class VARCHAR(24) NOT NULL
        CONSTRAINT ck_dim_metric_class
        CHECK (measurement_class IN (
            'POWER',
            'ENERGY',
            'CAPACITY',
            'COUNT',
            'CURRENCY',
            'PERCENTAGE',
            'METEOROLOGICAL',
            'STORAGE',
            'RATIO'
        )),
    canonical_unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_dim_metric_unit REFERENCES ref.unit (unit_code),
    generation_boundary VARCHAR(20) NOT NULL
        CONSTRAINT ck_dim_metric_boundary
        CHECK (generation_boundary IN ('GROSS', 'NET', 'AUXILIARY', 'NOT_APPLICABLE')),
    value_nature VARCHAR(24) NOT NULL
        CONSTRAINT ck_dim_metric_nature
        CHECK (value_nature IN ('REPORTED', 'ESTIMATED', 'DERIVED', 'AUDITED_FINAL', 'PROVISIONAL')),
    aggregation_behavior VARCHAR(32) NOT NULL
        CONSTRAINT ck_dim_metric_agg
        CHECK (aggregation_behavior IN ('SUM', 'AVG', 'MIN', 'MAX', 'NON_ADDITIVE', 'SEMI_ADDITIVE_PERIOD_END')),
    is_summable_across_time BOOLEAN NOT NULL,
    is_summable_across_entities BOOLEAN NOT NULL,
    comparability_group VARCHAR(64) NOT NULL,
    definition_notes TEXT NOT NULL
);

COMMENT ON TABLE dw.dim_metric IS
    'Defines exact physical meaning, unit, boundary (gross vs net), and additivity rules to prevent conflating power, energy, demand, sales, and capacity.';
