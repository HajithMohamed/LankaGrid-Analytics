-- ==============================================================================
-- Query Q05: 15-Minute Daily Dispatch Curves (Weekday vs Weekend Profile)
-- Member: Member 2 (Grid Dispatch & Operational Dynamics)
-- Business Question: How do observed dispatch profiles differ between weekdays and
--                    weekends in March 2024?
-- Business Relevance: Quantifies the industrial and commercial demand swing between working
--                     days and weekends, informing unit commitment and spinning reserve scheduling.
-- Relevant Lecture Theory: Lecture 2 (OLAP Slice & Dice), Lecture 3 (Time Dimension Grain),
--                          Lecture 5 (Descriptive Time-Series Comparison).
-- Source Data: PUCSL 15-Minute Operational Dispatch Telemetry (March 2024, 31 Days, 107,115 facts).
-- Fact Grain: 15-minute interval slot (1..96) aggregated across 21 weekdays and 10 weekend days.
-- Measurement Units: Average, Minimum, and Maximum Instantaneous Active Power (MW).
-- Applicable Dates: March 1, 2024 to March 31, 2024.
-- Classification: READY.
-- ==============================================================================

WITH slot_day_totals AS (
    SELECT
        fdi.date_key,
        dd.is_weekend,
        di.interval_index,
        di.start_time,
        di.end_time,
        di.tariff_time_block,
        SUM(fdi.active_power_mw) AS total_dispatch_mw
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_interval di ON fdi.interval_key = di.interval_key
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
    GROUP BY fdi.date_key, dd.is_weekend, di.interval_index, di.start_time, di.end_time, di.tariff_time_block
)
SELECT
    interval_index AS interval_slot_number,
    start_time,
    end_time,
    tariff_time_block,
    -- Weekday Aggregations (21 days)
    ROUND(AVG(CASE WHEN NOT is_weekend THEN total_dispatch_mw END), 2) AS weekday_avg_mw,
    ROUND(MIN(CASE WHEN NOT is_weekend THEN total_dispatch_mw END), 2) AS weekday_min_mw,
    ROUND(MAX(CASE WHEN NOT is_weekend THEN total_dispatch_mw END), 2) AS weekday_max_mw,
    -- Weekend Aggregations (10 days)
    ROUND(AVG(CASE WHEN is_weekend THEN total_dispatch_mw END), 2) AS weekend_avg_mw,
    ROUND(MIN(CASE WHEN is_weekend THEN total_dispatch_mw END), 2) AS weekend_min_mw,
    ROUND(MAX(CASE WHEN is_weekend THEN total_dispatch_mw END), 2) AS weekend_max_mw,
    -- Weekday vs Weekend Differential
    ROUND(
        AVG(CASE WHEN NOT is_weekend THEN total_dispatch_mw END) - 
        AVG(CASE WHEN is_weekend THEN total_dispatch_mw END),
        2
    ) AS weekday_weekend_spread_mw,
    -- Percentage reduction on weekends
    ROUND(
        100.0 * (
            AVG(CASE WHEN NOT is_weekend THEN total_dispatch_mw END) - 
            AVG(CASE WHEN is_weekend THEN total_dispatch_mw END)
        ) / NULLIF(AVG(CASE WHEN NOT is_weekend THEN total_dispatch_mw END), 0),
        2
    ) AS weekend_demand_drop_pct
FROM slot_day_totals
GROUP BY interval_index, start_time, end_time, tariff_time_block
ORDER BY interval_index;
