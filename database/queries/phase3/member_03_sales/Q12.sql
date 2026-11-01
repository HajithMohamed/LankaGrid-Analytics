-- ==============================================================================
-- Query Q12: LECO Bulk Supply Versus Direct CEB Retail Distribution Sales (2020-2024)
-- Member: Member 3 (Sectoral Electricity Sales & Demand Dynamics)
-- Business Question: How did bulk electricity supplied to LECO compare with direct
--                    consumer-category sales across the five years?
-- Business Relevance: Compares franchise distribution utility demand (LECO in coastal urban corridors)
--                     against national CEB direct retail areas, analyzing boundary transfers and revenue splits.
-- Relevant Lecture Theory: Lecture 3 (Conformed Dimension Segregation & No Double-Counting),
--                          Lecture 2 (OLAP Roll-Up & Slice), Lecture 8 (CUBE & ROLLUP Aggregation).
-- Source Data: CEB Audited Statistical Digests (2020-2024).
-- Fact Grain: Annual sales volume by distributor channel (LECO vs CEB Direct Retail).
-- Measurement Units: Energy in Gigawatt-hours (GWh) and distribution market share (%).
-- Applicable Dates: 2020 to 2024.
-- Classification: READY.
-- ==============================================================================

WITH sales_channel_breakdown AS (
    SELECT
        dd.calendar_year,
        CASE 
            WHEN dcs.sector_code = 'BULK_LECO' THEN 'LECO FRANCHISE DISTRIBUTION'
            ELSE 'CEB DIRECT RETAIL DISTRIBUTION'
        END AS distribution_channel,
        dcs.sector_code,
        dcs.sector_name,
        ROUND(fes.energy_sold_mwh / 1000.0, 2) AS sales_gwh
    FROM dw.fact_electricity_sales fes
    JOIN dw.dim_consumption_sector dcs ON fes.sector_key = dcs.sector_key
    JOIN dw.dim_date dd ON fes.period_start_date_key = dd.date_key
    WHERE fes.is_current_revision = TRUE
      AND dcs.sector_code <> 'ALL_SECTORS' -- Strictly avoid double counting published summary
),
channel_annual_totals AS (
    SELECT
        calendar_year,
        SUM(CASE WHEN distribution_channel = 'CEB DIRECT RETAIL DISTRIBUTION' THEN sales_gwh ELSE 0 END) AS ceb_retail_sales_gwh,
        SUM(CASE WHEN distribution_channel = 'LECO FRANCHISE DISTRIBUTION' THEN sales_gwh ELSE 0 END) AS leco_bulk_sales_gwh,
        SUM(sales_gwh) AS total_national_billed_sales_gwh
    FROM sales_channel_breakdown
    GROUP BY calendar_year
)
SELECT
    cat.calendar_year,
    cat.ceb_retail_sales_gwh,
    cat.leco_bulk_sales_gwh,
    cat.total_national_billed_sales_gwh,
    -- Market Shares
    ROUND(100.0 * cat.ceb_retail_sales_gwh / NULLIF(cat.total_national_billed_sales_gwh, 0), 2) AS ceb_retail_share_pct,
    ROUND(100.0 * cat.leco_bulk_sales_gwh / NULLIF(cat.total_national_billed_sales_gwh, 0), 2) AS leco_bulk_share_pct,
    -- Ratio of CEB Retail to LECO Bulk
    ROUND(cat.ceb_retail_sales_gwh / NULLIF(cat.leco_bulk_sales_gwh, 0), 2) AS ceb_to_leco_ratio,
    -- YoY Growth for LECO Bulk Supply
    ROUND(
        100.0 * (cat.leco_bulk_sales_gwh - LAG(cat.leco_bulk_sales_gwh) OVER (ORDER BY cat.calendar_year)) /
        NULLIF(LAG(cat.leco_bulk_sales_gwh) OVER (ORDER BY cat.calendar_year), 0),
        2
    ) AS leco_yoy_growth_pct,
    -- YoY Growth for CEB Direct Retail
    ROUND(
        100.0 * (cat.ceb_retail_sales_gwh - LAG(cat.ceb_retail_sales_gwh) OVER (ORDER BY cat.calendar_year)) /
        NULLIF(LAG(cat.ceb_retail_sales_gwh) OVER (ORDER BY cat.calendar_year), 0),
        2
    ) AS ceb_retail_yoy_growth_pct
FROM channel_annual_totals cat
ORDER BY cat.calendar_year;
