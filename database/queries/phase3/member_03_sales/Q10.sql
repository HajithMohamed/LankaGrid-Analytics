-- ==============================================================================
-- Query Q10: Sectoral Electricity Consumption Shifts Across Historical Periods (2020-2024)
-- Member: Member 3 (Sectoral Electricity Sales & Demand Dynamics)
-- Business Question: Which consumer sectors experienced the greatest changes between 2020 and 2024?
-- Business Relevance: Quantifies how consumer sectors adapted to macroeconomic shocks,
--                     identifying resilient versus vulnerable customer classes for tariff policy.
-- Relevant Lecture Theory: Lecture 5 (Descriptive Comparative Analytics & Growth Ranking),
--                          Lecture 2 (OLAP Multi-Level Aggregation & Pivoting).
-- Source Data: CEB Audited Statistical Digests (2020-2024).
-- Fact Grain: Sector-level multi-year summary.
-- Measurement Units: Energy in Gigawatt-hours (GWh), 5-Year Net Change (GWh), CAGR (%).
-- Applicable Dates: 2020 to 2024 (5 Years).
-- Classification: READY.
-- ==============================================================================

WITH sector_pivoted_sales AS (
    SELECT
        dcs.sector_code,
        dcs.sector_name,
        dcs.tariff_group,
        ROUND(SUM(CASE WHEN dd.calendar_year = 2020 THEN fes.energy_sold_mwh ELSE 0 END) / 1000.0, 2) AS sales_2020_gwh,
        ROUND(SUM(CASE WHEN dd.calendar_year = 2021 THEN fes.energy_sold_mwh ELSE 0 END) / 1000.0, 2) AS sales_2021_gwh,
        ROUND(SUM(CASE WHEN dd.calendar_year = 2022 THEN fes.energy_sold_mwh ELSE 0 END) / 1000.0, 2) AS sales_2022_gwh,
        ROUND(SUM(CASE WHEN dd.calendar_year = 2023 THEN fes.energy_sold_mwh ELSE 0 END) / 1000.0, 2) AS sales_2023_gwh,
        ROUND(SUM(CASE WHEN dd.calendar_year = 2024 THEN fes.energy_sold_mwh ELSE 0 END) / 1000.0, 2) AS sales_2024_gwh
    FROM dw.fact_electricity_sales fes
    JOIN dw.dim_consumption_sector dcs ON fes.sector_key = dcs.sector_key
    JOIN dw.dim_date dd ON fes.period_start_date_key = dd.date_key
    WHERE fes.is_current_revision = TRUE
      AND dcs.sector_code <> 'ALL_SECTORS'
    GROUP BY dcs.sector_code, dcs.sector_name, dcs.tariff_group
)
SELECT
    sector_code,
    sector_name,
    tariff_group,
    sales_2020_gwh,
    sales_2021_gwh,
    sales_2022_gwh,
    sales_2023_gwh,
    sales_2024_gwh,
    -- Net 5-year volumetric change
    ROUND(sales_2024_gwh - sales_2020_gwh, 2) AS net_5yr_change_gwh,
    -- Percentage change 2020 to 2024
    ROUND(
        100.0 * (sales_2024_gwh - sales_2020_gwh) / NULLIF(sales_2020_gwh, 0),
        2
    ) AS net_5yr_change_pct,
    -- 2022 Crisis Contraction (2022 vs 2021)
    ROUND(
        100.0 * (sales_2022_gwh - sales_2021_gwh) / NULLIF(sales_2021_gwh, 0),
        2
    ) AS crisis_impact_2022_pct,
    -- Compound Annual Growth Rate (CAGR 2020 to 2024)
    CASE 
        WHEN sales_2020_gwh > 0 AND sales_2024_gwh > 0 THEN
            ROUND((POWER((sales_2024_gwh / sales_2020_gwh)::double precision, 1.0 / 4.0) - 1.0)::numeric * 100.0, 2)
        ELSE NULL
    END AS cagr_2020_2024_pct,
    DENSE_RANK() OVER (ORDER BY (sales_2024_gwh - sales_2020_gwh) DESC) AS growth_magnitude_rank
FROM sector_pivoted_sales
ORDER BY net_5yr_change_gwh DESC;
