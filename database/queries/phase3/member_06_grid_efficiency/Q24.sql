-- ==============================================================================
-- Query Q24: ETL Pipeline Execution Performance, Throughput & End-to-End Data Lineage
-- Member: Member 6 (Grid Efficiency, Reconciliation & Data Quality)
-- Business Question: How effectively did the historical data ingestion pipeline process,
--                    validate and load records, and what was the end-to-end audit lineage?
-- Business Relevance: Proves warehouse operational efficiency, SLA compliance, and regulatory
--                     traceability from immutable raw files down to dimensional fact primary keys.
-- Relevant Lecture Theory: Lecture 4 (ETL Process Monitoring, Batch Scheduling & Index Performance),
--                          Lecture 6 (Audit Trail, Provenance & Lineage Maintenance),
--                          Lecture 5 (Pipeline Throughput & Duration Benchmarking).
-- Source Data: Warehouse Operational Audit Schema: audit.etl_run & audit.record_lineage.
-- Fact Grain: Pipeline batch run and target dimensional table lineage count.
-- Measurement Units: Duration (seconds), Ingestion Throughput (rows/sec), Record Counts.
-- Applicable Dates: Multi-Batch Historical Loading Pipeline.
-- Classification: READY.
-- ==============================================================================

WITH pipeline_benchmarks AS (
    SELECT
        aer.etl_run_id,
        aer.pipeline_name,
        aer.target_table,
        aer.run_status,
        aer.started_at,
        aer.completed_at,
        aer.rows_read,
        aer.rows_inserted,
        aer.rows_updated,
        aer.rows_quarantined,
        ROUND(EXTRACT(EPOCH FROM (aer.completed_at - aer.started_at))::numeric, 2) AS duration_seconds,
        CASE 
            WHEN EXTRACT(EPOCH FROM (aer.completed_at - aer.started_at)) > 0 THEN
                ROUND(aer.rows_read / EXTRACT(EPOCH FROM (aer.completed_at - aer.started_at))::numeric, 1)
            ELSE aer.rows_read
        END AS throughput_rows_per_sec
    FROM audit.etl_run aer
    WHERE aer.completed_at IS NOT NULL
),
lineage_counts AS (
    SELECT
        etl_run_id,
        target_dw_table,
        COUNT(*) AS audit_lineage_records
    FROM audit.record_lineage
    GROUP BY etl_run_id, target_dw_table
)
SELECT
    pb.pipeline_name,
    pb.target_table,
    COUNT(pb.etl_run_id) AS total_executed_runs,
    SUM(pb.rows_read) AS cumulative_rows_read,
    SUM(pb.rows_inserted) AS cumulative_rows_inserted,
    SUM(pb.rows_updated) AS cumulative_rows_updated,
    SUM(pb.rows_quarantined) AS cumulative_rows_quarantined,
    ROUND(AVG(pb.duration_seconds), 2) AS avg_duration_seconds,
    ROUND(MAX(pb.duration_seconds), 2) AS max_duration_seconds,
    ROUND(AVG(pb.throughput_rows_per_sec), 1) AS avg_throughput_rows_per_sec,
    -- Audit Lineage Verification
    COALESCE(SUM(lc.audit_lineage_records), 0) AS total_verified_lineage_records,
    -- Quarantine Rate (%)
    ROUND(
        100.0 * SUM(pb.rows_quarantined) / NULLIF(SUM(pb.rows_read), 0),
        2
    ) AS overall_quarantine_rate_pct,
    -- Pipeline Reliability Index
    CASE
        WHEN SUM(pb.rows_quarantined) = 0 THEN 'CLEAN ZERO-ERROR PIPELINE'
        WHEN (100.0 * SUM(pb.rows_quarantined) / SUM(pb.rows_read)) < 1.0 THEN 'HIGH FIDELITY (< 1.0% QUARANTINE)'
        ELSE 'GOVERNED QUARANTINE PIPELINE'
    END AS pipeline_quality_grade
FROM pipeline_benchmarks pb
LEFT JOIN lineage_counts lc ON pb.etl_run_id = lc.etl_run_id
GROUP BY pb.pipeline_name, pb.target_table
ORDER BY cumulative_rows_read DESC;

