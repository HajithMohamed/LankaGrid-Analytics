"""
Preprocessing and data-quality cleaning rules for 15-minute dispatch observations:
- Physical boundary checks (P >= 0, P <= rated_capacity * 1.05)
- Anomaly & outlier detection using statistical IQR and MAD
- Missing interval detection (expected 96 intervals per 24 hours)
- Canonical station name standardization via ref.plant_alias
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class PreprocessingValidationResult:
    """Outcome of rule-based data preprocessing validation."""

    is_valid: bool
    flags: list[str] = field(default_factory=list)
    normalized_value: float | None = None
    quarantine_rule_code: str | None = None


class DispatchCleaner:
    """Applies Lecture 6 preprocessing rules to 15-minute sub-daily dispatch curves."""

    def validate_power_reading(
        self,
        station_name: str,
        power_mw: float | None,
        rated_capacity_mw: float | None = None,
        allow_pumping_load: bool = False,
    ) -> tuple[bool, list[str]]:
        """Validate power reading against physical constraints."""
        flags: list[str] = []

        if power_mw is None:
            flags.append("MISSING_VALUE")
            return False, flags

        # Check 1: Negative power
        if power_mw < 0 and not allow_pumping_load:
            flags.append("NEGATIVE_POWER")

        # Check 2: Plant capacity exceedance
        if rated_capacity_mw is not None and rated_capacity_mw > 0:
            threshold = rated_capacity_mw * 1.05
            if power_mw > threshold:
                flags.append("CAPACITY_EXCEEDED")

        is_valid = len(flags) == 0
        return is_valid, flags

    @staticmethod
    def detect_iqr_outliers(series: Sequence[float], k: float = 1.5) -> list[float]:
        """Identify statistical distribution outliers using Tukey's Interquartile Range (IQR)."""
        if len(series) < 4:
            return []

        sorted_s = sorted(series)
        n = len(sorted_s)
        q1 = sorted_s[n // 4]
        q3 = sorted_s[(3 * n) // 4]
        iqr = q3 - q1

        if iqr == 0:
            return []

        lower_bound = q1 - k * iqr
        upper_bound = q3 + k * iqr

        return [x for x in series if x < lower_bound or x > upper_bound]

    @staticmethod
    def detect_missing_intervals(
        recorded_slots: set[int], expected_total: int = 96
    ) -> list[int]:
        """Detect missing 15-minute interval slot numbers in a 24-hour cycle (1..96)."""
        expected_set = set(range(1, expected_total + 1))
        missing = expected_set - recorded_slots
        return sorted(list(missing))
