"""
Integration tests for PostgreSQL connectivity, failure handling, and connection pool behavior.
"""

import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection, test_connection


@pytest.mark.integration
def test_db_connection_failure_handling() -> None:
    """Verify that attempting to connect to a nonexistent database host fails cleanly."""
    bad_config = DatabaseConfig(
        host="nonexistent.invalid.local",
        port=5432,
        dbname="sl_grid_warehouse",
        user="grid_admin",
        password="bad_password",
        connect_timeout=2,
    )
    is_connected, error_msg = test_connection(bad_config)
    assert not is_connected
    assert error_msg is not None


@pytest.mark.integration
def test_db_connection_success() -> None:
    """Verify successful connection to active PostgreSQL instance."""
    config = DatabaseConfig.from_env()
    is_connected, error_msg = test_connection(config)
    assert is_connected, f"Database connection failed: {error_msg}"


@pytest.mark.integration
def test_db_version_check() -> None:
    """Assert the active database is PostgreSQL 18."""
    config = DatabaseConfig.from_env()
    with get_connection(config) as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW server_version;")
            row = cur.fetchone()
            assert row is not None
            version_str = row[0]
            assert version_str.startswith("18"), f"Expected PostgreSQL 18, got: {version_str}"
