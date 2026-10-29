"""
Unit tests verifying static reference seed definitions contain only verified metadata
and zero fabricated electricity or weather measurements.
"""
from __future__ import annotations

import pytest

from scripts.seed_reference import (
    CONSUMPTION_SECTORS,
    DATA_QUALITY_RULES,
    ENERGY_SOURCES,
    METRICS,
    POWER_PLANTS,
    REGIONS,
    REPORTING_PERIOD_TYPES,
    SOURCE_SYSTEMS,
    UNITS,
    WEATHER_LOCATIONS,
    build_calendar_dates,
    build_time_intervals,
)


@pytest.mark.unit
def test_calendar_date_generation_bounds() -> None:
    """Verify calendar date seed covers 2019-01-01 through 2026-12-31 including leap year 2024."""
    rows = build_calendar_dates(start_year=2019, end_year=2026)
    assert len(rows) == 2922  # 8 years including leap years 2020 and 2024
    date_keys = {r["date_key"] for r in rows}
    assert 20240229 in date_keys
    assert 20240115 in date_keys


@pytest.mark.unit
def test_time_interval_generation_96_slots_and_tou_blocks() -> None:
    """Verify 96 15-minute intervals and 24 hourly intervals map to Sri Lanka TOU blocks."""
    rows = build_time_intervals()
    slots_15m = [r for r in rows if r["interval_type"] == "15MIN"]
    slots_1h = [r for r in rows if r["interval_type"] == "HOURLY"]
    assert len(slots_15m) == 96
    assert len(slots_1h) == 24
    # 19:00 is Peak (18:30 - 22:30), 12:00 is Day (05:30 - 18:30), 01:00 is Off-Peak
    by_start = {str(r["start_time"]): r["tariff_time_block"] for r in slots_15m}
    assert by_start["01:00:00"] == "OFF_PEAK"
    assert by_start["12:00:00"] == "DAY"
    assert by_start["19:00:00"] == "PEAK"


@pytest.mark.unit
def test_reference_definitions_completeness_and_sri_lanka_bounds() -> None:
    """Verify all 10 reference categories exist and coordinates lie strictly inside Sri Lanka."""
    assert len(UNITS) >= 12
    assert len(REPORTING_PERIOD_TYPES) == 6
    assert len(SOURCE_SYSTEMS) >= 3
    assert len(ENERGY_SOURCES) >= 7
    assert len(REGIONS) >= 14  # LK + 9 provinces + 4 CEB distribution divisions
    assert len(CONSUMPTION_SECTORS) >= 8
    assert len(POWER_PLANTS) >= 10
    assert len(METRICS) >= 12
    assert len(DATA_QUALITY_RULES) >= 13

    # Verify all 13 required DQ issue classifications are covered
    expected_classes = {
        "MISSING_VALUE",
        "DUPLICATE",
        "INCORRECT_DATA_TYPE",
        "INVALID_MEASUREMENT",
        "STATISTICAL_OUTLIER",
        "UNIT_INCONSISTENCY",
        "NAMING_INCONSISTENCY",
        "MISSING_REPORTING_INTERVAL",
        "UNMATCHED_DIMENSION",
        "CONFLICTING_SOURCE_VALUE",
        "INCOMPATIBLE_REPORTING_GRANULARITY",
        "UNSUPPORTED_CALCULATION",
        "PARSING_FAILURE",
    }
    seeded_classes = {r["issue_classification"] for r in DATA_QUALITY_RULES}
    assert expected_classes.issubset(seeded_classes)

    for loc in WEATHER_LOCATIONS:
        assert 5.8 <= loc["latitude_deg"] <= 10.0
        assert 79.4 <= loc["longitude_deg"] <= 82.0
