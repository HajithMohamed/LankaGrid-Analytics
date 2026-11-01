-- ==============================================================================
-- Query Q15: Five-Year Seasonal Monsoon Impact on Rainfall and Solar Insolation (2020-2024)
-- Member: Member 4 (Weather, Solar Resource & Renewable Potential)
-- Business Question: How do rainfall and solar irradiance patterns vary by month
--                    and season over five years?
-- Business Relevance: Directly informs the water-energy nexus in Sri Lanka: Southwest Monsoon
--                     fills major Mahaweli hydro reservoirs (Victoria, Kotmale) but suppresses solar PV,
--                     while dry inter-monsoons require thermal oil substitution.
-- Relevant Lecture Theory: Lecture 8 (Data Cube Generation with CUBE), Lecture 2 (OLAP Multidimensional Aggregation),
--                          Lecture 5 (Seasonal Pattern Identification).
-- Source Data: NASA POWER Meteorological Database (2020-2024, 21,924 facts).
-- Fact Grain: Seasonal summary per geographical node across 1,827 days.
-- Measurement Units: Total Rainfall (mm), Mean Daily Precipitation (mm/day), Mean Daily Solar Irradiance (MJ/m2/day).
-- Applicable Dates: 2020 to 2024 (5 full calendar years).
-- Classification: READY.
-- ==============================================================================

WITH daily_weather_metrics AS (
    SELECT
        dd.date_key,
        dd.calendar_year,
        dd.sl_monsoon_season,
        dwl.location_code,
        dwl.location_name,
        MAX(CASE WHEN dm.metric_code = 'PRECIPITATION_DAILY_MM' THEN fwd.standardized_value END) AS precip_mm,
        MAX(CASE WHEN dm.metric_code = 'SOLAR_IRRADIANCE_SW_DWN' THEN fwd.standardized_value END) AS solar_mj
    FROM dw.fact_weather_daily fwd
    JOIN dw.dim_weather_location dwl ON fwd.weather_location_key = dwl.weather_location_key
    JOIN dw.dim_metric dm ON fwd.metric_key = dm.metric_key
    JOIN dw.dim_date dd ON fwd.date_key = dd.date_key
    WHERE fwd.is_missing = FALSE
      AND fwd.is_current_revision = TRUE
      AND dm.metric_code IN ('PRECIPITATION_DAILY_MM', 'SOLAR_IRRADIANCE_SW_DWN')
    GROUP BY dd.date_key, dd.calendar_year, dd.sl_monsoon_season, dwl.location_code, dwl.location_name
)
SELECT
    CASE 
        WHEN GROUPING(location_name) = 1 THEN '>>> ALL LOCATIONS <<<'
        ELSE location_name
    END AS location_name,
    CASE 
        WHEN GROUPING(sl_monsoon_season) = 1 THEN '--- ALL SEASONS (ANNUAL) ---'
        ELSE sl_monsoon_season
    END AS monsoon_season,
    COUNT(date_key) AS observed_days,
    -- Rainfall Metrics
    ROUND(SUM(precip_mm), 1) AS total_rainfall_mm,
    ROUND(AVG(precip_mm), 2) AS mean_daily_rain_mm,
    ROUND(MAX(precip_mm), 2) AS max_single_day_rain_mm,
    -- Solar Insolation Metrics
    ROUND(AVG(solar_mj), 2) AS mean_daily_solar_mj,
    ROUND(AVG(solar_mj) / 3.6, 2) AS mean_daily_psh,
    -- Cube Grouping Flags
    GROUPING(location_name) AS grp_loc,
    GROUPING(sl_monsoon_season) AS grp_season
FROM daily_weather_metrics
GROUP BY CUBE(location_name, sl_monsoon_season)
ORDER BY 
    GROUPING(location_name) ASC,
    location_name,
    GROUPING(sl_monsoon_season) ASC,
    AVG(precip_mm) DESC;
