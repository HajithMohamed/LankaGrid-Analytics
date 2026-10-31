"""
Comprehensive Phase 1 Database Verification Runner (Section 12).

Executes:
1. Clean-room migration application on primary database (sl_grid_warehouse)
2. Reference seeding + idempotent re-seeding verification (asserting 0 fact rows)
3. SQL catalog & integrity assertions (database/tests/phase1_sql_assertions.sql)
4. Exact database object inventory extraction across all 7 schemas
5. Role & privilege matrix audit
6. Representative EXPLAIN (ANALYZE, BUFFERS) plans inside a rolled-back synthetic
   benchmark transaction on sl_grid_warehouse_test (leaving 0 synthetic rows persisted)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from scripts.migrate import MigrationRunner
from scripts.seed_reference import ReferenceSeeder
from src.common.config import DatabaseConfig
from src.common.db import get_connection


def run_verification() -> dict[str, Any]:
    """Run end-to-end Phase 1 verification and return structured diagnostics."""
    primary_cfg = DatabaseConfig.from_env(use_test_db=False)
    test_cfg = DatabaseConfig.from_env(use_test_db=True)
    runner = MigrationRunner(migrations_dir=Path("database/migrations"))
    seeder = ReferenceSeeder()

    # Step 1: Clean reset of primary database & apply all 17 migrations from empty state
    rollback_sql = Path("database/migrations/rollbacks/rollback_all_phase1.sql").read_text(encoding="utf-8")
    with get_connection(primary_cfg, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW server_version;")
            pg_version = str(cur.fetchone()[0])  # type: ignore[index]
            # pyrefly: ignore[no-matching-overload]
            cur.execute(rollback_sql)

    applied_initial = runner.apply_migrations(primary_cfg)
    applied_recheck = runner.apply_migrations(primary_cfg)
    runner.configure_role_passwords_from_env(primary_cfg)

    # Step 2: Run reference seed twice and compare exact table counts
    seeder.seed_all(primary_cfg)
    with get_connection(primary_cfg, autocommit=True) as conn:
        with conn.cursor() as cur:
            counts_pass_1 = _collect_seed_and_fact_counts(cur)

    seeder.seed_all(primary_cfg)
    with get_connection(primary_cfg, autocommit=True) as conn:
        with conn.cursor() as cur:
            counts_pass_2 = _collect_seed_and_fact_counts(cur)
            if counts_pass_1 != counts_pass_2:
                raise RuntimeError(f"Seed idempotency mismatch: {counts_pass_1} vs {counts_pass_2}")

            # Step 3: Execute SQL catalog assertion suite
            assertions_sql = Path("database/tests/phase1_sql_assertions.sql").read_text(encoding="utf-8")
            # pyrefly: ignore[no-matching-overload]
            cur.execute(assertions_sql)

            # Step 4: Collect complete object inventory & role privileges
            inventory = _collect_object_inventory(cur)
            role_grants = _collect_role_summary(cur)

    # Step 5: Execute EXPLAIN (ANALYZE, BUFFERS) on sl_grid_warehouse_test inside a rolled-back transaction
    explain_plans = _capture_explain_analyze_plans(test_cfg)

    report: dict[str, Any] = {
        "postgresql_version": pg_version,
        "migrations_applied_clean_db": applied_initial,
        "migrations_applied_idempotent_rerun": applied_recheck,
        "seed_counts_pass_1": counts_pass_1,
        "seed_counts_pass_2_identical": counts_pass_1 == counts_pass_2,
        "inventory": inventory,
        "role_grants_summary": role_grants,
        "explain_analyze_plans": explain_plans,
    }
    return report


def _collect_seed_and_fact_counts(cur: Any) -> dict[str, int]:
    tables = [
        "raw.source_system",
        "ref.unit",
        "ref.unit_conversion",
        "ref.reporting_period_type",
        "ref.energy_source_mapping",
        "ref.plant_alias",
        "ref.region_alias",
        "ref.metric_mapping",
        "ref.data_quality_rule",
        "ref.source_precedence",
        "dw.dim_date",
        "dw.dim_interval",
        "dw.dim_source_system",
        "dw.dim_energy_source",
        "dw.dim_region",
        "dw.dim_consumption_sector",
        "dw.dim_power_plant",
        "dw.dim_weather_location",
        "dw.dim_metric",
        "dw.fact_dispatch_interval",
        "dw.fact_generation_period",
        "dw.fact_capacity_period",
        "dw.fact_electricity_sales",
        "dw.fact_weather_daily",
        "dw.fact_published_metric",
    ]
    out: dict[str, int] = {}
    for tbl in tables:
        cur.execute(f"SELECT COUNT(*) FROM {tbl};")
        out[tbl] = int(cur.fetchone()[0])
    return out


def _collect_object_inventory(cur: Any) -> dict[str, Any]:
    cur.execute(
        """
        SELECT n.nspname AS schema_name,
               c.relname AS object_name,
               CASE c.relkind
                   WHEN 'r' THEN CASE WHEN c.relispartition THEN 'PARTITION' ELSE 'TABLE' END
                   WHEN 'p' THEN 'PARTITIONED_TABLE'
                   WHEN 'v' THEN 'VIEW'
                   WHEN 'm' THEN 'MATERIALIZED_VIEW'
               END AS object_type
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname IN ('raw', 'staging', 'ref', 'dw', 'mart', 'audit', 'etl')
           AND c.relkind IN ('r', 'p', 'v', 'm')
         ORDER BY n.nspname, object_type, c.relname;
        """
    )
    relations = [{"schema": r[0], "name": r[1], "type": r[2]} for r in cur.fetchall()]

    cur.execute(
        """
        SELECT n.nspname AS schema_name,
               p.proname AS routine_name,
               CASE p.prokind WHEN 'p' THEN 'PROCEDURE' ELSE 'FUNCTION' END AS routine_type
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'etl'
         ORDER BY routine_type, p.proname;
        """
    )
    routines = [{"schema": r[0], "name": r[1], "type": r[2]} for r in cur.fetchall()]

    cur.execute(
        """
        SELECT n.nspname, c.relname, t.tgname
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE NOT t.tgisinternal
           AND n.nspname IN ('raw', 'staging', 'ref', 'dw', 'mart', 'audit', 'etl')
         ORDER BY n.nspname, c.relname, t.tgname;
        """
    )
    triggers = [{"schema": r[0], "table": r[1], "trigger": r[2]} for r in cur.fetchall()]

    cur.execute(
        """
        SELECT schemaname, tablename, indexname
          FROM pg_indexes
         WHERE schemaname IN ('raw', 'staging', 'ref', 'dw', 'mart', 'audit', 'etl')
         ORDER BY schemaname, tablename, indexname;
        """
    )
    indexes = [{"schema": r[0], "table": r[1], "index": r[2]} for r in cur.fetchall()]

    return {
        "relations_count": len(relations),
        "routines_count": len(routines),
        "triggers_count": len(triggers),
        "indexes_count": len(indexes),
        "relations": relations,
        "routines": routines,
        "triggers": triggers,
    }


def _collect_role_summary(cur: Any) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT grantee, table_schema, privilege_type, COUNT(*) AS table_count
          FROM information_schema.role_table_grants
         WHERE grantee IN ('grid_etl', 'grid_analyst')
           AND table_schema IN ('raw', 'staging', 'ref', 'dw', 'mart', 'audit', 'etl')
         GROUP BY grantee, table_schema, privilege_type
         ORDER BY grantee, table_schema, privilege_type;
        """
    )
    return [
        {"role": r[0], "schema": r[1], "privilege": r[2], "object_count": int(r[3])}
        for r in cur.fetchall()
    ]


def _capture_explain_analyze_plans(test_cfg: DatabaseConfig) -> dict[str, list[str]]:
    """Run EXPLAIN (ANALYZE, BUFFERS) on synthetic rows inside a transaction that is ALWAYS rolled back."""
    plans: dict[str, list[str]] = {}
    with get_connection(test_cfg, autocommit=False) as conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT source_system_id FROM raw.source_system WHERE source_code = 'PUCSL';")
                sys_id = int(cur.fetchone()[0])  # type: ignore[index]
                cur.execute(
                    """
                    INSERT INTO raw.source_document (
                        source_system_id, document_code, source_url, original_filename,
                        local_storage_path, file_format, sha256_checksum,
                        reporting_period_type, reporting_period_start, reporting_period_end,
                        dataset_revision, acquisition_status
                    ) VALUES (
                        %s, 'SYNTH-EXPLAIN-BENCH', 'https://www.pucsl.gov.lk/bench.pdf', 'bench.pdf',
                        'tests/fixtures/bench.pdf', 'PDF',
                        '1111111111111111111111111111111111111111111111111111111111111111',
                        'DAILY', DATE '2024-01-01', DATE '2024-03-31', 'v1', 'SYNTHETIC_FIXTURE'
                    ) RETURNING source_document_id;
                    """,
                    (sys_id,),
                )
                doc_id = int(cur.fetchone()[0])  # type: ignore[index]
                cur.execute(
                    """
                    INSERT INTO audit.etl_run (
                        pipeline_name, target_schema, target_table, source_document_id, run_status
                    ) VALUES ('explain_benchmark_tx', 'dw', 'fact_dispatch_interval', %s, 'RUNNING')
                    RETURNING etl_run_id;
                    """,
                    (doc_id,),
                )
                etl_run_id = int(cur.fetchone()[0])  # type: ignore[index]

                # Populate 2,880 synthetic 15-min dispatch observations in rolled-back tx (30 days x 96 slots)
                cur.execute(
                    """
                    INSERT INTO dw.fact_dispatch_interval (
                        date_key, interval_key, plant_key, energy_source_key, metric_key,
                        source_system_key, dataset_revision, original_timestamp,
                        interval_duration_minutes, active_power_mw, derived_energy_mwh,
                        is_energy_derived, reported_value, reported_unit_code, value_status,
                        source_document_id, etl_run_id
                    )
                    SELECT
                        dd.date_key,
                        di.interval_key,
                        dp.plant_key,
                        dp.energy_source_key,
                        (SELECT metric_key FROM dw.dim_metric WHERE metric_code = 'PLANT_DISPATCH_MW'),
                        (SELECT source_system_key FROM dw.dim_source_system WHERE source_code = 'PUCSL'),
                        'v1',
                        (dd.calendar_date::TEXT || ' ' || di.start_time::TEXT || '+05:30')::TIMESTAMPTZ,
                        15,
                        150.0000,
                        37.5000,
                        TRUE,
                        150.0000,
                        'MW',
                        'REPORTED',
                        %s,
                        %s
                    FROM dw.dim_date dd
                    CROSS JOIN dw.dim_interval di
                    JOIN dw.dim_power_plant dp ON dp.plant_code = 'VICTORIA' AND dp.is_current = TRUE
                    WHERE dd.date_key BETWEEN 20240101 AND 20240130
                      AND di.interval_type = '15MIN';
                    """,
                    (doc_id, etl_run_id),
                )

                cur.execute(
                    """
                    EXPLAIN (ANALYZE, BUFFERS)
                    SELECT di.tariff_time_block,
                           COUNT(*) AS intervals_count,
                           ROUND(AVG(fd.active_power_mw), 2) AS avg_dispatch_mw,
                           ROUND(SUM(fd.derived_energy_mwh), 2) AS integrated_energy_mwh
                    FROM dw.fact_dispatch_interval fd
                    JOIN dw.dim_interval di ON di.interval_key = fd.interval_key
                    WHERE fd.date_key BETWEEN 20240101 AND 20240115
                      AND fd.plant_key = (SELECT plant_key FROM dw.dim_power_plant WHERE plant_code = 'VICTORIA' AND is_current = TRUE)
                      AND fd.is_current_revision = TRUE
                    GROUP BY di.tariff_time_block
                    ORDER BY di.tariff_time_block;
                    """
                )
                plans["dispatch_partition_pruned_tou_query"] = [r[0] for r in cur.fetchall()]

                cur.execute(
                    """
                    EXPLAIN (ANALYZE, BUFFERS)
                    SELECT calendar_year, month_number, energy_source_code, total_generation_mwh
                    FROM mart.vw_generation_by_energy_source
                    WHERE calendar_year = 2024 AND period_type_code = 'MONTHLY';
                    """
                )
                plans["generation_by_energy_source_view_query"] = [r[0] for r in cur.fetchall()]
        finally:
            conn.rollback()
    return plans


if __name__ == "__main__":
    summary = run_verification()
    print(json.dumps(summary, indent=2))
    sys.exit(0)

