"""
Unit tests for GridLens warehouse freshness and provenance monitor (src/analytics/freshness.py).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.analytics.freshness import (
    SourceFreshness,
    WarehouseFreshnessReport,
    inspect_warehouse_freshness,
    main,
)


@pytest.mark.unit
def test_freshness_report_dataclass() -> None:
    """Validate WarehouseFreshnessReport creation and serialization."""
    source = SourceFreshness(
        source_code="PUCSL",
        latest_document_code="DOC_001",
        latest_reporting_period="2024-03-31",
        last_acquired_at="2024-04-01T00:00:00+00:00",
        total_documents=31,
    )
    report = WarehouseFreshnessReport(
        timestamp="2024-04-01T12:00:00+00:00",
        is_connected=True,
        overall_status="FRESH",
        last_etl_completed_at="2024-04-01T10:00:00+00:00",
        last_etl_pipeline="pipeline_daily_refresh",
        last_etl_status="SUCCEEDED",
        total_quarantined_records=0,
        sources=[source],
        table_counts={"dw.fact_dispatch_interval": 2976},
        error_message=None,
    )
    assert report.is_connected is True
    assert report.overall_status == "FRESH"
    assert len(report.sources) == 1
    assert report.sources[0].source_code == "PUCSL"
    assert report.error_message is None


@pytest.mark.unit
def test_inspect_warehouse_freshness_online_fresh() -> None:
    """Validate inspect_warehouse_freshness when DB is healthy and ETL is fresh."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    # Mock query outputs
    now = datetime.now(UTC)
    mock_cur.fetchone.side_effect = [
        ("pipeline_daily_refresh", "SUCCEEDED", now - timedelta(hours=2)),  # query 1: etl_run
        (0,),  # query 3: data_quality_issue
    ]
    mock_cur.fetchall.side_effect = [
        [("PUCSL", 31, now - timedelta(hours=3), "DOC_PUCSL_2024_03", "2024-03-31")],  # query 2
        [("dw.fact_dispatch_interval", 2976), ("mart.mv_annual_energy_mix", 5)],  # query 4
    ]

    with patch("src.analytics.freshness.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        report = inspect_warehouse_freshness()

        assert report.is_connected is True
        assert report.overall_status == "FRESH"
        assert report.last_etl_pipeline == "pipeline_daily_refresh"
        assert report.last_etl_status == "SUCCEEDED"
        assert len(report.sources) == 1
        assert report.sources[0].source_code == "PUCSL"
        assert report.table_counts["dw.fact_dispatch_interval"] == 2976
        assert report.error_message is None


@pytest.mark.unit
def test_inspect_warehouse_freshness_online_stale() -> None:
    """Validate status is STALE when last ETL completed > 30 days ago."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    old_date = datetime.now(UTC) - timedelta(days=45)
    mock_cur.fetchone.side_effect = [
        ("pipeline_daily_refresh", "SUCCEEDED", old_date),
        (2,),
    ]
    mock_cur.fetchall.side_effect = [
        [],
        [],
    ]

    with patch("src.analytics.freshness.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        report = inspect_warehouse_freshness()

        assert report.is_connected is True
        assert report.overall_status == "STALE"
        assert report.total_quarantined_records == 2


@pytest.mark.unit
def test_inspect_warehouse_freshness_online_healthy() -> None:
    """Validate status is HEALTHY when last ETL completed 5 days ago."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    mid_date = datetime.now(UTC) - timedelta(days=5)
    mock_cur.fetchone.side_effect = [
        ("pipeline_daily_refresh", "SUCCEEDED", mid_date),
        (0,),
    ]
    mock_cur.fetchall.side_effect = [
        [],
        [],
    ]

    with patch("src.analytics.freshness.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        report = inspect_warehouse_freshness()

        assert report.is_connected is True
        assert report.overall_status == "HEALTHY"


@pytest.mark.unit
def test_inspect_warehouse_freshness_no_prior_runs() -> None:
    """Validate report when audit.etl_run has zero rows."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    mock_cur.fetchone.side_effect = [
        None,  # etl_run empty
        (0,),  # data_quality_issue
    ]
    mock_cur.fetchall.side_effect = [
        [],
        [],
    ]

    with patch("src.analytics.freshness.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        report = inspect_warehouse_freshness()

        assert report.is_connected is True
        assert report.overall_status == "HEALTHY"
        assert report.last_etl_completed_at is None
        assert report.last_etl_pipeline is None


@pytest.mark.unit
def test_inspect_warehouse_freshness_offline_fallback() -> None:
    """Validate offline fallback when connection fails."""
    with patch("src.analytics.freshness.get_connection") as mock_get_conn:
        mock_get_conn.side_effect = ConnectionError("Could not reach Supabase pooler host")

        report = inspect_warehouse_freshness()

        assert report.is_connected is False
        assert report.overall_status == "OFFLINE"
        assert report.last_etl_completed_at is None
        assert report.sources == []
        assert report.table_counts == {}
        assert report.error_message is not None
        assert "Could not reach Supabase pooler host" in report.error_message


@pytest.mark.unit
def test_inspect_warehouse_freshness_dict_rows() -> None:
    """Validate inspect_warehouse_freshness when cursor returns dict rows."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    now = datetime.now(UTC)
    mock_cur.fetchone.side_effect = [
        {"pipeline_name": "pipeline_daily_refresh", "run_status": "SUCCEEDED", "completed_at": now},
        {"count": 0},
    ]
    mock_cur.fetchall.side_effect = [
        [
            {
                "source_code": "CEB",
                "total_docs": 10,
                "last_acquired": now,
                "latest_doc": "CEB_DOC_2024",
                "latest_period": "2024-12-31",
            }
        ],
        [{"tbl_key": "dw.fact_electricity_sales", "approx_rows": 500}],
    ]

    with patch("src.analytics.freshness.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn

        report = inspect_warehouse_freshness()

        assert report.is_connected is True
        assert report.overall_status == "FRESH"
        assert len(report.sources) == 1
        assert report.sources[0].source_code == "CEB"
        assert report.sources[0].latest_reporting_period == "2024-12-31"
        assert report.table_counts["dw.fact_electricity_sales"] == 500


@pytest.mark.unit
def test_inspect_warehouse_freshness_cli_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validate CLI entrypoint returns exit code 0 when connected, 1 when offline."""
    # Online case
    dummy_report_online = WarehouseFreshnessReport(
        timestamp="2024-04-01T00:00:00+00:00",
        is_connected=True,
        overall_status="FRESH",
        last_etl_completed_at=None,
        last_etl_pipeline=None,
        last_etl_status=None,
        total_quarantined_records=0,
        sources=[],
        table_counts={},
    )
    with patch(
        "src.analytics.freshness.inspect_warehouse_freshness", return_value=dummy_report_online
    ):
        monkeypatch.setattr("sys.argv", ["freshness.py", "--timeout", "5"])
        exit_code = main()
        assert exit_code == 0

    # Offline case
    dummy_report_offline = WarehouseFreshnessReport(
        timestamp="2024-04-01T00:00:00+00:00",
        is_connected=False,
        overall_status="OFFLINE",
        last_etl_completed_at=None,
        last_etl_pipeline=None,
        last_etl_status=None,
        total_quarantined_records=0,
        sources=[],
        table_counts={},
        error_message="timeout",
    )
    with patch(
        "src.analytics.freshness.inspect_warehouse_freshness", return_value=dummy_report_offline
    ):
        monkeypatch.setattr("sys.argv", ["freshness.py", "--timeout", "5", "--test-db"])
        exit_code = main()
        assert exit_code == 1
