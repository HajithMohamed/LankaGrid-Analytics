"""
Data preprocessing routines following Data Warehousing Lecture 6 standards:
- Missing value sentinel normalization (strictly preserving NULL, never substituting 0)
- Exact and key-based duplicate detection
- Domain boundary & physical outlier detection
- Verified station alias standardization
- Timezone-aware timestamp normalization to Asia/Colombo (UTC+05:30)
"""
from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

COLOMBO_TZ = ZoneInfo("Asia/Colombo")

DEFAULT_MISSING_SENTINELS: tuple[str, ...] = (
    "-",
    "--",
    "N/A",
    "NA",
    "n/a",
    "NULL",
    "null",
    "None",
    "",
    "-999",
    "-999.0",
    "9999",
)

VERIFIED_STATION_ALIASES: dict[str, str] = {
    "Sapu A": "Sapugaskanda Diesel A",
    "Sapugaskanda A": "Sapugaskanda Diesel A",
    "Sapu B": "Sapugaskanda Diesel B",
    "Sapugaskanda B": "Sapugaskanda Diesel B",
    "KCCP": "Kelanitissa Combined Cycle",
    "Kelanitissa CC": "Kelanitissa Combined Cycle",
    "Lakvijaya 1": "Lakvijaya Unit 1",
    "Lakvijaya 2": "Lakvijaya Unit 2",
    "Lakvijaya 3": "Lakvijaya Unit 3",
}


def detect_and_clean_missing_values(
    df: pd.DataFrame,
    target_columns: list[str],
    sentinels: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Convert missing-value sentinels into explicit NaN/NULL in numeric target columns.
    NEVER replaces missing measurements with 0.0.
    """
    cleaned = df.copy()
    sentinel_set = {s.strip() for s in (sentinels if sentinels is not None else DEFAULT_MISSING_SENTINELS)}

    missing_by_column: dict[str, int] = {}
    total_missing = 0

    for col in target_columns:
        if col not in cleaned.columns:
            continue
        series = cleaned[col]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            normalized = series.map(
                lambda val: np.nan
                if pd.isna(val) or (isinstance(val, str) and val.strip() in sentinel_set)
                else val
            )
            cleaned[col] = pd.to_numeric(normalized, errors="coerce")
        else:
            cleaned[col] = pd.to_numeric(series, errors="coerce")

        col_missing = int(cleaned[col].isna().sum())
        missing_by_column[col] = col_missing
        total_missing += col_missing

    report: dict[str, Any] = {
        "missing_cells_count": total_missing,
        "missing_by_column": missing_by_column,
    }
    return cleaned, report


def detect_duplicate_records(
    df: pd.DataFrame,
    subset: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Partition a DataFrame into deduplicated records (first occurrence kept) and duplicate records.
    """
    dup_mask = df.duplicated(subset=subset, keep="first")
    deduped_df = df.loc[~dup_mask].copy()
    duplicates_df = df.loc[dup_mask].copy()
    return deduped_df, duplicates_df


def detect_physical_outliers(
    df: pd.DataFrame,
    capacity_col: str,
    peak_demand_col: str,
    overload_tolerance: float = 1.05,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Flag physically impossible power readings:
    - Negative active power (< 0 MW)
    - Active peak power exceeding rated plant capacity * overload_tolerance
    """
    working = df.copy()
    peak = pd.to_numeric(working[peak_demand_col], errors="coerce")
    cap = pd.to_numeric(working[capacity_col], errors="coerce")

    negative_mask = peak.notna() & (peak < 0.0)
    overflow_mask = peak.notna() & cap.notna() & (peak > cap * overload_tolerance)
    outlier_mask = negative_mask | overflow_mask

    valid_df = working.loc[~outlier_mask].copy()
    outlier_df = working.loc[outlier_mask].copy()
    return valid_df, outlier_df


def standardize_station_names(
    df: pd.DataFrame,
    column: str = "station_name",
    alias_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Map verified source station name variants to canonical power plant names.
    """
    mapping = alias_map if alias_map is not None else VERIFIED_STATION_ALIASES
    result = df.copy()
    result[column] = result[column].map(
        lambda val: mapping.get(val.strip(), val.strip()) if isinstance(val, str) else val
    )
    return result


def parse_grid_timestamps(
    df: pd.DataFrame,
    timestamp_col: str = "timestamp",
) -> pd.DataFrame:
    """
    Parse timestamps and normalize them to Sri Lanka Standard Time (Asia/Colombo, UTC+05:30).
    """
    result = df.copy()
    parsed = pd.to_datetime(result[timestamp_col], utc=False)
    if parsed.dt.tz is None:
        result["timestamp_normalized"] = parsed.dt.tz_localize(COLOMBO_TZ)
    else:
        result["timestamp_normalized"] = parsed.dt.tz_convert(COLOMBO_TZ)
    return result

