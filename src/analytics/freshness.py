"""
GridLens — Warehouse Freshness & Lineage Monitor.

Inspects audit ledgers, source document registries, and dimensional fact tables
to evaluate current warehouse freshness, sync status, and data quality metrics.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from src.common.config import DatabaseConfig
from src.common.db import get_connection

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


def inspect_warehouse_freshness(config: DatabaseConfig | None = None) -> WarehouseFreshnessReport:
    """Audit live database to construct warehouse freshness and provenance report."""
    cfg = config or DatabaseConfig.from_env()
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
                last_pipeline = etl_row[0] if etl_row else None
                last_status = etl_row[1] if etl_row else None
                last_completed = etl_row[2].isoformat() if etl_row and etl_row[2] else None

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
                            source_code=s_row[0],
                            total_documents=s_row[1],
                            last_acquired_at=s_row[2].isoformat() if s_row[2] else None,
                            latest_document_code=s_row[3],
                            latest_reporting_period=s_row[4],
                        )
                    )

                # 3. Quarantined records count
                cur.execute("SELECT COUNT(*) FROM audit.data_quality_issue;")
                quar_row = cur.fetchone()
                quarantine_count = int(quar_row[0]) if quar_row else 0

                # 4. Table counts across facts and marts
                table_counts: dict[str, int] = {}
                tables_to_check = [
                    ("dw", "fact_dispatch_interval"),
                    ("dw", "fact_generation_period"),
                    ("dw", "fact_capacity_period"),
                    ("dw", "fact_electricity_sales"),
                    ("dw", "fact_weather_daily"),
                    ("dw", "fact_published_metric"),
                    ("mart", "mv_monthly_generation_summary"),
                    ("mart", "mv_annual_energy_mix"),
                    ("mart", "mv_monthly_sales_summary"),
                    ("mart", "mv_daily_dispatch_by_source"),
                    ("mart", "mv_monthly_weather_summary"),
                ]
                for schema, tbl in tables_to_check:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {schema}.{tbl};")
                        cnt_row = cur.fetchone()
                        table_counts[f"{schema}.{tbl}"] = int(cnt_row[0]) if cnt_row else 0
                    except Exception:
                        table_counts[f"{schema}.{tbl}"] = 0

                # Determine overall status
                overall = "HEALTHY"
                if last_completed:
                    completed_dt = datetime.fromisoformat(last_completed)
                    delta_days = (datetime.now(UTC) - completed_dt).days
                    if delta_days <= 1:
                        overall = "FRESH"
                    elif delta_days > 30:
                        overall = "STALE"

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
                )

    except Exception as e:
        logger.error(f"Failed to inspect warehouse freshness: {e}")
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
        )


if __name__ == "__main__":
    import json

    report = inspect_warehouse_freshness()
    print(json.dumps(asdict(report), indent=2))
