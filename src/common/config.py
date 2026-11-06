"""
Application and PostgreSQL database configuration loaded from environment variables.
"""

from __future__ import annotations

import os
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def parse_database_url(url: str) -> dict[str, Any]:
    """Safely parse a database connection URL (e.g., Supabase, PostgreSQL).

    Handles bracketed placeholders like [YOUR-PASSWORD], URL-encoded
    credentials, query parameters like sslmode, and fallback defaults.
    """
    cleaned_url = url
    has_bracket_placeholder = False

    # Guard against RFC 3986 IPv6 validation errors when bracketed placeholders are present
    if "[" in url and "]" in url:
        at_pos = url.rfind("@")
        if at_pos != -1:
            user_pass_part = url[:at_pos]
            rest = url[at_pos:]
            if "[" in user_pass_part:
                has_bracket_placeholder = True
                cleaned_user_pass = (
                    user_pass_part.replace("[YOUR-PASSWORD]", "YOUR_PASSWORD_PLACEHOLDER")
                    .replace("[", "")
                    .replace("]", "")
                )
                cleaned_url = cleaned_user_pass + rest

    parsed = urllib.parse.urlparse(cleaned_url)
    qs = urllib.parse.parse_qs(parsed.query)

    hostname = parsed.hostname or "localhost"
    is_supabase = "supabase.co" in hostname or "supabase.com" in hostname

    username = urllib.parse.unquote(parsed.username) if parsed.username else None
    password = urllib.parse.unquote(parsed.password) if parsed.password else None

    # Supabase direct connection (db.<ref>.supabase.co) is IPv6-only.
    import re

    m = re.match(r"^db\.([a-z0-9]+)\.supabase\.co$", hostname, re.IGNORECASE)
    if m:
        is_supabase = True

    if has_bracket_placeholder and password == "YOUR_PASSWORD_PLACEHOLDER":
        password = "[YOUR-PASSWORD]"

    dbname = parsed.path.lstrip("/") or "postgres"

    port = parsed.port
    if port is None:
        port = 5432

    if is_supabase:
        sslmode = qs.get("sslmode", ["require"])[0]
    else:
        sslmode = qs.get("sslmode", [os.getenv("POSTGRES_SSLMODE", "disable")])[0]

    return {
        "host": hostname,
        "hostaddr": None,
        "port": port,
        "dbname": dbname,
        "user": username or ("postgres" if is_supabase else "grid_admin"),
        "password": password or "",
        "sslmode": sslmode,
        "is_supabase": is_supabase,
    }


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
    hostaddr: str | None = None

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
        host = self.host
        user = self.user
        hostaddr = self.hostaddr

        if host.startswith("db.") and host.endswith(".supabase.co"):
            project_ref = host.split(".")[1]
            host = os.getenv("SUPABASE_POOLER_HOST") or "aws-0-ap-northeast-2.pooler.supabase.com"
            if "." not in user:
                user = f"{user}.{project_ref}"

        kwargs: dict[str, Any] = {
            "host": host,
            "port": self.port,
            "dbname": self.dbname,
            "user": user,
            "password": self.password,
            "sslmode": self.sslmode,
            "connect_timeout": self.connect_timeout,
            "keepalives": 1,
            "keepalives_idle": 15,
            "keepalives_interval": 5,
            "keepalives_count": 3,
        }
        if hostaddr:
            kwargs["hostaddr"] = hostaddr
        return kwargs

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
            hostaddr=self.hostaddr,
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
            hostaddr=self.hostaddr,
        )

    @classmethod
    def from_url(cls, url: str) -> DatabaseConfig:
        """Create a DatabaseConfig from a connection URL string."""
        params = parse_database_url(url)
        return cls(
            host=params["host"],
            port=params["port"],
            dbname=params["dbname"],
            user=params["user"],
            password=params["password"],
            sslmode=params["sslmode"],
            connect_timeout=int(os.getenv("DB_TIMEOUT_SECONDS", "30")),
            hostaddr=params.get("hostaddr"),
        )

    @classmethod
    def from_env(cls, use_test_db: bool = False) -> DatabaseConfig:
        """Load database configuration from environment variables (and local .env if unset).

        Supports both granular POSTGRES_* parameters and unified DATABASE_URL connection strings
        (e.g., Supabase transaction/session poolers).
        """
        load_dotenv(override=False)

        db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
        if db_url and not use_test_db:
            return cls.from_url(db_url)

        db_key = "POSTGRES_TEST_DB" if use_test_db else "POSTGRES_DB"
        default_db = "sl_grid_warehouse_test" if use_test_db else "sl_grid_warehouse"
        host = os.getenv("POSTGRES_HOST", "localhost")
        is_supabase = "supabase.co" in host or "supabase.com" in host

        port_env = os.getenv("POSTGRES_PORT")
        if is_supabase and (not port_env or port_env == "5433"):
            port = 5432
        else:
            port = int(port_env) if port_env else 5432

        return cls(
            host=host,
            port=port,
            dbname=os.getenv(db_key, "postgres" if is_supabase else default_db),
            user=os.getenv("POSTGRES_USER", "postgres" if is_supabase else "grid_admin"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            sslmode="require" if is_supabase else os.getenv("POSTGRES_SSLMODE", "disable"),
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
