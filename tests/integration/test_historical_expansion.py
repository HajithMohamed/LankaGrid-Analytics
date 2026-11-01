"""
Integration tests for Phase 2.2 Five-Year Historical Data Expansion:
- CEB 5-Year Billed Electricity Sales (2020-2024)
- NASA POWER 5-Year Meteorological Observations (2020-2024: 21,924 records)
- PUCSL 31-Day March 2024 Sub-Daily 15-Minute Dispatch
Follows strict TDD Red -> Green protocol.
"""

from datetime import date
from pathlib import Path

import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection
from src.etl.real_data_loader import RealDataWarehouseLoader


@pytest.fixture(scope="module")
def real_loader(migrated_and_seeded_test_db: DatabaseConfig) -> RealDataWarehouseLoader:
    return RealDataWarehouseLoader(config=migrated_and_seeded_test_db)


@pytest.mark.integration
def test_etl_loads_5yr_ceb_sales(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
):
    """Verify loading CEB Statistical Digests for 2020-2024 into dw.fact_electricity_sales."""
    results = real_loader.load_5yr_ceb_sales()
    assert len(results) == 5
    for r in results:
        assert r.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")
        assert r.rows_inserted > 0

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # Query annual total sales per year
            cur.execute(
                """
                SELECT
                    dd.calendar_year,
                    sum(fes.energy_sold_mwh)
                FROM dw.fact_electricity_sales fes
                JOIN dw.dim_date dd ON fes.period_start_date_key = dd.date_key
                JOIN dw.dim_consumption_sector cs ON fes.sector_key = cs.sector_key
                WHERE cs.sector_code <> 'ALL_SECTORS'
                GROUP BY dd.calendar_year
                ORDER BY dd.calendar_year;
                """
            )
            rows = cur.fetchall()
            year_totals = {r[0]: float(r[1]) for r in rows}

            # Verify all 5 calendar years are present
            assert 2020 in year_totals
            assert 2021 in year_totals
            assert 2022 in year_totals
            assert 2023 in year_totals
            assert 2024 in year_totals

            # Reconcile against official CEB published national sales (GWh -> MWh)
            # 2020: 14,286 GWh = 14,286,000 MWh
            assert 14000000.0 <= year_totals[2020] <= 14500000.0
            # 2021: 15,214 GWh = 15,214,000 MWh
            assert 15000000.0 <= year_totals[2021] <= 15500000.0
            # 2022: 14,520 GWh = 14,520,000 MWh
            assert 14300000.0 <= year_totals[2022] <= 14700000.0
            # 2023: 14,153 GWh = 14,153,000 MWh
            assert 14000000.0 <= year_totals[2023] <= 14300000.0
            # 2024: 15,191 GWh = 15,191,000 MWh
            assert 15000000.0 <= year_totals[2024] <= 15300000.0


@pytest.mark.integration
def test_etl_loads_5yr_nasa_weather_dataset(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
):
    """Verify loading 5-year NASA POWER dataset (21,924 obs) with physical unit conversion."""
    json_path = Path("data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json")
    if not json_path.exists():
        pytest.skip("5-Year NASA POWER JSON dataset not present")

    result = real_loader.load_nasa_weather_json(json_path)
    assert result.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")
    assert (result.rows_inserted + result.rows_updated) == 21924

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # Check date boundaries
            cur.execute(
                """
                SELECT
                    min(dd.calendar_date),
                    max(dd.calendar_date),
                    count(DISTINCT dd.calendar_date),
                    count(*)
                FROM dw.fact_weather_daily fwd
                JOIN dw.dim_date dd ON fwd.date_key = dd.date_key
                WHERE fwd.source_document_id = %s;
                """,
                (result.source_document_id,),
            )
            min_date, max_date, distinct_days, total_obs = cur.fetchone()
            assert min_date == date(2020, 1, 1)
            assert max_date == date(2024, 12, 31)
            assert distinct_days == 1827
            assert total_obs == 21924

            # Verify Solar Irradiance Unit Conversion: kWh/m2/day -> MJ/m2/day
            cur.execute(
                """
                SELECT
                    fwd.original_reported_value,
                    fwd.original_unit_code,
                    fwd.standardized_value,
                    fwd.standardized_unit_code
                FROM dw.fact_weather_daily fwd
                JOIN dw.dim_metric dm ON fwd.metric_key = dm.metric_key
                WHERE fwd.source_document_id = %s
                  AND dm.metric_code = 'SOLAR_IRRADIANCE_SW_DWN'
                  AND fwd.is_missing = FALSE
                LIMIT 5;
                """,
                (result.source_document_id,),
            )
            sample_rows = cur.fetchall()
            assert len(sample_rows) == 5
            for orig_val, orig_unit, std_val, std_unit in sample_rows:
                assert orig_unit == "kWh/m2/day"
                assert std_unit == "MJ/m2/day"
                # Multiplier is 3.6
                expected_std = round(float(orig_val) * 3.6, 4)
                assert abs(float(std_val) - expected_std) < 0.001


@pytest.mark.integration
def test_etl_loads_pucsl_march_31_days(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
):
    """Verify loading all 31 days of March 2024 dispatch workbook with exact coverage."""
    xlsx_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
    if not xlsx_path.exists():
        pytest.skip("PUCSL 15-minute XLSX not present")

    # Load all 31 days of March 2024 dispatch
    result = real_loader.load_pucsl_dispatch_xlsx(xlsx_path)
    assert result.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")
    assert result.rows_quarantined == 21

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # Check partition table fact_dispatch_interval_y2024
            cur.execute(
                """
                SELECT
                    min(dd.calendar_date),
                    max(dd.calendar_date),
                    count(DISTINCT dd.calendar_date),
                    count(*)
                FROM dw.fact_dispatch_interval_y2024 fdi
                JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
                WHERE fdi.source_document_id = %s;
                """,
                (result.source_document_id,),
            )
            min_date, max_date, distinct_days, fact_count = cur.fetchone()
            assert min_date == date(2024, 3, 1)
            assert max_date == date(2024, 3, 31)
            assert distinct_days == 31
            assert fact_count == 107115

            # Assert zero leakage into April
            cur.execute(
                """
                SELECT count(*)
                FROM dw.fact_dispatch_interval
                WHERE date_key = 20240401;
                """
            )
            assert cur.fetchone()[0] == 0
