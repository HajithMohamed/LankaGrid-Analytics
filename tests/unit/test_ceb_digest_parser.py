"""
Unit tests for CEB Statistical Digest 2024 PDF parser.
Follows TDD Red -> Green protocol.
"""

from pathlib import Path

import pytest

from src.ingestion.ceb_digest_parser import (
    CebDigestParser,
)


@pytest.fixture
def sample_ceb_pdf_path() -> Path:
    return Path("data/raw/ceb/2024/Statistical_Digest_2024.pdf")


@pytest.mark.unit
def test_ceb_digest_extracts_provincial_sales(sample_ceb_pdf_path: Path):
    """Verify sales by distribution division in GWh and MWh from Page 5."""
    if not sample_ceb_pdf_path.exists():
        pytest.skip("Raw CEB PDF file not downloaded")

    parser = CebDigestParser()
    prov_records = parser.extract_provincial_sales(sample_ceb_pdf_path)

    assert len(prov_records) >= 10
    total_rec = next((r for r in prov_records if r.region_raw == "TOTAL"), None)
    assert total_rec is not None
    # 2024 Total sales: 15,191 GWh -> 15,191,000 MWh
    assert total_rec.sales_gwh == 15191.0
    assert total_rec.sales_mwh == 15191000.0


@pytest.mark.unit
def test_ceb_digest_extracts_tariff_sales(sample_ceb_pdf_path: Path):
    """Verify sales by consumer tariff group from Page 5 and 8."""
    if not sample_ceb_pdf_path.exists():
        pytest.skip("Raw CEB PDF file not downloaded")

    parser = CebDigestParser()
    tariff_records = parser.extract_tariff_sales(sample_ceb_pdf_path)

    assert len(tariff_records) >= 7
    tariff_dict = {r.tariff_group: r.sales_gwh for r in tariff_records}

    # Page 5 CEB 2024 Sales by Tariff:
    # Domestic: 4,701 GWh
    # Religious: 75 GWh
    # Industrial: 4,622 GWh
    # General Purpose: 3,472 GWh
    assert tariff_dict.get("Domestic") == 4701.0
    assert tariff_dict.get("Religious") == 75.0
    assert tariff_dict.get("Industrial Total") == 4622.0
    assert tariff_dict.get("General Purpose Total") == 3472.0
