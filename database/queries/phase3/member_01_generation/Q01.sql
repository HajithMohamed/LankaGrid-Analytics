-- ==============================================================================
-- Query Q01: Historical Generation Mix by Energy Source
-- Member: Member 1 (Generation Mix & Renewable Energy Penetration)
-- Business Question: How has recorded electricity generation by hydro, coal, oil,
--                    wind, solar and other categories changed across available reporting periods?
-- Business Relevance: Provides the foundational energy generation baseline for Sri Lanka's
--                     grid, tracking fossil vs non-fossil shares to guide national decarbonization.
-- Relevant Lecture Theory: Lecture 2 (OLAP Roll-up & Slice), Lecture 3 (Star Schema Joins),
--                          Lecture 8 (Data Cube Generation with ROLLUP).
-- Source Data: PUCSL 15-Minute Operational Dispatch Telemetry (March 2024, 31 Days, 107,115 facts).
-- Fact Grain: Aggregated from 15-minute dispatch interval facts (grain: station / 15-min interval).
-- Measurement Units: Generation in Megawatt-hours (MWh = MW * 0.25h) and percentage contribution (%).
-- Applicable Dates: March 1, 2024 to March 31, 2024 (744 operating hours).
-- Classification: READY (Fully supported by 107,115 verified dispatch facts).
-- ==============================================================================

WITH station_energy AS (
    SELECT
        des.energy_category,
        des.energy_source_code,
        des.is_renewable,
        SUM(fdi.derived_energy_mwh) AS energy_mwh,
        COUNT(DISTINCT fdi.plant_key) AS active_plant_count
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_energy_source des ON fdi.energy_source_key = des.energy_source_key
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
    GROUP BY des.energy_category, des.energy_source_code, des.is_renewable
),
total_energy AS (
    SELECT SUM(energy_mwh) AS grand_total_mwh FROM station_energy
)
SELECT
    CASE 
        WHEN GROUPING(se.energy_category) = 1 THEN '>>> NATIONAL TOTAL <<<'
        ELSE se.energy_category
    END AS energy_category,
    CASE 
        WHEN GROUPING(se.energy_source_code) = 1 AND GROUPING(se.energy_category) = 0 THEN '--- Category Subtotal ---'
        WHEN GROUPING(se.energy_source_code) = 1 AND GROUPING(se.energy_category) = 1 THEN 'ALL TECHNOLOGIES'
        ELSE se.energy_source_code
    END AS energy_source_code,
    ROUND(SUM(se.energy_mwh), 2) AS total_generation_mwh,
    ROUND(100.0 * SUM(se.energy_mwh) / (SELECT grand_total_mwh FROM total_energy), 2) AS share_pct,
    MAX(se.active_plant_count) AS reporting_plants,
    GROUPING(se.energy_category) AS grp_cat,
    GROUPING(se.energy_source_code) AS grp_src
FROM station_energy se
GROUP BY ROLLUP(se.energy_category, se.energy_source_code)
ORDER BY 
    GROUPING(se.energy_category) ASC,
    SUM(se.energy_mwh) DESC;
