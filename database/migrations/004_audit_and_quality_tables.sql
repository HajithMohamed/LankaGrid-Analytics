-- =============================================================================
-- Migration: 004_audit_and_quality_tables.sql
-- Purpose  : Create ETL execution audit, row-level data quality issue ledger,
--            source conflict reconciliation cases, and record lineage tables.
-- Rollback : DROP TABLE IF EXISTS audit.record_lineage, audit.reconciliation_case,
--            audit.data_quality_issue, audit.etl_run CASCADE;
-- =============================================================================

CREATE TABLE audit.etl_run (
    etl_run_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_audit_etl_run PRIMARY KEY,
    pipeline_name VARCHAR(100) NOT NULL,
    target_schema VARCHAR(32) NOT NULL,
    target_table VARCHAR(64) NOT NULL,
    source_document_id BIGINT
        CONSTRAINT fk_audit_etl_run_document
        REFERENCES raw.source_document (source_document_id),
    batch_id BIGINT
        CONSTRAINT fk_audit_etl_run_batch
        REFERENCES raw.ingestion_batch (batch_id),
    run_status VARCHAR(24) NOT NULL
        CONSTRAINT ck_audit_etl_run_status
        CHECK (run_status IN ('RUNNING', 'SUCCEEDED', 'FAILED', 'ROLLED_BACK', 'PARTIAL_QUARANTINE')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    rows_read INTEGER NOT NULL DEFAULT 0
        CONSTRAINT ck_audit_etl_run_read CHECK (rows_read >= 0),
    rows_inserted INTEGER NOT NULL DEFAULT 0
        CONSTRAINT ck_audit_etl_run_ins CHECK (rows_inserted >= 0),
    rows_updated INTEGER NOT NULL DEFAULT 0
        CONSTRAINT ck_audit_etl_run_upd CHECK (rows_updated >= 0),
    rows_quarantined INTEGER NOT NULL DEFAULT 0
        CONSTRAINT ck_audit_etl_run_quar CHECK (rows_quarantined >= 0),
    error_message TEXT,
    invoked_by VARCHAR(64) NOT NULL DEFAULT CURRENT_USER
);

COMMENT ON TABLE audit.etl_run IS
    'Execution log for every validation, reference promotion, and warehouse loading run.';

CREATE TABLE audit.data_quality_issue (
    issue_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_audit_data_quality_issue PRIMARY KEY,
    etl_run_id BIGINT
        CONSTRAINT fk_audit_dq_issue_etl_run
        REFERENCES audit.etl_run (etl_run_id),
    source_document_id BIGINT
        CONSTRAINT fk_audit_dq_issue_document
        REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_audit_dq_issue_raw_record
        REFERENCES raw.extracted_record (raw_record_id),
    staging_table_name VARCHAR(80) NOT NULL,
    staging_record_ref VARCHAR(128) NOT NULL,
    rule_code VARCHAR(48) NOT NULL
        CONSTRAINT fk_audit_dq_issue_rule
        REFERENCES ref.data_quality_rule (rule_code),
    issue_classification VARCHAR(48) NOT NULL
        CONSTRAINT ck_audit_dq_issue_classification
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
    severity VARCHAR(16) NOT NULL
        CONSTRAINT ck_audit_dq_issue_severity
        CHECK (severity IN ('CRITICAL', 'ERROR', 'WARNING', 'INFO')),
    original_value TEXT,
    suggested_normalized_value TEXT,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    issue_status VARCHAR(24) NOT NULL DEFAULT 'unresolved'
        CONSTRAINT ck_audit_dq_issue_status
        CHECK (issue_status IN ('unresolved', 'quarantined', 'accepted', 'corrected')),
    resolved_by VARCHAR(80),
    resolved_at TIMESTAMPTZ,
    resolution_justification TEXT
);

COMMENT ON TABLE audit.data_quality_issue IS
    'Row-level data quality issue tracker preserving original values, rule references, quarantine state, and signed-off resolutions.';

CREATE TABLE audit.reconciliation_case (
    reconciliation_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_audit_reconciliation_case PRIMARY KEY,
    etl_run_id BIGINT
        CONSTRAINT fk_audit_reconciliation_etl_run
        REFERENCES audit.etl_run (etl_run_id),
    metric_code VARCHAR(48) NOT NULL,
    period_type_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_audit_reconciliation_period
        REFERENCES ref.reporting_period_type (period_type_code),
    period_start_date DATE NOT NULL,
    period_end_date DATE NOT NULL,
    entity_scope_code VARCHAR(64) NOT NULL,
    unit_code VARCHAR(24) NOT NULL
        CONSTRAINT fk_audit_reconciliation_unit
        REFERENCES ref.unit (unit_code),
    primary_source_code VARCHAR(32) NOT NULL,
    primary_value NUMERIC(18, 4) NOT NULL,
    secondary_source_code VARCHAR(32) NOT NULL,
    secondary_value NUMERIC(18, 4) NOT NULL,
    absolute_variance NUMERIC(18, 4) GENERATED ALWAYS AS (ABS(primary_value - secondary_value)) STORED,
    pct_variance NUMERIC(10, 4),
    reconciliation_status VARCHAR(24) NOT NULL DEFAULT 'OPEN'
        CONSTRAINT ck_audit_reconciliation_status
        CHECK (reconciliation_status IN (
            'OPEN',
            'WITHIN_TOLERANCE',
            'CONFLICT_FLAGGED',
            'RESOLVED_PRIMARY',
            'RESOLVED_SECONDARY'
        )),
    authoritative_source_chosen VARCHAR(32),
    resolution_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_audit_reconciliation_dates CHECK (period_end_date >= period_start_date),
    CONSTRAINT ck_audit_reconciliation_distinct_sources CHECK (primary_source_code <> secondary_source_code)
);

COMMENT ON TABLE audit.reconciliation_case IS
    'Cross-source reconciliation registry comparing compatible metrics, boundaries, units, and periods (e.g. CEB vs PUCSL).';

CREATE TABLE audit.record_lineage (
    lineage_id BIGINT GENERATED ALWAYS AS IDENTITY
        CONSTRAINT pk_audit_record_lineage PRIMARY KEY,
    etl_run_id BIGINT NOT NULL
        CONSTRAINT fk_audit_lineage_etl_run
        REFERENCES audit.etl_run (etl_run_id),
    source_document_id BIGINT NOT NULL
        CONSTRAINT fk_audit_lineage_document
        REFERENCES raw.source_document (source_document_id),
    raw_record_id BIGINT
        CONSTRAINT fk_audit_lineage_raw_record
        REFERENCES raw.extracted_record (raw_record_id),
    staging_table VARCHAR(80) NOT NULL,
    staging_row_id BIGINT NOT NULL,
    target_dw_table VARCHAR(80) NOT NULL,
    target_dw_pk BIGINT NOT NULL,
    transformation_notes TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE audit.record_lineage IS
    'End-to-end record-level lineage tracing promoted warehouse fact rows back to staging and raw source locators.';
