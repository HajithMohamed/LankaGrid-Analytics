-- ==============================================================================
-- Query Q21: Five-Year Grid Sales Efficiency & Productive Demand Share Analysis (2020-2024)
-- Member: Member 6 (Grid Efficiency, Reconciliation & Data Quality)
-- Business Question: How did the sectoral distribution of billed electricity consumption,
--                    productive economic demand share, and system sales intensity evolve between 2020 and 2024?
-- Business Relevance: Productive demand share (Industrial + Commercial + Hotel vs Domestic) is the key
--                     utility efficiency metric indicating economic value generated per unit of electricity sold.
-- Relevant Lecture Theory: Lecture 8 (Data Cube Generation with GROUPING SETS),
--                          Lecture 1 (Multi-Year Subject-Oriented Analysis),
--                          Lecture 3 (Avoiding Aggregate Double-Counting).
-- Source Data: CEB Audited Statistical Digests (2020-2024, 5-Year Continuous Coverage).
-- Fact Grain: Multi-level aggregation across Sector Tariff Group and Calendar Year.
-- Measurement Units: Energy in Gigawatt-hours (GWh) and Productive Economic Share (%).
-- Applicable Dates: 2020 to 2024 (5 Calendar Years).
-- Classification: READY (Redesigned as instructed to evaluate 5-year operational efficiency indicators).
-- ==============================================================================

WITH sector_annual_data AS (
    SELECT
        dd.calendar_year,
        dcs.tariff_group,
        dcs.sector_code,
        CASE 
            WHEN dcs.sector_code IN ('INDUSTRIAL', 'GENERAL_PURPOSE', 'HOTEL', 'AGRICULTURE') THEN 'PRODUCTIVE ECONOMIC SECTOR'
            WHEN dcs.sector_code = 'DOMESTIC' THEN 'RESIDENTIAL CONSUMPTION'
            WHEN dcs.sector_code = 'BULK_LECO' THEN 'LECO BULK FRANCHISE'
            ELSE 'CIVIC & PUBLIC SERVICES'
        END AS economic_classification,
        ROUND(fes.energy_sold_mwh / 1000.0, 2) AS sales_gwh
    FROM dw.fact_electricity_sales fes
    JOIN dw.dim_consumption_sector dcs ON fes.sector_key = dcs.sector_key
    JOIN dw.dim_date dd ON fes.period_start_date_key = dd.date_key
    WHERE fes.is_current_revision = TRUE
      AND dcs.sector_code <> 'ALL_SECTORS' -- Strictly exclude published summary to prevent double counting
),
annual_totals AS (
    SELECT
        calendar_year,
        SUM(sales_gwh) AS year_total_gwh
    FROM sector_annual_data
    GROUP BY calendar_year
),
grand_total AS (
    SELECT
        SUM(sales_gwh) AS five_year_total_gwh
    FROM sector_annual_data
)
SELECT
    CASE 
        WHEN GROUPING(sad.calendar_year) = 1 THEN '>>> 5-YEAR TOTAL <<<'
        ELSE sad.calendar_year::text
    END AS reporting_year,
    CASE 
        WHEN GROUPING(sad.economic_classification) = 1 AND GROUPING(sad.calendar_year) = 0 THEN '--- Annual All-Sector Subtotal ---'
        WHEN GROUPING(sad.economic_classification) = 1 AND GROUPING(sad.calendar_year) = 1 THEN 'GRAND 5-YEAR RECONCILED TOTAL'
        ELSE sad.economic_classification
    END AS economic_sector_class,
    ROUND(SUM(sad.sales_gwh), 2) AS total_sales_gwh,
    -- Percentage of annual grid sales (normalized to annual total for subtotals, grand total for 5-year total)
    ROUND(
        100.0 * SUM(sad.sales_gwh) / CASE
            WHEN GROUPING(sad.calendar_year) = 1 THEN (SELECT five_year_total_gwh FROM grand_total)
            ELSE MAX(at.year_total_gwh)
        END,
        2
    ) AS annual_share_pct,
    -- Grouping indicators
    GROUPING(sad.calendar_year) AS grp_year,
    GROUPING(sad.economic_classification) AS grp_class
FROM sector_annual_data sad
LEFT JOIN annual_totals at ON sad.calendar_year = at.calendar_year
GROUP BY GROUPING SETS (
    (sad.calendar_year, sad.economic_classification),
    (sad.calendar_year),
    ()
)
ORDER BY 
    GROUPING(sad.calendar_year) ASC,
    sad.calendar_year,
    GROUPING(sad.economic_classification) ASC,
    SUM(sad.sales_gwh) DESC;

