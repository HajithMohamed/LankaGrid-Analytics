-- ==============================================================================
-- Query Q06: Grid Dispatch Ramp Rate Analysis (15-Minute Load Gradient)
-- Member: Member 2 (Grid Dispatch & Operational Dynamics)
-- Business Question: During which consecutive 15-minute intervals did measured dispatch
--                    change most significantly?
-- Business Relevance: Severe ramp rates (MW/15-min) strain transmission frequency regulation,
--                     requiring fast-responding hydro governor and gas turbine response.
-- Relevant Lecture Theory: Lecture 5 (Anomaly & Outlier Detection), Lecture 5 (Descriptive Trend Analysis),
--                          Lecture 3 (Windowed Analytical Partitions).
-- Source Data: PUCSL 15-Minute Operational Dispatch Telemetry (March 2024, 107,115 facts).
-- Fact Grain: Consecutive 15-minute intervals per calendar day (slots 1..96).
-- Measurement Units: Delta Active Power (MW / 15-min) and Ramp Velocity (MW / minute).
-- Applicable Dates: March 1, 2024 to March 31, 2024.
-- Classification: READY.
-- ==============================================================================

WITH interval_system_power AS (
    SELECT
        fdi.date_key,
        dd.calendar_date,
        dd.day_name,
        di.interval_index,
        di.start_time,
        di.end_time,
        di.tariff_time_block,
        SUM(fdi.active_power_mw) AS total_dispatch_mw
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_interval di ON fdi.interval_key = di.interval_key
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
    GROUP BY fdi.date_key, dd.calendar_date, dd.day_name, di.interval_index, di.start_time, di.end_time, di.tariff_time_block
),
ramping_events AS (
    SELECT
        calendar_date,
        day_name,
        interval_index,
        start_time,
        end_time,
        tariff_time_block,
        total_dispatch_mw,
        LAG(total_dispatch_mw) OVER (
            PARTITION BY date_key 
            ORDER BY interval_index
        ) AS prior_dispatch_mw,
        ROUND(
            total_dispatch_mw - LAG(total_dispatch_mw) OVER (
                PARTITION BY date_key 
                ORDER BY interval_index
            ),
            2
        ) AS ramp_rate_mw,
        ROUND(
            (total_dispatch_mw - LAG(total_dispatch_mw) OVER (
                PARTITION BY date_key 
                ORDER BY interval_index
            )) / 15.0,
            2
        ) AS ramp_velocity_mw_per_min
    FROM interval_system_power
)
SELECT
    calendar_date,
    day_name,
    interval_index,
    start_time,
    end_time,
    tariff_time_block,
    prior_dispatch_mw,
    total_dispatch_mw,
    ramp_rate_mw,
    ramp_velocity_mw_per_min,
    CASE 
        WHEN ramp_rate_mw > 0 THEN 'UPWARD RAMP (SURGE)'
        WHEN ramp_rate_mw < 0 THEN 'DOWNWARD RAMP (SHED)'
        ELSE 'STEADY'
    END AS ramp_direction,
    RANK() OVER (ORDER BY ABS(ramp_rate_mw) DESC NULLS LAST) AS severity_rank
FROM ramping_events
WHERE prior_dispatch_mw IS NOT NULL
ORDER BY ABS(ramp_rate_mw) DESC
LIMIT 25;
