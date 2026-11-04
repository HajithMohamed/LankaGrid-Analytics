#!/usr/bin/env python3
"""
GridLens — Automated Incremental Warehouse Refresh CLI.

GOVERNANCE:
- Identifies newly downloaded or modified official files from CEB, PUCSL, and NASA POWER.
- Ingests new records idempotently into Kimball dimensional facts.
- Quarantines invalid or unmapped records in audit.data_quality_issue without failing the pipeline.
- Automatically refreshes analytical materialized views (mart.mv_*) upon completion.
- Logs pipeline metrics to audit.etl_run.

Usage:
    python scripts/refresh_warehouse.py                    # Refresh all eligible datasets
    python scripts/refresh_warehouse.py --dataset ceb       # Refresh only CEB sales
    python scripts/refresh_warehouse.py --dataset pucsl     # Refresh only PUCSL dispatch
    python scripts/refresh_warehouse.py --dataset nasa      # Refresh only NASA weather
    python scripts/refresh_warehouse.py --dry-run           # Preview planned actions without DB changes
    python scripts/refresh_warehouse.py --force             # Force re-ingestion of existing files
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from src.common.config import DatabaseConfig
from src.etl.incremental_refresher import IncrementalWarehouseRefresher


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute scheduled or on-demand incremental warehouse refresh."
    )
    parser.add_argument(
        "--dataset",
        choices=["all", "ceb", "pucsl", "nasa"],
        default="all",
        help="Specify which dataset to incrementally ingest and refresh (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate ingestion and refresh without persisting database mutations.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-processing of source files even if already recorded in raw.source_document.",
    )
    parser.add_argument(
        "--test-db",
        action="store_true",
        help="Target test database instead of primary production/development warehouse.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging output.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = DatabaseConfig.from_env(use_test_db=args.test_db)
    refresher = IncrementalWarehouseRefresher(config=config)

    print(f"Connecting to warehouse on {config.host}:{config.port}/{config.dbname}...")
    t_start = time.time()

    results = refresher.run_refresh(
        dataset=args.dataset,
        dry_run=args.dry_run,
        force=args.force,
    )

    print("\n" + "=" * 65)
    print("INCREMENTAL REFRESH EXECUTION SUMMARY")
    print("=" * 65)
    has_errors = False
    for r in results:
        flag = f"[{r.status}]"
        print(
            f"{flag:<10} {r.dataset:<8} | Scanned: {r.files_scanned:2d} | Processed: {r.files_processed:2d}"
        )
        print(
            f"           | Inserted: {r.rows_inserted:6,d} | Updated: {r.rows_updated:6,d} | Quarantined: {r.rows_quarantined:4,d}"
        )
        print(
            f"           | Duration: {r.duration_seconds:.2f}s | Marts Refreshed: {'YES' if r.marts_refreshed else 'NO'}"
        )
        if r.errors:
            has_errors = True
            for err in r.errors:
                print(f"           ! ERROR: {err}")
        print("-" * 65)

    total_time = time.time() - t_start
    print(f"Total Refresh Time: {total_time:.2f}s")
    print("=" * 65)

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
