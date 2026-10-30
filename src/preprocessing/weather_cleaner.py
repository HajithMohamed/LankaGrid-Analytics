"""
Preprocessing and domain physical validation for NASA POWER meteorological observations:
- Relative humidity in [0, 100] %
- Ambient temperature in [-20, 60] °C
- Solar irradiance >= 0
- Wind speed >= 0 m/s
- Precipitation >= 0 mm/day
- Null / fill value sentinel preservation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from src.preprocessing.dispatch_cleaner import PreprocessingValidationResult


class WeatherCleaner:
    """Validates physical range boundaries and missing-value flags for meteorological data."""

    def validate_observation(
        self, parameter_name: str, value: float | None
    ) -> PreprocessingValidationResult:
        """Validate parameter value against physical atmospheric boundaries."""
        if value is None:
            return PreprocessingValidationResult(
                is_valid=True,
                flags=["MISSING_VALUE"],
                normalized_value=None,
            )

        flags: list[str] = []

        if parameter_name == "RH2M":
            if value < 0 or value > 100:
                flags.append("PHYSICAL_BOUND_VIOLATION")
        elif parameter_name.startswith("T2M"):
            if value < -20.0 or value > 60.0:
                flags.append("PHYSICAL_BOUND_VIOLATION")
        elif parameter_name in ("ALLSKY_SFC_SW_DWN", "WS10M", "WS50M", "PRECTOTCORR"):
            if value < 0:
                flags.append("PHYSICAL_BOUND_VIOLATION")

        is_valid = len(flags) == 0
        rule_code = "DQ_PHYSICAL_RANGE" if not is_valid else None

        return PreprocessingValidationResult(
            is_valid=is_valid,
            flags=flags,
            normalized_value=value if is_valid else None,
            quarantine_rule_code=rule_code,
        )
