"""
Source-specific extractor for NASA POWER daily meteorological JSON datasets.
Parses multi-parameter daily observations for Sri Lanka energy node coordinates,
faithfully preserving the -999.0 fill-value sentinel as NULL (never coerced to 0).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

NODE_LOCATION_MAPPING = {
    "victoria_hydro": "LOC_VICTORIA_CATCHMENT",
    "mannar_wind": "LOC_MANNAR_WIND",
}

PARAMETER_UNIT_MAPPING = {
    "ALLSKY_SFC_SW_DWN": "kWh/m2/day",
    "T2M": "C",
    "RH2M": "PCT",
    "WS10M": "m/s",
    "WS50M": "m/s",
    "PRECTOTCORR": "mm/day",
}


@dataclass(frozen=True)
class DailyWeatherRecord:
    """Daily point meteorological observation for a grid sampling location."""

    observation_date: date
    location_code: str
    source_variable_name: str
    parsed_value: float | None
    is_missing: bool
    missing_value_code: str | None
    reported_unit_code: str
    time_standard: str = "LST"
    source_code: str = "NASA_POWER"


class NasaPowerParser:
    """Parses NASA POWER daily point observations JSON files."""

    def parse_file(self, file_path: Path) -> list[DailyWeatherRecord]:
        """Parse all nodes and parameters from the NASA POWER JSON payload."""
        with file_path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        records: list[DailyWeatherRecord] = []
        nodes = data.get("nodes", {})

        for node_id, node_payload in nodes.items():
            loc_code = NODE_LOCATION_MAPPING.get(node_id, f"LOC_{node_id.upper()}")
            props = node_payload.get("properties", {})
            param_dict = props.get("parameter", {})

            for param_name, date_values in param_dict.items():
                unit_code = PARAMETER_UNIT_MAPPING.get(param_name, "DIMENSIONLESS")

                for date_str, val in date_values.items():
                    # Parse YYYYMMDD
                    obs_date = datetime.strptime(date_str, "%Y%m%d").date()

                    parsed_val: float | None = None
                    is_missing = False
                    missing_code: str | None = None

                    # NASA POWER sentinel for missing observations is -999.0
                    if val is None or val == -999.0 or str(val).strip() in ("-999", "-999.0"):
                        parsed_val = None
                        is_missing = True
                        missing_code = "NASA_FILL_VALUE_-999"
                    else:
                        try:
                            parsed_val = float(val)
                        except (ValueError, TypeError):
                            parsed_val = None
                            is_missing = True
                            missing_code = "PARSE_ERROR"

                    records.append(
                        DailyWeatherRecord(
                            observation_date=obs_date,
                            location_code=loc_code,
                            source_variable_name=param_name,
                            parsed_value=parsed_val,
                            is_missing=is_missing,
                            missing_value_code=missing_code,
                            reported_unit_code=unit_code,
                            time_standard="LST",
                            source_code="NASA_POWER",
                        )
                    )

        return records
