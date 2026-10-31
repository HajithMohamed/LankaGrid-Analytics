"""
Unit tests for 5-year historical dataset extractors:
- CEB Statistical Digests (2020, 2021, 2022, 2023, 2024)
- NASA POWER 5-Year Multi-Node Dataset (2020-2024)
- PUCSL 31-Day March 2024 Dispatch Workbook
Follows TDD protocol.
"""

from datetime import date
from pathlib import Path

import pytest

from src.ingestion.ceb_digest_parser import CebDigestParser
from src.ingestion.nasa_power_parser import NasaPowerParser
from src.ingestion.pucsl_dispatch_parser import PucslDispatchParser


def test_ceb_parser_extracts_5yr_tariff_sales():
    """Verify version-aware extraction of tariff sales for all 5 calendar years."""
    # 2020 from 2020 Digest
    p2020 = Path("data/raw/ceb/2020/Statistical_Digest_2020.pdf")
    if p2020.exists():
        parser2020 = CebDigestParser(reporting_year=2020)
        recs2020 = parser2020.extract_tariff_sales(p2020, target_year=2020)
        assert len(recs2020) >= 7
        total_2020 = next((r.sales_gwh for r in recs2020 if r.tariff_group == "TOTAL"), None)
        assert total_2020 == 14286.0

    # 2021 & 2022 from 2022 Digest
    p2022 = Path("data/raw/ceb/2022/Statistical_Digest_2022.pdf")
    if p2022.exists():
        parser2022 = CebDigestParser(reporting_year=2022)
        recs2021 = parser2022.extract_tariff_sales(p2022, target_year=2021)
        assert len(recs2021) >= 7
        total_2021 = next((r.sales_gwh for r in recs2021 if r.tariff_group == "TOTAL"), None)
        assert total_2021 == 15214.0

        recs2022 = parser2022.extract_tariff_sales(p2022, target_year=2022)
        assert len(recs2022) >= 7
        total_2022 = next((r.sales_gwh for r in recs2022 if r.tariff_group == "TOTAL"), None)
        assert total_2022 == 14520.0

    # 2023 & 2024 from 2024 Digest
    p2024 = Path("data/raw/ceb/2024/Statistical_Digest_2024.pdf")
    if p2024.exists():
        parser2024 = CebDigestParser(reporting_year=2024)
        recs2023 = parser2024.extract_tariff_sales(p2024, target_year=2023)
        assert len(recs2023) >= 7
        total_2023 = next((r.sales_gwh for r in recs2023 if r.tariff_group == "TOTAL"), None)
        assert total_2023 == 14153.0

        recs2024 = parser2024.extract_tariff_sales(p2024, target_year=2024)
        assert len(recs2024) >= 7
        total_2024 = next((r.sales_gwh for r in recs2024 if r.tariff_group == "TOTAL"), None)
        assert total_2024 == 15191.0


def test_nasa_power_5yr_observation_volume_and_sentinels():
    """Verify 5-year NASA POWER JSON contains 21,924 observations and preserves nulls."""
    json_path = Path("data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json")
    if not json_path.exists():
        pytest.skip("5-year NASA POWER JSON not present")

    parser = NasaPowerParser()
    records = parser.parse_file(json_path)
    # 1,827 days x 6 parameters x 2 nodes = 21,924
    assert len(records) == 21924

    # Verify date range
    dates = [r.observation_date for r in records]
    assert min(dates) == date(2020, 1, 1)
    assert max(dates) == date(2024, 12, 31)

    # Verify both locations present
    locs = {r.location_code for r in records}
    assert "LOC_VICTORIA_CATCHMENT" in locs
    assert "LOC_MANNAR_WIND" in locs

    # Verify unit mappings
    solar_records = [r for r in records if r.source_variable_name == "ALLSKY_SFC_SW_DWN"]
    assert len(solar_records) == 1827 * 2
    assert all(r.reported_unit_code == "kWh/m2/day" for r in solar_records)


def test_pucsl_31_day_sheet_discovery():
    """Verify PUCSL March 2024 dispatch workbook exposes all 31 days."""
    xlsx_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
    if not xlsx_path.exists():
        pytest.skip("PUCSL March 2024 dispatch workbook not present")

    parser = PucslDispatchParser()
    sheets = parser.get_sheet_names(xlsx_path)
    assert len(sheets) == 31
    assert "01.03" in sheets
    assert "31.03" in sheets
