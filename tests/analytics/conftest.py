"""
Shared fixtures for Phase 3 analytics integration tests.
Ensures the test database has historical datasets loaded before executing analytical tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection
from src.etl.real_data_loader import RealDataWarehouseLoader


@pytest.fixture(scope="package")
def populated_analytics_db(migrated_and_seeded_test_db: DatabaseConfig) -> DatabaseConfig:
    """Ensure that the test database has 5-year sales, weather, and dispatch facts populated."""
    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM dw.fact_electricity_sales;")
            sales_row = cur.fetchone()
            assert sales_row is not None, "Query must return count of sales"
            sales_cnt = int(sales_row[0])

            cur.execute("SELECT count(*) FROM dw.fact_weather_daily;")
            weather_row = cur.fetchone()
            assert weather_row is not None, "Query must return count of weather"
            weather_cnt = int(weather_row[0])

            cur.execute("SELECT count(*) FROM dw.fact_dispatch_interval;")
            dispatch_row = cur.fetchone()
            assert dispatch_row is not None, "Query must return count of dispatch"
            dispatch_cnt = int(dispatch_row[0])

    loader = RealDataWarehouseLoader(config=migrated_and_seeded_test_db)

    # 1. Load CEB 5-Year Sales if missing
    if sales_cnt < 40:
        loader.load_5yr_ceb_sales()

    # 2. Load NASA 5-Year Weather if missing
    if weather_cnt < 1000:
        nasa_path = Path("data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json")
        if nasa_path.exists():
            loader.load_nasa_weather_json(nasa_path)

    # 3. Load PUCSL March Dispatch if missing
    if dispatch_cnt < 10000:
        pucsl_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
        if pucsl_path.exists():
            # Load 31 days to ensure full coverage
            loader.load_pucsl_dispatch_xlsx(pucsl_path)

    # 4. Refresh Materialized Views
    with get_connection(migrated_and_seeded_test_db, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("CALL mart.sp_refresh_analytical_marts();")

    return migrated_and_seeded_test_db
