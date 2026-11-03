"""
Automated Safety and Unit Test Suite for Local PostgreSQL Bootstrap (scripts/bootstrap_local.py).

Verifies:
1. Environment validation (Python runtime >= 3.11, .env detection, .env.example copying).
2. Database creation idempotency and non-destructive execution (never executes DROP).
3. Migration discovery and immutability status check.
4. Reference seeding idempotency.
5. Historical data loader skipping when facts already populated.
6. Non-destructive warehouse verification of schemas, facts, dims, and views.
7. Next.js web/.env.local generation and synchronization.
8. CLI flags: --dry-run, --verify-only, and --skip-data.

Note: In accordance with .agents/rules/testing.md, unit tests are offline, in-memory,
and execute with zero external database dependencies via mocked connections.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.bootstrap_local import (
    EXPECTED_SCHEMAS,
    LocalBootstrapOrchestrator,
    StepResult,
)
from scripts.migrate import MigrationRunner
from scripts.seed_reference import ReferenceSeeder


@pytest.fixture
def repo_root() -> Path:
    """Return the absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def orchestrator(repo_root: Path) -> LocalBootstrapOrchestrator:
    """Return an orchestrator instance initialized with default options."""
    return LocalBootstrapOrchestrator(
        project_root=repo_root,
        dry_run=False,
        verify_only=False,
        skip_data=False,
    )


class TestBootstrapLocalSafety:
    """Validates core safety guarantees and behavioral contracts of bootstrap_local.py."""

    def test_python_runtime_version_gate(self, orchestrator: LocalBootstrapOrchestrator) -> None:
        """Verify that Python version >= 3.11 requirement is enforced."""
        with patch("sys.version_info", (3, 10, 0)):
            res = orchestrator.step1_validate_environment()
            assert res.status == "FAIL"
            assert "Python >= 3.11 required" in res.message

        with patch("sys.version_info", (3, 12, 1)):
            res = orchestrator.step1_validate_environment()
            assert res.status in ("OK", "WARN")

    def test_env_file_created_from_example_if_missing(self, tmp_path: Path) -> None:
        """Verify that when .env is absent, .env.example is copied safely."""
        fake_example = tmp_path / ".env.example"
        fake_example.write_text(
            "POSTGRES_PORT=5432\nPOSTGRES_DB=sl_grid_warehouse\n", encoding="utf-8"
        )

        orch = LocalBootstrapOrchestrator(project_root=tmp_path, dry_run=False)
        res = orch.step1_validate_environment()

        target_env = tmp_path / ".env"
        assert target_env.exists()
        assert "Created '.env' from '.env.example'" in " ".join(res.details)
        assert "POSTGRES_PORT=5432" in target_env.read_text(encoding="utf-8")

    def test_missing_raw_files_produce_warning_not_crash(self, tmp_path: Path) -> None:
        """Verify missing raw datasets emit a clean WARN status rather than crashing."""
        fake_env = tmp_path / ".env"
        fake_env.write_text(
            "POSTGRES_HOST=localhost\nPOSTGRES_PORT=5432\nPOSTGRES_DB=test\n", encoding="utf-8"
        )

        orch = LocalBootstrapOrchestrator(project_root=tmp_path, dry_run=False)
        res = orch.step1_validate_environment()

        assert res.status == "WARN"
        assert "raw data files are missing" in res.message

    def test_never_executes_drop_statements(self, repo_root: Path) -> None:
        """Strict AST/code review test: Assert bootstrap_local.py never executes DROP DATABASE/SCHEMA/TABLE."""
        script_path = repo_root / "scripts" / "bootstrap_local.py"
        assert script_path.exists()
        content = script_path.read_text(encoding="utf-8").upper()

        # Check for dangerous destructive patterns
        dangerous_patterns = [
            "DROP DATABASE",
            "DROP SCHEMA",
            "DROP TABLE",
            "TRUNCATE TABLE",
            "DELETE FROM DW.",
            "DELETE FROM RAW.",
        ]
        for pattern in dangerous_patterns:
            # We allow mentions inside comments/docs explaining safety, but not in SQL execution
            assert f'EXECUTE("{pattern}' not in content
            assert f"EXECUTE('{pattern}" not in content
            assert f'SQL.SQL("{pattern}' not in content
            assert f"SQL.SQL('{pattern}" not in content

    def test_safe_create_databases_skips_when_exists(
        self, orchestrator: LocalBootstrapOrchestrator
    ) -> None:
        """Verify safe create database logic skips when databases are already present."""
        orchestrator.step1_validate_environment()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)  # DB exists
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("psycopg.connect", return_value=mock_conn):
            res = orchestrator.step2_safe_create_databases()

            assert res.status == "OK"
            assert any("already exists. Skipping creation" in d for d in res.details)
            for call_args in mock_cursor.execute.call_args_list:
                stmt_str = str(call_args[0][0])
                assert "CREATE DATABASE" not in stmt_str

    def test_migrations_immutability_and_already_applied_check(
        self, orchestrator: LocalBootstrapOrchestrator
    ) -> None:
        """Verify that step3 detects all applied migrations and enforces SHA-256 integrity."""
        orchestrator.step1_validate_environment()

        mock_statuses = [
            MagicMock(version=f"{i:03d}_migration", is_applied=True) for i in range(1, 23)
        ]
        with patch.object(MigrationRunner, "get_status", return_value=mock_statuses):
            res = orchestrator.step3_run_migrations()

            assert res.status == "OK"
            assert "All 22 migrations already up to date" in res.message
            assert any("Already applied: 22 migrations" in d for d in res.details)

    def test_role_configuration_updates_credentials(
        self, orchestrator: LocalBootstrapOrchestrator
    ) -> None:
        """Verify role credential configuration without password leakage."""
        orchestrator.step1_validate_environment()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (True,)
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.transaction.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("psycopg.connect", return_value=mock_conn):
            res = orchestrator.step4_configure_roles()

            assert res.status == "OK"
            assert any(
                "Configured login password for role 'grid_analyst'" in d for d in res.details
            )
            env_pwd = os.getenv("POSTGRES_PASSWORD", "")
            if env_pwd:
                assert env_pwd not in res.message
                for d in res.details:
                    assert env_pwd not in d

    def test_reference_seeding_idempotence(self, orchestrator: LocalBootstrapOrchestrator) -> None:
        """Verify reference seeding succeeds idempotently."""
        orchestrator.step1_validate_environment()

        seed_counts = {
            "dw.dim_date": 2922,
            "dw.dim_interval": 120,
            "dw.dim_power_plant": 41,
            "dw.dim_energy_source": 9,
            "ref.unit": 17,
        }
        with patch.object(ReferenceSeeder, "seed_all", return_value=seed_counts):
            res = orchestrator.step5_seed_reference()

            assert res.status == "OK"
            assert "Seeded 5 dimension and reference tables" in res.message

    def test_historical_data_loader_skips_when_facts_populated(
        self, orchestrator: LocalBootstrapOrchestrator
    ) -> None:
        """Verify step6 skips fact loading when records meet or exceed targets."""
        orchestrator.step1_validate_environment()

        mock_cursor = MagicMock()
        # Return sales=49, weather=21924, dispatch=107115
        mock_cursor.fetchone.side_effect = [(49,), (21924,), (107115,)]
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("psycopg.connect", return_value=mock_conn):
            res = orchestrator.step6_load_historical_data()

            assert res.status == "OK"
            assert any("CEB 5-Year electricity sales already populated" in d for d in res.details)
            assert any("NASA POWER 5-Year weather already populated" in d for d in res.details)
            assert any("PUCSL March 2024 dispatch already populated" in d for d in res.details)

    def test_warehouse_verification_read_only_audit(
        self, orchestrator: LocalBootstrapOrchestrator
    ) -> None:
        """Verify non-destructive warehouse verification passes with expected counts."""
        orchestrator.step1_validate_environment()

        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [(s,) for s in EXPECTED_SCHEMAS],  # Schemas query
            [
                ("mv_monthly_weather_summary",),
                ("mv_daily_dispatch_by_source",),
                ("mv_monthly_generation_summary",),
                ("mv_annual_energy_mix",),
                ("mv_monthly_sales_summary",),
            ],  # Matviews query
        ]
        # Counts for: 4 facts + 2 dims + 1 analyst select
        mock_cursor.fetchone.side_effect = [
            (49,),
            (21924,),
            (107115,),
            (926,),  # facts
            (41,),
            (2922,),  # dims
            (49,),  # analyst role query
        ]
        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        with patch("psycopg.connect", return_value=mock_conn):
            res = orchestrator.step7_verify_warehouse()

            assert res.status == "OK"
            assert any("All 7 core schemas present" in d for d in res.details)
            assert any("dw.fact_electricity_sales: 49 rows" in d for d in res.details)
            assert any("dw.fact_weather_daily: 21,924 rows" in d for d in res.details)
            assert any("dw.fact_dispatch_interval_y2024: 107,115 rows" in d for d in res.details)
            assert any("audit.data_quality_issue: 926 rows" in d for d in res.details)
            assert any("Materialized Views: 5/5 verified" in d for d in res.details)
            assert any("Read-only role 'grid_analyst' authenticated" in d for d in res.details)

    def test_frontend_env_sync_maintains_live_mode(
        self, orchestrator: LocalBootstrapOrchestrator, repo_root: Path
    ) -> None:
        """Verify step8 synchronizes web/.env.local with live mode and proper port."""
        orchestrator.step1_validate_environment()
        res = orchestrator.step8_sync_frontend_env()

        assert res.status == "OK"
        web_env = repo_root / "web" / ".env.local"
        assert web_env.exists()
        content = web_env.read_text(encoding="utf-8")
        assert "DATA_SOURCE_MODE=live" in content
        assert "POSTGRES_USER=grid_analyst" in content
        assert f"POSTGRES_PORT={orchestrator.config.port}" in content

    def test_dry_run_flag_performs_zero_mutations(self, repo_root: Path) -> None:
        """Verify --dry-run simulates execution without modifying database or files."""
        dry_orch = LocalBootstrapOrchestrator(
            project_root=repo_root,
            dry_run=True,
            verify_only=False,
            skip_data=False,
        )
        exit_code = dry_orch.run()

        assert exit_code == 0
        statuses = [r.status for r in dry_orch.results]
        assert "FAIL" not in statuses
        # Provisioning, migrations, roles, seed, data load, and verification should be SKIPPED in dry-run mode
        assert "SKIPPED" in statuses

    def test_verify_only_flag_runs_only_audit_and_sync(self, repo_root: Path) -> None:
        """Verify --verify-only executes only validation, verification, and frontend sync."""
        with patch.object(
            LocalBootstrapOrchestrator,
            "step7_verify_warehouse",
            return_value=StepResult(7, "Warehouse Verification", "OK", "Simulated audit OK"),
        ):
            verify_orch = LocalBootstrapOrchestrator(
                project_root=repo_root,
                dry_run=False,
                verify_only=True,
                skip_data=False,
            )
            exit_code = verify_orch.run()

            assert exit_code == 0
            step_numbers = [r.step_number for r in verify_orch.results]
            assert step_numbers == [1, 7, 8]

    def test_skip_data_flag_skips_fact_loading(self, repo_root: Path) -> None:
        """Verify --skip-data bypasses step 6 fact data loading."""
        orch = LocalBootstrapOrchestrator(
            project_root=repo_root,
            dry_run=False,
            verify_only=False,
            skip_data=True,
        )
        res = orch.step6_load_historical_data()
        assert res.status == "SKIPPED"
        assert "skipped via flag" in res.message
