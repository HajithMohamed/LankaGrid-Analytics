-- ==============================================================================
-- Query Q17: Zero-Generation Interval and Offline Streak Duration Analysis
-- Member: Member 5 (Plant Operations & Capacity Analysis)
-- Business Question: Which generating units recorded the greatest number or longest
--                    sequences of zero-dispatch intervals?
-- Business Relevance: Highlights plant non-availability, reserve shutdown durations,
--                     and cyclical peaking idling without conflating zero power with missing data.
-- Relevant Lecture Theory: Lecture 5 (Operational Anomaly Detection & Island-and-Gaps Grouping),
--                          Lecture 6 (Preserving Missing Values as Distinct from Zero),
--                          Lecture 2 (OLAP Ranking & Window Aggregation).
-- Source Data: PUCSL 15-Minute Operational Dispatch Telemetry (March 2024, 107,115 facts).
-- Fact Grain: Plant-level aggregated offline and zero-power intervals across 2,976 intervals (744 hours).
-- Measurement Units: Zero Intervals Count, Offline Hours, Max Consecutive Outage Hours.
-- Applicable Dates: March 1, 2024 to March 31, 2024.
-- Classification: READY.
-- ==============================================================================

WITH plant_interval_status AS (
    SELECT
        fdi.plant_key,
        dpp.plant_name,
        des.energy_category,
        fdi.date_key,
        di.interval_index,
        fdi.active_power_mw,
        -- Distinguish true zero from unrecorded/missing data
        CASE 
            WHEN fdi.active_power_mw = 0.0 THEN 'OFFLINE_ZERO'
            WHEN fdi.active_power_mw > 0.0 THEN 'ONLINE_GENERATING'
            ELSE 'MISSING_TELEMETRY'
        END AS operating_state,
        -- Islands and gaps grouping key for consecutive intervals in the same state
        ROW_NUMBER() OVER (PARTITION BY fdi.plant_key ORDER BY fdi.date_key, di.interval_index) -
        ROW_NUMBER() OVER (PARTITION BY fdi.plant_key, (CASE WHEN fdi.active_power_mw = 0.0 THEN 1 ELSE 0 END) ORDER BY fdi.date_key, di.interval_index) AS streak_group
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_power_plant dpp ON fdi.plant_key = dpp.plant_key
    JOIN dw.dim_energy_source des ON fdi.energy_source_key = des.energy_source_key
    JOIN dw.dim_interval di ON fdi.interval_key = di.interval_key
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
),
offline_streaks AS (
    SELECT
        plant_key,
        plant_name,
        energy_category,
        streak_group,
        COUNT(*) AS streak_intervals,
        COUNT(*) * 0.25 AS streak_hours
    FROM plant_interval_status
    WHERE operating_state = 'OFFLINE_ZERO'
    GROUP BY plant_key, plant_name, energy_category, streak_group
),
max_streaks AS (
    SELECT
        plant_key,
        MAX(streak_hours) AS max_consecutive_offline_hours
    FROM offline_streaks
    GROUP BY plant_key
),
plant_summary AS (
    SELECT
        pis.plant_name,
        pis.energy_category,
        COUNT(*) AS total_recorded_intervals,
        COUNT(*) FILTER (WHERE pis.operating_state = 'ONLINE_GENERATING') AS online_intervals,
        COUNT(*) FILTER (WHERE pis.operating_state = 'OFFLINE_ZERO') AS zero_intervals,
        COUNT(*) FILTER (WHERE pis.operating_state = 'MISSING_TELEMETRY') AS missing_intervals,
        ROUND(COUNT(*) FILTER (WHERE pis.operating_state = 'OFFLINE_ZERO') * 0.25, 1) AS total_offline_hours,
        ROUND(100.0 * COUNT(*) FILTER (WHERE pis.operating_state = 'OFFLINE_ZERO') / COUNT(*), 1) AS offline_percentage,
        COALESCE(ms.max_consecutive_offline_hours, 0.0) AS max_consecutive_offline_hours
    FROM plant_interval_status pis
    LEFT JOIN max_streaks ms ON pis.plant_key = ms.plant_key
    GROUP BY pis.plant_name, pis.energy_category, ms.max_consecutive_offline_hours
)
SELECT
    plant_name,
    energy_category,
    total_recorded_intervals,
    online_intervals,
    zero_intervals,
    missing_intervals,
    total_offline_hours,
    offline_percentage,
    max_consecutive_offline_hours,
    CASE
        WHEN zero_intervals = 0 THEN 'CONTINUOUS BASELOAD OPERATION'
        WHEN offline_percentage < 15.0 THEN 'HIGH AVAILABILITY / LOAD FOLLOWING'
        WHEN offline_percentage BETWEEN 15.0 AND 75.0 THEN 'PEAKING / RESERVE CYCLING'
        ELSE 'EXTENDED SHUTDOWN / COLD STANDBY'
    END AS operational_state_label,
    RANK() OVER (ORDER BY zero_intervals DESC) AS offline_rank
FROM plant_summary
ORDER BY offline_rank;
