"""
Tabular CSV and JSON dispatch interval parsers for raw/fixture ingestion.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_csv_data(csv_path: Path) -> pd.DataFrame:
    """Load tabular electricity records from a CSV file without fabricating defaults."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    return pd.read_csv(csv_path)


def load_dispatch_15min_json(json_path: Path) -> dict[str, Any]:
    """Load 15-minute dispatch profile records from a JSON file."""
    if not json_path.exists():
        raise FileNotFoundError(f"Dispatch JSON file not found: {json_path}")
    with json_path.open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = json.load(handle)
    return payload

