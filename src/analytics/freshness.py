"""
GridLens — Warehouse Freshness & Lineage Monitor.

Inspects audit ledgers, source document registries, and dimensional fact tables
to evaluate current warehouse freshness, sync status, and data quality metrics.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

# Ensure repository root is in sys.path for direct CLI execution
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.common.config import DatabaseConfig  # noqa: E402
from src.common.db import get_connection  # noqa: E402

logger = logging.getLogger("gridlens.analytics.freshness")


@dataclass
class SourceFreshness:
    source_code: str
    latest_document_code: str | None
    latest_reporting_period: str | None
    last_acquired_at: str | None
    total_documents: int


@dataclass
class WarehouseFreshnessReport:
    timestamp: str
    is_connected: bool
    overall_status: str  # FRESH, HEALTHY, STALE, OFFLINE
    last_etl_completed_at: str | None
    last_etl_pipeline: str | None
    last_etl_status: str | None
    total_quarantined_records: int
    sources: list[SourceFreshness]
    table_counts: dict[str, int]
    error_message: str | None = None


def inspect_warehouse_freshness(
    config: DatabaseConfig | None = None,
    connect_timeout_sec: int = 10,
) -> WarehouseFreshnessReport:
    """Audit live database to construct warehouse freshness and provenance report."""
    base_cfg = config or DatabaseConfig.from_env()
    cfg = replace(base_cfg, connect_timeout=connect_timeout_sec)
    now_iso = datetime.now(UTC).isoformat()

    try:
        with get_connection(cfg, autocommit=True) as conn:
            with conn.cursor() as cur:
                # 1. Last ETL run
                cur.execute(
                    """
                    SELECT pipeline_name, run_status, completed_at
                    FROM audit.etl_run
                    WHERE run_status IN ('SUCCEEDED', 'PARTIAL_QUARANTINE')
                    ORDER BY completed_at DESC NULLS LAST
                    LIMIT 1;
                    """
                )
                etl_row = cur.fetchone()
                last_pipeline = str(etl_row[0]) if etl_row and etl_row[0] else None
                last_status = str(etl_row[1]) if etl_row and etl_row[1] else None
                last_completed = (
                    etl_row[2].isoformat()
                    if etl_row and hasattr(etl_row[2], "isoformat")
                    else str(etl_row[2])
                    if etl_row and etl_row[2] is not None
                    else None
                )

                # 2. Source Documents per provider
                cur.execute(
                    """
                    SELECT
                        s.source_code,
                        COUNT(d.source_document_id) AS total_docs,
                        MAX(d.created_at) AS last_acquired,
                        (
                            SELECT document_code
                            FROM raw.source_document d2
                            WHERE d2.source_system_id = s.source_system_id
                            ORDER BY d2.reporting_period_end DESC, d2.source_document_id DESC
                            LIMIT 1
                        ) AS latest_doc,
                        (
                            SELECT reporting_period_end::text
                            FROM raw.source_document d2
                            WHERE d2.source_system_id = s.source_system_id
                            ORDER BY d2.reporting_period_end DESC, d2.source_document_id DESC
                            LIMIT 1
                        ) AS latest_period
                    FROM raw.source_system s
                    LEFT JOIN raw.source_document d ON s.source_system_id = d.source_system_id
                    GROUP BY s.source_system_id, s.source_code;
                    """
                )
                source_rows = cur.fetchall()
                sources: list[SourceFreshness] = []
                for s_row in source_rows:
                    sources.append(
                        SourceFreshness(
                            source_code=str(s_row[0]),
                            total_documents=int(s_row[1]),
                            last_acquired_at=(
                                s_row[2].isoformat()
                                if hasattr(s_row[2], "isoformat")
                                else str(s_row[2])
                                if s_row[2] is not None
                                else None
                            ),
                            latest_document_code=str(s_row[3]) if s_row[3] is not None else None,
                            latest_reporting_period=str(s_row[4]) if s_row[4] is not None else None,
                        )
                    )

                # 3. Quarantined records count
                cur.execute("SELECT COUNT(*) FROM audit.data_quality_issue;")
                quar_row = cur.fetchone()
                quarantine_count = int(quar_row[0]) if quar_row else 0

                # 4. Table counts across facts and marts via high-performance catalog lookup
                table_counts: dict[str, int] = {}
                try:
                    cur.execute(
                        """
                        SELECT
                            n.nspname || '.' || c.relname AS tbl_key,
                            COALESCE(NULLIF(c.reltuples, -1)::bigint, 0) AS approx_rows
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname IN ('dw', 'mart')
                          AND c.relkind IN ('r', 'm', 'p');
                        """
                    )
                    for r_key, r_count in cur.fetchall():
                        table_counts[str(r_key)] = max(0, int(r_count))
                except Exception as cat_err:
                    logger.warning(f"Catalog table count query failed, falling back: {cat_err}")

                # Ensure canonical fact tables are represented
                canonical_tables = [
                    "dw.fact_dispatch_interval",
                    "dw.fact_generation_period",
                    "dw.fact_capacity_period",
                    "dw.fact_electricity_sales",
                    "dw.fact_weather_daily",
                    "dw.fact_published_metric",
                    "mart.mv_monthly_generation_summary",
                    "mart.mv_annual_energy_mix",
                    "mart.mv_monthly_sales_summary",
                    "mart.mv_daily_dispatch_by_source",
                    "mart.mv_monthly_weather_summary",
                ]
                for tbl_name in canonical_tables:
                    if tbl_name not in table_counts:
                        table_counts[tbl_name] = 0

                # Determine overall freshness status
                overall = "HEALTHY"
                if last_completed:
                    try:
                        clean_ts = last_completed.replace("Z", "+00:00")
                        completed_dt = datetime.fromisoformat(clean_ts)
                        if completed_dt.tzinfo is None:
                            completed_dt = completed_dt.replace(tzinfo=UTC)
                        delta_days = (datetime.now(UTC) - completed_dt).total_seconds() / 86400.0
                        if delta_days <= 1.0:
                            overall = "FRESH"
                        elif delta_days > 30.0:
                            overall = "STALE"
                    except Exception as parse_err:
                        logger.warning(
                            f"Could not parse last_completed timestamp {last_completed}: {parse_err}"
                        )
                        overall = "HEALTHY"

                return WarehouseFreshnessReport(
                    timestamp=now_iso,
                    is_connected=True,
                    overall_status=overall,
                    last_etl_completed_at=last_completed,
                    last_etl_pipeline=last_pipeline,
                    last_etl_status=last_status,
                    total_quarantined_records=quarantine_count,
                    sources=sources,
                    table_counts=table_counts,
                    error_message=None,
                )

    except Exception as e:
        err_msg = str(e)
        logger.error(f"Failed to inspect warehouse freshness: {err_msg}")
        return WarehouseFreshnessReport(
            timestamp=now_iso,
            is_connected=False,
            overall_status="OFFLINE",
            last_etl_completed_at=None,
            last_etl_pipeline=None,
            last_etl_status=None,
            total_quarantined_records=0,
            sources=[],
            table_counts={},
            error_message=err_msg,
        )


def main() -> int:
    """CLI entrypoint for warehouse freshness audit."""
    parser = argparse.ArgumentParser(description="GridLens Warehouse Freshness & Lineage Monitor.")
    parser.add_argument(
        "--timeout", type=int, default=10, help="Database connection timeout in seconds."
    )
    parser.add_argument(
        "--test-db", action="store_true", help="Audit test database instead of primary."
    )
    args = parser.parse_args()

    cfg = DatabaseConfig.from_env(use_test_db=args.test_db)
    report = inspect_warehouse_freshness(cfg, connect_timeout_sec=args.timeout)
    print(json.dumps(asdict(report), indent=2))
    return 0 if report.is_connected else 1


if __name__ == "__main__":
    sys.exit(main())
