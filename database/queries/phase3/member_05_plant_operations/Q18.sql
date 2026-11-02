-- ==============================================================================
-- Query Q18: Power Plant Peak Dispatch vs Installed Nameplate Capacity Analysis
-- Member: Member 5 (Plant Operations & Capacity Analysis)
-- Business Question: How does observed peak dispatch compare with historically valid installed capacity?
-- Business Relevance: Determines whether thermal and hydro stations achieve their rated nameplate
--                     output under ambient operating conditions, or suffer derating / transmission bottlenecks.
-- Relevant Lecture Theory: Lecture 3 (Physical Dimension Attributes & Non-Additive Ratios),
--                          Lecture 5 (Ratio Analysis & Capacity Envelope Ranking).
-- Source Data: PUCSL 15-Minute Operational Dispatch Telemetry (March 2024).
--              Reference Plant Nameplate Ratings from CEB Statistical Digest / PUCSL Registry.
-- Fact Grain: Plant-level operational capacity comparison over 744 operating hours.
-- Measurement Units: Megawatts (MW), Peak Capacity Ratio (%), Mean Capacity Factor (%).
-- Applicable Dates: March 1, 2024 to March 31, 2024.
-- Classification: CONDITIONAL (Uses verified CEB/PUCSL reference nameplate ratings).
-- ==============================================================================

WITH plant_reference_ratings AS (
    SELECT * FROM (VALUES
        ('Lakvijaya Unit 1', 300.0, 'Thermal Coal', 'CEB'),
        ('Lakvijaya Unit 2', 300.0, 'Thermal Coal', 'CEB'),
        ('Lakvijaya Unit 3', 300.0, 'Thermal Coal', 'CEB'),
        ('West Coast (Yugadanavi)', 270.0, 'Thermal Oil', 'IPP'),
        ('Kelanitissa Combined Cycle', 165.0, 'Thermal Oil', 'CEB'),
        ('Victoria', 210.0, 'Hydro', 'CEB'),
        ('Kotmale', 201.0, 'Hydro', 'CEB'),
        ('Upper Kotmale', 150.0, 'Hydro', 'CEB'),
        ('Randenigala', 122.0, 'Hydro', 'CEB'),
        ('Samanalawewa', 120.0, 'Hydro', 'CEB'),
        ('New Laxapana', 100.0, 'Hydro', 'CEB'),
        ('Polpitiya', 75.0, 'Hydro', 'CEB'),
        ('Sapugaskanda Diesel A', 72.0, 'Thermal Oil', 'CEB'),
        ('Sapugaskanda Diesel B', 72.0, 'Thermal Oil', 'CEB'),
        ('Colombo Harbour Barge-Mounted Plant', 60.0, 'Thermal Oil', 'CEB'),
        ('Canyon', 60.0, 'Hydro', 'CEB'),
        ('Old Laxapana', 53.5, 'Hydro', 'CEB'),
        ('Wimalasurendra', 50.0, 'Hydro', 'CEB'),
        ('Ukuwela', 40.0, 'Hydro', 'CEB'),
        ('Bowatenna', 40.0, 'Hydro', 'CEB'),
        ('Sojitz Kelanitissa', 163.0, 'Thermal Oil', 'IPP'),
        ('Kelanitissa Gas Turbine 7', 115.0, 'Thermal Oil', 'CEB'),
        ('Kelanitissa Small Gas Turbines', 68.0, 'Thermal Oil', 'CEB'),
        ('ACE Matara', 24.0, 'Thermal Oil', 'IPP')
    ) AS ref(station_name, installed_capacity_mw, technology_type, operator_type)
),
observed_dispatch_peaks AS (
    SELECT
        dpp.plant_name,
        ROUND(MIN(fdi.active_power_mw), 2) AS min_power_mw,
        ROUND(AVG(fdi.active_power_mw), 2) AS mean_power_mw,
        ROUND(MAX(fdi.active_power_mw), 2) AS observed_peak_mw,
        ROUND(SUM(fdi.derived_energy_mwh), 2) AS total_generation_mwh
    FROM dw.fact_dispatch_interval fdi
    JOIN dw.dim_power_plant dpp ON fdi.plant_key = dpp.plant_key
    JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
    WHERE dd.calendar_year = 2024 AND dd.month_number = 3
    GROUP BY dpp.plant_name
)
SELECT
    prr.station_name,
    prr.technology_type,
    prr.operator_type,
    prr.installed_capacity_mw,
    odp.observed_peak_mw,
    -- Peak to Nameplate Ratio
    ROUND(
        100.0 * odp.observed_peak_mw / NULLIF(prr.installed_capacity_mw, 0),
        1
    ) AS peak_to_nameplate_ratio_pct,
    odp.mean_power_mw,
    -- Mean Utilization Factor
    ROUND(
        100.0 * odp.mean_power_mw / NULLIF(prr.installed_capacity_mw, 0),
        1
    ) AS mean_capacity_utilization_pct,
    -- Unused Peak Headroom (Derating or Operational Reserve)
    ROUND(
        prr.installed_capacity_mw - odp.observed_peak_mw,
        2
    ) AS peak_headroom_mw,
    CASE
        WHEN (odp.observed_peak_mw / NULLIF(prr.installed_capacity_mw, 0)) > 1.00 THEN 'OBSERVED PEAK EXCEEDS REFERENCE NAMEPLATE (FURTHER EVIDENCE REQUIRED)'
        WHEN (odp.observed_peak_mw / NULLIF(prr.installed_capacity_mw, 0)) >= 0.95 THEN 'FULL NAMEPLATE CAPABILITY DELIVERED'
        WHEN (odp.observed_peak_mw / NULLIF(prr.installed_capacity_mw, 0)) BETWEEN 0.80 AND 0.95 THEN 'NEAR-RATED DISPATCH (MILD DERATING)'
        WHEN odp.observed_peak_mw > 0 THEN 'CONSTRAINED / PARTIAL DISPATCH'
        ELSE 'ZERO RECORDED DISPATCH (RESERVE STANDBY OR OUTAGE)'
    END AS operational_delivery_status,
    RANK() OVER (ORDER BY (odp.observed_peak_mw / NULLIF(prr.installed_capacity_mw, 0)) DESC) AS peak_ratio_rank
FROM plant_reference_ratings prr
JOIN observed_dispatch_peaks odp ON prr.station_name = odp.plant_name
ORDER BY peak_ratio_rank;

