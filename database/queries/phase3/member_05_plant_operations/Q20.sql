-- ==============================================================================
-- Query Q20: Evening Peak-Hour Generation-Source Contribution & Merit-Order Analysis
-- Member: Member 5 (Plant Operations & Capacity Analysis)
-- Business Question: How did different generation technologies contribute during the critical
--                    evening peak hours (18:30-22:30) vs daytime and off-peak hours across March 2024?
-- Business Relevance: Evaluates grid flexibility and peaking resource adequacy during Sri Lanka's
--                     most stressed operating window, identifying technologies that ramp to meet peak demand.
-- Relevant Lecture Theory: Lecture 2 (OLAP Slice & Dice on Time-of-Use Block),
--                          Lecture 3 (Fact Grain & Dimensional Hierarchy),
--                          Lecture 5 (Peaking Duty Ratio & Contribution Ranking).
-- Source Data: PUCSL 15-Minute Operational Dispatch Telemetry (March 2024, 107,115 facts).
-- Fact Grain: Technology-level aggregation during Evening Peak (18:30-22:30, slots 75..90).
-- Measurement Units: Energy in Megawatt-hours (MWh), Peak MW, and Share of Evening Peak (%).
-- Applicable Dates: March 1, 2024 to March 31, 2024 (124 peak operating hours).
-- Classification: READY (Redesigned as instructed to evaluate peak generation-source contribution).
-- ==============================================================================

WITH tou_source_energy AS (
    SELECT
        des.energy_category,
        des.energy_source_code,
        des.is_renewable,
        di.tariff_time_block,
        SUM(fdi.derived_energy_mwh) AS energy_mwh,
        MAX(fdi.active_power_mw) AS max_active_power_mw,
        AVG(fdi.active_power_mw) AS avg_active_power_mw
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_interval di ON fdi.interval_key = di.interval_key
    JOIN dw.dim_energy_source des ON fdi.energy_source_key = des.energy_source_key
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
    GROUP BY des.energy_category, des.energy_source_code, des.is_renewable, di.tariff_time_block
),
pivoted_tou AS (
    SELECT
        energy_category,
        energy_source_code,
        is_renewable,
        ROUND(SUM(CASE WHEN tariff_time_block = 'PEAK' THEN energy_mwh ELSE 0 END), 2) AS evening_peak_mwh,
        ROUND(MAX(CASE WHEN tariff_time_block = 'PEAK' THEN max_active_power_mw ELSE 0 END), 2) AS max_peak_mw,
        ROUND(AVG(CASE WHEN tariff_time_block = 'PEAK' THEN avg_active_power_mw ELSE 0 END), 2) AS avg_peak_mw,
        ROUND(SUM(CASE WHEN tariff_time_block = 'DAY' THEN energy_mwh ELSE 0 END), 2) AS daytime_mwh,
        ROUND(SUM(CASE WHEN tariff_time_block = 'OFF_PEAK' THEN energy_mwh ELSE 0 END), 2) AS off_peak_mwh,
        ROUND(SUM(energy_mwh), 2) AS total_month_mwh
    FROM tou_source_energy
    GROUP BY energy_category, energy_source_code, is_renewable
),
system_peak_total AS (
    SELECT SUM(evening_peak_mwh) AS total_peak_mwh FROM pivoted_tou
)
SELECT
    pt.energy_category,
    pt.energy_source_code,
    CASE WHEN pt.is_renewable THEN 'RENEWABLE' ELSE 'CONVENTIONAL THERMAL' END AS fuel_class,
    pt.evening_peak_mwh,
    -- Percentage share of the evening peak (18:30-22:30)
    ROUND(100.0 * pt.evening_peak_mwh / (SELECT total_peak_mwh FROM system_peak_total), 2) AS evening_peak_share_pct,
    pt.avg_peak_mw,
    pt.max_peak_mw,
    -- Peaking Duty Index: (Peak Energy Share / Total Month Energy Share)
    -- Value > 1.0 indicates specialized peaking role (ramps up during evening peak)
    ROUND(
        (100.0 * pt.evening_peak_mwh / (SELECT total_peak_mwh FROM system_peak_total)) /
        NULLIF((100.0 * pt.total_month_mwh / (SELECT SUM(total_month_mwh) FROM pivoted_tou)), 0),
        2
    ) AS peaking_duty_index,
    CASE
        WHEN pt.evening_peak_mwh = 0 THEN 'ZERO PEAK CONTRIBUTION (SOLAR)'
        WHEN ((100.0 * pt.evening_peak_mwh / (SELECT total_peak_mwh FROM system_peak_total)) /
             (100.0 * pt.total_month_mwh / (SELECT SUM(total_month_mwh) FROM pivoted_tou))) > 1.25 THEN 'DEDICATED PEAKING RESOURCE'
        WHEN ((100.0 * pt.evening_peak_mwh / (SELECT total_peak_mwh FROM system_peak_total)) /
             (100.0 * pt.total_month_mwh / (SELECT SUM(total_month_mwh) FROM pivoted_tou))) BETWEEN 0.85 AND 1.25 THEN 'BASELOAD / FLAT CARRIER'
        ELSE 'OFF-PEAK / DAYTIME CONCENTRATED'
    END AS peaking_role_classification,
    RANK() OVER (ORDER BY pt.evening_peak_mwh DESC) AS peak_contribution_rank
FROM pivoted_tou pt
ORDER BY peak_contribution_rank;

