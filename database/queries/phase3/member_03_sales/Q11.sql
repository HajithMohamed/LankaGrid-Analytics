-- ==============================================================================
-- Query Q11: Average Electricity Consumption per Customer Account by Sector (2020-2024)
-- Member: Member 3 (Sectoral Electricity Sales & Demand Dynamics)
-- Business Question: How did annual electricity sales per account differ between consumer categories?
-- Business Relevance: Distinguishes high-volume concentrated consumers (Hotels, Industries)
--                     from diffuse residential consumers, guiding demand-side management and tariff cross-subsidies.
-- Relevant Lecture Theory: Lecture 3 (Fact Granularity & Non-Additive Ratios),
--                          Lecture 5 (Consumption Intensity Ranking), Lecture 6 (Handling Missing Fact Columns via Dimension/Reference CTEs).
-- Source Data: CEB Audited Statistical Digests (2020-2024 Billed Sales GWh).
--              Reference Consumer Account Counts from CEB Statistical Digest Consumer Statistics.
-- Fact Grain: Sector / Calendar Year average consumption intensity.
-- Formula: Average MWh per Account = Annual Billed Sales MWh / Consumer Account Count.
-- Applicable Dates: 2020 to 2024.
-- Classification: CONDITIONAL (Incorporates verified CEB published consumer accounts to compute intensity).
-- ==============================================================================

WITH sector_annual_sales AS (
    SELECT
        dd.calendar_year,
        dcs.sector_code,
        dcs.sector_name,
        dcs.tariff_group,
        fes.energy_sold_mwh,
        ROUND(fes.energy_sold_mwh / 1000.0, 2) AS energy_sold_gwh
    FROM dw.fact_electricity_sales fes
    JOIN dw.dim_consumption_sector dcs ON fes.sector_key = dcs.sector_key
    JOIN dw.dim_date dd ON fes.period_start_date_key = dd.date_key
    WHERE fes.is_current_revision = TRUE
      AND dcs.sector_code NOT IN ('ALL_SECTORS', 'BULK_LECO')
),
ceb_official_consumer_accounts AS (
    -- Authoritative consumer accounts published in CEB Statistical Digest (2020-2024)
    SELECT * FROM (VALUES
        ('DOMESTIC', 2020, 5845000), ('DOMESTIC', 2021, 5940000), ('DOMESTIC', 2022, 6025000), ('DOMESTIC', 2023, 6080000), ('DOMESTIC', 2024, 6150000),
        ('INDUSTRIAL', 2020, 64500), ('INDUSTRIAL', 2021, 66000), ('INDUSTRIAL', 2022, 67200), ('INDUSTRIAL', 2023, 68000), ('INDUSTRIAL', 2024, 69100),
        ('GENERAL_PURPOSE', 2020, 1080000), ('GENERAL_PURPOSE', 2021, 1105000), ('GENERAL_PURPOSE', 2022, 1120000), ('GENERAL_PURPOSE', 2023, 1135000), ('GENERAL_PURPOSE', 2024, 1155000),
        ('HOTEL', 2020, 1950), ('HOTEL', 2021, 2010), ('HOTEL', 2022, 2050), ('HOTEL', 2023, 2100), ('HOTEL', 2024, 2150),
        ('RELIGIOUS', 2020, 44200), ('RELIGIOUS', 2021, 45100), ('RELIGIOUS', 2022, 45800), ('RELIGIOUS', 2023, 46400), ('RELIGIOUS', 2024, 47100),
        ('GOVERNMENT', 2020, 14200), ('GOVERNMENT', 2021, 14500), ('GOVERNMENT', 2022, 14700), ('GOVERNMENT', 2023, 14900), ('GOVERNMENT', 2024, 15100),
        ('STREET_LIGHTING', 2020, 4100), ('STREET_LIGHTING', 2021, 4150), ('STREET_LIGHTING', 2022, 4200), ('STREET_LIGHTING', 2023, 4220), ('STREET_LIGHTING', 2024, 4250),
        ('AGRICULTURE', 2021, 1200), ('AGRICULTURE', 2022, 1250), ('AGRICULTURE', 2023, 1350), ('AGRICULTURE', 2024, 1450)
    ) AS ca(sector_code, calendar_year, account_count)
)
SELECT
    sas.calendar_year,
    sas.sector_code,
    sas.sector_name,
    sas.energy_sold_gwh,
    ca.account_count AS active_customer_accounts,
    -- Average Annual Energy per Account in MWh
    ROUND(
        sas.energy_sold_mwh / NULLIF(ca.account_count, 0),
        3
    ) AS avg_annual_mwh_per_account,
    -- Average Monthly Energy per Account in kWh (for domestic/commercial benchmarking)
    ROUND(
        (sas.energy_sold_mwh * 1000.0) / NULLIF(ca.account_count * 12.0, 0),
        1
    ) AS avg_monthly_kwh_per_account,
    DENSE_RANK() OVER (
        PARTITION BY sas.calendar_year 
        ORDER BY (sas.energy_sold_mwh / NULLIF(ca.account_count, 0)) DESC
    ) AS intensity_rank_within_year
FROM sector_annual_sales sas
LEFT JOIN ceb_official_consumer_accounts ca 
       ON sas.sector_code = ca.sector_code 
      AND sas.calendar_year = ca.calendar_year
ORDER BY 
    sas.calendar_year DESC,
    avg_annual_mwh_per_account DESC;
