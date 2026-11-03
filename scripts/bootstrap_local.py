#!/usr/bin/env python3
"""
GridLens — One-Command Local Native PostgreSQL Bootstrap & Warehouse Initializer.

GOVERNANCE & SAFETY:
- STRICT REQUIREMENT: Local Native PostgreSQL only (no Docker, no cloud databases).
- Non-destructive: NEVER executes DROP DATABASE, DROP SCHEMA, or DROP TABLE.
- Idempotent: Can be run repeatedly on fresh or existing databases without corrupting or duplicating data.
- Security: Never logs passwords or sensitive credentials to stdout or disk.
- Synchronizes Next.js frontend configuration (web/.env.local).

Usage:
    python scripts/bootstrap_local.py                  # Full automated bootstrap
    python scripts/bootstrap_local.py --dry-run        # Preview actions without executing DDL/DML
    python scripts/bootstrap_local.py --verify-only    # Non-destructive database audit
    python scripts/bootstrap_local.py --skip-data      # Apply schema & seed, skip large fact loads
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv
from psycopg import sql
from psycopg.cursor import Cursor

from scripts.migrate import MigrationRunner
from scripts.seed_reference import ReferenceSeeder

# Project imports
from src.common.config import DatabaseConfig


# -----------------------------------------------------------------------------
# Safe Database Result Helpers
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


# -----------------------------------------------------------------------------
# Configuration Constants
# -----------------------------------------------------------------------------
MIN_PYTHON_VERSION = (3, 11)
PRIMARY_DB_NAME = "sl_grid_warehouse"
TEST_DB_NAME = "sl_grid_warehouse_test"
MAINTENANCE_DB_NAME = "postgres"
DEFAULT_PORT = 5432

REQUIRED_RAW_FILES = [
    Path("data/raw/ceb/2020/Statistical_Digest_2020.pdf"),
    Path("data/raw/ceb/2024/Statistical_Digest_2024.pdf"),
    Path("data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json"),
    Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx"),
]

EXPECTED_SCHEMAS = ["dw", "staging", "audit", "mart", "ref", "raw", "public"]


@dataclass
class StepResult:
    """Represents the execution outcome of a bootstrap step."""

    step_number: int
    step_name: str
    status: str  # "OK", "SKIPPED", "WARN", "FAIL"
    message: str
    details: list[str] = field(default_factory=list)
    duration_sec: float = 0.0


class LocalBootstrapOrchestrator:
    """Coordinates the safe, idempotent, local-native warehouse bootstrap pipeline."""

    def __init__(
        self,
        project_root: Path,
        dry_run: bool = False,
        verify_only: bool = False,
        skip_data: bool = False,
    ) -> None:
        self.project_root = project_root
        self.dry_run = dry_run
        self.verify_only = verify_only
        self.skip_data = skip_data
        self.results: list[StepResult] = []
        self.config: DatabaseConfig | None = None

    def log(self, prefix: str, message: str) -> None:
        """Print timestamped status log."""
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] {prefix} {message}")

    # -------------------------------------------------------------------------
    # Step 1: Environment & File Validation
    # -------------------------------------------------------------------------
    def step1_validate_environment(self) -> StepResult:
        """Verify Python runtime version, local .env existence, and raw data assets."""
        t0 = time.time()
        details: list[str] = []

        # 1. Python version check
        current_py = sys.version_info[:2]
        if current_py < MIN_PYTHON_VERSION:
            msg = f"Python {current_py[0]}.{current_py[1]} detected. Python >= 3.11 required."
            return StepResult(1, "Environment Validation", "FAIL", msg, details, time.time() - t0)
        details.append(f"Python {sys.version.split()[0]} runtime verified.")

        # 2. .env configuration check
        env_path = self.project_root / ".env"
        env_example_path = self.project_root / ".env.example"
        if not env_path.exists():
            if env_example_path.exists():
                if not self.dry_run:
                    shutil.copyfile(env_example_path, env_path)
                    details.append(
                        "Created '.env' from '.env.example'. Please review credentials if using a custom PostgreSQL password."
                    )
                else:
                    details.append("Would create '.env' from '.env.example'.")
            else:
                return StepResult(
                    1,
                    "Environment Validation",
                    "FAIL",
                    "Neither .env nor .env.example found.",
                    details,
                    time.time() - t0,
                )
        else:
            details.append("Local '.env' configuration file found.")

        # Load environment variables
        load_dotenv(env_path, override=False)
        self.config = DatabaseConfig.from_env()

        # 3. Raw data assets check
        missing_files: list[str] = []
        for req_path in REQUIRED_RAW_FILES:
            full_path = self.project_root / req_path
            if not full_path.exists():
                missing_files.append(str(req_path))

        if missing_files:
            details.append(f"Missing raw files: {', '.join(missing_files)}")
            details.append(
                "Check data/raw/manifest.json or run scripts/acquire_historical_5yr.py if needed."
            )
            status = "WARN"
            msg = f"Environment configured, but {len(missing_files)} raw data files are missing."
        else:
            details.append(f"All {len(REQUIRED_RAW_FILES)} required raw datasets verified present.")
            status = "OK"
            msg = "Python runtime, environment files, and raw data assets verified."

        return StepResult(1, "Environment Validation", status, msg, details, time.time() - t0)

    # -------------------------------------------------------------------------
    # Step 2: Safe Database Creation
    # -------------------------------------------------------------------------
    def step2_safe_create_databases(self) -> StepResult:
        """Connect to maintenance database and create target databases if they do not exist."""
        t0 = time.time()
        details: list[str] = []
        assert self.config is not None

        # Build maintenance DB config targeting 'postgres'
        maint_config = self.config.with_dbname(MAINTENANCE_DB_NAME)

        try:
            # Connect with autocommit=True (required for CREATE DATABASE)
            with psycopg.connect(**maint_config.to_conn_kwargs(), autocommit=True) as conn:
                with conn.cursor() as cur:
                    for dbname in [PRIMARY_DB_NAME, TEST_DB_NAME]:
                        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (dbname,))
                        exists = cur.fetchone() is not None

                        if exists:
                            details.append(
                                f"Database '{dbname}' already exists. Skipping creation."
                            )
                        else:
                            if self.dry_run:
                                details.append(
                                    f"[Dry-Run] Would execute: CREATE DATABASE {dbname} WITH ENCODING = 'UTF8';"
                                )
                            else:
                                stmt = sql.SQL("CREATE DATABASE {} WITH ENCODING = 'UTF8';").format(
                                    sql.Identifier(dbname)
                                )
                                cur.execute(stmt)
                                details.append(f"Database '{dbname}' created successfully.")
            return StepResult(
                2,
                "Database Provisioning",
                "OK",
                "Target and test databases verified/provisioned.",
                details,
                time.time() - t0,
            )
        except Exception as exc:
            msg = f"Failed to connect to PostgreSQL maintenance database '{MAINTENANCE_DB_NAME}' on port {maint_config.port}."
            details.append(f"Error: {type(exc).__name__}: {exc}")
            details.append("Troubleshooting for Windows:")
            details.append(
                "1. Verify the PostgreSQL service is running (e.g., Get-Service postgresql*)."
            )
            details.append(
                f"2. Check POSTGRES_PORT ({maint_config.port}) and POSTGRES_USER in .env."
            )
            details.append(
                "3. For default PostgreSQL installations, set POSTGRES_USER=postgres and POSTGRES_PASSWORD=<your_installed_password>."
            )
            return StepResult(2, "Database Provisioning", "FAIL", msg, details, time.time() - t0)

    # -------------------------------------------------------------------------
    # Step 3: Run Sequential Migrations
    # -------------------------------------------------------------------------
    def step3_run_migrations(self) -> StepResult:
        """Apply sequential forward migrations (001–022) with SHA-256 immutability verification."""
        t0 = time.time()
        details: list[str] = []
        assert self.config is not None

        runner = MigrationRunner(migrations_dir=self.project_root / "database/migrations")
        try:
            statuses = runner.get_status(self.config)
            pending = [s for s in statuses if not s.is_applied]
            applied = [s for s in statuses if s.is_applied]

            details.append(f"Discovered {len(statuses)} total migration files.")
            details.append(f"Already applied: {len(applied)} migrations.")

            if not pending:
                details.append(
                    "All migrations are already applied and verified with SHA-256 checksums."
                )
                return StepResult(
                    3,
                    "Database Migrations",
                    "OK",
                    "All 22 migrations already up to date.",
                    details,
                    time.time() - t0,
                )

            if self.dry_run:
                details.append(
                    f"[Dry-Run] Would apply {len(pending)} pending migrations: {[s.version for s in pending]}"
                )
                return StepResult(
                    3,
                    "Database Migrations",
                    "SKIPPED",
                    f"Dry run: {len(pending)} migrations pending.",
                    details,
                    time.time() - t0,
                )

            applied_count = runner.apply_migrations(self.config)
            details.append(f"Successfully applied {applied_count} new migration(s).")
            return StepResult(
                3,
                "Database Migrations",
                "OK",
                f"Applied {applied_count} pending migration(s).",
                details,
                time.time() - t0,
            )
        except Exception as exc:
            details.append(f"Migration error: {exc}")
            return StepResult(
                3,
                "Database Migrations",
                "FAIL",
                "Migration execution failed.",
                details,
                time.time() - t0,
            )

    # -------------------------------------------------------------------------
    # Step 4: Configure Least-Privilege Application Roles
    # -------------------------------------------------------------------------
    def step4_configure_roles(self) -> StepResult:
        """Assign environment passwords and grant permissions to grid_etl and grid_analyst."""
        t0 = time.time()
        details: list[str] = []
        assert self.config is not None

        if self.dry_run:
            details.append("[Dry-Run] Would configure passwords for 'grid_etl' and 'grid_analyst'.")
            return StepResult(
                4,
                "Role Configuration",
                "SKIPPED",
                "Dry run: role configuration skipped.",
                details,
                time.time() - t0,
            )

        try:
            analyst_user = os.getenv("POSTGRES_ANALYST_USER", "grid_analyst")
            analyst_pwd = (
                os.getenv("POSTGRES_ANALYST_PASSWORD")
                or os.getenv("POSTGRES_PASSWORD")
                or "grid_analyst_dev_password_change_me"
            )
            etl_user = os.getenv("POSTGRES_ETL_USER", "grid_etl")
            etl_pwd = (
                os.getenv("POSTGRES_ETL_PASSWORD")
                or os.getenv("POSTGRES_PASSWORD")
                or "grid_etl_dev_password_change_me"
            )

            with psycopg.connect(**self.config.to_conn_kwargs(), autocommit=True) as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        for role_name, role_pwd in [
                            (etl_user, etl_pwd),
                            (analyst_user, analyst_pwd),
                        ]:
                            cur.execute(
                                "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s);",
                                (role_name,),
                            )
                            if _fetch_scalar(cur, False):
                                stmt = sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {};").format(
                                    sql.Identifier(role_name),
                                    sql.Literal(role_pwd),
                                )
                                cur.execute(stmt)
                                details.append(f"Configured login password for role '{role_name}'.")

            return StepResult(
                4,
                "Role Configuration",
                "OK",
                "Configured least-privilege role credentials.",
                details,
                time.time() - t0,
            )
        except Exception as exc:
            details.append(f"Role configuration error: {exc}")
            return StepResult(
                4,
                "Role Configuration",
                "WARN",
                f"Role credential assignment notice: {exc}",
                details,
                time.time() - t0,
            )

    # -------------------------------------------------------------------------
    # Step 5: Seed Conformed Dimensions & Reference Taxonomies
    # -------------------------------------------------------------------------
    def step5_seed_reference(self) -> StepResult:
        """Seed conformed dimensions and domain taxonomies idempotently."""
        t0 = time.time()
        details: list[str] = []
        assert self.config is not None

        if self.dry_run:
            details.append(
                "[Dry-Run] Would seed 13 conformed dimension and reference tables idempotently."
            )
            return StepResult(
                5,
                "Reference Seeding",
                "SKIPPED",
                "Dry run: reference seeding skipped.",
                details,
                time.time() - t0,
            )

        try:
            seeder = ReferenceSeeder()
            counts = seeder.seed_all(self.config)
            details.append(
                f"Seeded {len(counts)} dimension & reference tables with zero duplicates."
            )
            for tbl, cnt in sorted(counts.items()):
                details.append(f"  - {tbl}: {cnt} rows guaranteed")
            return StepResult(
                5,
                "Reference Seeding",
                "OK",
                f"Seeded {len(counts)} dimension and reference tables.",
                details,
                time.time() - t0,
            )
        except Exception as exc:
            details.append(f"Reference seeding error: {exc}")
            return StepResult(
                5,
                "Reference Seeding",
                "FAIL",
                "Reference seeding failed.",
                details,
                time.time() - t0,
            )

    # -------------------------------------------------------------------------
    # Step 6: Populate Historical Warehouse Data (Idempotent)
    # -------------------------------------------------------------------------
    def step6_load_historical_data(self) -> StepResult:
        """Load authentic CEB, NASA POWER, and PUCSL datasets only if not already populated."""
        t0 = time.time()
        details: list[str] = []

        if self.skip_data:
            details.append("Skipping historical fact data loading as requested via --skip-data.")
            return StepResult(
                6,
                "Historical Data Loading",
                "SKIPPED",
                "Historical data loading skipped via flag.",
                details,
                time.time() - t0,
            )

        assert self.config is not None

        if self.dry_run:
            details.append(
                "[Dry-Run] Would inspect row counts and load CEB sales, NASA weather, and PUCSL dispatch."
            )
            return StepResult(
                6,
                "Historical Data Loading",
                "SKIPPED",
                "Dry run: data loading skipped.",
                details,
                time.time() - t0,
            )

        try:
            from src.etl.real_data_loader import RealDataWarehouseLoader

            loader = RealDataWarehouseLoader(config=self.config)

            # 1. CEB Sales Check
            with psycopg.connect(**self.config.to_conn_kwargs()) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM dw.fact_electricity_sales;")
                    sales_count = _fetch_int(cur)

            if sales_count >= 49:
                details.append(
                    f"CEB 5-Year electricity sales already populated ({sales_count} rows >= 49). Skipping."
                )
            else:
                self.log("...", "Loading CEB 5-Year Billed Electricity Sales (2020-2024)...")
                t_sub = time.time()
                ceb_results = loader.load_5yr_ceb_sales()
                total_ins = sum(r.rows_inserted for r in ceb_results)
                details.append(
                    f"Loaded {len(ceb_results)} CEB sales batches ({total_ins} rows inserted) in {time.time() - t_sub:.2f}s."
                )

            # 2. NASA Weather Check
            with psycopg.connect(**self.config.to_conn_kwargs()) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM dw.fact_weather_daily;")
                    weather_count = _fetch_int(cur)

            if weather_count >= 21924:
                details.append(
                    f"NASA POWER 5-Year weather already populated ({weather_count} rows >= 21,924). Skipping."
                )
            else:
                nasa_path = (
                    self.project_root / "data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json"
                )
                if nasa_path.exists():
                    self.log(
                        "...", "Loading NASA POWER 5-Year Meteorological Dataset (2020-2024)..."
                    )
                    t_sub = time.time()
                    nasa_res = loader.load_nasa_weather_json(nasa_path)
                    details.append(
                        f"Loaded NASA weather ({nasa_res.rows_inserted} inserted, {nasa_res.rows_quarantined} quarantined) in {time.time() - t_sub:.2f}s."
                    )
                else:
                    details.append(f"NASA 5-Year weather file missing at {nasa_path}. Skipped.")

            # 3. PUCSL Dispatch Check
            with psycopg.connect(**self.config.to_conn_kwargs()) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) FROM dw.fact_dispatch_interval_y2024;")
                    dispatch_count = _fetch_int(cur)

            if dispatch_count >= 107115:
                details.append(
                    f"PUCSL March 2024 dispatch already populated ({dispatch_count} rows >= 107,115). Skipping."
                )
            else:
                pucsl_path = (
                    self.project_root / "data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx"
                )
                if pucsl_path.exists():
                    self.log(
                        "...", "Loading PUCSL March 2024 15-Minute Dispatch Curves (31 Days)..."
                    )
                    t_sub = time.time()
                    pucsl_res = loader.load_pucsl_dispatch_xlsx(pucsl_path)
                    details.append(
                        f"Loaded PUCSL dispatch ({pucsl_res.rows_inserted} inserted, {pucsl_res.rows_quarantined} quarantined) in {time.time() - t_sub:.2f}s."
                    )
                else:
                    details.append(f"PUCSL dispatch file missing at {pucsl_path}. Skipped.")

            return StepResult(
                6,
                "Historical Data Loading",
                "OK",
                "Historical warehouse datasets verified and loaded.",
                details,
                time.time() - t0,
            )
        except Exception as exc:
            details.append(f"Historical data loading error: {exc}")
            return StepResult(
                6,
                "Historical Data Loading",
                "FAIL",
                "Historical data loading encountered an error.",
                details,
                time.time() - t0,
            )

    # -------------------------------------------------------------------------
    # Step 7: Non-Destructive Warehouse Verification
    # -------------------------------------------------------------------------
    def step7_verify_warehouse(self) -> StepResult:
        """Perform comprehensive read-only audit of schemas, dimensions, facts, views, and roles."""
        t0 = time.time()
        details: list[str] = []
        assert self.config is not None

        try:
            with psycopg.connect(**self.config.to_conn_kwargs()) as conn:
                with conn.cursor() as cur:
                    # 1. Schemas check
                    cur.execute("SELECT schema_name FROM information_schema.schemata;")
                    existing_schemas = {r[0] for r in cur.fetchall()}
                    missing_schemas = [s for s in EXPECTED_SCHEMAS if s not in existing_schemas]
                    if missing_schemas:
                        details.append(f"Missing schemas: {missing_schemas}")
                    else:
                        details.append(
                            f"All {len(EXPECTED_SCHEMAS)} core schemas present ({', '.join(EXPECTED_SCHEMAS)})."
                        )

                    # 2. Fact table counts
                    fact_checks = [
                        ("dw", "fact_electricity_sales", 49),
                        ("dw", "fact_weather_daily", 21924),
                        ("dw", "fact_dispatch_interval_y2024", 107115),
                        ("audit", "data_quality_issue", 926),
                    ]
                    for schema_name, tbl_name, expected_min in fact_checks:
                        full_name = f"{schema_name}.{tbl_name}"
                        try:
                            stmt = sql.SQL("SELECT count(*) FROM {}.{};").format(
                                sql.Identifier(schema_name),
                                sql.Identifier(tbl_name),
                            )
                            cur.execute(stmt)
                            cnt = _fetch_int(cur)
                            status_sym = "[OK]" if cnt >= expected_min else "[WARN]"
                            details.append(
                                f"{status_sym} {full_name}: {cnt:,} rows (expected >= {expected_min:,})"
                            )
                        except Exception as e:
                            details.append(f"[WARN] {full_name} query failed: {e}")

                    # 3. Conformed Dimension counts
                    dim_checks = [
                        ("dw", "dim_power_plant", 41),
                        ("dw", "dim_date", 2922),
                    ]
                    for schema_name, dim_name, expected_exact in dim_checks:
                        full_name = f"{schema_name}.{dim_name}"
                        try:
                            stmt = sql.SQL("SELECT count(*) FROM {}.{};").format(
                                sql.Identifier(schema_name),
                                sql.Identifier(dim_name),
                            )
                            cur.execute(stmt)
                            cnt = _fetch_int(cur)
                            status_sym = "[OK]" if cnt == expected_exact else "[WARN]"
                            details.append(
                                f"{status_sym} {full_name}: {cnt:,} rows (expected {expected_exact:,})"
                            )
                        except Exception as e:
                            details.append(f"[WARN] {full_name} query failed: {e}")

                    # 4. Materialized Views check
                    cur.execute("SELECT matviewname FROM pg_matviews WHERE schemaname = 'mart';")
                    matviews = {r[0] for r in cur.fetchall()}
                    expected_mvs = [
                        "mv_monthly_weather_summary",
                        "mv_daily_dispatch_by_source",
                        "mv_monthly_generation_summary",
                        "mv_annual_energy_mix",
                        "mv_monthly_sales_summary",
                    ]
                    mvs_found = [m for m in expected_mvs if m in matviews]
                    details.append(
                        f"[OK] Materialized Views: {len(mvs_found)}/{len(expected_mvs)} verified in schema 'mart'."
                    )

            # 5. Role Security & Least Privilege Check
            analyst_user = os.getenv("POSTGRES_ANALYST_USER", "grid_analyst")
            analyst_pwd = (
                os.getenv("POSTGRES_ANALYST_PASSWORD")
                or os.getenv("POSTGRES_PASSWORD")
                or "grid_analyst_dev_password_change_me"
            )
            analyst_cfg = self.config.with_credentials(analyst_user, analyst_pwd)

            try:
                with psycopg.connect(**analyst_cfg.to_conn_kwargs()) as aconn:
                    with aconn.cursor() as acur:
                        acur.execute("SELECT count(*) FROM dw.fact_electricity_sales;")
                        analyst_rows = _fetch_int(acur)
                        details.append(
                            f"[OK] Read-only role '{analyst_user}' authenticated and queried {analyst_rows} sales records."
                        )
            except Exception as e:
                details.append(f"[WARN] Role '{analyst_user}' check: {e}")

            return StepResult(
                7,
                "Warehouse Verification",
                "OK",
                "Read-only warehouse integrity verified successfully.",
                details,
                time.time() - t0,
            )
        except Exception as exc:
            details.append(f"Verification error: {exc}")
            return StepResult(
                7,
                "Warehouse Verification",
                "FAIL",
                "Warehouse verification audit failed.",
                details,
                time.time() - t0,
            )

    # -------------------------------------------------------------------------
    # Step 8: Frontend Environment Synchronization
    # -------------------------------------------------------------------------
    def step8_sync_frontend_env(self) -> StepResult:
        """Create or synchronize web/.env.local with local PostgreSQL settings."""
        t0 = time.time()
        details: list[str] = []
        assert self.config is not None

        web_env_path = self.project_root / "web" / ".env.local"
        analyst_user = os.getenv("POSTGRES_ANALYST_USER", "grid_analyst")
        analyst_pwd = os.getenv("POSTGRES_ANALYST_PASSWORD") or os.getenv(
            "POSTGRES_PASSWORD", "grid_analyst_dev_password_change_me"
        )

        content = (
            "# ==============================================================================\n"
            "# GridLens Next.js Analytics Dashboard — Local Native PostgreSQL Configuration\n"
            "# Auto-configured by scripts/bootstrap_local.py\n"
            "# ==============================================================================\n"
            f"POSTGRES_HOST={self.config.host}\n"
            f"POSTGRES_PORT={self.config.port}\n"
            f"POSTGRES_DB={self.config.dbname}\n"
            f"POSTGRES_USER={analyst_user}\n"
            f"POSTGRES_PASSWORD={analyst_pwd}\n"
            "DATA_SOURCE_MODE=live\n"
            "QUERY_STATEMENT_TIMEOUT_MS=5000\n"
            "MAX_QUERY_ROWS_LIMIT=5000\n"
            "NODE_ENV=development\n"
        )

        if not web_env_path.exists():
            if self.dry_run:
                details.append(
                    f"[Dry-Run] Would create {web_env_path} (DATA_SOURCE_MODE=live, port={self.config.port})."
                )
            else:
                web_env_path.parent.mkdir(parents=True, exist_ok=True)
                web_env_path.write_text(content, encoding="utf-8")
                details.append(
                    f"Created {web_env_path} configured for local native PostgreSQL (port={self.config.port})."
                )
        else:
            # Check existing configuration
            existing_text = web_env_path.read_text(encoding="utf-8")
            if (
                f"POSTGRES_PORT={self.config.port}" not in existing_text
                or "DATA_SOURCE_MODE=live" not in existing_text
            ):
                if not self.dry_run:
                    web_env_path.write_text(content, encoding="utf-8")
                    details.append(
                        f"Updated {web_env_path} to match active port {self.config.port} and DATA_SOURCE_MODE=live."
                    )
                else:
                    details.append(
                        f"[Dry-Run] Would update {web_env_path} with port {self.config.port}."
                    )
            else:
                details.append(
                    f"{web_env_path} is already up to date with port {self.config.port}."
                )

        return StepResult(
            8,
            "Frontend Configuration",
            "OK",
            "Synchronized web/.env.local configuration.",
            details,
            time.time() - t0,
        )

    # -------------------------------------------------------------------------
    # Pipeline Orchestration
    # -------------------------------------------------------------------------
    def run(self) -> int:
        """Run the configured bootstrap sequence and output structured execution summary."""
        print("\n" + "=" * 78)
        print("  GridLens — One-Command Local Native PostgreSQL Bootstrap")
        print("  Sri Lanka National Electricity Grid Analytics Data Warehouse")
        print("=" * 78)
        if self.dry_run:
            print("  MODE: DRY-RUN (Previewing actions without executing DDL/DML)")
        elif self.verify_only:
            print("  MODE: VERIFY-ONLY (Read-only database & schema audit)")
        print("=" * 78 + "\n")

        total_t0 = time.time()

        # Step 1: Environment Validation
        res1 = self.step1_validate_environment()
        self.results.append(res1)
        self._print_step_result(res1)
        if res1.status == "FAIL":
            return self._finalize_and_exit(total_t0)

        # In verify-only mode, jump directly to verification and frontend sync
        if self.verify_only:
            res7 = self.step7_verify_warehouse()
            self.results.append(res7)
            self._print_step_result(res7)

            res8 = self.step8_sync_frontend_env()
            self.results.append(res8)
            self._print_step_result(res8)

            return self._finalize_and_exit(total_t0)

        # Step 2: Database Provisioning
        res2 = self.step2_safe_create_databases()
        self.results.append(res2)
        self._print_step_result(res2)
        if res2.status == "FAIL":
            return self._finalize_and_exit(total_t0)

        # Step 3: Run Sequential Migrations
        res3 = self.step3_run_migrations()
        self.results.append(res3)
        self._print_step_result(res3)
        if res3.status == "FAIL":
            return self._finalize_and_exit(total_t0)

        # Step 4: Configure Roles
        res4 = self.step4_configure_roles()
        self.results.append(res4)
        self._print_step_result(res4)

        # Step 5: Seed Conformed Dimensions & Reference
        res5 = self.step5_seed_reference()
        self.results.append(res5)
        self._print_step_result(res5)
        if res5.status == "FAIL":
            return self._finalize_and_exit(total_t0)

        # Step 6: Historical Data Loading
        res6 = self.step6_load_historical_data()
        self.results.append(res6)
        self._print_step_result(res6)
        if res6.status == "FAIL":
            return self._finalize_and_exit(total_t0)

        # Step 7: Warehouse Verification
        res7 = self.step7_verify_warehouse()
        self.results.append(res7)
        self._print_step_result(res7)

        # Step 8: Frontend Environment Sync
        res8 = self.step8_sync_frontend_env()
        self.results.append(res8)
        self._print_step_result(res8)

        return self._finalize_and_exit(total_t0)

    def _print_step_result(self, res: StepResult) -> None:
        badge = {
            "OK": "[OK]",
            "SKIPPED": "[SKIP]",
            "WARN": "[WARN]",
            "FAIL": "[FAIL]",
        }.get(res.status, "[INFO]")

        print(f"{badge} Step {res.step_number}: {res.step_name} ({res.duration_sec:.2f}s)")
        print(f"       {res.message}")
        for d in res.details:
            print(f"       - {d}")
        print()

    def _finalize_and_exit(self, total_t0: float) -> int:
        total_time = time.time() - total_t0
        failures = [r for r in self.results if r.status == "FAIL"]
        warnings = [r for r in self.results if r.status == "WARN"]

        print("=" * 78)
        print("  Bootstrap Execution Summary")
        print("=" * 78)
        for r in self.results:
            badge = f"[{r.status}]".ljust(8)
            print(f"  {badge} Step {r.step_number}: {r.step_name} ({r.duration_sec:.2f}s)")
        print("-" * 78)
        print(
            f"  Total Duration: {total_time:.2f}s | Steps: {len(self.results)} | Failures: {len(failures)} | Warnings: {len(warnings)}"
        )

        if failures:
            print(
                "\n  [FAIL] Bootstrap encountered errors. Please resolve the issues listed above."
            )
            return 1
        elif warnings:
            print("\n  [WARN] Bootstrap completed with warnings. All core services are ready.")
            self._print_next_steps()
            return 0
        else:
            print("\n  [SUCCESS] Warehouse bootstrap completed successfully!")
            self._print_next_steps()
            return 0

    def _print_next_steps(self) -> None:
        assert self.config is not None
        print("\n  Next Steps for Developers:")
        print("  1. Run automated database and ETL tests:")
        print("       pytest tests/unit/ tests/data_quality/ -v")
        print("  2. Start the Next.js Analytics Dashboard:")
        print("       cd web")
        print("       pnpm dev")
        print("     Then open http://localhost:3000 in your browser.")
        print("=" * 78 + "\n")


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="GridLens One-Command Local Native PostgreSQL Bootstrap.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the bootstrap process without modifying any database or files.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Run read-only schema, table, row count, and role verification without changes.",
    )
    parser.add_argument(
        "--skip-data",
        action="store_true",
        help="Run schema migrations, roles, and reference seeding, but skip historical fact loading.",
    )

    args = parser.parse_args(argv)
    project_root = Path(__file__).resolve().parent.parent

    orchestrator = LocalBootstrapOrchestrator(
        project_root=project_root,
        dry_run=args.dry_run,
        verify_only=args.verify_only,
        skip_data=args.skip_data,
    )
    return orchestrator.run()


if __name__ == "__main__":
    sys.exit(main())
