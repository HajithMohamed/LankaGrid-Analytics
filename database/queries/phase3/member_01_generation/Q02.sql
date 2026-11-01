-- ==============================================================================
-- Query Q02: Renewable Versus Non-Renewable Generation Daily Share
-- Member: Member 1 (Generation Mix & Renewable Energy Penetration)
-- Business Question: What share of measured generation came from renewable versus
--                    non-renewable sources during compatible reporting periods?
-- Business Relevance: Directly tracks Sri Lanka's statutory target of 70% renewable
--                     generation by 2030, showing daily operational swings driven by hydro availability.
-- Relevant Lecture Theory: Lecture 2 (OLAP Slice & Dice), Lecture 5 (Descriptive Trend Analysis),
--                          Lecture 3 (Fact Constellation Star Schema).
-- Source Data: PUCSL 15-Minute Operational Dispatch Telemetry (March 2024, 31 Days, 107,115 facts).
-- Fact Grain: Daily technology aggregation from 15-minute dispatch interval facts.
-- Measurement Units: Energy in Megawatt-hours (MWh) and daily renewable penetration share (%).
-- Applicable Dates: March 1, 2024 to March 31, 2024 (31 consecutive days).
-- Classification: READY.
-- ==============================================================================

WITH daily_classification AS (
    SELECT
        dd.calendar_date,
        dd.day_name,
        dd.is_weekend,
        ROUND(SUM(CASE WHEN des.is_renewable THEN fdi.derived_energy_mwh ELSE 0 END), 2) AS renewable_mwh,
        ROUND(SUM(CASE WHEN NOT des.is_renewable THEN fdi.derived_energy_mwh ELSE 0 END), 2) AS non_renewable_mwh,
        ROUND(SUM(fdi.derived_energy_mwh), 2) AS total_daily_mwh
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_energy_source des ON fdi.energy_source_key = des.energy_source_key
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
    GROUP BY dd.calendar_date, dd.day_name, dd.is_weekend
)
SELECT
    calendar_date,
    day_name,
    is_weekend,
    renewable_mwh,
    non_renewable_mwh,
    total_daily_mwh,
    ROUND(100.0 * renewable_mwh / NULLIF(total_daily_mwh, 0), 2) AS renewable_share_pct,
    ROUND(100.0 * non_renewable_mwh / NULLIF(total_daily_mwh, 0), 2) AS thermal_share_pct,
    -- 7-day centered moving average of renewable share to smooth day-of-week volatility
    ROUND(
        AVG(100.0 * renewable_mwh / NULLIF(total_daily_mwh, 0)) OVER (
            ORDER BY calendar_date
            ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
        ),
        2
    ) AS renewable_share_7d_ma_pct
FROM daily_classification
ORDER BY calendar_date;
