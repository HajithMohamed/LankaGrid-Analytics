-- ==============================================================================
-- Query Q03: Power Plant Capacity Factor & Utilization Analysis
-- Member: Member 1 (Generation Mix & Renewable Energy Penetration)
-- Business Question: How effectively did selected plants utilize their verified installed
--                    capacities during the available reporting period?
-- Business Relevance: Capacity factor measures base-load efficiency, hydro conservation
--                     strategies, and thermal cycling costs across major grid generators.
-- Relevant Lecture Theory: Lecture 3 (Fact Granularity & Unit Consistency),
--                          Lecture 5 (Ranking & Descriptive Statistics),
--                          Lecture 6 (Handling Data Boundaries & Sentinels).
-- Source Data: PUCSL 15-Minute Operational Dispatch Telemetry (March 2024, 744 hours).
--              Reference Plant Nameplate Ratings from CEB Statistical Digest 2024 / PUCSL Registry.
-- Fact Grain: Plant-level aggregated generation over the 31-day period (744 operating hours).
-- Formula: Capacity Factor (%) = Generated MWh / (Installed Nameplate MW * 744 hours) * 100.
--          Observed Peak Utilization (%) = Generated MWh / (Observed Peak MW * 744 hours) * 100.
-- Applicable Dates: March 1, 2024 to March 31, 2024 (744 period hours).
-- Classification: CONDITIONAL (Uses verified reference nameplate capacities for major stations
--                              alongside empirical observed peak utilization proxies).
-- ==============================================================================

WITH plant_reference_capacity AS (
    -- Authoritative nameplate capacities from CEB Statistical Digest / PUCSL Registry
    SELECT * FROM (VALUES
        ('Lakvijaya Unit 1', 300.0, 'CEB'),
        ('Lakvijaya Unit 2', 300.0, 'CEB'),
        ('Lakvijaya Unit 3', 300.0, 'CEB'),
        ('West Coast (Yugadanavi)', 270.0, 'IPP'),
        ('Kelanitissa Combined Cycle', 165.0, 'CEB'),
        ('Victoria', 210.0, 'CEB'),
        ('Kotmale', 201.0, 'CEB'),
        ('Upper Kotmale', 150.0, 'CEB'),
        ('Samanalawewa', 120.0, 'CEB'),
        ('Randenigala', 122.0, 'CEB'),
        ('New Laxapana', 100.0, 'CEB'),
        ('Polpitiya', 75.0, 'CEB'),
        ('Sapugaskanda Diesel A', 72.0, 'CEB'),
        ('Sapugaskanda Diesel B', 72.0, 'CEB'),
        ('Colombo Harbour Barge-Mounted Plant', 60.0, 'CEB'),
        ('KPS Small Gas Turbines', 68.0, 'CEB'),
        ('Ukuwela', 40.0, 'CEB'),
        ('Bowatenna', 40.0, 'CEB'),
        ('Canyon', 60.0, 'CEB'),
        ('Old Laxapana', 53.5, 'CEB'),
        ('Wimalasurendra', 50.0, 'CEB'),
        ('Sojitz Kelanitissa', 163.0, 'IPP'),
        ('ACE Matara', 24.0, 'IPP')
    ) AS ref(station_name, installed_capacity_mw, operator_category)
),
plant_march_metrics AS (
    SELECT
        dpp.plant_name,
        des.energy_category,
        COUNT(fdi.dispatch_fact_id) AS total_intervals,
        COUNT(fdi.dispatch_fact_id) FILTER (WHERE fdi.active_power_mw > 0) AS online_intervals,
        ROUND(MAX(fdi.active_power_mw), 2) AS observed_peak_mw,
        ROUND(AVG(fdi.active_power_mw), 2) AS avg_power_mw,
        ROUND(SUM(fdi.derived_energy_mwh), 2) AS total_generation_mwh
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_power_plant dpp ON fdi.plant_key = dpp.plant_key
    JOIN dw.dim_energy_source des ON fdi.energy_source_key = des.energy_source_key
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
    GROUP BY dpp.plant_name, des.energy_category
)
SELECT
    pmm.plant_name,
    pmm.energy_category,
    prc.operator_category,
    prc.installed_capacity_mw,
    pmm.observed_peak_mw,
    pmm.total_generation_mwh,
    pmm.online_intervals,
    ROUND(100.0 * pmm.online_intervals / 2976.0, 1) AS duty_cycle_pct,
    -- Official Capacity Factor formula: MWh / (MW * 744h) * 100
    ROUND(
        100.0 * pmm.total_generation_mwh / NULLIF(prc.installed_capacity_mw * 744.0, 0),
        2
    ) AS official_capacity_factor_pct,
    -- Defensible Peak Utilization Proxy: MWh / (Observed Peak MW * 744h) * 100
    ROUND(
        100.0 * pmm.total_generation_mwh / NULLIF(pmm.observed_peak_mw * 744.0, 0),
        2
    ) AS observed_peak_utilization_pct,
    RANK() OVER (ORDER BY pmm.total_generation_mwh DESC) AS generation_rank
FROM plant_march_metrics pmm
JOIN plant_reference_capacity prc ON pmm.plant_name = prc.station_name
ORDER BY pmm.total_generation_mwh DESC;
