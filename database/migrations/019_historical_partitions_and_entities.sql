-- =============================================================================
-- Migration: 019_historical_partitions_and_entities.sql
-- Purpose  : 1. Create historical dispatch interval partitions for 2020-2022.
--            2. Register BULK_LECO sector in dw.dim_consumption_sector.
--            3. Update etl.sp_validate_staged_dispatch to quarantine summary rows.
--            4. Update etl.sp_validate_staged_sales & etl.sp_load_electricity_sales
--               to support Bulk Supply to LECO mapping.
--            5. Update etl.sp_load_weather_daily to apply unit conversion via
--               etl.fn_convert_unit (e.g. kWh/m2/day -> MJ/m2/day).
-- Rollback : database/migrations/rollbacks/019_historical_partitions_and_entities_rollback.sql
-- =============================================================================

-- 1. Create Historical Dispatch Interval Partitions
ALTER TABLE dw.fact_dispatch_interval DETACH PARTITION dw.fact_dispatch_interval_default;

CREATE TABLE IF NOT EXISTS dw.fact_dispatch_interval_y2020
    PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20200101) TO (20210101);

CREATE TABLE IF NOT EXISTS dw.fact_dispatch_interval_y2021
    PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20210101) TO (20220101);

CREATE TABLE IF NOT EXISTS dw.fact_dispatch_interval_y2022
    PARTITION OF dw.fact_dispatch_interval
    FOR VALUES FROM (20220101) TO (20230101);

ALTER TABLE dw.fact_dispatch_interval ATTACH PARTITION dw.fact_dispatch_interval_default DEFAULT;

-- 2. Add Bulk Supply to LECO Sector
INSERT INTO dw.dim_consumption_sector (
    sector_code,
    sector_name,
    tariff_group,
    is_aggregate_bucket,
    source_classification
) VALUES (
    'BULK_LECO',
    'Bulk Supply to LECO',
    'BULK',
    FALSE,
    'CEB_COMMERCIAL_DIGEST'
) ON CONFLICT (sector_code) DO NOTHING;

-- 3. Procedure: Validate Staged Dispatch Observations (Updated with summary exclusion)
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
    v_trimmed_name VARCHAR(160);
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
        v_trimmed_name := UPPER(BTRIM(rec.raw_entity_name));

        -- Check 0: Exclude system summary and total rows from station grain
        IF v_trimmed_name LIKE 'TOTAL MW%'
           OR v_trimmed_name = 'TOTAL'
           OR v_trimmed_name = 'ACTUAL SYSTEM DISPATCH' THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'SUMMARY_ROW_EXCLUDED;';
            INSERT INTO audit.data_quality_issue (
                etl_run_id, source_document_id, raw_record_id,
                staging_table_name, staging_record_ref, rule_code,
                issue_classification, severity, original_value, issue_status
            ) VALUES (
                p_etl_run_id, rec.source_document_id, rec.raw_record_id,
                'staging.stg_dispatch_observation', 'stg_dispatch_id=' || rec.stg_dispatch_id,
                'DQ_DIM_UNMATCHED_ENTITY', 'INCOMPATIBLE_REPORTING_GRANULARITY', 'INFO',
                rec.raw_entity_name, 'quarantined'
            );
        END IF;

        -- Check 1: Missing timestamp
        IF NOT v_has_error AND rec.parsed_timestamp IS NULL THEN
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
        IF NOT v_has_error AND rec.parsed_power_mw IS NOT NULL AND rec.parsed_power_mw < 0 THEN
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
        IF NOT v_has_error THEN
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

-- 4. Procedure: Validate Staged Electricity Sales (Updated with LECO support)
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

        -- Check 3: Resolve sector (including Bulk LECO)
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
            OR (UPPER(rec.raw_sector_name) LIKE '%LECO%' AND dcs.sector_code = 'BULK_LECO')
            OR (UPPER(rec.raw_sector_name) LIKE 'BULK SUPPLY%' AND dcs.sector_code = 'BULK_LECO')
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

-- 5. Procedure: Idempotent Load of Electricity Sales (Updated with LECO support)
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
            OR (UPPER(rec.raw_sector_name) LIKE '%LECO%' AND dcs.sector_code = 'BULK_LECO')
            OR (UPPER(rec.raw_sector_name) LIKE 'BULK SUPPLY%' AND dcs.sector_code = 'BULK_LECO')
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

-- 6. Procedure: Idempotent Load of Daily Weather Observations (Updated with unit conversion)
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
            -- Convert unit if original differs from canonical unit (e.g., kWh/m2/day -> MJ/m2/day)
            IF rec.original_unit_code IS NOT NULL AND v_std_unit IS NOT NULL AND rec.original_unit_code <> v_std_unit THEN
                v_std_val := etl.fn_convert_unit(rec.parsed_value, rec.original_unit_code, v_std_unit, NULL);
                IF v_std_val IS NULL THEN
                    v_std_val := rec.parsed_value;
                END IF;
            ELSE
                v_std_val := rec.parsed_value;
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
