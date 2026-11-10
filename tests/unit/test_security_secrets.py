"""
Unit tests for Phase 6.2 security, Supabase configuration, secret scanning,
and preflight database verification.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.common.config import (
    DatabaseConfig,
    validate_production_database_url,
)
from src.common.db import verify_warehouse_preflight

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
class TestProductionDatabaseUrlValidation:
    """Tests for strict production DATABASE_URL validation."""

    def test_rejects_empty_or_none_url(self) -> None:
        with pytest.raises(ValueError, match="missing or empty"):
            validate_production_database_url(None)

        with pytest.raises(ValueError, match="missing or empty"):
            validate_production_database_url("   ")

    def test_rejects_localhost_and_loopback_hosts(self) -> None:
        for host in ["localhost", "127.0.0.1", "0.0.0.0"]:
            url = f"postgresql://grid_admin:secret@{host}:5432/sl_grid_warehouse"
            with pytest.raises(ValueError, match="cannot target local host"):
                validate_production_database_url(url)

    def test_rejects_unsubstituted_placeholders(self) -> None:
        placeholder_urls = [
            "postgresql://postgres:[YOUR-PASSWORD]@db.example.supabase.co:5432/postgres",
            "postgresql://postgres:secret@db.<project-ref>.supabase.co:5432/postgres",
            "postgresql://postgres:grid_dev_password_change_me@db.example.supabase.co:5432/postgres",
        ]
        for url in placeholder_urls:
            with pytest.raises(ValueError, match="placeholder"):
                validate_production_database_url(url)

    def test_rejects_missing_password(self) -> None:
        url = "postgresql://postgres@db.example.supabase.co:5432/postgres"
        with pytest.raises(ValueError, match="does not include a database password"):
            validate_production_database_url(url)

    def test_accepts_valid_supabase_direct_and_pooler_urls(self) -> None:
        direct_url = (
            "postgresql://postgres:Str0ngP@ssw0rd@db.abcdefghijklmnop.supabase.co:5432/postgres"
        )
        pooler_url = "postgresql://postgres.abcdefghijklmnop:Str0ngP@ssw0rd@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
        validate_production_database_url(direct_url)
        validate_production_database_url(pooler_url)

    def test_from_env_require_remote_url_never_falls_back_to_localhost(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", "")
        monkeypatch.setenv("SUPABASE_DB_URL", "")
        monkeypatch.setenv("ETL_DATABASE_URL", "")
        monkeypatch.setenv("MIGRATION_DATABASE_URL", "")
        monkeypatch.setenv("ANALYST_DATABASE_URL", "")
        monkeypatch.setenv("READONLY_DATABASE_URL", "")

        with pytest.raises(ValueError, match="missing or empty"):
            DatabaseConfig.from_env(role="etl", require_remote_url=True)


@pytest.mark.unit
class TestSupabaseConnectionModesAndRoleSeparation:
    """Tests for Supabase connection modes, pooler handling, and role separation."""

    def test_does_not_rewrite_direct_host_to_guessed_regional_pooler(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SUPABASE_POOLER_HOST", raising=False)
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://postgres:secretpass@db.abcdefghijklmnop.supabase.co:5432/postgres",
        )
        cfg = DatabaseConfig.from_env()
        kwargs = cfg.to_conn_kwargs()

        assert kwargs["host"] == "db.abcdefghijklmnop.supabase.co"
        assert kwargs["user"] == "postgres"
        assert kwargs["sslmode"] == "require"
        assert cfg.connection_mode == "direct"

    def test_detects_session_and_transaction_pooler_modes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://postgres.abcdefghijklmnop:secret@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres",
        )
        session_cfg = DatabaseConfig.from_env()
        assert session_cfg.connection_mode == "session_pooler"

        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://postgres.abcdefghijklmnop:secret@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres",
        )
        tx_cfg = DatabaseConfig.from_env()
        assert tx_cfg.connection_mode == "transaction_pooler"

    def test_role_separated_environment_urls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "MIGRATION_DATABASE_URL",
            "postgresql://grid_admin:adminpass@db.proj.supabase.co:5432/postgres",
        )
        monkeypatch.setenv(
            "ETL_DATABASE_URL",
            "postgresql://grid_etl:etlpass@db.proj.supabase.co:5432/postgres",
        )
        monkeypatch.setenv(
            "ANALYST_DATABASE_URL",
            "postgresql://grid_analyst:analystpass@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres",
        )
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://postgres:defaultpass@db.proj.supabase.co:5432/postgres",
        )

        admin_cfg = DatabaseConfig.from_env(role="admin")
        etl_cfg = DatabaseConfig.from_env(role="etl")
        analyst_cfg = DatabaseConfig.from_env(role="analyst")

        assert admin_cfg.user == "grid_admin"
        assert etl_cfg.user == "grid_etl"
        assert analyst_cfg.user == "grid_analyst"
        assert analyst_cfg.port == 6543


@pytest.mark.unit
class TestWarehousePreflightVerification:
    """Tests for read-only database preflight check before ETL writes."""

    def test_preflight_passes_when_all_requirements_met(self) -> None:
        cfg = DatabaseConfig(
            host="db.abcdefghijklmnop.supabase.co",
            port=5432,
            dbname="postgres",
            user="grid_etl",
            password="valid_password_123",
            sslmode="require",
        )

        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [
            ("postgres", "grid_etl", True),  # current_database, current_user, ssl_active
            (True,),  # EXISTS public.schema_migrations
            (23, "023_phase6_warehouse_freshness_and_maintenance.sql"),  # count, max
            (True,),  # has_schema_privilege & has_table_privilege
        ]
        mock_cur.fetchall.return_value = [
            ("audit",),
            ("dw",),
            ("etl",),
            ("mart",),
            ("raw",),
            ("ref",),
            ("staging",),
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        with patch("src.common.db.psycopg.connect") as mock_connect:
            mock_connect.return_value.__enter__.return_value = mock_conn
            result = verify_warehouse_preflight(cfg, require_remote=True)

        assert result.ok is True
        assert result.ssl_in_use is True
        assert result.migrations_count == 23
        assert result.missing_schemas == ()

    def test_preflight_fails_when_schemas_or_migrations_missing(self) -> None:
        cfg = DatabaseConfig(
            host="db.abcdefghijklmnop.supabase.co",
            port=5432,
            dbname="postgres",
            user="grid_etl",
            password="valid_password_123",
            sslmode="require",
        )

        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [
            ("postgres", "grid_etl", True),
            (False,),  # schema_migrations missing
        ]
        mock_cur.fetchall.return_value = [("public",)]  # Missing warehouse schemas

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        with patch("src.common.db.psycopg.connect") as mock_connect:
            mock_connect.return_value.__enter__.return_value = mock_conn
            result = verify_warehouse_preflight(cfg, require_remote=True)

        assert result.ok is False
        assert len(result.missing_schemas) == 7
        assert any("missing required warehouse schemas" in e for e in result.errors)
        assert any("public.schema_migrations" in e for e in result.errors)


@pytest.mark.unit
class TestRepositorySecurityAndSecretHygiene:
    """Automated checks preventing reintroduction of insecure TLS or leaked secrets."""

    def test_nextjs_db_client_enforces_verified_tls(self) -> None:
        client_ts = (REPO_ROOT / "web" / "src" / "lib" / "db" / "client.ts").read_text(
            encoding="utf-8"
        )
        assert "rejectUnauthorized: false" not in client_ts
        assert "rejectUnauthorized: true" in client_ts

    def test_no_hardcoded_regional_pooler_in_code_or_env_templates(self) -> None:
        files_to_check = [
            REPO_ROOT / "src" / "common" / "config.py",
            REPO_ROOT / "src" / "common" / "db.py",
            REPO_ROOT / ".env.example",
            REPO_ROOT / "web" / ".env.example",
            REPO_ROOT / "README.md",
        ]
        for path in files_to_check:
            content = path.read_text(encoding="utf-8")
            assert "aws-0-ap-northeast-2.pooler.supabase.com" not in content, (
                f"Found hardcoded regional pooler in {path}"
            )

    def test_no_secret_tokens_in_source_files(self) -> None:
        secret_pattern = re.compile(r"(ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|leormbswimbnpixkkbbu)")
        scan_dirs = [
            REPO_ROOT / "src",
            REPO_ROOT / "scripts",
            REPO_ROOT / "web" / "src",
            REPO_ROOT / ".github",
            REPO_ROOT / "docs",
        ]
        for base in scan_dirs:
            for file_path in base.rglob("*"):
                if file_path.is_file() and file_path.suffix in {
                    ".py",
                    ".ts",
                    ".tsx",
                    ".yml",
                    ".yaml",
                    ".json",
                    ".md",
                }:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    assert not secret_pattern.search(text), (
                        f"Potential secret token or leaked project ref detected in {file_path}"
                    )
