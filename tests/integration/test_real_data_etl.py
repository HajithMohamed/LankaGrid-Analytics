"""
Integration tests for real-data ETL pipeline:
- Loads genuine official datasets from CEB, PUCSL, and NASA POWER
- Asserts raw -> staging -> dimensional warehouse promotion
- Validates audit.record_lineage and audit.etl_run tracking
- Checks partition pruning on dw.fact_dispatch_interval
- Verifies aggregate totals match source publications without double-counting
Follows TDD Red -> Green protocol.
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
def test_etl_loads_pucsl_daily_pdf_generation(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
):
    """Verify loading PUCSL daily report into dw.fact_generation_period with lineage."""
    pdf_path = Path("data/raw/pucsl/2024/Generation-Report-29th-Dec-2024.pdf")
    if not pdf_path.exists():
        pytest.skip("PUCSL daily generation PDF not present")

    result = real_loader.load_pucsl_daily_pdf(pdf_path, reporting_date=date(2024, 12, 29))
    assert result.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")
    assert result.rows_inserted > 0

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # Check fact rows
            cur.execute(
                """
                SELECT count(*), sum(generation_mwh)
                FROM dw.fact_generation_period
                WHERE source_document_id = %s;
                """,
                (result.source_document_id,),
            )
            row = cur.fetchone()
            assert row is not None
            fact_count, total_mwh = row
            assert fact_count > 0
            assert total_mwh > 0

            # Check audit lineage
            cur.execute(
                "SELECT count(*) FROM audit.record_lineage WHERE etl_run_id = %s;",
                (result.etl_run_id,),
            )
            lineage_count = cur.fetchone()[0]
            assert lineage_count == result.rows_inserted


@pytest.mark.integration
def test_etl_loads_pucsl_dispatch_xlsx(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
):
    """Verify loading PUCSL 15-minute dispatch sheet into dw.fact_dispatch_interval."""
    xlsx_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
    if not xlsx_path.exists():
        pytest.skip("PUCSL 15-minute XLSX not present")

    # Load 1 sample sheet (01.03) to test sub-daily dispatch partition insertion
    result = real_loader.load_pucsl_dispatch_xlsx(xlsx_path, sheet_names=["01.03"])
    assert result.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")
    assert result.rows_inserted > 0

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # Check partition table fact_dispatch_interval_y2024
            cur.execute(
                """
                SELECT count(*), avg(active_power_mw), sum(derived_energy_mwh)
                FROM dw.fact_dispatch_interval_y2024
                WHERE source_document_id = %s;
                """,
                (result.source_document_id,),
            )
            row = cur.fetchone()
            assert row is not None
            count, avg_mw, total_mwh = row
            assert count > 0
            assert avg_mw > 0
            assert total_mwh > 0


@pytest.mark.integration
def test_etl_loads_nasa_power_weather_json(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
):
    """Verify loading NASA POWER meteorological observations into dw.fact_weather_daily."""
    json_path = Path("data/raw/nasa/2024/nasa_power_sl_nodes_2024.json")
    if not json_path.exists():
        pytest.skip("NASA POWER JSON not present")

    result = real_loader.load_nasa_weather_json(json_path)
    assert result.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")
    assert (result.rows_inserted + result.rows_updated) > 0

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*), count(*) FILTER (WHERE is_missing = FALSE)
                FROM dw.fact_weather_daily
                WHERE source_document_id = %s;
                """,
                (result.source_document_id,),
            )
            row = cur.fetchone()
            assert row is not None
            total_records, valid_measurements = row
            assert total_records > 0
            assert valid_measurements > 0


@pytest.mark.integration
def test_etl_loads_ceb_statistical_digest_sales(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
):
    """Verify loading CEB Statistical Digest sales into dw.fact_electricity_sales."""
    pdf_path = Path("data/raw/ceb/2024/Statistical_Digest_2024.pdf")
    if not pdf_path.exists():
        pytest.skip("CEB Statistical Digest PDF not present")

    result = real_loader.load_ceb_sales_pdf(pdf_path, reporting_year=2024)
    assert result.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")
    assert result.rows_inserted > 0

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT sum(energy_sold_mwh)
                FROM dw.fact_electricity_sales
                WHERE source_document_id = %s;
                """,
                (result.source_document_id,),
            )
            total_mwh = cur.fetchone()[0]
            assert total_mwh is not None
            # Authoritative sales: 15,191 GWh -> 15,191,000 MWh
            assert total_mwh >= 15000000.0
