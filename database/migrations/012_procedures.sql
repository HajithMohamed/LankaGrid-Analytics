-- =============================================================================
-- Migration: 012_procedures.sql
-- Purpose  : Implement ETL stored procedures for run lifecycle tracking, staged
--            generation validation, approved alias checking, idempotent fact
--            loading with revision superseding, reconciliation, and MV refresh.
-- Rollback : DROP PROCEDURE IF EXISTS etl.sp_refresh_mart_views,
--            etl.sp_record_reconciliation_case, etl.sp_load_generation_period,
--            etl.sp_load_approved_plant_aliases, etl.sp_validate_staged_generation,
--            etl.sp_finalize_etl_run, etl.sp_start_etl_run CASCADE;
-- =============================================================================

-- 1. Start ETL Run Procedure
CREATE OR REPLACE PROCEDURE etl.sp_start_etl_run(
    IN p_pipeline_name VARCHAR,
    IN p_target_schema VARCHAR,
    IN p_target_table VARCHAR,
    IN p_source_document_id BIGINT,
    IN p_batch_id BIGINT,
    INOUT p_etl_run_id BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO audit.etl_run (
        pipeline_name,
        target_schema,
        target_table,
        source_document_id,
        batch_id,
        run_status,
        started_at
    ) VALUES (
        p_pipeline_name,
        p_target_schema,
        p_target_table,
        p_source_document_id,
        p_batch_id,
        'RUNNING',
        CURRENT_TIMESTAMP
    )
    RETURNING etl_run_id INTO p_etl_run_id;
END;
$$;

-- 2. Finalize ETL Run Procedure
CREATE OR REPLACE PROCEDURE etl.sp_finalize_etl_run(
    IN p_etl_run_id BIGINT,
    IN p_status VARCHAR,
    IN p_rows_read INTEGER,
    IN p_rows_inserted INTEGER,
    IN p_rows_updated INTEGER,
    IN p_rows_quarantined INTEGER,
    IN p_error_message TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE audit.etl_run
       SET run_status = p_status,
           completed_at = CURRENT_TIMESTAMP,
           rows_read = p_rows_read,
           rows_inserted = p_rows_inserted,
           rows_updated = p_rows_updated,
           rows_quarantined = p_rows_quarantined,
           error_message = p_error_message
     WHERE etl_run_id = p_etl_run_id;
END;
$$;

-- 3. Validate Staged Generation Records Procedure
CREATE OR REPLACE PROCEDURE etl.sp_validate_staged_generation(
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
        SELECT sg.*
          FROM staging.stg_generation_report sg
         WHERE sg.batch_id = p_batch_id
           AND sg.validation_status = 'pending'
         ORDER BY sg.stg_generation_id
    LOOP
        v_has_error := FALSE;
        v_notes := '';

        -- Check 1: Missing generation measurement
        IF rec.parsed_generation_value IS NULL THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'MISSING_VALUE;';
            INSERT INTO audit.data_quality_issue (
                etl_run_id, source_document_id, raw_record_id,
                staging_table_name, staging_record_ref, rule_code,
                issue_classification, severity, original_value, issue_status
            ) VALUES (
                p_etl_run_id, rec.source_document_id, rec.raw_record_id,
                'staging.stg_generation_report', 'stg_generation_id=' || rec.stg_generation_id,
                'DQ_GEN_MISSING_ENERGY', 'MISSING_VALUE', 'WARNING',
                rec.raw_generation_text, 'quarantined'
            );
        END IF;

        -- Check 2: Negative generation value
        IF rec.parsed_generation_value IS NOT NULL AND rec.parsed_generation_value < 0
           AND rec.generation_boundary <> 'AUXILIARY' THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'NEGATIVE_MEASUREMENT;';
            INSERT INTO audit.data_quality_issue (
                etl_run_id, source_document_id, raw_record_id,
                staging_table_name, staging_record_ref, rule_code,
                issue_classification, severity, original_value, issue_status
            ) VALUES (
                p_etl_run_id, rec.source_document_id, rec.raw_record_id,
                'staging.stg_generation_report', 'stg_generation_id=' || rec.stg_generation_id,
                'DQ_GEN_NEGATIVE_OUTPUT', 'INVALID_MEASUREMENT', 'ERROR',
                rec.raw_generation_text, 'quarantined'
            );
        END IF;

        -- Check 3: Reporting period alignment
        IF NOT etl.fn_validate_reporting_period(rec.period_type_code, rec.period_start_date, rec.period_end_date) THEN
            v_has_error := TRUE;
            v_notes := v_notes || 'INVALID_REPORTING_PERIOD;';
            INSERT INTO audit.data_quality_issue (
                etl_run_id, source_document_id, raw_record_id,
                staging_table_name, staging_record_ref, rule_code,
                issue_classification, severity, original_value, issue_status
            ) VALUES (
                p_etl_run_id, rec.source_document_id, rec.raw_record_id,
                'staging.stg_generation_report', 'stg_generation_id=' || rec.stg_generation_id,
                'DQ_PERIOD_GRANULARITY_MISMATCH', 'INCOMPATIBLE_REPORTING_GRANULARITY', 'ERROR',
                rec.period_type_code || ':' || COALESCE(rec.period_start_date::TEXT, 'NULL') || '..' || COALESCE(rec.period_end_date::TEXT, 'NULL'),
                'quarantined'
            );
        END IF;

        -- Check 4: Plant resolution (direct canonical match or VERIFIED alias)
        SELECT dp.plant_key
          INTO v_plant_key
          FROM dw.dim_power_plant dp
         WHERE dp.is_current = TRUE
           AND (
               UPPER(dp.plant_name) = UPPER(BTRIM(rec.raw_plant_name))
               OR UPPER(dp.plant_code) = UPPER(BTRIM(rec.raw_plant_name))
               OR EXISTS (
                   SELECT 1
                     FROM ref.plant_alias pa
                    WHERE pa.source_code = rec.source_code
                      AND UPPER(pa.alias_name) = UPPER(BTRIM(rec.raw_plant_name))
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
                'staging.stg_generation_report', 'stg_generation_id=' || rec.stg_generation_id,
                'DQ_DIM_UNMATCHED_ENTITY', 'UNMATCHED_DIMENSION', 'ERROR',
                rec.raw_plant_name, 'quarantined'
            );
        END IF;

        IF v_has_error THEN
            UPDATE staging.stg_generation_report
               SET validation_status = 'quarantined',
                   validation_notes = v_notes
             WHERE stg_generation_id = rec.stg_generation_id;
            p_quarantined_count := p_quarantined_count + 1;
        ELSE
            UPDATE staging.stg_generation_report
               SET validation_status = 'valid',
                   validation_notes = 'PASSED_QUALITY_GATES'
             WHERE stg_generation_id = rec.stg_generation_id;
            p_valid_count := p_valid_count + 1;
        END IF;
    END LOOP;
END;
$$;

-- 4. Audit / Promote Approved Plant Aliases Procedure
CREATE OR REPLACE PROCEDURE etl.sp_load_approved_plant_aliases(
    IN p_etl_run_id BIGINT,
    INOUT p_verified_count INTEGER DEFAULT 0,
    INOUT p_pending_count INTEGER DEFAULT 0
)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT COUNT(*)::INTEGER
      INTO p_verified_count
      FROM ref.plant_alias pa
      JOIN dw.dim_power_plant dp
        ON dp.plant_code = pa.canonical_plant_code
       AND dp.is_current = TRUE
     WHERE pa.verification_status = 'VERIFIED';

    SELECT COUNT(*)::INTEGER
      INTO p_pending_count
      FROM ref.plant_alias pa
     WHERE pa.verification_status = 'PENDING_EVIDENCE';
END;
$$;

-- 5. Idempotent Fact Generation Period Loader Procedure
CREATE OR REPLACE PROCEDURE etl.sp_load_generation_period(
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
    v_start_key INTEGER;
    v_end_key INTEGER;
    v_norm_mwh NUMERIC(14, 4);
    v_fact_id BIGINT;
    v_was_inserted BOOLEAN;
BEGIN
    p_inserted_count := 0;
    p_updated_count := 0;

    FOR rec IN
        SELECT sg.*
          FROM staging.stg_generation_report sg
         WHERE sg.batch_id = p_batch_id
           AND sg.validation_status = 'valid'
         ORDER BY sg.stg_generation_id
    LOOP
        SELECT dp.plant_key, dp.energy_source_key
          INTO v_plant_key, v_energy_source_key
          FROM dw.dim_power_plant dp
         WHERE dp.is_current = TRUE
           AND (
               UPPER(dp.plant_name) = UPPER(BTRIM(rec.raw_plant_name))
               OR UPPER(dp.plant_code) = UPPER(BTRIM(rec.raw_plant_name))
               OR EXISTS (
                   SELECT 1
                     FROM ref.plant_alias pa
                    WHERE pa.source_code = rec.source_code
                      AND UPPER(pa.alias_name) = UPPER(BTRIM(rec.raw_plant_name))
                      AND pa.canonical_plant_code = dp.plant_code
                      AND pa.verification_status = 'VERIFIED'
               )
           )
         LIMIT 1;

        SELECT dm.metric_key
          INTO v_metric_key
          FROM dw.dim_metric dm
         WHERE dm.metric_code = CASE
             WHEN rec.generation_boundary = 'NET' THEN 'NET_GENERATION_MWH'
             ELSE 'GROSS_GENERATION_MWH'
         END;

        SELECT dss.source_system_key
          INTO v_source_system_key
          FROM dw.dim_source_system dss
         WHERE dss.source_code = rec.source_code;

        SELECT dd.date_key INTO v_start_key FROM dw.dim_date dd WHERE dd.calendar_date = rec.period_start_date;
        SELECT dd.date_key INTO v_end_key FROM dw.dim_date dd WHERE dd.calendar_date = rec.period_end_date;

        v_norm_mwh := etl.fn_convert_unit(rec.parsed_generation_value, rec.reported_unit_code, 'MWh', NULL);

        -- Supersede prior dataset revisions for the identical grain
        UPDATE dw.fact_generation_period
           SET is_current_revision = FALSE
         WHERE plant_key = v_plant_key
           AND metric_key = v_metric_key
           AND period_type_code = rec.period_type_code
           AND period_start_date_key = v_start_key
           AND period_end_date_key = v_end_key
           AND source_system_key = v_source_system_key
           AND dataset_revision <> rec.dataset_revision
           AND is_current_revision = TRUE;

        INSERT INTO dw.fact_generation_period (
            plant_key,
            energy_source_key,
            metric_key,
            source_system_key,
            period_type_code,
            period_start_date_key,
            period_end_date_key,
            dataset_revision,
            generation_mwh,
            peak_generation_mw,
            reported_source_value,
            reported_unit_code,
            generation_boundary,
            value_nature,
            is_current_revision,
            source_document_id,
            raw_record_id,
            etl_run_id
        ) VALUES (
            v_plant_key,
            v_energy_source_key,
            v_metric_key,
            v_source_system_key,
            rec.period_type_code,
            v_start_key,
            v_end_key,
            rec.dataset_revision,
            v_norm_mwh,
            rec.parsed_peak_mw,
            rec.parsed_generation_value,
            rec.reported_unit_code,
            rec.generation_boundary,
            rec.value_nature,
            TRUE,
            rec.source_document_id,
            rec.raw_record_id,
            p_etl_run_id
        )
        ON CONFLICT ON CONSTRAINT uq_fact_generation_period_grain
        DO UPDATE SET
            generation_mwh = EXCLUDED.generation_mwh,
            peak_generation_mw = EXCLUDED.peak_generation_mw,
            reported_source_value = EXCLUDED.reported_source_value,
            reported_unit_code = EXCLUDED.reported_unit_code,
            value_nature = EXCLUDED.value_nature,
            is_current_revision = TRUE,
            etl_run_id = EXCLUDED.etl_run_id,
            loaded_at = CURRENT_TIMESTAMP
        RETURNING generation_fact_id, (xmax = 0) INTO v_fact_id, v_was_inserted;

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
            'staging.stg_generation_report',
            rec.stg_generation_id,
            'dw.fact_generation_period',
            v_fact_id,
            'Unit converted ' || rec.reported_unit_code || ' -> MWh'
        );

        UPDATE staging.stg_generation_report
           SET validation_status = 'loaded'
         WHERE stg_generation_id = rec.stg_generation_id;
    END LOOP;
END;
$$;

-- 6. Source Reconciliation Case Recording Procedure
CREATE OR REPLACE PROCEDURE etl.sp_record_reconciliation_case(
    IN p_etl_run_id BIGINT,
    IN p_metric_code VARCHAR,
    IN p_period_type_code VARCHAR,
    IN p_start_date DATE,
    IN p_end_date DATE,
    IN p_entity_scope VARCHAR,
    IN p_unit_code VARCHAR,
    IN p_primary_source VARCHAR,
    IN p_primary_val NUMERIC,
    IN p_secondary_source VARCHAR,
    IN p_secondary_val NUMERIC,
    IN p_tolerance_pct NUMERIC,
    INOUT p_reconciliation_id BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_metric_exists BOOLEAN;
    v_pct_var NUMERIC(10, 4);
    v_status VARCHAR(24);
    v_auth_source VARCHAR(32);
    v_domain VARCHAR(48);
BEGIN
    IF NOT etl.fn_validate_reporting_period(p_period_type_code, p_start_date, p_end_date) THEN
        RAISE EXCEPTION 'Incompatible or invalid reporting period for reconciliation: % (% to %)',
            p_period_type_code, p_start_date, p_end_date
            USING ERRCODE = '22023';
    END IF;

    SELECT TRUE, dm.business_domain
      INTO v_metric_exists, v_domain
      FROM dw.dim_metric dm
     WHERE dm.metric_code = p_metric_code;

    IF NOT COALESCE(v_metric_exists, FALSE) THEN
        RAISE EXCEPTION 'Unregistered metric_code for reconciliation: %', p_metric_code
            USING ERRCODE = '22023';
    END IF;

    IF p_primary_val = 0 THEN
        v_pct_var := CASE WHEN p_secondary_val = 0 THEN 0.0 ELSE NULL END;
    ELSE
        v_pct_var := ROUND((ABS(p_primary_val - p_secondary_val) / ABS(p_primary_val)) * 100.0, 4);
    END IF;

    IF v_pct_var IS NULL OR v_pct_var > p_tolerance_pct THEN
        v_status := 'CONFLICT_FLAGGED';
    ELSE
        v_status := 'WITHIN_TOLERANCE';
    END IF;

    SELECT sp.authoritative_source_code
      INTO v_auth_source
      FROM ref.source_precedence sp
     WHERE sp.business_domain = v_domain
       AND sp.period_type_code = p_period_type_code
     ORDER BY sp.precedence_rank ASC
     LIMIT 1;

    INSERT INTO audit.reconciliation_case (
        etl_run_id,
        metric_code,
        period_type_code,
        period_start_date,
        period_end_date,
        entity_scope_code,
        unit_code,
        primary_source_code,
        primary_value,
        secondary_source_code,
        secondary_value,
        pct_variance,
        reconciliation_status,
        authoritative_source_chosen
    ) VALUES (
        p_etl_run_id,
        p_metric_code,
        p_period_type_code,
        p_start_date,
        p_end_date,
        p_entity_scope,
        p_unit_code,
        p_primary_source,
        p_primary_val,
        p_secondary_source,
        p_secondary_val,
        v_pct_var,
        v_status,
        v_auth_source
    )
    RETURNING reconciliation_id INTO p_reconciliation_id;
END;
$$;

-- 7. Materialized Views Refresh Procedure
CREATE OR REPLACE PROCEDURE etl.sp_refresh_mart_views(
    IN p_concurrent BOOLEAN DEFAULT TRUE
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_concurrent THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mart.mv_monthly_generation_summary;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mart.mv_annual_energy_mix;
        REFRESH MATERIALIZED VIEW CONCURRENTLY mart.mv_monthly_sales_summary;
    ELSE
        REFRESH MATERIALIZED VIEW mart.mv_monthly_generation_summary;
        REFRESH MATERIALIZED VIEW mart.mv_annual_energy_mix;
        REFRESH MATERIALIZED VIEW mart.mv_monthly_sales_summary;
    END IF;
END;
$$;
