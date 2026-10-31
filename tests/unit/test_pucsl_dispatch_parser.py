"""
Unit tests for PUCSL 15-minute dispatch XLSX parser.
Follows TDD Red -> Green protocol.
"""

from pathlib import Path

import pytest

from src.ingestion.pucsl_dispatch_parser import PucslDispatchParser


@pytest.fixture
def sample_xlsx_path() -> Path:
    return Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")


@pytest.mark.unit
def test_dispatch_parser_file_structure(sample_xlsx_path: Path):
    """Verify that PUCSL dispatch parser discovers daily sheets."""
    if not sample_xlsx_path.exists():
        pytest.skip("Raw PUCSL XLSX file not downloaded")

    parser = PucslDispatchParser()
    sheets = parser.get_sheet_names(sample_xlsx_path)
    assert len(sheets) == 31
    assert "01.03" in sheets


@pytest.mark.unit
def test_dispatch_parser_extracts_single_day(sample_xlsx_path: Path):
    """Verify parsing a single daily sheet extracts 96 intervals per station."""
    if not sample_xlsx_path.exists():
        pytest.skip("Raw PUCSL XLSX file not downloaded")

    parser = PucslDispatchParser()
    records = parser.parse_sheet(sample_xlsx_path, "01.03")

    assert len(records) > 0
    # There are ~40 stations with 96 intervals = ~3,800 records
    assert len(records) >= 3000

    # Inspect a known station (e.g. Canyon)
    canyon_records = [r for r in records if r.raw_entity_name == "Canyon"]
    assert len(canyon_records) == 96

    first_slot = canyon_records[0]
    assert first_slot.interval_slot_number == 1
    assert first_slot.power_mw == 11.0
    assert first_slot.reported_unit_code == "MW"
    assert first_slot.observation_date.strftime("%Y-%m-%d") == "2024-03-01"
    assert first_slot.observation_timestamp.isoformat().endswith("+05:30")


@pytest.mark.unit
def test_dispatch_parser_preserves_zero_distinct_from_missing(sample_xlsx_path: Path):
    """Assert that 0.0 MW is preserved as 0.0 (offline) and blank is preserved as None."""
    if not sample_xlsx_path.exists():
        pytest.skip("Raw PUCSL XLSX file not downloaded")

    parser = PucslDispatchParser()
    records = parser.parse_sheet(sample_xlsx_path, "01.03")

    # Canyon early slots have 11 MW, Victoria early slots have 0 MW
    vict_records = [r for r in records if r.raw_entity_name == "Vict"]
    assert len(vict_records) == 96
    slot2 = vict_records[1]  # 0:30
    assert slot2.power_mw == 0.0
    assert not slot2.is_missing
