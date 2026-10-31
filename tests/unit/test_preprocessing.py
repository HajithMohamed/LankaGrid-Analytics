"""
Unit tests for Data Preprocessing routines (Lecture 6 standards).
"""

from pathlib import Path

import pandas as pd
import pytest

from src.preprocessing.cleaning import (
    detect_and_clean_missing_values,
    detect_duplicate_records,
    detect_physical_outliers,
    parse_grid_timestamps,
    standardize_station_names,
)


@pytest.fixture
def raw_generation_df() -> pd.DataFrame:
    """Load the synthetic raw generation fixture."""
    fixture_path = Path("tests/fixtures/sample_generation_raw.csv")
    return pd.read_csv(fixture_path)


@pytest.mark.unit
def test_missing_values_detection_and_null_preservation(raw_generation_df):
    """
    Ensure sentinels like '-', 'N/A', and blanks are identified as NULL
    and are NEVER replaced with zero.
    """
    cleaned_df, report = detect_and_clean_missing_values(
        raw_generation_df,
        target_columns=["peak_demand_mw", "generation_mwh"],
        sentinels=["-", "N/A", "NA", ""],
    )

    # Row 5 (Kelanitissa CC) had '-' for peak_demand_mw
    row5 = cleaned_df[cleaned_df["record_id"] == 5].iloc[0]
    assert pd.isna(row5["peak_demand_mw"])
    assert row5["peak_demand_mw"] != 0.0

    # Row 6 (Sapugaskanda Diesel A) had 'N/A' for both
    row6 = cleaned_df[cleaned_df["record_id"] == 6].iloc[0]
    assert pd.isna(row6["peak_demand_mw"])
    assert pd.isna(row6["generation_mwh"])

    # Row 10 (Ukuwela) had empty string for generation_mwh
    row10 = cleaned_df[cleaned_df["record_id"] == 10].iloc[0]
    assert pd.isna(row10["generation_mwh"])

    assert report["missing_cells_count"] >= 4


@pytest.mark.unit
def test_duplicate_record_detection(raw_generation_df):
    """
    Identify exact duplicate records (rows 3 and 4: Lakvijaya Unit 1).
    """
    deduped_df, duplicates_df = detect_duplicate_records(
        raw_generation_df,
        subset=["station_name", "timestamp", "generation_mwh"],
    )

    assert len(duplicates_df) == 1
    assert duplicates_df.iloc[0]["record_id"] == 4
    assert len(deduped_df) == len(raw_generation_df) - 1


@pytest.mark.unit
def test_physical_outlier_detection(raw_generation_df):
    """
    Detect physical violations:
    1. Negative power (-15.0 MW for Mannar Wind)
    2. Generation exceeding rated plant capacity (550 MW peak for 10 MW Hambantota Solar)
    """
    cleaned_missing, _ = detect_and_clean_missing_values(
        raw_generation_df,
        target_columns=["peak_demand_mw", "generation_mwh"],
    )
    valid_df, outlier_df = detect_physical_outliers(
        cleaned_missing,
        capacity_col="rated_capacity_mw",
        peak_demand_col="peak_demand_mw",
    )

    outlier_ids = outlier_df["record_id"].tolist()
    assert 7 in outlier_ids  # Negative power (-15.0 MW)
    assert 8 in outlier_ids  # Exceeding plant capacity (550 MW > 10 MW)


@pytest.mark.unit
def test_canonical_station_name_standardization(raw_generation_df):
    """
    Standardize station name variants (e.g. 'Sapu A' -> 'Sapugaskanda Diesel A').
    """
    standardized_df = standardize_station_names(raw_generation_df, column="station_name")
    sapu_records = standardized_df[standardized_df["record_id"].isin([6, 9])]
    assert sapu_records["station_name"].nunique() == 1
    assert sapu_records["station_name"].iloc[0] == "Sapugaskanda Diesel A"


@pytest.mark.unit
def test_timestamp_parsing_with_colombo_timezone(raw_generation_df):
    """
    Verify timestamps are parsed with Sri Lanka Standard Time (+05:30) preserved.
    """
    parsed_df = parse_grid_timestamps(raw_generation_df, timestamp_col="timestamp")
    first_dt = parsed_df["timestamp_normalized"].iloc[0]
    assert first_dt.tzinfo is not None
    assert str(first_dt.tzinfo) in ["Asia/Colombo", "UTC+05:30", "+05:30"]
