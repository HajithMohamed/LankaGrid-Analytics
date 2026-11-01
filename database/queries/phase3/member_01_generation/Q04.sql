-- ==============================================================================
-- Query Q04: Peak, Daytime and Off-Peak Generation Contribution by Technology
-- Member: Member 1 (Generation Mix & Renewable Energy Penetration)
-- Business Question: How do different electricity-generation technologies contribute
--                    across time-of-use periods?
-- Business Relevance: Critical for understanding peaking plant merit order, hydro storage
--                     dispatch during expensive evening peak hours (18:30-22:30), and base-load absorption.
-- Relevant Lecture Theory: Lecture 2 (OLAP Slice & Dice), Lecture 2 (Pivot-Style Multidimensional Aggregation),
--                          Lecture 3 (Conformed Interval Dimension Hierarchy).
-- Source Data: PUCSL 15-Minute Operational Dispatch Telemetry (March 2024, 107,115 facts).
-- Fact Grain: 15-minute dispatch aggregated to technology and tariff time block.
-- Measurement Units: Generation in Megawatt-hours (MWh) and period share (%).
-- Applicable Dates: March 1, 2024 to March 31, 2024.
-- Classification: READY.
-- ==============================================================================

WITH tou_generation AS (
    SELECT
        des.energy_category,
        des.energy_source_code,
        des.is_renewable,
        di.tariff_time_block,
        SUM(fdi.derived_energy_mwh) AS energy_mwh
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_interval di ON fdi.interval_key = di.interval_key
    JOIN dw.dim_energy_source des ON fdi.energy_source_key = des.energy_source_key
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
    GROUP BY des.energy_category, des.energy_source_code, des.is_renewable, di.tariff_time_block
),
pivoted AS (
    SELECT
        energy_category,
        energy_source_code,
        is_renewable,
        ROUND(SUM(CASE WHEN tariff_time_block = 'DAY' THEN energy_mwh ELSE 0 END), 2) AS day_mwh,
        ROUND(SUM(CASE WHEN tariff_time_block = 'PEAK' THEN energy_mwh ELSE 0 END), 2) AS peak_mwh,
        ROUND(SUM(CASE WHEN tariff_time_block = 'OFF_PEAK' THEN energy_mwh ELSE 0 END), 2) AS off_peak_mwh,
        ROUND(SUM(energy_mwh), 2) AS total_mwh
    FROM tou_generation
    GROUP BY energy_category, energy_source_code, is_renewable
),
totals AS (
    SELECT
        SUM(day_mwh) AS total_day_mwh,
        SUM(peak_mwh) AS total_peak_mwh,
        SUM(off_peak_mwh) AS total_off_peak_mwh,
        SUM(total_mwh) AS grand_total_mwh
    FROM pivoted
)
SELECT
    p.energy_category,
    p.energy_source_code,
    CASE WHEN p.is_renewable THEN 'RENEWABLE' ELSE 'CONVENTIONAL' END AS fuel_class,
    p.day_mwh,
    ROUND(100.0 * p.day_mwh / (SELECT total_day_mwh FROM totals), 2) AS day_share_pct,
    p.peak_mwh,
    ROUND(100.0 * p.peak_mwh / (SELECT total_peak_mwh FROM totals), 2) AS peak_share_pct,
    p.off_peak_mwh,
    ROUND(100.0 * p.off_peak_mwh / (SELECT total_off_peak_mwh FROM totals), 2) AS off_peak_share_pct,
    p.total_mwh,
    ROUND(100.0 * p.total_mwh / (SELECT grand_total_mwh FROM totals), 2) AS month_share_pct
FROM pivoted p
ORDER BY p.peak_mwh DESC;
