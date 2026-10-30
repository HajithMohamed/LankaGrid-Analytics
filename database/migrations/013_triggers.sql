-- =============================================================================
-- Migration: 013_triggers.sql
-- Purpose  : Implement lightweight governance triggers:
--            1. Maintain updated_at timestamps on reference table updates.
--            2. Require documented verification_evidence before marking aliases
--               or source mappings as VERIFIED.
--            3. Require reviewer identity and justification when resolving DQ
--               issues to 'accepted' or 'corrected'.
-- Rollback : Drop triggers and trigger functions defined below.
-- =============================================================================

-- 1. Timestamp Maintenance Trigger Function
CREATE OR REPLACE FUNCTION etl.fn_trg_touch_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_ref_unit_updated_at
    BEFORE UPDATE ON ref.unit
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_touch_updated_at();

CREATE TRIGGER trg_ref_unit_conversion_updated_at
    BEFORE UPDATE ON ref.unit_conversion
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_touch_updated_at();

CREATE TRIGGER trg_ref_period_type_updated_at
    BEFORE UPDATE ON ref.reporting_period_type
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_touch_updated_at();

CREATE TRIGGER trg_ref_esm_updated_at
    BEFORE UPDATE ON ref.energy_source_mapping
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_touch_updated_at();

CREATE TRIGGER trg_ref_plant_alias_updated_at
    BEFORE UPDATE ON ref.plant_alias
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_touch_updated_at();

CREATE TRIGGER trg_ref_region_alias_updated_at
    BEFORE UPDATE ON ref.region_alias
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_touch_updated_at();

CREATE TRIGGER trg_ref_metric_mapping_updated_at
    BEFORE UPDATE ON ref.metric_mapping
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_touch_updated_at();

CREATE TRIGGER trg_ref_dq_rule_updated_at
    BEFORE UPDATE ON ref.data_quality_rule
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_touch_updated_at();

CREATE TRIGGER trg_ref_source_precedence_updated_at
    BEFORE UPDATE ON ref.source_precedence
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_touch_updated_at();

-- 2. Alias & Source Mapping Evidence Validation Trigger Function
CREATE OR REPLACE FUNCTION etl.fn_trg_validate_verification_evidence()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.verification_status = 'VERIFIED'
       AND (NEW.verification_evidence IS NULL OR BTRIM(NEW.verification_evidence) = '') THEN
        RAISE EXCEPTION 'Cannot mark reference mapping as VERIFIED without documented verification_evidence (table: %)',
            TG_TABLE_NAME;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_plant_alias_evidence
    BEFORE INSERT OR UPDATE ON ref.plant_alias
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_validate_verification_evidence();

CREATE TRIGGER trg_validate_esm_evidence
    BEFORE INSERT OR UPDATE ON ref.energy_source_mapping
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_validate_verification_evidence();

CREATE TRIGGER trg_validate_region_alias_evidence
    BEFORE INSERT OR UPDATE ON ref.region_alias
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_validate_verification_evidence();

-- 3. Data Quality Issue Resolution Audit Trigger Function
CREATE OR REPLACE FUNCTION etl.fn_trg_audit_dq_issue_resolution()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.issue_status IN ('accepted', 'corrected') THEN
        IF NEW.resolved_by IS NULL OR BTRIM(NEW.resolved_by) = '' THEN
            RAISE EXCEPTION 'Resolving a data quality issue to "%" requires resolved_by reviewer identity.',
                NEW.issue_status;
        END IF;
        IF NEW.resolution_justification IS NULL OR BTRIM(NEW.resolution_justification) = '' THEN
            RAISE EXCEPTION 'Resolving a data quality issue to "%" requires a non-empty resolution_justification.',
                NEW.issue_status;
        END IF;
        NEW.resolved_at := COALESCE(NEW.resolved_at, CURRENT_TIMESTAMP);
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_audit_dq_issue_resolution
    BEFORE INSERT OR UPDATE ON audit.data_quality_issue
    FOR EACH ROW EXECUTE FUNCTION etl.fn_trg_audit_dq_issue_resolution();
