"""
Application and PostgreSQL database configuration loaded from environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseConfig:
    """Connection parameters for PostgreSQL with password masking in representations."""

    host: str
    port: int
    dbname: str
    user: str
    password: str
    sslmode: str = "disable"
    connect_timeout: int = 30

    def __repr__(self) -> str:
        return (
            f"DatabaseConfig(host={self.host!r}, port={self.port!r}, "
            f"dbname={self.dbname!r}, user={self.user!r}, "
            f"password='******', sslmode={self.sslmode!r}, "
            f"connect_timeout={self.connect_timeout!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def to_conn_kwargs(self) -> dict[str, Any]:
        """Return keyword arguments suitable for psycopg.connect()."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
            "sslmode": self.sslmode,
            "connect_timeout": self.connect_timeout,
        }

    def with_dbname(self, dbname: str) -> DatabaseConfig:
        """Return a copy of this configuration targeting a different database name."""
        return DatabaseConfig(
            host=self.host,
            port=self.port,
            dbname=dbname,
            user=self.user,
            password=self.password,
            sslmode=self.sslmode,
            connect_timeout=self.connect_timeout,
        )

    def with_credentials(self, user: str, password: str) -> DatabaseConfig:
        """Return a copy of this configuration using alternate role credentials."""
        return DatabaseConfig(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=user,
            password=password,
            sslmode=self.sslmode,
            connect_timeout=self.connect_timeout,
        )

    @classmethod
    def from_env(cls, use_test_db: bool = False) -> DatabaseConfig:
        """Load database configuration from environment variables (and local .env if unset)."""
        load_dotenv(override=False)
        db_key = "POSTGRES_TEST_DB" if use_test_db else "POSTGRES_DB"
        default_db = "sl_grid_warehouse_test" if use_test_db else "sl_grid_warehouse"
        return cls(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            dbname=os.getenv(db_key, default_db),
            user=os.getenv("POSTGRES_USER", "grid_admin"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            sslmode=os.getenv("POSTGRES_SSLMODE", "disable"),
            connect_timeout=int(os.getenv("DB_TIMEOUT_SECONDS", "30")),
        )


@dataclass(frozen=True)
class AppConfig:
    """Top-level application paths and environment configuration."""

    app_env: str
    log_level: str
    raw_dir: Path
    staging_dir: Path
    processed_dir: Path
    fixtures_dir: Path
    database: DatabaseConfig


def get_config(use_test_db: bool = False) -> AppConfig:
    """Load application and database configuration from environment."""
    load_dotenv(override=False)
    return AppConfig(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        raw_dir=Path(os.getenv("DATA_RAW_DIR", "data/raw")),
        staging_dir=Path(os.getenv("DATA_STAGING_DIR", "data/staging")),
        processed_dir=Path(os.getenv("DATA_PROCESSED_DIR", "data/processed")),
        fixtures_dir=Path(os.getenv("DATA_FIXTURES_DIR", "tests/fixtures")),
        database=DatabaseConfig.from_env(use_test_db=use_test_db),
    )

