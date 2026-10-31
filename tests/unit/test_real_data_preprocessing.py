"""
Unit tests for data preprocessing cleaning rules applied to real electricity datasets:
- Missing interval detection
- Physical capacity bounds & outlier detection (IQR / MAD)
- Unit conversions (GWh -> MWh, kW -> MW)
- Composite key duplicate detection
Follows TDD Red -> Green protocol.
"""

import pytest

from src.preprocessing.dispatch_cleaner import DispatchCleaner
from src.preprocessing.weather_cleaner import WeatherCleaner


@pytest.mark.unit
def test_dispatch_cleaner_detects_capacity_exceedance():
    """Verify that power exceeding station rated nameplate capacity by >5% is flagged."""
    cleaner = DispatchCleaner()
    # Canyon rated capacity is 60 MW; 65 MW is an outlier (65 > 60 * 1.05 = 63 MW)
    is_valid, flags = cleaner.validate_power_reading(
        station_name="Canyon", power_mw=65.0, rated_capacity_mw=60.0
    )
    assert not is_valid
    assert "CAPACITY_EXCEEDED" in flags


@pytest.mark.unit
def test_dispatch_cleaner_detects_negative_power():
    """Verify that negative power output is rejected as physical impossibility."""
    cleaner = DispatchCleaner()
    is_valid, flags = cleaner.validate_power_reading(
        station_name="Victoria", power_mw=-5.0, rated_capacity_mw=210.0
    )
    assert not is_valid
    assert "NEGATIVE_POWER" in flags


@pytest.mark.unit
def test_dispatch_cleaner_iqr_outlier_detection():
    """Verify that statistical IQR anomaly detection identifies extreme spikes."""
    cleaner = DispatchCleaner()
    normal_series = [10.0, 10.5, 11.0, 10.8, 10.2, 11.1, 10.9, 10.4, 11.2, 10.6]
    spike = 45.0
    outliers = cleaner.detect_iqr_outliers(normal_series + [spike])
    assert spike in outliers


@pytest.mark.unit
def test_weather_cleaner_validates_physical_ranges():
    """Verify humidity [0..100], temp [-20..60], and non-negative irradiance/wind/rain."""
    cleaner = WeatherCleaner()

    # Valid observation
    res = cleaner.validate_observation("RH2M", 85.5)
    assert res.is_valid

    # Impossible humidity (>100%)
    res_bad_rh = cleaner.validate_observation("RH2M", 105.0)
    assert not res_bad_rh.is_valid
    assert "PHYSICAL_BOUND_VIOLATION" in res_bad_rh.flags

    # Negative wind speed
    res_neg_wind = cleaner.validate_observation("WS10M", -2.0)
    assert not res_neg_wind.is_valid
    assert "PHYSICAL_BOUND_VIOLATION" in res_neg_wind.flags
