"""
Automated data quality gates separating clean warehouse-ready rows from quarantined rows.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from src.preprocessing.cleaning import (
    detect_and_clean_missing_values,
    standardize_station_names,
)


def evaluate_generation_quality_gate(
    raw_df: pd.DataFrame,
    overload_tolerance: float = 1.05,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Evaluate raw generation records against missing-value, duplicate, and physical capacity rules.
    Returns (clean_df, quarantine_df, metrics) without dropping or fabricating any rows.
    """
    working, missing_report = detect_and_clean_missing_values(
        raw_df,
        target_columns=["rated_capacity_mw", "peak_demand_mw", "generation_mwh"],
    )
    working = standardize_station_names(working, column="station_name")

    dup_mask = working.duplicated(subset=["station_name", "timestamp", "generation_mwh"], keep="first")
    missing_mask = working["peak_demand_mw"].isna() | working["generation_mwh"].isna()
    negative_mask = (
        (working["peak_demand_mw"].notna() & (working["peak_demand_mw"] < 0.0))
        | (working["generation_mwh"].notna() & (working["generation_mwh"] < 0.0))
    )
    overflow_mask = (
        working["peak_demand_mw"].notna()
        & working["rated_capacity_mw"].notna()
        & (working["peak_demand_mw"] > working["rated_capacity_mw"] * overload_tolerance)
    )

    quarantine_mask = dup_mask | missing_mask | negative_mask | overflow_mask

    reasons: list[str] = []
    for idx in working.index:
        row_reasons: list[str] = []
        if bool(dup_mask.loc[idx]):
            row_reasons.append("DUPLICATE_RECORD")
        if bool(missing_mask.loc[idx]):
            row_reasons.append("MISSING_REQUIRED_MEASUREMENT")
        if bool(negative_mask.loc[idx]):
            row_reasons.append("NEGATIVE_MEASUREMENT")
        if bool(overflow_mask.loc[idx]):
            row_reasons.append("EXCEEDS_RATED_CAPACITY")
        reasons.append(";".join(row_reasons))

    working_with_reasons = working.copy()
    working_with_reasons["quarantine_reason"] = reasons

    clean_df = working.loc[~quarantine_mask].copy()
    quarantine_df = working_with_reasons.loc[quarantine_mask].copy()

    metrics: dict[str, Any] = {
        "total_records": len(raw_df),
        "clean_records": len(clean_df),
        "quarantined_records": len(quarantine_df),
        "duplicate_records": int(dup_mask.sum()),
        "missing_value_records": int(missing_mask.sum()),
        "physical_outlier_records": int((negative_mask | overflow_mask).sum()),
        "missing_cells_count": missing_report["missing_cells_count"],
    }
    return clean_df, quarantine_df, metrics
