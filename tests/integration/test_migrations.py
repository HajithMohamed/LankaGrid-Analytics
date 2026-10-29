"""
Integration tests for database migration runner and schema bootstrap.
"""
from pathlib import Path
import pytest
from src.common.config import DatabaseConfig
from src.common.db import get_connection
from scripts.migrate import MigrationRunner


@pytest.mark.integration
def test_migration_runner_discovery() -> None:
    """Verify runner discovers migration SQL files in database/migrations."""
    migrations_dir = Path("database/migrations")
    runner = MigrationRunner(migrations_dir=migrations_dir)
    files = runner.discover_migrations()
    assert len(files) >= 1
    assert any("001_bootstrap.sql" in str(f) for f in files)


@pytest.mark.integration
def test_migration_application_and_idempotency() -> None:
    """
    Apply initial bootstrap migration, verify schema_migrations table,
    and assert re-running is strictly idempotent.
    """
    config = DatabaseConfig.from_env()
    runner = MigrationRunner(migrations_dir=Path("database/migrations"))

    # Initial migration application
    applied_count_1 = runner.apply_migrations(config)
    assert applied_count_1 >= 0

    # Verify schema_migrations table exists
    with get_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'schema_migrations'
                );
            """)
            exists = cur.fetchone()[0]
            assert exists is True

            cur.execute("SELECT version FROM schema_migrations;")
            applied_versions = [row[0] for row in cur.fetchall()]
            assert "001_bootstrap" in applied_versions

    # Re-running must be completely idempotent (0 new migrations applied)
    applied_count_2 = runner.apply_migrations(config)
    assert applied_count_2 == 0
