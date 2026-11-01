-- ==============================================================================
-- Query Q07: Base-Load vs Peaking Plant Operating Behavior & Dispatch Dynamics
-- Member: Member 2 (Grid Dispatch & Operational Dynamics)
-- Business Question: How do selected coal, hydro and thermal plants differ in their
--                    dispatch patterns?
-- Business Relevance: Categorizes generating stations by operational role (constant baseload,
--                     mid-merit load following, or steep peak shaving) to optimize fuel dispatch cost.
-- Relevant Lecture Theory: Lecture 5 (Descriptive Statistics & Dispersion Analysis),
--                          Lecture 3 (Dimension Grouping & Filtering), Lecture 2 (OLAP Ranking).
-- Source Data: PUCSL 15-Minute Operational Dispatch Telemetry (March 2024, 107,115 facts).
-- Fact Grain: 15-minute dispatch interval per plant (2,976 intervals per plant in March).
-- Measurement Units: Active Power in Megawatts (MW), Standard Deviation (MW), Coefficient of Variation (CV).
-- Applicable Dates: March 1, 2024 to March 31, 2024.
-- Classification: READY.
-- ==============================================================================

WITH plant_dispatch_stats AS (
    SELECT
        dpp.plant_name,
        des.energy_category,
        des.fuel_type,
        COUNT(fdi.dispatch_fact_id) AS total_recorded_intervals,
        COUNT(fdi.dispatch_fact_id) FILTER (WHERE fdi.active_power_mw > 0) AS online_intervals,
        COUNT(fdi.dispatch_fact_id) FILTER (WHERE fdi.active_power_mw = 0) AS zero_dispatch_intervals,
        ROUND(MIN(fdi.active_power_mw), 2) AS min_dispatched_mw,
        ROUND(MAX(fdi.active_power_mw), 2) AS peak_dispatched_mw,
        ROUND(AVG(fdi.active_power_mw), 2) AS mean_dispatched_mw,
        ROUND(STDDEV_SAMP(fdi.active_power_mw), 2) AS stddev_dispatched_mw
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_power_plant dpp ON fdi.plant_key = dpp.plant_key
    JOIN dw.dim_energy_source des ON fdi.energy_source_key = des.energy_source_key
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
    GROUP BY dpp.plant_name, des.energy_category, des.fuel_type
    HAVING MAX(fdi.active_power_mw) >= 20.0 -- Focus on major grid-connected utility stations
)
SELECT
    plant_name,
    energy_category,
    fuel_type,
    min_dispatched_mw,
    peak_dispatched_mw,
    mean_dispatched_mw,
    stddev_dispatched_mw,
    -- Coefficient of Variation (CV = sigma / mu): high CV denotes peaking/intermittent; low CV denotes baseload
    ROUND(
        stddev_dispatched_mw / NULLIF(mean_dispatched_mw, 0),
        3
    ) AS coefficient_of_variation,
    -- Operational Load Factor: mean power / peak power
    ROUND(
        100.0 * mean_dispatched_mw / NULLIF(peak_dispatched_mw, 0),
        1
    ) AS operational_load_factor_pct,
    -- Duty Cycle: percentage of month generating active power
    ROUND(
        100.0 * online_intervals / NULLIF(total_recorded_intervals, 0),
        1
    ) AS online_duty_cycle_pct,
    -- Behavioral Classification
    CASE
        WHEN (stddev_dispatched_mw / NULLIF(mean_dispatched_mw, 0)) < 0.25 
             AND (100.0 * online_intervals / total_recorded_intervals) > 95.0 THEN 'CONTINUOUS BASELOAD'
        WHEN (stddev_dispatched_mw / NULLIF(mean_dispatched_mw, 0)) BETWEEN 0.25 AND 0.65 THEN 'MID-MERIT / LOAD FOLLOWING'
        WHEN (stddev_dispatched_mw / NULLIF(mean_dispatched_mw, 0)) > 0.65 
             AND zero_dispatch_intervals > 100 THEN 'CYCLICAL PEAKING'
        ELSE 'VARIABLE / INTERMITTENT'
    END AS operational_behavior_class,
    RANK() OVER (ORDER BY (stddev_dispatched_mw / NULLIF(mean_dispatched_mw, 0)) ASC) AS baseload_stability_rank
FROM plant_dispatch_stats
ORDER BY baseload_stability_rank;
