-- ==============================================================================
-- Query Q13: Five-Year Daily Solar Irradiance Profiles: Victoria Hydro vs Mannar Corridor (2020-2024)
-- Member: Member 4 (Weather, Solar Resource & Renewable Potential)
-- Business Question: How did solar irradiance vary over time between Victoria and Mannar?
-- Business Relevance: Evaluates solar resource complementarity: comparing high-insolation northern
--                     arid zones (Mannar) against cloudy mountain hydro catchment basins (Victoria).
-- Relevant Lecture Theory: Lecture 1 (Time-Variant Meteorological Analysis),
--                          Lecture 2 (OLAP Multi-Level Roll-Up by Year and Month),
--                          Lecture 5 (Descriptive Dispersion: Min, Mean, Max, StdDev).
-- Source Data: NASA POWER Solar & Meteorological Database (2020-2024, 1,827 Days, 21,924 facts).
-- Fact Grain: Daily aggregated solar insolation per geographical node (grain: location / calendar date).
-- Measurement Units: All-Sky Surface Shortwave Downward Irradiance in Megajoules per square metre per day (MJ/m2/day).
-- Applicable Dates: January 1, 2020 to December 31, 2024 (1,827 consecutive days).
-- Classification: READY.
-- ==============================================================================

WITH daily_insolation AS (
    SELECT
        dd.calendar_year,
        dd.month_number,
        dd.month_name,
        dd.calendar_date,
        dwl.location_code,
        dwl.location_name,
        fwd.standardized_value AS irradiance_mj_m2_day
    FROM dw.fact_weather_daily fwd
    JOIN dw.dim_weather_location dwl ON fwd.weather_location_key = dwl.weather_location_key
    JOIN dw.dim_metric dm ON fwd.metric_key = dm.metric_key
    JOIN dw.dim_date dd ON fwd.date_key = dd.date_key
    WHERE dm.metric_code = 'SOLAR_IRRADIANCE_SW_DWN'
      AND fwd.is_missing = FALSE
      AND fwd.is_current_revision = TRUE
)
SELECT
    calendar_year,
    location_code,
    location_name,
    COUNT(calendar_date) AS valid_days_measured,
    ROUND(MIN(irradiance_mj_m2_day), 2) AS min_daily_irradiance_mj,
    ROUND(AVG(irradiance_mj_m2_day), 2) AS mean_daily_irradiance_mj,
    ROUND(MAX(irradiance_mj_m2_day), 2) AS max_daily_irradiance_mj,
    ROUND(STDDEV_SAMP(irradiance_mj_m2_day), 2) AS stddev_irradiance_mj,
    -- Converted daily equivalent in kWh/m2/day (1 kWh = 3.6 MJ) for PV engineering comparison
    ROUND(AVG(irradiance_mj_m2_day) / 3.6, 3) AS mean_daily_kwh_per_m2,
    -- Peak Sun Hours (PSH) proxy per day
    ROUND(AVG(irradiance_mj_m2_day) / 3.6, 2) AS approx_peak_sun_hours_psh
FROM daily_insolation
GROUP BY calendar_year, location_code, location_name
ORDER BY calendar_year, location_code;
