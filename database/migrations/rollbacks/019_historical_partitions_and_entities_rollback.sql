-- ============================================================================
-- Migration Rollback: 019_historical_partitions_and_entities_rollback.sql
-- Description: Rollback 019 historical partitions and procedures
-- ============================================================================

-- Re-attach default partition after dropping historical partitions
ALTER TABLE dw.fact_dispatch_interval DETACH PARTITION dw.fact_dispatch_interval_default;

DROP TABLE IF EXISTS dw.fact_dispatch_interval_y2020;
DROP TABLE IF EXISTS dw.fact_dispatch_interval_y2021;
DROP TABLE IF EXISTS dw.fact_dispatch_interval_y2022;

ALTER TABLE dw.fact_dispatch_interval ATTACH PARTITION dw.fact_dispatch_interval_default DEFAULT;

DELETE FROM dw.dim_consumption_sector WHERE sector_code = 'BULK_LECO';
