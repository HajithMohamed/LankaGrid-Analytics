-- =============================================================================
-- Migration: 020_dispatch_reporting_date_fix_and_reconciliation.sql
-- Purpose  : 1. Add reporting_date and interval_slot_number columns to
--               staging.stg_dispatch_observation.
--            2. Update etl.sp_load_dispatch_interval to prioritize explicit
--               reporting_date and interval_slot_number, preventing 24:00 (slot 96)
--               from spilling into the next calendar day.
--            3. Update etl.sp_load_weather_daily to set time_standard = 'LST'.
--            4. Data repair: Shift existing misplaced interval 96 facts from
--               date D+1 back to reporting date D, and update weather time_standard.
-- Rollback : database/migrations/rollbacks/020_dispatch_reporting_date_fix_and_reconciliation_rollback.sql
-- =============================================================================

-- 1. Schema Evolution: Add reporting_date and interval_slot_number to staging
ALTER TABLE staging.stg_dispatch_observation
    ADD COLUMN IF NOT EXISTS reporting_date DATE,
    ADD COLUMN IF NOT EXISTS interval_slot_number SMALLINT;

COMMENT ON COLUMN staging.stg_dispatch_observation.reporting_date IS
    'Source publication reporting date (calendar day of the dispatch schedule)';
COMMENT ON COLUMN staging.stg_dispatch_observation.interval_slot_number IS
    'Source 15-minute slot index (1..96). Slot 96 represents interval 23:45-24:00 ending at midnight';

CREATE INDEX IF NOT EXISTS idx_extracted_record_dispatch_lookup
    ON raw.extracted_record (batch_id, (raw_payload->>'station'), (raw_payload->>'timestamp'));

CREATE INDEX IF NOT EXISTS idx_stg_dispatch_batch_lookup
    ON staging.stg_dispatch_observation (batch_id, raw_entity_name, raw_timestamp_text);

-- 2. Procedure: Updated Idempotent Load of 15-Minute Dispatch Intervals
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

        -- Resolve interval key (1..96)
        IF rec.interval_slot_number IS NOT NULL THEN
            v_interval_key := rec.interval_slot_number;
        ELSE
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
        END IF;

        -- Resolve reporting date key
        -- In 15-minute dispatch, interval 96 ending at 24:00 belongs to reporting_date.
        IF rec.reporting_date IS NOT NULL THEN
            v_cal_date := rec.reporting_date;
        ELSE
            v_cal_time := (rec.parsed_timestamp AT TIME ZONE 'Asia/Colombo')::TIME;
            IF v_interval_key = 96 AND v_cal_time = TIME '00:00:00' THEN
                v_cal_date := ((rec.parsed_timestamp AT TIME ZONE 'Asia/Colombo') - INTERVAL '1 day')::DATE;
            ELSE
                v_cal_date := (rec.parsed_timestamp AT TIME ZONE 'Asia/Colombo')::DATE;
            END IF;
        END IF;

        SELECT dd.date_key INTO v_date_key FROM dw.dim_date dd WHERE dd.calendar_date = v_cal_date;

        -- Derive energy: MW * 0.25h = MWh
        IF rec.parsed_power_mw IS NOT NULL THEN
            v_derived_energy := ROUND((rec.parsed_power_mw * 0.25)::NUMERIC, 4);
        ELSE
            v_derived_energy := NULL;
        END IF;

        -- Check if fact row already exists for insert/update counting
        SELECT fdi.dispatch_fact_id INTO v_fact_id
          FROM dw.fact_dispatch_interval fdi
         WHERE fdi.date_key = v_date_key
           AND fdi.interval_key = v_interval_key
           AND fdi.plant_key = v_plant_key
           AND fdi.metric_key = v_metric_key
           AND fdi.source_system_key = v_source_system_key
           AND fdi.dataset_revision = rec.dataset_revision;

        IF v_fact_id IS NULL THEN
            p_inserted_count := p_inserted_count + 1;
        ELSE
            p_updated_count := p_updated_count + 1;
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
            15,
            rec.parsed_power_mw,
            v_derived_energy,
            TRUE,
            rec.parsed_power_mw,
            rec.reported_unit_code,
            CASE
                WHEN rec.parsed_power_mw IS NULL THEN 'MISSING'
                WHEN rec.parsed_power_mw < 0 THEN 'PUMPING_LOAD'
                ELSE 'REPORTED'
            END,
            TRUE,
            rec.source_document_id,
            rec.raw_record_id,
            p_etl_run_id
        )
        ON CONFLICT ON CONSTRAINT uq_fact_dispatch_interval_grain
        DO UPDATE SET
            active_power_mw = EXCLUDED.active_power_mw,
            derived_energy_mwh = EXCLUDED.derived_energy_mwh,
            reported_value = EXCLUDED.reported_value,
            value_status = EXCLUDED.value_status,
            is_current_revision = TRUE,
            etl_run_id = EXCLUDED.etl_run_id,
            loaded_at = CURRENT_TIMESTAMP
        RETURNING dispatch_fact_id INTO v_fact_id;

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

-- 3. Procedure: Updated Idempotent Load of Daily Weather Observations (LST metadata)
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
        -- Resolve date
        SELECT dd.date_key INTO v_date_key FROM dw.dim_date dd WHERE dd.calendar_date = rec.observation_date;

        -- Resolve weather location
        SELECT dwl.weather_location_key
          INTO v_loc_key
          FROM dw.dim_weather_location dwl
         WHERE UPPER(dwl.location_code) = UPPER(BTRIM(rec.location_code))
         LIMIT 1;

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
            ELSE
                v_canonical_metric_code := rec.source_variable_name;
            END IF;
        END IF;

        SELECT dm.metric_key, dm.canonical_unit_code
          INTO v_metric_key, v_std_unit
          FROM dw.dim_metric dm
         WHERE dm.metric_code = v_canonical_metric_code;

        -- Resolve source system
        SELECT dss.source_system_key
          INTO v_source_system_key
          FROM dw.dim_source_system dss
         WHERE dss.source_code = rec.source_code;

        -- Standardized values and unit conversions
        v_is_missing := (rec.parsed_value IS NULL OR rec.missing_value_code IS NOT NULL);

        IF v_is_missing THEN
            v_std_val := NULL;
            v_std_unit := rec.original_unit_code;
        ELSE
            IF rec.source_variable_name = 'ALLSKY_SFC_SW_DWN' AND rec.original_unit_code = 'kWh/m2/day' THEN
                v_std_val := etl.fn_convert_unit(rec.parsed_value, 'kWh/m2/day', 'MJ/m2/day', NULL);
                v_std_unit := 'MJ/m2/day';
            ELSE
                v_std_val := rec.parsed_value;
                v_std_unit := rec.original_unit_code;
            END IF;
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
            'LST',
            TRUE,
            rec.source_document_id,
            rec.raw_record_id,
            p_etl_run_id
        )
        ON CONFLICT ON CONSTRAINT uq_fact_weather_daily_grain
        DO UPDATE SET
            standardized_value = EXCLUDED.standardized_value,
            standardized_unit_code = EXCLUDED.standardized_unit_code,
            original_reported_value = EXCLUDED.original_reported_value,
            is_missing = EXCLUDED.is_missing,
            missing_value_code = EXCLUDED.missing_value_code,
            time_standard = 'LST',
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

-- 4. Default for time_standard in weather fact
ALTER TABLE dw.fact_weather_daily
    ALTER COLUMN time_standard SET DEFAULT 'LST';

-- 5. Data Repair DML: Shift existing misplaced interval 96 facts from D+1 back to D
UPDATE dw.fact_dispatch_interval fdi
   SET date_key = (
       SELECT dd_prev.date_key
         FROM dw.dim_date dd_curr
         JOIN dw.dim_date dd_prev ON dd_prev.calendar_date = dd_curr.calendar_date - 1
        WHERE dd_curr.date_key = fdi.date_key
   )
 WHERE fdi.interval_key = 96
   AND (fdi.original_timestamp AT TIME ZONE 'Asia/Colombo')::TIME = TIME '00:00:00'
   AND fdi.date_key = (
       SELECT dd.date_key
         FROM dw.dim_date dd
        WHERE dd.calendar_date = (fdi.original_timestamp AT TIME ZONE 'Asia/Colombo')::DATE
   );

-- 6. Data Repair DML: Update weather fact time_standard from erroneous SLST label to LST
UPDATE dw.fact_weather_daily
   SET time_standard = 'LST'
 WHERE time_standard = 'LST / UTC+05:30';

-- 7. Data Repair DML: Backfill staging reporting_date and interval_slot_number
UPDATE staging.stg_dispatch_observation
   SET reporting_date = ((parsed_timestamp AT TIME ZONE 'Asia/Colombo') - INTERVAL '1 day')::DATE,
       interval_slot_number = 96
 WHERE (parsed_timestamp AT TIME ZONE 'Asia/Colombo')::TIME = TIME '00:00:00'
   AND reporting_date IS NULL;

UPDATE staging.stg_dispatch_observation
   SET reporting_date = (parsed_timestamp AT TIME ZONE 'Asia/Colombo')::DATE,
       interval_slot_number = ((EXTRACT(HOUR FROM (parsed_timestamp AT TIME ZONE 'Asia/Colombo')::TIME) * 60 + EXTRACT(MINUTE FROM (parsed_timestamp AT TIME ZONE 'Asia/Colombo')::TIME)) / 15)::SMALLINT
 WHERE (parsed_timestamp AT TIME ZONE 'Asia/Colombo')::TIME <> TIME '00:00:00'
   AND reporting_date IS NULL;
