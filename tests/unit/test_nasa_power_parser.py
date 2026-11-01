"""
Unit tests for NASA POWER JSON parser.
Follows TDD Red -> Green protocol.
"""

import json
from pathlib import Path

import pytest

from src.ingestion.nasa_power_parser import NasaPowerParser


@pytest.fixture
def sample_nasa_json_path() -> Path:
    return Path("data/raw/nasa/2024/nasa_power_sl_nodes_2024.json")


@pytest.mark.unit
def test_nasa_power_parser_extracts_observations(sample_nasa_json_path: Path):
    """Verify parsing multi-node NASA POWER daily JSON structure."""
    if not sample_nasa_json_path.exists():
        pytest.skip("Raw NASA POWER JSON file not downloaded")

    parser = NasaPowerParser()
    records = parser.parse_file(sample_nasa_json_path)

    assert len(records) > 0
    # 2 nodes * 31 days * 6 parameters = 372 records
    assert len(records) == 372

    # Check a specific record
    rec_0 = records[0]
    assert rec_0.location_code in ("LOC_VICTORIA_CATCHMENT", "LOC_MANNAR_WIND")
    assert rec_0.source_variable_name in (
        "ALLSKY_SFC_SW_DWN",
        "T2M",
        "RH2M",
        "WS10M",
        "WS50M",
        "PRECTOTCORR",
    )
    assert rec_0.time_standard == "LST"
    assert rec_0.reported_unit_code != ""

    # NASA POWER All-Sky Surface Shortwave Irradiance unit must be kWh/m2/day
    irradiance_recs = [r for r in records if r.source_variable_name == "ALLSKY_SFC_SW_DWN"]
    assert len(irradiance_recs) > 0
    assert irradiance_recs[0].reported_unit_code == "kWh/m2/day"


@pytest.mark.unit
def test_nasa_power_parser_preserves_fill_value_sentinel(tmp_path: Path):
    """Verify that NASA fill value -999.0 is parsed as None / null, NEVER coerced to 0.0."""
    synthetic_payload = {
        "nodes": {
            "victoria_hydro": {
                "metadata": {"name": "Victoria Hydro Reservoir", "lat": 7.24, "lon": 80.785},
                "properties": {
                    "parameter": {
                        "ALLSKY_SFC_SW_DWN": {"20240101": -999.0, "20240102": 4.5},
                        "T2M": {"20240101": 22.5, "20240102": -999.0},
                    }
                },
            }
        }
    }
    synth_file = tmp_path / "nasa_synth.json"
    synth_file.write_text(json.dumps(synthetic_payload), encoding="utf-8")

    parser = NasaPowerParser()
    records = parser.parse_file(synth_file)

    assert len(records) == 4
    missing_irradiance = next(
        r
        for r in records
        if r.observation_date.strftime("%Y%m%d") == "20240101"
        and r.source_variable_name == "ALLSKY_SFC_SW_DWN"
    )
    assert missing_irradiance.parsed_value is None
    assert missing_irradiance.is_missing is True
    assert missing_irradiance.missing_value_code == "NASA_FILL_VALUE_-999"

    valid_irradiance = next(
        r
        for r in records
        if r.observation_date.strftime("%Y%m%d") == "20240102"
        and r.source_variable_name == "ALLSKY_SFC_SW_DWN"
    )
    assert valid_irradiance.parsed_value == 4.5
    assert valid_irradiance.is_missing is False
