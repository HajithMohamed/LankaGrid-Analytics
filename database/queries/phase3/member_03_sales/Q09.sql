-- ==============================================================================
-- Query Q09: Five-Year Sectoral Electricity Sales Trends (2020-2024)
-- Member: Member 3 (Sectoral Electricity Sales & Demand Dynamics)
-- Business Question: How did electricity sales change across consumer categories
--                    from 2020 to 2024?
-- Business Relevance: Evaluates long-term national electricity demand trajectories,
--                     capturing the impact of COVID-19, the 2022 macroeconomic crisis,
--                     and tariff restructuring on domestic and industrial consumption.
-- Relevant Lecture Theory: Lecture 1 (Historical Non-Volatile Data Analysis),
--                          Lecture 2 (OLAP Drill-Down across Time Hierarchy),
--                          Lecture 5 (YoY Trend Analysis using Analytical Windows).
-- Source Data: CEB Audited Statistical Digests (2020-2024, 5-Year Continuous Coverage).
-- Fact Grain: Annual sales volume per consumption sector (grain: sector / calendar year).
-- Measurement Units: Energy Sold in Gigawatt-hours (GWh) and Megawatt-hours (MWh), YoY Growth (%).
-- Applicable Dates: Calendar Years 2020, 2021, 2022, 2023, 2024.
-- Classification: READY (Fully supported by 49 audited fact rows).
-- ==============================================================================

WITH sector_annual_sales AS (
    SELECT
        dd.calendar_year,
        dcs.sector_code,
        dcs.sector_name,
        dcs.tariff_group,
        fes.energy_sold_mwh,
        ROUND(fes.energy_sold_mwh / 1000.0, 2) AS energy_sold_gwh,
        fes.consumer_account_count,
        fes.revenue_lkr
    FROM dw.fact_electricity_sales fes
    JOIN dw.dim_consumption_sector dcs ON fes.sector_key = dcs.sector_key
    JOIN dw.dim_date dd ON fes.period_start_date_key = dd.date_key
    WHERE fes.is_current_revision = TRUE
      AND dcs.sector_code <> 'ALL_SECTORS' -- Prevent double-counting aggregate summary with constituents
)
SELECT
    calendar_year,
    sector_code,
    sector_name,
    tariff_group,
    energy_sold_gwh,
    -- Prior year sales using window LAG()
    LAG(energy_sold_gwh) OVER (
        PARTITION BY sector_code 
        ORDER BY calendar_year
    ) AS prior_year_sales_gwh,
    -- YoY Growth in GWh and Percentage
    ROUND(
        energy_sold_gwh - LAG(energy_sold_gwh) OVER (
            PARTITION BY sector_code 
            ORDER BY calendar_year
        ),
        2
    ) AS yoy_change_gwh,
    ROUND(
        100.0 * (energy_sold_gwh - LAG(energy_sold_gwh) OVER (
            PARTITION BY sector_code 
            ORDER BY calendar_year
        )) / NULLIF(LAG(energy_sold_gwh) OVER (
            PARTITION BY sector_code 
            ORDER BY calendar_year
        ), 0),
        2
    ) AS yoy_growth_pct,
    -- Sectoral share of total annual sales (excluding bulk LECO)
    ROUND(
        100.0 * energy_sold_gwh / NULLIF(
            SUM(CASE WHEN sector_code <> 'BULK_LECO' THEN energy_sold_gwh ELSE 0 END) OVER (
                PARTITION BY calendar_year
            ),
            0
        ),
        2
    ) AS retail_market_share_pct
FROM sector_annual_sales
ORDER BY 
    sector_code,
    calendar_year;
