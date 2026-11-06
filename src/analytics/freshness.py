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
from typing import Any

# Ensure repository root is in sys.path for direct CLI execution
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from psycopg import sql  # noqa: E402

from src.common.config import DatabaseConfig  # noqa: E402
from src.common.db import get_connection  # noqa: E402

logger = logging.getLogger("gridlens.analytics.freshness")


def _get_field(row: Any, idx: int, name: str) -> Any:
    """Safely extract a column by index or name from tuple, list, dict, or row object."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(name)
    if isinstance(row, (tuple, list)):
        return row[idx] if 0 <= idx < len(row) else None
    if hasattr(row, name):
        return getattr(row, name)
    try:
        return row[idx]
    except Exception:
        try:
            return row[name]
        except Exception:
            return None


@dataclass
class SourceFreshness:
    source_code: str
    latest_document_code: str | None = None
    latest_reporting_period: str | None = None
    last_acquired_at: str | None = None
    total_documents: int = 0


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
                    sql.SQL(
                        """
                        SELECT pipeline_name, run_status, completed_at
                        FROM audit.etl_run
                        WHERE run_status IN ('SUCCEEDED', 'PARTIAL_QUARANTINE')
                        ORDER BY completed_at DESC NULLS LAST
                        LIMIT 1;
                        """
                    )
                )
                etl_row = cur.fetchone()
                last_pipeline: str | None = None
                last_status: str | None = None
                last_completed: str | None = None

                if etl_row:
                    pipe_val = _get_field(etl_row, 0, "pipeline_name")
                    last_pipeline = str(pipe_val) if pipe_val is not None else None
                    stat_val = _get_field(etl_row, 1, "run_status")
                    last_status = str(stat_val) if stat_val is not None else None
                    comp_val = _get_field(etl_row, 2, "completed_at")
                    if comp_val is not None:
                        if hasattr(comp_val, "isoformat"):
                            last_completed = comp_val.isoformat()
                        else:
                            last_completed = str(comp_val)

                # 2. Source Documents per provider
                cur.execute(
                    sql.SQL(
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
                )
                source_rows = cur.fetchall()
                sources: list[SourceFreshness] = []
                for s_row in source_rows:
                    code_val = _get_field(s_row, 0, "source_code")
                    s_code = str(code_val) if code_val is not None else ""

                    docs_val = _get_field(s_row, 1, "total_docs")
                    total_docs = int(docs_val) if docs_val is not None else 0

                    acq_val = _get_field(s_row, 2, "last_acquired")
                    last_acq: str | None = None
                    if acq_val is not None:
                        if hasattr(acq_val, "isoformat"):
                            last_acq = acq_val.isoformat()
                        else:
                            last_acq = str(acq_val)

                    doc_val = _get_field(s_row, 3, "latest_doc")
                    latest_doc = str(doc_val) if doc_val is not None else None

                    period_val = _get_field(s_row, 4, "latest_period")
                    latest_period = str(period_val) if period_val is not None else None

                    sources.append(
                        SourceFreshness(
                            source_code=s_code,
                            latest_document_code=latest_doc,
                            latest_reporting_period=latest_period,
                            last_acquired_at=last_acq,
                            total_documents=total_docs,
                        )
                    )

                # 3. Quarantined records count
                cur.execute(sql.SQL("SELECT COUNT(*) FROM audit.data_quality_issue;"))
                quar_row = cur.fetchone()
                quar_val = _get_field(quar_row, 0, "count")
                quarantine_count = int(quar_val) if quar_val is not None else 0

                # 4. Table counts across facts and marts via high-performance catalog lookup
                table_counts: dict[str, int] = {}
                try:
                    cur.execute(
                        sql.SQL(
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
                    )
                    for r_row in cur.fetchall():
                        r_key = _get_field(r_row, 0, "tbl_key")
                        r_count = _get_field(r_row, 1, "approx_rows")
                        if r_key is not None:
                            table_counts[str(r_key)] = max(0, int(r_count or 0))
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
