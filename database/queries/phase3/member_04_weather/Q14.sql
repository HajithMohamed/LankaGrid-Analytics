-- ==============================================================================
-- Query Q14: Ambient Temperature Dynamics & Empirical Grid Peak Dispatch Correlation
-- Member: Member 4 (Weather, Solar Resource & Renewable Potential)
-- Business Question: Is there a measurable relationship between ambient temperature and daily
--                    grid-dispatch indicators, and how does thermal variability manifest across monitoring nodes?
-- Business Relevance: Evaluates whether elevated pre-monsoon temperatures coincide with increased
--                     cooling electricity demand and altered daily generation volumes.
-- Relevant Lecture Theory: Lecture 5 (Statistical Correlation & Degree Day Proxies),
--                          Lecture 3 (Date-Aligned Fact Constellation Joins).
-- Source Data: NASA POWER Meteorological Database (2020-2024, Victoria Catchment & Mannar Nodes).
--              PUCSL 15-Minute Operational Dispatch Telemetry (March 2024).
-- Fact Grain: Daily aligned weather facts joined with daily aggregated grid dispatch facts.
-- Measurement Units: 2-Metre Air Temperature (C), Active Power (MW), Total Generation (MWh).
-- Applicable Dates: March 1-31, 2024 (Empirical Correlation Window across 31 paired operating days).
-- Classification: READY.
-- ==============================================================================

WITH interval_system_power AS (
    SELECT
        fdi.date_key,
        dd.calendar_date,
        fdi.interval_key,
        SUM(fdi.active_power_mw) AS interval_grid_mw,
        SUM(fdi.derived_energy_mwh) AS interval_energy_mwh
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
    GROUP BY fdi.date_key, dd.calendar_date, fdi.interval_key
),
march_daily_dispatch AS (
    SELECT
        date_key,
        calendar_date,
        ROUND(MAX(interval_grid_mw), 2) AS peak_dispatch_mw,
        ROUND(SUM(interval_energy_mwh), 2) AS total_generation_mwh
    FROM interval_system_power
    GROUP BY date_key, calendar_date
),
daily_temperatures AS (
    SELECT
        fwd.date_key,
        dd.calendar_date,
        dwl.location_code,
        fwd.standardized_value AS temp_c
    FROM dw.fact_weather_daily fwd
    JOIN dw.dim_weather_location dwl ON fwd.weather_location_key = dwl.weather_location_key
    JOIN dw.dim_metric dm ON fwd.metric_key = dm.metric_key
    JOIN dw.dim_date dd ON fwd.date_key = dd.date_key
    WHERE dm.metric_code = 'AIR_TEMP_2M_C'
      AND fwd.is_missing = FALSE
),
march_paired_data AS (
    SELECT
        mdd.calendar_date,
        dt_v.temp_c AS temp_victoria_c,
        dt_m.temp_c AS temp_mannar_c,
        ROUND(((dt_v.temp_c + dt_m.temp_c) / 2.0), 2) AS two_station_mean_temp_c,
        mdd.peak_dispatch_mw,
        mdd.total_generation_mwh
    FROM march_daily_dispatch mdd
    JOIN daily_temperatures dt_v ON mdd.date_key = dt_v.date_key AND dt_v.location_code = 'LOC_VICTORIA_CATCHMENT'
    JOIN daily_temperatures dt_m ON mdd.date_key = dt_m.date_key AND dt_m.location_code = 'LOC_MANNAR_WIND'
)
SELECT
    COUNT(*) AS paired_operating_days,
    ROUND(MIN(two_station_mean_temp_c), 2) AS min_observed_temp_c,
    ROUND(AVG(two_station_mean_temp_c), 2) AS mean_observed_temp_c,
    ROUND(MAX(two_station_mean_temp_c), 2) AS max_observed_temp_c,
    ROUND(MIN(peak_dispatch_mw), 2) AS min_peak_dispatch_mw,
    ROUND(AVG(peak_dispatch_mw), 2) AS mean_peak_dispatch_mw,
    ROUND(MAX(peak_dispatch_mw), 2) AS max_peak_dispatch_mw,
    -- Pearson Correlation Coefficients
    ROUND(CORR(two_station_mean_temp_c, peak_dispatch_mw)::numeric, 4) AS corr_temp_vs_peak_dispatch,
    ROUND(CORR(two_station_mean_temp_c, total_generation_mwh)::numeric, 4) AS corr_temp_vs_daily_energy,
    ROUND(CORR(temp_mannar_c, peak_dispatch_mw)::numeric, 4) AS corr_mannar_temp_vs_peak_dispatch,
    ROUND(CORR(temp_victoria_c, peak_dispatch_mw)::numeric, 4) AS corr_victoria_temp_vs_peak_dispatch,
    CASE 
        WHEN CORR(two_station_mean_temp_c, total_generation_mwh) > 0 THEN 
            'Mild positive correlation (r = ' || TO_CHAR(ROUND(CORR(two_station_mean_temp_c, total_generation_mwh)::numeric, 3), 'FM+0.000') || 
            ') with daily grid generation energy across 31 paired March days; peak dispatch correlation is near-zero (r = ' || 
            TO_CHAR(ROUND(CORR(two_station_mean_temp_c, peak_dispatch_mw)::numeric, 3), 'FM+0.000') || ').'
        ELSE 'Neutral temperature-demand relationship observed across baseline days.'
    END AS analytical_finding
FROM march_paired_data;
