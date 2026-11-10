#!/usr/bin/env python3
"""
GridLens — Supabase Cloud Data Warehouse Migration & Provisioning Runner.

GOVERNANCE & SAFETY:
- Connects to Supabase Managed PostgreSQL via DatabaseConfig.from_env() or --database-url.
- Non-destructive: NEVER executes DROP DATABASE, DROP SCHEMA, or DROP TABLE.
- Applies all 22 sequential forward migrations with SHA-256 immutability verification.
- Seeds 13 conformed dimensions and reference domains idempotently.
- Loads verified authentic historical facts (CEB sales, NASA weather, PUCSL dispatch).
- Refreshes analytical materialized views (mart.mv_*).
- Audits and verifies all 7 schemas and 5 materialized views.
- Never prints or logs plain-text passwords or secret credentials.

Usage:
    python scripts/migrate_supabase.py                  # Full migration and historical data load
    python scripts/migrate_supabase.py --dry-run        # Preview migrations without executing DDL/DML
    python scripts/migrate_supabase.py --verify-only    # Non-destructive audit of remote warehouse
    python scripts/migrate_supabase.py --skip-data      # Apply schema and seed, skip large fact loads
    python scripts/migrate_supabase.py --database-url "postgresql://postgres:pass@host:5432/postgres"
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from psycopg import sql
from psycopg.cursor import Cursor

from scripts.migrate import MigrationRunner
from scripts.seed_reference import ReferenceSeeder
from src.common.config import DatabaseConfig
from src.common.db import get_connection
from src.etl.real_data_loader import RealDataWarehouseLoader


# -----------------------------------------------------------------------------
# Safe Database Helpers
# -----------------------------------------------------------------------------
def _fetch_scalar(cur: Cursor[Any], default: Any = None) -> Any:
    """Safely fetch a scalar value from the first column of the next row."""
    row = cur.fetchone()
    if row is None or len(row) == 0:
        return default
    return row[0]


def _fetch_int(cur: Cursor[Any], default: int = 0) -> int:
    """Safely fetch an integer count from the first column of the next row."""
    val = _fetch_scalar(cur, default)
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


@dataclass
class SupabaseAuditReport:
    """Structured audit metrics from a Supabase warehouse instance."""

    server_version: str = "Unknown"
    database_name: str = "Unknown"
    ssl_active: bool = False
    schemas_found: list[str] = field(default_factory=list)
    migrations_applied: int = 0
    migrations_total: int = 0
    reference_tables: dict[str, int] = field(default_factory=dict)
    dimension_tables: dict[str, int] = field(default_factory=dict)
    fact_tables: dict[str, int] = field(default_factory=dict)
    materialized_views: dict[str, int] = field(default_factory=dict)
    data_quality_issues: int = 0
    all_schemas_healthy: bool = False


class SupabaseMigrator:
    """Manages deployment, historical data ingestion, and verification on Supabase."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self.migrations_dir = Path("database/migrations")
        self.migration_runner = MigrationRunner(migrations_dir=self.migrations_dir)
        self.reference_seeder = ReferenceSeeder()

    def check_connection(self) -> tuple[bool, str]:
        """Test database connectivity with masked diagnostics."""
        raw_env_url = os.getenv("DATABASE_URL", "")
        if "[YOUR-PASSWORD]" in (self.config.password or "") or "[YOUR-PASSWORD]" in raw_env_url:
            return (
                False,
                "Supabase password placeholder '[YOUR-PASSWORD]' detected in environment.\n"
                "Please replace '[YOUR-PASSWORD]' in your .env / DATABASE_URL with your actual database password.",
            )

        try:
            with get_connection(self.config, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version();")
                    ver = str(_fetch_scalar(cur, "PostgreSQL"))
                    cur.execute("SHOW ssl;")
                    ssl_status = str(_fetch_scalar(cur, "off"))
                    return (
                        True,
                        f"Connected to {self.config.host}:{self.config.port}/{self.config.dbname} "
                        f"(SSL: {ssl_status}) — {ver}",
                    )
        except Exception as e:
            return False, f"Failed to connect to {self.config.host}:{self.config.port}: {e}"

    def audit_warehouse(self) -> SupabaseAuditReport:
        """Perform comprehensive non-destructive inspection of warehouse objects."""
        report = SupabaseAuditReport()
        report.database_name = self.config.dbname

        with get_connection(self.config, autocommit=True) as conn:
            with conn.cursor() as cur:
                # 1. Server & SSL Info
                try:
                    cur.execute("SHOW server_version;")
                    report.server_version = str(_fetch_scalar(cur, "Unknown"))
                except Exception:
                    report.server_version = "Unknown"

                try:
                    cur.execute("SHOW ssl;")
                    report.ssl_active = str(_fetch_scalar(cur, "off")).lower() in ("on", "true")
                except Exception:
                    report.ssl_active = False

                # 2. Schemas
                cur.execute(
                    """
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name IN ('raw', 'staging', 'ref', 'dw', 'mart', 'audit', 'etl')
                    ORDER BY schema_name;
                    """
                )
                rows = cur.fetchall()
                report.schemas_found = [str(r[0]) for r in rows if r and len(r) > 0]
                expected_schemas = {"raw", "staging", "ref", "dw", "mart", "audit", "etl"}
                report.all_schemas_healthy = expected_schemas.issubset(set(report.schemas_found))

                # 3. Migrations
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'schema_migrations'
                    );
                    """
                )
                has_migration_table = bool(_fetch_scalar(cur, False))
                if has_migration_table:
                    cur.execute("SELECT count(*) FROM public.schema_migrations;")
                    report.migrations_applied = _fetch_int(cur)

                total_files = len(self.migration_runner.discover_migrations())
                report.migrations_total = total_files

                # Helper to count rows safely via to_regclass
                def _safe_table_count(qualified_name: str) -> int:
                    try:
                        cur.execute("SELECT to_regclass(%s);", (qualified_name,))
                        if _fetch_scalar(cur) is not None:
                            parts = qualified_name.split(".")
                            if len(parts) == 2:
                                stmt = sql.SQL("SELECT count(*) FROM {}.{};").format(
                                    sql.Identifier(parts[0]),
                                    sql.Identifier(parts[1]),
                                )
                            else:
                                stmt = sql.SQL("SELECT count(*) FROM {};").format(
                                    sql.Identifier(qualified_name)
                                )
                            cur.execute(stmt)
                            return _fetch_int(cur)
                        return -1
                    except Exception:
                        return -1

                # 4. Dimensions & Reference Tables
                dim_tables = [
                    "dw.dim_date",
                    "dw.dim_interval",
                    "dw.dim_source_system",
                    "dw.dim_energy_source",
                    "dw.dim_region",
                    "dw.dim_consumption_sector",
                    "dw.dim_power_plant",
                    "dw.dim_weather_location",
                    "dw.dim_metric",
                ]
                for tbl in dim_tables:
                    report.dimension_tables[tbl] = _safe_table_count(tbl)

                ref_tables = [
                    "ref.unit",
                    "ref.unit_conversion",
                    "ref.reporting_period_type",
                    "ref.energy_source_mapping",
                    "ref.plant_alias",
                    "ref.region_alias",
                    "ref.metric_mapping",
                    "ref.data_quality_rule",
                    "ref.source_precedence",
                ]
                for tbl in ref_tables:
                    report.reference_tables[tbl] = _safe_table_count(tbl)

                # 5. Fact Tables
                fact_tables = [
                    "dw.fact_dispatch_interval",
                    "dw.fact_dispatch_interval_y2024",
                    "dw.fact_generation_period",
                    "dw.fact_capacity_period",
                    "dw.fact_electricity_sales",
                    "dw.fact_weather_daily",
                    "dw.fact_published_metric",
                ]
                for tbl in fact_tables:
                    report.fact_tables[tbl] = _safe_table_count(tbl)

                # 6. Materialized Views
                mvs = [
                    "mart.mv_monthly_generation_summary",
                    "mart.mv_annual_energy_mix",
                    "mart.mv_monthly_sales_summary",
                    "mart.mv_daily_dispatch_by_source",
                    "mart.mv_monthly_weather_summary",
                ]
                for mv in mvs:
                    report.materialized_views[mv] = _safe_table_count(mv)

                # 7. Data Quality Audit
                report.data_quality_issues = _safe_table_count("audit.data_quality_issue")

        return report

    def apply_migrations(self, dry_run: bool = False) -> int:
        """Run all pending sequential forward migrations."""
        if dry_run:
            status = self.migration_runner.get_status(self.config)
            pending = [s for s in status if not s.is_applied]
            print(f"[DRY-RUN] Discovered {len(status)} total migrations ({len(pending)} pending):")
            for m in status:
                flag = "APPLIED" if m.is_applied else "PENDING"
                print(f"  [{flag}] {m.filename} (checksum: {m.checksum[:12]}...)")
            return len(pending)

        print("Executing sequential forward migrations...")
        applied_count = self.migration_runner.apply_migrations(self.config)
        try:
            self.migration_runner.configure_role_passwords_from_env(self.config)
        except Exception as e:
            print(f"Notice: Role password configuration skipped or restricted: {e}")
        return applied_count

    def seed_dimensions(self, dry_run: bool = False) -> dict[str, int]:
        """Seed verified static reference taxonomies and conformed dimensions."""
        if dry_run:
            print("[DRY-RUN] Would seed 13 conformed dimensions and reference tables idempotently.")
            return {}

        print("Seeding conformed dimensions and reference taxonomies...")
        return self.reference_seeder.seed_all(self.config)

    def load_historical_data(self, dry_run: bool = False) -> dict[str, Any]:
        """Load authentic historical facts (CEB sales, NASA weather, PUCSL dispatch)."""
        if dry_run:
            print("[DRY-RUN] Would load historical datasets:")
            print("  - CEB 5-Year Billed Electricity Sales (2020-2024: 49 records)")
            print("  - NASA POWER 5-Year Weather Observations (2020-2024: 21,924 records)")
            print("  - PUCSL March 2024 Sub-Daily Dispatch Curves (107,115 records)")
            return {}

        results: dict[str, Any] = {}
        loader = RealDataWarehouseLoader(config=self.config)

        # 1. CEB Sales
        print("\n--- 1. Loading CEB 5-Year Billed Electricity Sales (2020-2024) ---")
        t0 = time.time()
        ceb_batches = loader.load_5yr_ceb_sales()
        total_ceb_inserted = sum(b.rows_inserted for b in ceb_batches)
        print(
            f"Loaded {len(ceb_batches)} CEB sales batches ({total_ceb_inserted} rows) in {time.time() - t0:.2f}s"
        )
        results["ceb_sales_rows"] = total_ceb_inserted

        # 2. NASA Weather
        print("\n--- 2. Loading NASA POWER 5-Year Weather Dataset (2020-2024) ---")
        nasa_path = Path("data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json")
        if nasa_path.exists():
            t0 = time.time()
            nasa_res = loader.load_nasa_weather_json(nasa_path)
            print(
                f"Loaded NASA weather in {time.time() - t0:.2f}s: "
                f"inserted={nasa_res.rows_inserted}, quarantined={nasa_res.rows_quarantined}"
            )
            results["nasa_weather_rows"] = nasa_res.rows_inserted
        else:
            print(f"WARNING: NASA file not found at {nasa_path}")
            results["nasa_weather_rows"] = 0

        # 3. PUCSL Dispatch
        print("\n--- 3. Loading PUCSL March 2024 Sub-Daily Dispatch Curves ---")
        pucsl_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
        if pucsl_path.exists():
            t0 = time.time()
            dispatch_res = loader.load_pucsl_dispatch_xlsx(pucsl_path)
            print(
                f"Loaded PUCSL dispatch in {time.time() - t0:.2f}s: "
                f"inserted={dispatch_res.rows_inserted}, updated={dispatch_res.rows_updated}, quarantined={dispatch_res.rows_quarantined}"
            )
            results["pucsl_dispatch_rows"] = dispatch_res.rows_inserted
        else:
            print(f"WARNING: PUCSL file not found at {pucsl_path}")
            results["pucsl_dispatch_rows"] = 0

        return results

    def refresh_analytical_marts(self, dry_run: bool = False) -> None:
        """Invoke PostgreSQL stored procedures / commands to refresh all 5 analytical materialized views."""
        if dry_run:
            print("[DRY-RUN] Would refresh analytical materialized views.")
            return

        print("\nRefreshing analytical materialized views in schema 'mart'...")
        t0 = time.time()
        with get_connection(self.config, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("CALL etl.sp_refresh_mart_views(FALSE);")
                print(
                    "  - Refreshed monthly generation, annual energy mix, and monthly sales marts."
                )
                cur.execute("CALL mart.sp_refresh_analytical_marts();")
                print("  - Refreshed daily dispatch by source and monthly weather marts.")
        print(f"Materialized views refresh sequence completed in {time.time() - t0:.2f}s.")


def print_audit_summary(report: SupabaseAuditReport) -> None:
    """Print readable audit diagnostics."""
    print("\n" + "=" * 70)
    print("SUPABASE DATA WAREHOUSE HEALTH & INVENTORY AUDIT")
    print("=" * 70)
    print(f"Database Name       : {report.database_name}")
    print(f"PostgreSQL Version  : {report.server_version}")
    print(f"SSL Connection      : {'Enabled' if report.ssl_active else 'Disabled'}")
    print(
        f"Schemas (7 Segregated): {', '.join(report.schemas_found)} "
        f"({'PASS' if report.all_schemas_healthy else 'INCOMPLETE'})"
    )
    print(
        f"Migrations Status   : {report.migrations_applied} of {report.migrations_total} applied "
        f"({'PASS' if report.migrations_applied == report.migrations_total else 'PENDING'})"
    )

    print("\nConformed Dimensions:")
    for dim, count in sorted(report.dimension_tables.items()):
        status = f"{count:>8,d} rows" if count >= 0 else "  NOT CREATED"
        print(f"  - {dim:<35}: {status}")

    print("\nReference Taxonomies:")
    for ref, count in sorted(report.reference_tables.items()):
        status = f"{count:>8,d} rows" if count >= 0 else "  NOT CREATED"
        print(f"  - {ref:<35}: {status}")

    print("\nFact Tables (Kimball Constellation):")
    for fact, count in sorted(report.fact_tables.items()):
        status = f"{count:>8,d} rows" if count >= 0 else "  NOT CREATED"
        print(f"  - {fact:<35}: {status}")

    print("\nAnalytical Materialized Views (Marts):")
    for mv, count in sorted(report.materialized_views.items()):
        status = f"{count:>8,d} rows" if count >= 0 else "  NOT CREATED"
        print(f"  - {mv:<35}: {status}")

    print(
        f"\nAudit Quality Ledger: {max(report.data_quality_issues, 0):,d} issues tracked in audit.data_quality_issue"
    )
    print("=" * 70)


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint for Supabase migration and data provisioning."""
    load_dotenv(override=False)

    parser = argparse.ArgumentParser(
        description="Migrate and provision the GridLens Data Warehouse on Supabase PostgreSQL."
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Explicit PostgreSQL connection URL (e.g. Supabase connection string). Overrides .env.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect remote database and preview planned operations without mutating state.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Perform non-destructive health and inventory audit of the Supabase warehouse.",
    )
    parser.add_argument(
        "--skip-data",
        action="store_true",
        help="Apply migrations and seed dimensions, but skip loading historical facts.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed execution diagnostics.",
    )
    args = parser.parse_args(argv)

    if args.database_url:
        config = DatabaseConfig.from_url(args.database_url)
    else:
        config = DatabaseConfig.from_env(use_test_db=False, role="admin")

    migrator = SupabaseMigrator(config=config)

    print(f"Targeting database: {config.host}:{config.port}/{config.dbname}")

    # Check if user forgot to set DATABASE_URL
    if not args.database_url and not os.getenv("DATABASE_URL") and not os.getenv("SUPABASE_DB_URL"):
        if "supabase.co" not in config.host:
            print("\n[NOTE] No DATABASE_URL specified. Defaulting to local configuration.")
            print("To target Supabase, set DATABASE_URL in .env or pass --database-url:")
            print(
                "  python scripts/migrate_supabase.py --database-url "
                '"postgresql://postgres:[PASSWORD]@db.<project-ref>.supabase.co:5432/postgres"\n'
            )

    # Step 1: Connectivity check
    ok, msg = migrator.check_connection()
    if not ok:
        print("\n[ERROR] Database connection check failed:")
        print(f"  {msg}")
        return 1

    print(f"[OK] {msg}")

    # Mode: Verify Only
    if args.verify_only:
        report = migrator.audit_warehouse()
        print_audit_summary(report)
        return 0 if report.all_schemas_healthy and report.migrations_applied > 0 else 1

    # Mode: Dry Run
    if args.dry_run:
        print("\n--- Running Dry-Run Inspection ---")
        migrator.apply_migrations(dry_run=True)
        migrator.seed_dimensions(dry_run=True)
        if not args.skip_data:
            migrator.load_historical_data(dry_run=True)
        migrator.refresh_analytical_marts(dry_run=True)
        return 0

    # Mode: Full Migration & Data Load
    t_start = time.time()
    print("\n--- Step 1: Applying Sequential Database Migrations (001–022) ---")
    applied = migrator.apply_migrations(dry_run=False)
    print(f"Migrations applied: {applied}")

    print("\n--- Step 2: Seeding Conformed Dimensions & Reference Domains ---")
    seed_counts = migrator.seed_dimensions(dry_run=False)
    for tbl, cnt in seed_counts.items():
        if args.verbose:
            print(f"  Ensured {cnt} rows in {tbl}")

    if not args.skip_data:
        print("\n--- Step 3: Loading Authentic Historical Warehouse Data ---")
        migrator.load_historical_data(dry_run=False)

    print("\n--- Step 4: Refreshing Analytical Materialized Views ---")
    migrator.refresh_analytical_marts(dry_run=False)

    print("\n--- Step 5: Post-Migration Warehouse Verification ---")
    final_report = migrator.audit_warehouse()
    print_audit_summary(final_report)

    total_time = time.time() - t_start
    print(f"\nSupabase Data Warehouse provisioning completed successfully in {total_time:.2f}s!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
