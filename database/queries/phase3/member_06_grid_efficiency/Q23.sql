-- ==============================================================================
-- Query Q23: Data Quality Anomaly Categorization & Quarantine Audit Trail
-- Member: Member 6 (Grid Efficiency, Reconciliation & Data Quality)
-- Business Question: What types of data-quality problems were detected during the historical
--                    data integration process, and what were the quarantine rates?
-- Business Relevance: Provides transparency into data-cleaning gates, verifying that corrupt,
--                     negative, or unmapped telemetry records were isolated without contaminating warehouse facts.
-- Relevant Lecture Theory: Lecture 6 (Data Preprocessing: Noise, Outlier & Quarantine Isolation),
--                          Lecture 8 (Multilevel Summaries using GROUPING SETS),
--                          Lecture 5 (Data Quality Profiling & Distribution Metrics).
-- Source Data: Warehouse Audit Schema: audit.data_quality_issue & audit.etl_run.
-- Fact Grain: Aggregated issue occurrences across historical pipeline execution batches.
-- Measurement Units: Issue Count, Total Quarantined Records, Relative Fault Frequency (%).
-- Applicable Dates: Multi-Batch Historical Loading Pipeline.
-- Classification: READY.
-- ==============================================================================

WITH issue_details AS (
    SELECT
        dqi.issue_id,
        dqi.rule_code,
        dqi.issue_classification,
        dqi.severity,
        dqi.staging_table_name,
        dqi.issue_status,
        aer.pipeline_name
    FROM audit.data_quality_issue dqi
    LEFT JOIN audit.etl_run aer ON dqi.etl_run_id = aer.etl_run_id
),
issue_base_total AS (
    SELECT COUNT(*) AS total_warehouse_issues FROM issue_details
),
pipeline_quarantine_rates AS (
    SELECT
        pipeline_name,
        SUM(rows_read) AS total_rows_read,
        SUM(rows_quarantined) AS total_rows_quarantined,
        ROUND(100.0 * SUM(rows_quarantined) / NULLIF(SUM(rows_read), 0), 3) AS pipeline_quarantine_rate_pct
    FROM audit.etl_run
    GROUP BY pipeline_name
)
SELECT
    CASE 
        WHEN GROUPING(rule_code) = 1 THEN '>>> TOTAL WAREHOUSE QUALITY ISSUES <<<'
        ELSE rule_code
    END AS dq_rule_code,
    CASE 
        WHEN GROUPING(issue_classification) = 1 AND GROUPING(rule_code) = 0 THEN '--- Rule Subtotal ---'
        WHEN GROUPING(issue_classification) = 1 AND GROUPING(rule_code) = 1 THEN 'ALL CLASSIFICATIONS'
        ELSE issue_classification
    END AS issue_classification,
    CASE 
        WHEN GROUPING(severity) = 1 THEN 'ALL SEVERITIES'
        ELSE severity
    END AS severity_level,
    COUNT(issue_id) AS total_issues_logged,
    ROUND(
        100.0 * COUNT(issue_id) / NULLIF((SELECT total_warehouse_issues FROM issue_base_total), 0),
        2
    ) AS percentage_of_all_issues,
    COUNT(DISTINCT staging_table_name) AS affected_staging_tables,
    MAX(pipeline_name) AS primary_affected_pipeline,
    GROUPING(rule_code) AS grp_rule,
    GROUPING(issue_classification) AS grp_class
FROM issue_details
GROUP BY GROUPING SETS (
    (rule_code, issue_classification, severity),
    (rule_code),
    ()
)
ORDER BY 
    GROUPING(rule_code) ASC,
    COUNT(issue_id) DESC;
