"""
Unit tests for data parsers (CSV and JSON 15-minute dispatch profiles).
"""

from pathlib import Path

import pytest

from src.ingestion.parsers import load_csv_data, load_dispatch_15min_json


@pytest.mark.unit
def test_load_csv_parser():
    """Verify CSV parser correctly loads tabular electricity records."""
    csv_file = Path("tests/fixtures/sample_generation_raw.csv")
    df = load_csv_data(csv_file)
    assert len(df) == 10
    assert "station_name" in df.columns
    assert "generation_mwh" in df.columns


@pytest.mark.unit
def test_load_dispatch_15min_json():
    """Verify JSON parser loads 15-minute dispatch intervals."""
    json_file = Path("tests/fixtures/sample_dispatch_15min.json")
    data = load_dispatch_15min_json(json_file)
    assert data["date"] == "2024-01-15"
    assert len(data["intervals"]) == 4
    first_interval = data["intervals"][0]
    assert first_interval["system_demand_mw"] == 1420.5
    assert first_interval["thermal_mw"] + first_interval["major_hydro_mw"] + first_interval[
        "renewable_mw"
    ] == pytest.approx(1420.5, rel=1e-3)
