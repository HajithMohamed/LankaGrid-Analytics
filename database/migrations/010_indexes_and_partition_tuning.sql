-- =============================================================================
-- Migration: 010_indexes_and_partition_tuning.sql
-- Purpose  : Create B-Tree indexes on foreign keys and filter predicates,
--            partial indexes for current dataset revisions, and BRIN indexes
--            for chronologically ordered fact tables.
-- Rollback : Drop secondary indexes defined in this migration.
-- =============================================================================

-- Raw & Staging Lineage Indexes
CREATE INDEX idx_raw_source_doc_system ON raw.source_document (source_system_id);
CREATE INDEX idx_raw_ingestion_batch_doc ON raw.ingestion_batch (source_document_id);
CREATE INDEX idx_raw_extracted_record_doc ON raw.extracted_record (source_document_id);

CREATE INDEX idx_stg_dispatch_batch_status ON staging.stg_dispatch_observation (batch_id, validation_status);
CREATE INDEX idx_stg_gen_batch_status ON staging.stg_generation_report (batch_id, validation_status);
CREATE INDEX idx_stg_sales_batch_status ON staging.stg_electricity_sales (batch_id, validation_status);
CREATE INDEX idx_stg_cap_batch_status ON staging.stg_plant_capacity (batch_id, validation_status);
CREATE INDEX idx_stg_weather_batch_status ON staging.stg_weather_observation (batch_id, validation_status);
CREATE INDEX idx_stg_pub_batch_status ON staging.stg_published_statistic (batch_id, validation_status);

-- Audit Indexes
CREATE INDEX idx_audit_dq_issue_run ON audit.data_quality_issue (etl_run_id, issue_status);
CREATE INDEX idx_audit_dq_issue_rule ON audit.data_quality_issue (rule_code);
CREATE INDEX idx_audit_recon_metric_period ON audit.reconciliation_case (metric_code, period_type_code, period_start_date);
CREATE INDEX idx_audit_lineage_doc ON audit.record_lineage (source_document_id);

-- Dimension Foreign Key & Hierarchy Indexes
CREATE INDEX idx_dim_region_parent ON dw.dim_region (parent_region_key);
CREATE INDEX idx_dim_plant_energy_source ON dw.dim_power_plant (energy_source_key);
CREATE INDEX idx_dim_plant_region ON dw.dim_power_plant (region_key);
CREATE INDEX idx_dim_weather_loc_region ON dw.dim_weather_location (region_key);

-- Fact A: dw.fact_dispatch_interval (Partitioned B-Tree + BRIN Indexes)
CREATE INDEX idx_fact_dispatch_plant_date
    ON dw.fact_dispatch_interval (plant_key, date_key);
CREATE INDEX idx_fact_dispatch_energy_date
    ON dw.fact_dispatch_interval (energy_source_key, date_key);
CREATE INDEX idx_fact_dispatch_interval_key
    ON dw.fact_dispatch_interval (interval_key);
CREATE INDEX idx_fact_dispatch_current_rev
    ON dw.fact_dispatch_interval (date_key, plant_key)
    WHERE is_current_revision = TRUE;
CREATE INDEX idx_brin_fact_dispatch_timestamp
    ON dw.fact_dispatch_interval USING BRIN (original_timestamp) WITH (pages_per_range = 32);

-- Fact B: dw.fact_generation_period
CREATE INDEX idx_fact_gen_period_dates
    ON dw.fact_generation_period (period_type_code, period_start_date_key, period_end_date_key);
CREATE INDEX idx_fact_gen_period_energy
    ON dw.fact_generation_period (energy_source_key, period_type_code)
    WHERE is_current_revision = TRUE;
CREATE INDEX idx_fact_gen_period_source_doc
    ON dw.fact_generation_period (source_document_id);

-- Fact C: dw.fact_capacity_period
CREATE INDEX idx_fact_cap_period_energy
    ON dw.fact_capacity_period (energy_source_key, effective_start_date_key)
    WHERE is_current_revision = TRUE;

-- Fact D: dw.fact_electricity_sales
CREATE INDEX idx_fact_sales_period_sector
    ON dw.fact_electricity_sales (period_type_code, period_start_date_key, sector_key)
    WHERE is_current_revision = TRUE;
CREATE INDEX idx_fact_sales_region
    ON dw.fact_electricity_sales (region_key);

-- Fact E: dw.fact_weather_daily (B-Tree + BRIN)
CREATE INDEX idx_fact_weather_loc_metric
    ON dw.fact_weather_daily (weather_location_key, metric_key, date_key)
    WHERE is_current_revision = TRUE;
CREATE INDEX idx_brin_fact_weather_date
    ON dw.fact_weather_daily USING BRIN (date_key) WITH (pages_per_range = 32);

-- Fact F: dw.fact_published_metric
CREATE INDEX idx_fact_pub_metric_period
    ON dw.fact_published_metric (metric_key, period_type_code, period_start_date_key)
    WHERE is_current_revision = TRUE;
