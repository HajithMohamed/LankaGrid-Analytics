-- =============================================================================
-- Migration: 011_functions.sql
-- Purpose  : Implement validated SQL and PL/pgSQL functions for safe unit
--            conversion, reporting-period validation, 15-minute SLST interval
--            normalization, YoY percentage change, and DQ summary reporting.
-- Rollback : DROP FUNCTION IF EXISTS etl.fn_get_dq_summary,
--            etl.fn_calculate_yoy_change, etl.fn_normalize_interval_15min,
--            etl.fn_validate_reporting_period, etl.fn_convert_unit CASCADE;
-- =============================================================================

-- 1. Safe Unit Conversion Function
CREATE OR REPLACE FUNCTION etl.fn_convert_unit(
    p_value NUMERIC,
    p_from_unit VARCHAR,
    p_to_unit VARCHAR,
    p_interval_hours NUMERIC DEFAULT NULL
)
RETURNS NUMERIC
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_multiplier NUMERIC(20, 10);
    v_offset NUMERIC(20, 10);
    v_requires_hours BOOLEAN;
    v_unit_exists BOOLEAN;
BEGIN
    IF p_value IS NULL THEN
        RETURN NULL;
    END IF;

    IF p_from_unit = p_to_unit THEN
        SELECT EXISTS (SELECT 1 FROM ref.unit WHERE unit_code = p_from_unit)
          INTO v_unit_exists;
        IF NOT v_unit_exists THEN
            RAISE EXCEPTION 'Unknown unit code: %', p_from_unit
                USING ERRCODE = '22023';
        END IF;
        RETURN ROUND(p_value, 6);
    END IF;

    SELECT uc.multiplier, uc.additive_offset, uc.requires_interval_hours
      INTO v_multiplier, v_offset, v_requires_hours
      FROM ref.unit_conversion uc
     WHERE uc.from_unit_code = p_from_unit
       AND uc.to_unit_code = p_to_unit;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unsupported or physically incompatible unit conversion: % -> %',
            p_from_unit, p_to_unit
            USING ERRCODE = '22023';
    END IF;

    IF v_requires_hours THEN
        IF p_interval_hours IS NULL OR p_interval_hours <= 0 THEN
            RAISE EXCEPTION 'Power-to-energy conversion (% -> %) requires positive p_interval_hours',
                p_from_unit, p_to_unit
                USING ERRCODE = '22023';
        END IF;
        RETURN ROUND(((p_value * v_multiplier) + v_offset) * p_interval_hours, 6);
    END IF;

    RETURN ROUND((p_value * v_multiplier) + v_offset, 6);
END;
$$;

COMMENT ON FUNCTION etl.fn_convert_unit(NUMERIC, VARCHAR, VARCHAR, NUMERIC) IS
    'Converts physical measurements using ref.unit_conversion; preserves NULLs and blocks unparameterized power-to-energy conversions.';

-- 2. Reporting Period Validation Function
CREATE OR REPLACE FUNCTION etl.fn_validate_reporting_period(
    p_period_type VARCHAR,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_min_days INTEGER;
    v_max_days INTEGER;
    v_span_days INTEGER;
BEGIN
    IF p_period_type IS NULL OR p_start_date IS NULL OR p_end_date IS NULL THEN
        RETURN FALSE;
    END IF;

    IF p_end_date < p_start_date THEN
        RETURN FALSE;
    END IF;

    SELECT rpt.min_days, rpt.max_days
      INTO v_min_days, v_max_days
      FROM ref.reporting_period_type rpt
     WHERE rpt.period_type_code = p_period_type;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    v_span_days := (p_end_date - p_start_date) + 1;
    IF v_span_days < v_min_days OR v_span_days > v_max_days THEN
        RETURN FALSE;
    END IF;

    CASE p_period_type
        WHEN 'INTERVAL_15MIN', 'HOURLY', 'DAILY' THEN
            RETURN p_start_date = p_end_date;
        WHEN 'MONTHLY' THEN
            RETURN p_start_date = DATE_TRUNC('month', p_start_date)::DATE
               AND p_end_date = (DATE_TRUNC('month', p_start_date) + INTERVAL '1 month - 1 day')::DATE;
        WHEN 'QUARTERLY' THEN
            RETURN p_start_date = DATE_TRUNC('quarter', p_start_date)::DATE
               AND p_end_date = (DATE_TRUNC('quarter', p_start_date) + INTERVAL '3 months - 1 day')::DATE;
        WHEN 'ANNUAL' THEN
            RETURN EXTRACT(MONTH FROM p_start_date) = 1
               AND EXTRACT(DAY FROM p_start_date) = 1
               AND EXTRACT(MONTH FROM p_end_date) = 12
               AND EXTRACT(DAY FROM p_end_date) = 31
               AND EXTRACT(YEAR FROM p_start_date) = EXTRACT(YEAR FROM p_end_date);
        ELSE
            RETURN TRUE;
    END CASE;
END;
$$;

COMMENT ON FUNCTION etl.fn_validate_reporting_period(VARCHAR, DATE, DATE) IS
    'Validates that start and end calendar dates match the exact calendar boundaries of the declared reporting period type.';

-- 3. 15-Minute Sri Lanka Standard Time Interval Normalization Function
CREATE OR REPLACE FUNCTION etl.fn_normalize_interval_15min(
    p_ts TIMESTAMPTZ
)
RETURNS TABLE (
    colombo_date DATE,
    date_key INTEGER,
    interval_index SMALLINT,
    start_time TIME,
    tariff_block VARCHAR
)
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_local TIMESTAMP;
    v_minutes INTEGER;
    v_slot_start TIME;
BEGIN
    IF p_ts IS NULL THEN
        RETURN;
    END IF;

    v_local := p_ts AT TIME ZONE 'Asia/Colombo';
    colombo_date := v_local::DATE;
    date_key := (EXTRACT(YEAR FROM colombo_date)::INTEGER * 10000)
              + (EXTRACT(MONTH FROM colombo_date)::INTEGER * 100)
              + EXTRACT(DAY FROM colombo_date)::INTEGER;

    v_minutes := (EXTRACT(HOUR FROM v_local)::INTEGER * 60)
               + EXTRACT(MINUTE FROM v_local)::INTEGER;

    interval_index := ((v_minutes / 15) + 1)::SMALLINT;
    v_slot_start := MAKE_TIME((v_minutes / 60), ((v_minutes / 15) % 4) * 15, 0.0);
    start_time := v_slot_start;

    IF v_slot_start >= TIME '18:30:00' AND v_slot_start < TIME '22:30:00' THEN
        tariff_block := 'PEAK';
    ELSIF v_slot_start >= TIME '05:30:00' AND v_slot_start < TIME '18:30:00' THEN
        tariff_block := 'DAY';
    ELSE
        tariff_block := 'OFF_PEAK';
    END IF;

    RETURN NEXT;
END;
$$;

COMMENT ON FUNCTION etl.fn_normalize_interval_15min(TIMESTAMPTZ) IS
    'Maps any timezone-aware timestamp into Sri Lanka Standard Time (UTC+05:30) calendar date_key, 1..96 15-min slot, and TOU block.';

-- 4. Historical Year-over-Year Percentage Change Function
CREATE OR REPLACE FUNCTION etl.fn_calculate_yoy_change(
    p_current NUMERIC,
    p_prior NUMERIC
)
RETURNS NUMERIC
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE
        WHEN p_current IS NULL OR p_prior IS NULL OR p_prior = 0 THEN NULL
        ELSE ROUND(((p_current - p_prior) / ABS(p_prior)) * 100.0, 4)
    END;
$$;

COMMENT ON FUNCTION etl.fn_calculate_yoy_change(NUMERIC, NUMERIC) IS
    'Calculates percentage YoY change; returns NULL when prior baseline is NULL or zero to prevent division-by-zero distortion.';

-- 5. Data Quality Summary Calculation Function
CREATE OR REPLACE FUNCTION etl.fn_get_dq_summary(
    p_etl_run_id BIGINT DEFAULT NULL
)
RETURNS TABLE (
    issue_classification VARCHAR,
    severity VARCHAR,
    issue_status VARCHAR,
    issue_count BIGINT
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        dqi.issue_classification,
        dqi.severity,
        dqi.issue_status,
        COUNT(*)::BIGINT AS issue_count
    FROM audit.data_quality_issue dqi
    WHERE (p_etl_run_id IS NULL OR dqi.etl_run_id = p_etl_run_id)
    GROUP BY dqi.issue_classification, dqi.severity, dqi.issue_status
    ORDER BY issue_count DESC, dqi.issue_classification;
$$;

COMMENT ON FUNCTION etl.fn_get_dq_summary(BIGINT) IS
    'Returns grouped counts of data quality issues by classification, severity, and resolution status.';
