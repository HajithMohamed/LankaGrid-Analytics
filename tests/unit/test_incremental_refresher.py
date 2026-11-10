"""
Unit tests for IncrementalWarehouseRefresher and Supabase DatabaseConfig.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.common.config import DatabaseConfig
from src.etl.incremental_refresher import IncrementalWarehouseRefresher, RefreshResult


@pytest.mark.unit
def test_supabase_database_config_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DATABASE_URL for Supabase is correctly parsed with SSL require and dbname postgres."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:mysecretpass@db.abcdefghijklmnopqrst.supabase.co:5432/postgres",
    )
    cfg = DatabaseConfig.from_env()

    assert cfg.host == "db.abcdefghijklmnopqrst.supabase.co"
    assert cfg.port == 5432
    assert cfg.dbname == "postgres"
    assert cfg.user == "postgres"
    assert cfg.password == "mysecretpass"
    assert cfg.sslmode == "require"


@pytest.mark.unit
def test_compute_sha256_accuracy() -> None:
    """Ensure compute_sha256 produces exact cryptographic hashes."""
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(b"National Electricity Grid Analytics Data Warehouse - Sri Lanka")
        temp_path = Path(f.name)

    try:
        digest = IncrementalWarehouseRefresher.compute_sha256(temp_path)
        # Expected SHA-256 for the test byte sequence
        import hashlib

        expected = hashlib.sha256(
            b"National Electricity Grid Analytics Data Warehouse - Sri Lanka"
        ).hexdigest()
        assert digest == expected
    finally:
        if temp_path.exists():
            temp_path.unlink()


@pytest.mark.unit
def test_refresh_result_initialization() -> None:
    """Verify RefreshResult defaults and attributes."""
    res = RefreshResult(dataset="PUCSL")
    assert res.dataset == "PUCSL"
    assert res.files_scanned == 0
    assert res.files_processed == 0
    assert res.rows_inserted == 0
    assert res.rows_quarantined == 0
    assert res.marts_refreshed is False
    assert res.status == "SUCCEEDED"
    assert res.errors == []


@pytest.mark.unit
def test_dry_run_performs_zero_database_mutations() -> None:
    """Ensure dry-run mode returns scanned metrics without database writes."""
    cfg = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="sl_grid_warehouse",
        user="grid_etl",
        password="dummy_password",
    )
    refresher = IncrementalWarehouseRefresher(config=cfg)

    results = refresher.run_refresh(dataset="all", dry_run=True)
    assert len(results) == 3
    for r in results:
        assert r.status == "SUCCEEDED"
        assert r.duration_seconds >= 0.0
        assert r.marts_refreshed is True  # Dry run marks simulated success


@pytest.mark.unit
def test_mart_refresh_failure_marks_run_failed() -> None:
    """Verify that a materialized view refresh failure propagates and marks the refresh FAILED."""
    from unittest.mock import patch

    cfg = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="sl_grid_warehouse",
        user="grid_etl",
        password="dummy_password",
    )
    refresher = IncrementalWarehouseRefresher(config=cfg)

    fake_res = RefreshResult(
        dataset="NASA",
        files_scanned=1,
        files_processed=1,
        rows_inserted=100,
        status="SUCCEEDED",
    )

    with (
        patch.object(refresher, "refresh_nasa_weather", return_value=fake_res),
        patch.object(
            refresher,
            "refresh_marts",
            return_value=(False, "Database connection dropped during MV refresh"),
        ),
    ):
        results = refresher.run_refresh(dataset="nasa", dry_run=False, acquire=False)

    assert len(results) == 1
    assert results[0].status == "FAILED"
    assert results[0].marts_refreshed is False
    assert any("Database connection dropped during MV refresh" in e for e in results[0].errors)
