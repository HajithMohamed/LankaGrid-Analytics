-- =============================================================================
-- Migration: 018_real_data_etl_procedures.sql
-- Purpose  : Implement ETL validation and loading procedures for sub-daily dispatch
--            intervals, daily weather observations, and billed electricity sales.
-- Rollback : DROP PROCEDURE IF EXISTS etl.sp_load_electricity_sales,
--            etl.sp_validate_staged_sales, etl.sp_load_weather_daily,
--            etl.sp_validate_staged_weather, etl.sp_load_dispatch_interval,
--            etl.sp_validate_staged_dispatch CASCADE;
-- =============================================================================

-- 1. Procedure: Validate Staged Dispatch Observations
CREATE OR REPLACE PROCEDURE etl.sp_validate_staged_dispatch(
    IN p_batch_id BIGINT,
    IN p_etl_run_id BIGINT,
    INOUT p_valid_count INTEGER DEFAULT 0,
    INOUT p_quarantined_count INTEGER DEFAULT 0
)
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    v_plant_key INTEGER;
    v_has_error BOOLEAN;
    v_notes TEXT;
BEGIN
    p_valid_count := 0;
    p_quarantined_count := 0;

    FOR rec IN
        SELECT sd.*
          FROM staging.stg_dispatch_observation sd
         WHERE sd.batch_id = p_batch_id
           AND sd.validation_status = 'pending'
         ORDER BY sd.stg_dispatch_id
    LOOP
        v_has_error := FALSE;
        v_notes := '';

        -- Check 1: Missing timestamp
        IF rec.parsed_timestamp IS NULL THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'NULL_TIMESTAMP;';
            INSERT INTO audit.data_quality_issue (
                etl_run_id, source_document_id, raw_record_id,
                staging_table_name, staging_record_ref, rule_code,
                issue_classification, severity, original_value, issue_status
            ) VALUES (
                p_etl_run_id, rec.source_document_id, rec.raw_record_id,
                'staging.stg_dispatch_observation', 'stg_dispatch_id=' || rec.stg_dispatch_id,
                'DQ_DISPATCH_MISSING_SLOT', 'MISSING_REPORTING_INTERVAL', 'WARNING',
                rec.raw_timestamp_text, 'quarantined'
            );
        END IF;

        -- Check 2: Negative power measurement
        IF rec.parsed_power_mw IS NOT NULL AND rec.parsed_power_mw < 0 THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'NEGATIVE_POWER;';
            INSERT INTO audit.data_quality_issue (
                etl_run_id, source_document_id, raw_record_id,
                staging_table_name, staging_record_ref, rule_code,
                issue_classification, severity, original_value, issue_status
            ) VALUES (
                p_etl_run_id, rec.source_document_id, rec.raw_record_id,
                'staging.stg_dispatch_observation', 'stg_dispatch_id=' || rec.stg_dispatch_id,
                'DQ_GEN_NEGATIVE_OUTPUT', 'INVALID_MEASUREMENT', 'ERROR',
                rec.raw_power_text, 'quarantined'
            );
        END IF;

        -- Check 3: Plant entity resolution
        SELECT dp.plant_key
          INTO v_plant_key
          FROM dw.dim_power_plant dp
         WHERE dp.is_current = TRUE
           AND (
               UPPER(dp.plant_name) = UPPER(BTRIM(rec.raw_entity_name))
               OR UPPER(dp.plant_code) = UPPER(BTRIM(rec.raw_entity_name))
               OR EXISTS (
                   SELECT 1
                     FROM ref.plant_alias pa
                    WHERE pa.source_code = rec.source_code
                      AND UPPER(pa.alias_name) = UPPER(BTRIM(rec.raw_entity_name))
                      AND pa.canonical_plant_code = dp.plant_code
                      AND pa.verification_status = 'VERIFIED'
               )
           )
         LIMIT 1;

        IF v_plant_key IS NULL THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'UNMATCHED_PLANT;';
            INSERT INTO audit.data_quality_issue (
                etl_run_id, source_document_id, raw_record_id,
                staging_table_name, staging_record_ref, rule_code,
                issue_classification, severity, original_value, issue_status
            ) VALUES (
                p_etl_run_id, rec.source_document_id, rec.raw_record_id,
                'staging.stg_dispatch_observation', 'stg_dispatch_id=' || rec.stg_dispatch_id,
                'DQ_DIM_UNMATCHED_ENTITY', 'UNMATCHED_DIMENSION', 'ERROR',
                rec.raw_entity_name, 'quarantined'
            );
        END IF;

        IF v_has_error THEN
            UPDATE staging.stg_dispatch_observation
               SET validation_status = 'quarantined',
                   validation_notes = v_notes
             WHERE stg_dispatch_id = rec.stg_dispatch_id;
            p_quarantined_count := p_quarantined_count + 1;
        ELSE
            UPDATE staging.stg_dispatch_observation
               SET validation_status = 'valid',
                   validation_notes = 'PASSED_QUALITY_GATES'
             WHERE stg_dispatch_id = rec.stg_dispatch_id;
            p_valid_count := p_valid_count + 1;
        END IF;
    END LOOP;
END;
$$;

-- 2. Procedure: Idempotent Load of 15-Minute Dispatch Intervals
CREATE OR REPLACE PROCEDURE etl.sp_load_dispatch_interval(
    IN p_batch_id BIGINT,
    IN p_etl_run_id BIGINT,
    INOUT p_inserted_count INTEGER DEFAULT 0,
    INOUT p_updated_count INTEGER DEFAULT 0
)
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    v_plant_key INTEGER;
    v_energy_source_key INTEGER;
    v_metric_key INTEGER;
    v_source_system_key INTEGER;
    v_date_key INTEGER;
    v_interval_key INTEGER;
    v_derived_energy NUMERIC(12, 4);
    v_fact_id BIGINT;
    v_was_inserted BOOLEAN;
    v_cal_date DATE;
    v_cal_time TIME;
BEGIN
    p_inserted_count := 0;
    p_updated_count := 0;

    FOR rec IN
        SELECT sd.*
          FROM staging.stg_dispatch_observation sd
         WHERE sd.batch_id = p_batch_id
           AND sd.validation_status = 'valid'
         ORDER BY sd.stg_dispatch_id
    LOOP
        -- Resolve power plant and energy source
        SELECT dp.plant_key, dp.energy_source_key
          INTO v_plant_key, v_energy_source_key
          FROM dw.dim_power_plant dp
         WHERE dp.is_current = TRUE
           AND (
               UPPER(dp.plant_name) = UPPER(BTRIM(rec.raw_entity_name))
               OR UPPER(dp.plant_code) = UPPER(BTRIM(rec.raw_entity_name))
               OR EXISTS (
                   SELECT 1
                     FROM ref.plant_alias pa
                    WHERE pa.source_code = rec.source_code
                      AND UPPER(pa.alias_name) = UPPER(BTRIM(rec.raw_entity_name))
                      AND pa.canonical_plant_code = dp.plant_code
                      AND pa.verification_status = 'VERIFIED'
               )
           )
         LIMIT 1;

        -- Resolve metric
        SELECT dm.metric_key
          INTO v_metric_key
          FROM dw.dim_metric dm
         WHERE dm.metric_code = rec.metric_code;

        -- Resolve source system
        SELECT dss.source_system_key
          INTO v_source_system_key
          FROM dw.dim_source_system dss
         WHERE dss.source_code = rec.source_code;

        -- Resolve date key
        v_cal_date := (rec.parsed_timestamp AT TIME ZONE 'Asia/Colombo')::DATE;
        SELECT dd.date_key INTO v_date_key FROM dw.dim_date dd WHERE dd.calendar_date = v_cal_date;

        -- Resolve interval key (1..96 based on end time of 15-minute slot)
        v_cal_time := (rec.parsed_timestamp AT TIME ZONE 'Asia/Colombo')::TIME;
        SELECT di.interval_key
          INTO v_interval_key
          FROM dw.dim_interval di
         WHERE di.interval_type = '15MIN'
           AND di.end_time = v_cal_time;

        IF v_interval_key IS NULL THEN
            v_interval_key := ((EXTRACT(HOUR FROM v_cal_time) * 60 + EXTRACT(MINUTE FROM v_cal_time)) / 15)::INTEGER;
            IF v_interval_key = 0 THEN
                v_interval_key := 96;
            END IF;
        END IF;

        -- Derive energy: MW * 0.25h = MWh
        IF rec.parsed_power_mw IS NOT NULL THEN
            v_derived_energy := ROUND((rec.parsed_power_mw * 0.25)::NUMERIC, 4);
        ELSE
            v_derived_energy := NULL;
        END IF;

        INSERT INTO dw.fact_dispatch_interval (
            date_key,
            interval_key,
            plant_key,
            energy_source_key,
            metric_key,
            source_system_key,
            dataset_revision,
            original_timestamp,
            time_standard,
            interval_duration_minutes,
            active_power_mw,
            derived_energy_mwh,
            is_energy_derived,
            reported_value,
            reported_unit_code,
            value_status,
            is_current_revision,
            source_document_id,
            raw_record_id,
            etl_run_id
        ) VALUES (
            v_date_key,
            v_interval_key,
            v_plant_key,
            v_energy_source_key,
            v_metric_key,
            v_source_system_key,
            rec.dataset_revision,
            rec.parsed_timestamp,
            'Asia/Colombo (UTC+05:30)',
            rec.interval_duration_minutes,
            rec.parsed_power_mw,
            v_derived_energy,
            (v_derived_energy IS NOT NULL),
            rec.parsed_power_mw,
            rec.reported_unit_code,
            CASE WHEN rec.parsed_power_mw IS NULL THEN 'MISSING' ELSE 'REPORTED' END,
            TRUE,
            rec.source_document_id,
            rec.raw_record_id,
            p_etl_run_id
        )
        ON CONFLICT ON CONSTRAINT uq_fact_dispatch_interval_grain
        DO UPDATE SET
            active_power_mw = EXCLUDED.active_power_mw,
            derived_energy_mwh = EXCLUDED.derived_energy_mwh,
            is_energy_derived = EXCLUDED.is_energy_derived,
            reported_value = EXCLUDED.reported_value,
            reported_unit_code = EXCLUDED.reported_unit_code,
            value_status = EXCLUDED.value_status,
            is_current_revision = TRUE,
            etl_run_id = EXCLUDED.etl_run_id,
            loaded_at = CURRENT_TIMESTAMP
        RETURNING dispatch_fact_id INTO v_fact_id;

        p_inserted_count := p_inserted_count + 1;

        INSERT INTO audit.record_lineage (
            etl_run_id,
            source_document_id,
            raw_record_id,
            staging_table,
            staging_row_id,
            target_dw_table,
            target_dw_pk,
            transformation_notes
        ) VALUES (
            p_etl_run_id,
            rec.source_document_id,
            rec.raw_record_id,
            'staging.stg_dispatch_observation',
            rec.stg_dispatch_id,
            'dw.fact_dispatch_interval',
            v_fact_id,
            'Sub-daily 15-min dispatch slot integrated to MWh'
        );

        UPDATE staging.stg_dispatch_observation
           SET validation_status = 'loaded'
         WHERE stg_dispatch_id = rec.stg_dispatch_id;
    END LOOP;
END;
$$;

-- 3. Procedure: Validate Staged Weather Observations
CREATE OR REPLACE PROCEDURE etl.sp_validate_staged_weather(
    IN p_batch_id BIGINT,
    IN p_etl_run_id BIGINT,
    INOUT p_valid_count INTEGER DEFAULT 0,
    INOUT p_quarantined_count INTEGER DEFAULT 0
)
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    v_loc_key INTEGER;
    v_has_error BOOLEAN;
    v_notes TEXT;
BEGIN
    p_valid_count := 0;
    p_quarantined_count := 0;

    FOR rec IN
        SELECT sw.*
          FROM staging.stg_weather_observation sw
         WHERE sw.batch_id = p_batch_id
           AND sw.validation_status = 'pending'
         ORDER BY sw.stg_weather_id
    LOOP
        v_has_error := FALSE;
        v_notes := '';

        -- Check 1: Observation date
        IF rec.observation_date IS NULL THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'NULL_DATE;';
        END IF;

        -- Check 2: Resolve location
        SELECT dwl.weather_location_key
          INTO v_loc_key
          FROM dw.dim_weather_location dwl
         WHERE dwl.location_code = rec.location_code;

        IF v_loc_key IS NULL THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'UNMATCHED_LOCATION;';
            INSERT INTO audit.data_quality_issue (
                etl_run_id, source_document_id, raw_record_id,
                staging_table_name, staging_record_ref, rule_code,
                issue_classification, severity, original_value, issue_status
            ) VALUES (
                p_etl_run_id, rec.source_document_id, rec.raw_record_id,
                'staging.stg_weather_observation', 'stg_weather_id=' || rec.stg_weather_id,
                'DQ_DIM_UNMATCHED_ENTITY', 'UNMATCHED_DIMENSION', 'ERROR',
                rec.location_code, 'quarantined'
            );
        END IF;

        -- Check 3: Physical range bounds
        IF rec.parsed_value IS NOT NULL THEN
            IF rec.source_variable_name = 'RH2M' AND (rec.parsed_value < 0 OR rec.parsed_value > 100) THEN
                v_has_error := TRUE;
                v_notes := v_notes || 'INVALID_HUMIDITY;';
            ELSIF rec.source_variable_name LIKE 'T2M%' AND (rec.parsed_value < -20 OR rec.parsed_value > 60) THEN
                v_has_error := TRUE;
                v_notes := v_notes || 'INVALID_TEMPERATURE;';
            ELSIF rec.source_variable_name IN ('ALLSKY_SFC_SW_DWN', 'WS10M', 'WS50M', 'PRECTOTCORR') AND rec.parsed_value < 0 THEN
                v_has_error := TRUE;
                v_notes := v_notes || 'NEGATIVE_METEOROLOGICAL_VALUE;';
            END IF;
        END IF;

        IF v_has_error THEN
            UPDATE staging.stg_weather_observation
               SET validation_status = 'quarantined',
                   validation_notes = v_notes
             WHERE stg_weather_id = rec.stg_weather_id;
            p_quarantined_count := p_quarantined_count + 1;
        ELSE
            UPDATE staging.stg_weather_observation
               SET validation_status = 'valid',
                   validation_notes = 'PASSED_QUALITY_GATES'
             WHERE stg_weather_id = rec.stg_weather_id;
            p_valid_count := p_valid_count + 1;
        END IF;
    END LOOP;
END;
$$;

-- 4. Procedure: Idempotent Load of Daily Weather Observations
CREATE OR REPLACE PROCEDURE etl.sp_load_weather_daily(
    IN p_batch_id BIGINT,
    IN p_etl_run_id BIGINT,
    INOUT p_inserted_count INTEGER DEFAULT 0,
    INOUT p_updated_count INTEGER DEFAULT 0
)
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    v_date_key INTEGER;
    v_loc_key INTEGER;
    v_metric_key INTEGER;
    v_source_system_key INTEGER;
    v_canonical_metric_code VARCHAR(48);
    v_std_val NUMERIC(14, 5);
    v_std_unit VARCHAR(24);
    v_is_missing BOOLEAN;
    v_fact_id BIGINT;
    v_was_inserted BOOLEAN;
BEGIN
    p_inserted_count := 0;
    p_updated_count := 0;

    FOR rec IN
        SELECT sw.*
          FROM staging.stg_weather_observation sw
         WHERE sw.batch_id = p_batch_id
           AND sw.validation_status = 'valid'
         ORDER BY sw.stg_weather_id
    LOOP
        -- Resolve date key
        SELECT dd.date_key INTO v_date_key FROM dw.dim_date dd WHERE dd.calendar_date = rec.observation_date;

        -- Resolve weather location
        SELECT dwl.weather_location_key INTO v_loc_key FROM dw.dim_weather_location dwl WHERE dwl.location_code = rec.location_code;

        -- Resolve canonical metric code via ref.metric_mapping or direct match
        SELECT rmm.canonical_metric_code
          INTO v_canonical_metric_code
          FROM ref.metric_mapping rmm
         WHERE rmm.source_code = rec.source_code
           AND rmm.source_field_name = rec.source_variable_name
           AND rmm.verification_status = 'VERIFIED';

        IF v_canonical_metric_code IS NULL THEN
            IF rec.source_variable_name = 'WS50M' THEN
                v_canonical_metric_code := 'WIND_SPEED_50M_MS';
            ELSIF rec.source_variable_name = 'ALLSKY_SFC_SW_DWN' THEN
                v_canonical_metric_code := 'SOLAR_IRRADIANCE_SW_DWN';
            ELSIF rec.source_variable_name = 'T2M' THEN
                v_canonical_metric_code := 'AIR_TEMP_2M_C';
            ELSIF rec.source_variable_name = 'RH2M' THEN
                v_canonical_metric_code := 'REL_HUMIDITY_2M_PCT';
            ELSIF rec.source_variable_name = 'WS10M' THEN
                v_canonical_metric_code := 'WIND_SPEED_10M_MS';
            ELSIF rec.source_variable_name = 'PRECTOTCORR' THEN
                v_canonical_metric_code := 'PRECIPITATION_DAILY_MM';
            END IF;
        END IF;

        SELECT dm.metric_key, dm.canonical_unit_code
          INTO v_metric_key, v_std_unit
          FROM dw.dim_metric dm
         WHERE dm.metric_code = v_canonical_metric_code;

        SELECT dss.source_system_key
          INTO v_source_system_key
          FROM dw.dim_source_system dss
         WHERE dss.source_code = rec.source_code;

        -- Handle missing value sentinel (-999.0)
        IF rec.parsed_value IS NULL OR rec.missing_value_code IS NOT NULL THEN
            v_is_missing := TRUE;
            v_std_val := NULL;
        ELSE
            v_is_missing := FALSE;
            v_std_val := rec.parsed_value;
        END IF;

        INSERT INTO dw.fact_weather_daily (
            date_key,
            weather_location_key,
            metric_key,
            source_system_key,
            dataset_revision,
            source_variable_name,
            standardized_value,
            standardized_unit_code,
            original_reported_value,
            original_unit_code,
            missing_value_code,
            is_missing,
            time_standard,
            is_current_revision,
            source_document_id,
            raw_record_id,
            etl_run_id
        ) VALUES (
            v_date_key,
            v_loc_key,
            v_metric_key,
            v_source_system_key,
            rec.dataset_revision,
            rec.source_variable_name,
            v_std_val,
            v_std_unit,
            rec.parsed_value,
            rec.original_unit_code,
            rec.missing_value_code,
            v_is_missing,
            'LST / UTC+05:30',
            TRUE,
            rec.source_document_id,
            rec.raw_record_id,
            p_etl_run_id
        )
        ON CONFLICT ON CONSTRAINT uq_fact_weather_daily_grain
        DO UPDATE SET
            standardized_value = EXCLUDED.standardized_value,
            is_missing = EXCLUDED.is_missing,
            missing_value_code = EXCLUDED.missing_value_code,
            is_current_revision = TRUE,
            etl_run_id = EXCLUDED.etl_run_id,
            loaded_at = CURRENT_TIMESTAMP
        RETURNING weather_fact_id, (xmax = 0) INTO v_fact_id, v_was_inserted;

        IF v_was_inserted THEN
            p_inserted_count := p_inserted_count + 1;
        ELSE
            p_updated_count := p_updated_count + 1;
        END IF;

        INSERT INTO audit.record_lineage (
            etl_run_id,
            source_document_id,
            raw_record_id,
            staging_table,
            staging_row_id,
            target_dw_table,
            target_dw_pk,
            transformation_notes
        ) VALUES (
            p_etl_run_id,
            rec.source_document_id,
            rec.raw_record_id,
            'staging.stg_weather_observation',
            rec.stg_weather_id,
            'dw.fact_weather_daily',
            v_fact_id,
            'Daily NASA POWER point observation standardized'
        );

        UPDATE staging.stg_weather_observation
           SET validation_status = 'loaded'
         WHERE stg_weather_id = rec.stg_weather_id;
    END LOOP;
END;
$$;

-- 5. Procedure: Validate Staged Electricity Sales
CREATE OR REPLACE PROCEDURE etl.sp_validate_staged_sales(
    IN p_batch_id BIGINT,
    IN p_etl_run_id BIGINT,
    INOUT p_valid_count INTEGER DEFAULT 0,
    INOUT p_quarantined_count INTEGER DEFAULT 0
)
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    v_region_key INTEGER;
    v_sector_key INTEGER;
    v_has_error BOOLEAN;
    v_notes TEXT;
BEGIN
    p_valid_count := 0;
    p_quarantined_count := 0;

    FOR rec IN
        SELECT ss.*
          FROM staging.stg_electricity_sales ss
         WHERE ss.batch_id = p_batch_id
           AND ss.validation_status = 'pending'
         ORDER BY ss.stg_sales_id
    LOOP
        v_has_error := FALSE;
        v_notes := '';

        -- Check 1: Negative sales
        IF rec.parsed_energy_sold IS NOT NULL AND rec.parsed_energy_sold < 0 THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'NEGATIVE_SALES;';
        END IF;

        -- Check 2: Resolve region
        SELECT dr.region_key
          INTO v_region_key
          FROM dw.dim_region dr
         WHERE UPPER(dr.region_name) = UPPER(BTRIM(rec.raw_region_name))
            OR UPPER(dr.region_code) = UPPER(BTRIM(rec.raw_region_name))
            OR EXISTS (
                SELECT 1 FROM ref.region_alias ra
                 WHERE ra.source_code = rec.source_code
                   AND UPPER(ra.alias_name) = UPPER(BTRIM(rec.raw_region_name))
                   AND ra.canonical_region_code = dr.region_code
            );

        IF v_region_key IS NULL THEN
            SELECT dr.region_key INTO v_region_key FROM dw.dim_region dr WHERE dr.region_code = 'LK';
        END IF;

        -- Check 3: Resolve sector
        SELECT dcs.sector_key
          INTO v_sector_key
          FROM dw.dim_consumption_sector dcs
         WHERE UPPER(dcs.sector_name) = UPPER(BTRIM(rec.raw_sector_name))
            OR UPPER(dcs.sector_code) = UPPER(BTRIM(rec.raw_sector_name))
            OR UPPER(dcs.tariff_group) = UPPER(BTRIM(rec.raw_sector_name))
            OR (UPPER(rec.raw_sector_name) LIKE 'GENERAL PURPOSE%' AND dcs.sector_code = 'GENERAL_PURPOSE')
            OR (UPPER(rec.raw_sector_name) LIKE 'HOTEL%' AND dcs.sector_code = 'HOTEL')
            OR (UPPER(rec.raw_sector_name) LIKE 'INDUSTRIAL%' AND dcs.sector_code = 'INDUSTRIAL')
            OR (UPPER(rec.raw_sector_name) LIKE 'GOVERNMENT%' AND dcs.sector_code = 'GOVERNMENT')
            OR (UPPER(rec.raw_sector_name) LIKE 'STREET LIGHT%' AND dcs.sector_code = 'STREET_LIGHTING')
            OR (UPPER(rec.raw_sector_name) LIKE 'AGRICULTURE%' AND dcs.sector_code = 'AGRICULTURE')
            OR (UPPER(rec.raw_sector_name) = 'TOTAL' AND dcs.sector_code = 'ALL_SECTORS')
         LIMIT 1;

        IF v_sector_key IS NULL THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'UNMATCHED_SECTOR;';
            INSERT INTO audit.data_quality_issue (
                etl_run_id, source_document_id, raw_record_id,
                staging_table_name, staging_record_ref, rule_code,
                issue_classification, severity, original_value, issue_status
            ) VALUES (
                p_etl_run_id, rec.source_document_id, rec.raw_record_id,
                'staging.stg_electricity_sales', 'stg_sales_id=' || rec.stg_sales_id,
                'DQ_DIM_UNMATCHED_ENTITY', 'UNMATCHED_DIMENSION', 'ERROR',
                rec.raw_sector_name, 'quarantined'
            );
        END IF;

        IF v_has_error THEN
            UPDATE staging.stg_electricity_sales
               SET validation_status = 'quarantined',
                   validation_notes = v_notes
             WHERE stg_sales_id = rec.stg_sales_id;
            p_quarantined_count := p_quarantined_count + 1;
        ELSE
            UPDATE staging.stg_electricity_sales
               SET validation_status = 'valid',
                   validation_notes = 'PASSED_QUALITY_GATES'
             WHERE stg_sales_id = rec.stg_sales_id;
            p_valid_count := p_valid_count + 1;
        END IF;
    END LOOP;
END;
$$;

-- 6. Procedure: Idempotent Load of Electricity Sales
CREATE OR REPLACE PROCEDURE etl.sp_load_electricity_sales(
    IN p_batch_id BIGINT,
    IN p_etl_run_id BIGINT,
    INOUT p_inserted_count INTEGER DEFAULT 0,
    INOUT p_updated_count INTEGER DEFAULT 0
)
LANGUAGE plpgsql
AS $$
DECLARE
    rec RECORD;
    v_region_key INTEGER;
    v_sector_key INTEGER;
    v_metric_key INTEGER;
    v_source_system_key INTEGER;
    v_start_date_key INTEGER;
    v_end_date_key INTEGER;
    v_sold_mwh NUMERIC(14, 4);
    v_fact_id BIGINT;
    v_was_inserted BOOLEAN;
BEGIN
    p_inserted_count := 0;
    p_updated_count := 0;

    FOR rec IN
        SELECT ss.*
          FROM staging.stg_electricity_sales ss
         WHERE ss.batch_id = p_batch_id
           AND ss.validation_status = 'valid'
         ORDER BY ss.stg_sales_id
    LOOP
        -- Resolve region
        SELECT dr.region_key
          INTO v_region_key
          FROM dw.dim_region dr
         WHERE UPPER(dr.region_name) = UPPER(BTRIM(rec.raw_region_name))
            OR UPPER(dr.region_code) = UPPER(BTRIM(rec.raw_region_name))
            OR EXISTS (
                SELECT 1 FROM ref.region_alias ra
                 WHERE ra.source_code = rec.source_code
                   AND UPPER(ra.alias_name) = UPPER(BTRIM(rec.raw_region_name))
                   AND ra.canonical_region_code = dr.region_code
            );

        IF v_region_key IS NULL THEN
            SELECT dr.region_key INTO v_region_key FROM dw.dim_region dr WHERE dr.region_code = 'LK';
        END IF;

        -- Resolve sector
        SELECT dcs.sector_key
          INTO v_sector_key
          FROM dw.dim_consumption_sector dcs
         WHERE UPPER(dcs.sector_name) = UPPER(BTRIM(rec.raw_sector_name))
            OR UPPER(dcs.sector_code) = UPPER(BTRIM(rec.raw_sector_name))
            OR UPPER(dcs.tariff_group) = UPPER(BTRIM(rec.raw_sector_name))
            OR (UPPER(rec.raw_sector_name) LIKE 'GENERAL PURPOSE%' AND dcs.sector_code = 'GENERAL_PURPOSE')
            OR (UPPER(rec.raw_sector_name) LIKE 'HOTEL%' AND dcs.sector_code = 'HOTEL')
            OR (UPPER(rec.raw_sector_name) LIKE 'INDUSTRIAL%' AND dcs.sector_code = 'INDUSTRIAL')
            OR (UPPER(rec.raw_sector_name) LIKE 'GOVERNMENT%' AND dcs.sector_code = 'GOVERNMENT')
            OR (UPPER(rec.raw_sector_name) LIKE 'STREET LIGHT%' AND dcs.sector_code = 'STREET_LIGHTING')
            OR (UPPER(rec.raw_sector_name) LIKE 'AGRICULTURE%' AND dcs.sector_code = 'AGRICULTURE')
            OR (UPPER(rec.raw_sector_name) = 'TOTAL' AND dcs.sector_code = 'ALL_SECTORS')
         LIMIT 1;

        -- Resolve metric
        SELECT dm.metric_key
          INTO v_metric_key
          FROM dw.dim_metric dm
         WHERE dm.metric_code = 'ELECTRICITY_SALES_MWH';

        -- Resolve source system
        SELECT dss.source_system_key
          INTO v_source_system_key
          FROM dw.dim_source_system dss
         WHERE dss.source_code = rec.source_code;

        -- Resolve dates
        SELECT dd.date_key INTO v_start_date_key FROM dw.dim_date dd WHERE dd.calendar_date = rec.period_start_date;
        SELECT dd.date_key INTO v_end_date_key FROM dw.dim_date dd WHERE dd.calendar_date = rec.period_end_date;

        -- Unit conversion: GWh -> MWh
        v_sold_mwh := etl.fn_convert_unit(rec.parsed_energy_sold, rec.reported_unit_code, 'MWh', NULL);

        INSERT INTO dw.fact_electricity_sales (
            region_key,
            sector_key,
            metric_key,
            source_system_key,
            period_type_code,
            period_start_date_key,
            period_end_date_key,
            dataset_revision,
            energy_sold_mwh,
            consumer_account_count,
            revenue_lkr,
            reported_energy_value,
            reported_energy_unit_code,
            is_current_revision,
            source_document_id,
            raw_record_id,
            etl_run_id
        ) VALUES (
            v_region_key,
            v_sector_key,
            v_metric_key,
            v_source_system_key,
            rec.period_type_code,
            v_start_date_key,
            v_end_date_key,
            rec.dataset_revision,
            v_sold_mwh,
            rec.parsed_consumer_count,
            rec.parsed_revenue_lkr,
            rec.parsed_energy_sold,
            rec.reported_unit_code,
            TRUE,
            rec.source_document_id,
            rec.raw_record_id,
            p_etl_run_id
        )
        ON CONFLICT ON CONSTRAINT uq_fact_electricity_sales_grain
        DO UPDATE SET
            energy_sold_mwh = EXCLUDED.energy_sold_mwh,
            consumer_account_count = EXCLUDED.consumer_account_count,
            revenue_lkr = EXCLUDED.revenue_lkr,
            reported_energy_value = EXCLUDED.reported_energy_value,
            reported_energy_unit_code = EXCLUDED.reported_energy_unit_code,
            is_current_revision = TRUE,
            etl_run_id = EXCLUDED.etl_run_id,
            loaded_at = CURRENT_TIMESTAMP
        RETURNING sales_fact_id INTO v_fact_id;

        p_inserted_count := p_inserted_count + 1;

        INSERT INTO audit.record_lineage (
            etl_run_id,
            source_document_id,
            raw_record_id,
            staging_table,
            staging_row_id,
            target_dw_table,
            target_dw_pk,
            transformation_notes
        ) VALUES (
            p_etl_run_id,
            rec.source_document_id,
            rec.raw_record_id,
            'staging.stg_electricity_sales',
            rec.stg_sales_id,
            'dw.fact_electricity_sales',
            v_fact_id,
            'Billed electricity sales loaded from CEB Statistical Digest'
        );

        UPDATE staging.stg_electricity_sales
           SET validation_status = 'loaded'
         WHERE stg_sales_id = rec.stg_sales_id;
    END LOOP;
END;
$$;
