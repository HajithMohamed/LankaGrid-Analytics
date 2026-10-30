"""
Data quality assertions and quarantine testing.
"""

from pathlib import Path

# pyrefly: ignore[missing-source-for-stubs]
import pandas as pd
import pytest

from src.validation.quality_gates import evaluate_generation_quality_gate


@pytest.mark.data_quality
def test_quality_gate_quarantine_evaluation() -> None:
    """
    Ensure the data quality gate detects defective rows, separates them into
    a quarantine DataFrame, and computes standard quality metrics.
    """
    fixture_path = Path("tests/fixtures/sample_generation_raw.csv")
    raw_df = pd.read_csv(fixture_path)

    clean_df, quarantine_df, metrics = evaluate_generation_quality_gate(raw_df)

    # Defective rows (missing values, negative power, capacity overflow, duplicates)
    assert len(quarantine_df) > 0
    assert len(clean_df) + len(quarantine_df) == len(raw_df)

    assert "total_records" in metrics
    assert "clean_records" in metrics
    assert "quarantined_records" in metrics
    assert metrics["total_records"] == 10
    assert metrics["quarantined_records"] == len(quarantine_df)
