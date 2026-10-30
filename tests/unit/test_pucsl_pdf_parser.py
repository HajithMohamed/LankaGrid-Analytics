"""
Unit tests for PUCSL Daily Generation Report PDF parser.
Follows TDD Red -> Green protocol.
"""
from pathlib import Path
import pytest

from src.ingestion.pucsl_pdf_parser import PucslPdfParser, PlantGenerationRecord, DailyMixRecord


@pytest.fixture
def sample_pdf_path() -> Path:
    return Path("data/raw/pucsl/2024/Generation-Report-29th-Dec-2024.pdf")


@pytest.mark.unit
def test_pucsl_pdf_extracts_generation_mix(sample_pdf_path: Path):
    """Verify daily generation mix extraction from Page 2 Table 01."""
    if not sample_pdf_path.exists():
        pytest.skip("Raw PUCSL PDF file not downloaded")

    parser = PucslPdfParser()
    mix_records = parser.extract_daily_generation_mix(sample_pdf_path)
    
    assert len(mix_records) >= 8
    mix_dict = {r.category_name: r.generation_mwh for r in mix_records}
    
    # Authoritative numbers from Table 01 on Page 2:
    # CEB Hydro: 14,679 MWh
    # CEB Coal: 12,436 MWh
    # CEB Thermal Oil: 5,064 MWh
    assert mix_dict.get("CEB Hydro") == 14679.0
    assert mix_dict.get("CEB Coal") == 12436.0
    assert mix_dict.get("CEB Thermal Oil") == 5064.0


@pytest.mark.unit
def test_pucsl_pdf_extracts_plant_table(sample_pdf_path: Path):
    """Verify plant-by-plant generation & capacity extraction from Page 4 Table 2."""
    if not sample_pdf_path.exists():
        pytest.skip("Raw PUCSL PDF file not downloaded")

    parser = PucslPdfParser()
    plant_records = parser.extract_plant_dispatch_table(sample_pdf_path)
    
    assert len(plant_records) >= 15
    plant_dict = {r.plant_name: r for r in plant_records}
    
    # Check known stations from page 4:
    # Wimalasurendra: dispatch 311 MWh, max cap 50 MW
    # Canyon: dispatch 228 MWh, max cap 60 MW
    wps = plant_dict.get("Wimalasurendra")
    assert wps is not None
    assert wps.generation_mwh == 311.0
    assert wps.max_capacity_mw == 50.0

    canyon = plant_dict.get("Canyon")
    assert canyon is not None
    assert canyon.generation_mwh == 228.0
    assert canyon.max_capacity_mw == 60.0


@pytest.mark.unit
def test_pucsl_pdf_extracts_peak_demand(sample_pdf_path: Path):
    """Verify day and night peak demand values extracted from Page 5."""
    if not sample_pdf_path.exists():
        pytest.skip("Raw PUCSL PDF file not downloaded")

    parser = PucslPdfParser()
    peaks = parser.extract_peak_demands(sample_pdf_path)
    
    # Night peak: 2,278 MW, Day peak: 1,742 MW
    assert peaks["night_peak_mw"] == 2278.0
    assert peaks["day_peak_max_mw"] == 1742.0
