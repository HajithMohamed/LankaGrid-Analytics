"""
Shared pytest fixtures providing isolated PostgreSQL 18 test database setup.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

from scripts.migrate import MigrationRunner
from src.common.config import DatabaseConfig
from src.common.db import get_connection


@pytest.fixture(scope="session")
def test_db_config() -> DatabaseConfig:
    """Return configuration targeting the isolated sl_grid_warehouse_test database."""
    return DatabaseConfig.from_env(use_test_db=True)


@pytest.fixture(scope="session")
def migrated_and_seeded_test_db(test_db_config: DatabaseConfig) -> Iterator[DatabaseConfig]:
    """
    Reset sl_grid_warehouse_test to a completely clean state, apply all forward migrations,
    configure least-privilege role passwords from environment, and execute reference seeding.
    """
    from scripts.seed_reference import ReferenceSeeder

    with get_connection(test_db_config, autocommit=True) as conn:
        with conn.cursor() as cur:
            for schema_name in ("mart", "etl", "staging", "dw", "audit", "ref", "raw"):
                cur.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;")
            cur.execute("DROP TABLE IF EXISTS public.schema_migrations CASCADE;")

    runner = MigrationRunner(migrations_dir=Path("database/migrations"))
    applied = runner.apply_migrations(test_db_config)
    assert applied >= 17, f"Expected at least 17 migrations applied, got {applied}"

    runner.configure_role_passwords_from_env(test_db_config)

    seeder = ReferenceSeeder()
    seeder.seed_all(test_db_config)

    yield test_db_config


@pytest.fixture
def db_conn(migrated_and_seeded_test_db: DatabaseConfig) -> Iterator[psycopg.Connection[object]]:
    """Provide a transactional connection to the migrated & seeded test database."""
    with get_connection(migrated_and_seeded_test_db) as conn:
        yield conn
