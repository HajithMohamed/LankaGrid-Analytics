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

    sslrootcert = qs.get("sslrootcert", [os.getenv("PGSSLROOTCERT", "")])[0] or None

    return {
        "host": hostname,
        "hostaddr": None,
        "port": port,
        "dbname": dbname,
        "user": username or ("postgres" if is_supabase else "grid_admin"),
        "password": password or "",
        "sslmode": sslmode,
        "sslrootcert": sslrootcert,
        "is_supabase": is_supabase,
    }


def validate_production_database_url(url: str | None) -> str:
    """Validate that a production/scheduled DATABASE_URL secret is present and safe.

    Raises ValueError with an actionable, credential-safe error message when
    the secret is missing, empty, uses placeholder values, or targets localhost.
    """
    if not url or not url.strip():
        raise ValueError(
            "DATABASE_URL is missing or empty. Configure the protected GitHub Actions "
            "secret 'DATABASE_URL' (or environment variable) with a valid Supabase "
            "PostgreSQL connection string before running scheduled ingestion."
        )

    cleaned = url.strip()
    if (
        "[YOUR-PASSWORD]" in cleaned
        or "<project-ref>" in cleaned
        or "<region>" in cleaned
        or "change_me" in cleaned.lower()
    ):
        raise ValueError(
            "DATABASE_URL contains an unreplaced placeholder ([YOUR-PASSWORD], <project-ref>, "
            "<region>, or change_me). Provide the actual authorized Supabase connection string."
        )

    params = parse_database_url(cleaned)
    host = str(params["host"]).lower()
    if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
        raise ValueError(
            f"Scheduled production runs cannot target local host '{host}'. "
            "Configure DATABASE_URL to point to the authorized remote Supabase PostgreSQL endpoint."
        )

    if not params["password"]:
        raise ValueError(
            "DATABASE_URL does not include a database password. "
            "Verify the connection string format: postgresql://<user>:<password>@<host>:<port>/<db>"
        )

    return cleaned


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
    sslrootcert: str | None = None

    def __repr__(self) -> str:
        return (
            f"DatabaseConfig(host={self.host!r}, port={self.port!r}, "
            f"dbname={self.dbname!r}, user={self.user!r}, "
            f"password='******', sslmode={self.sslmode!r}, "
            f"connect_timeout={self.connect_timeout!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def is_supabase(self) -> bool:
        """Return True if the host belongs to Supabase managed PostgreSQL."""
        host_lower = self.host.lower()
        return "supabase.co" in host_lower or "supabase.com" in host_lower

    @property
    def connection_mode(self) -> str:
        """Classify the connection mode (direct, session_pooler, transaction_pooler, local)."""
        host_lower = self.host.lower()
        if host_lower in {"localhost", "127.0.0.1", "::1"}:
            return "local"
        if "pooler.supabase.com" in host_lower:
            return "transaction_pooler" if self.port == 6543 else "session_pooler"
        if host_lower.startswith("db.") and host_lower.endswith(".supabase.co"):
            return "direct"
        return "standard"

    def validate_for_production(self) -> None:
        """Ensure this configuration is valid for remote production/scheduled execution."""
        host_lower = self.host.lower()
        if host_lower in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
            raise ValueError(
                f"Production database configuration cannot use local host {self.host!r}. "
                "Set DATABASE_URL to a remote Supabase PostgreSQL connection string."
            )
        if "<project-ref>" in host_lower or "<region>" in host_lower:
            raise ValueError(
                f"Database host {self.host!r} contains a template placeholder. "
                "Configure the actual Supabase endpoint."
            )
        if not self.password or self.password == "[YOUR-PASSWORD]":
            raise ValueError("Database password is missing or uses placeholder '[YOUR-PASSWORD]'.")
        if self.sslmode in {"disable", "allow"}:
            raise ValueError(
                f"Production database connection requires TLS (sslmode='require', 'verify-ca', "
                f"or 'verify-full'), got sslmode={self.sslmode!r}."
            )

    def to_conn_kwargs(self) -> dict[str, Any]:
        """Return keyword arguments suitable for psycopg.connect().

        Does not rewrite direct endpoints into guessed regional poolers unless an explicit
        SUPABASE_POOLER_HOST override is provided in the environment.
        """
        host = self.host
        user = self.user
        hostaddr = self.hostaddr

        explicit_pooler_host = os.getenv("SUPABASE_POOLER_HOST", "").strip()
        if explicit_pooler_host and host.startswith("db.") and host.endswith(".supabase.co"):
            project_ref = host.split(".")[1]
            host = explicit_pooler_host
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
        if self.sslrootcert:
            kwargs["sslrootcert"] = self.sslrootcert
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
            sslrootcert=self.sslrootcert,
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
            sslrootcert=self.sslrootcert,
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
            sslrootcert=params.get("sslrootcert"),
        )

    @classmethod
    def from_env(
        cls,
        use_test_db: bool = False,
        role: str = "default",
        require_remote_url: bool = False,
    ) -> DatabaseConfig:
        """Load database configuration from environment variables (and local .env if unset).

        Supports separated credentials by role:
        - role='admin': checks MIGRATION_DATABASE_URL, ADMIN_DATABASE_URL, then DATABASE_URL
        - role='etl': checks ETL_DATABASE_URL, then DATABASE_URL
        - role='analyst': checks ANALYST_DATABASE_URL, READONLY_DATABASE_URL, then DATABASE_URL
        - role='default': checks DATABASE_URL, then SUPABASE_DB_URL

        When require_remote_url=True (used by scheduled production ingestion), fails
        immediately if no valid remote connection URL is configured rather than falling
        back to localhost:5432.
        """
        load_dotenv(override=False)

        role_env_keys: dict[str, tuple[str, ...]] = {
            "admin": (
                "MIGRATION_DATABASE_URL",
                "ADMIN_DATABASE_URL",
                "DATABASE_URL",
                "SUPABASE_DB_URL",
            ),
            "etl": ("ETL_DATABASE_URL", "DATABASE_URL", "SUPABASE_DB_URL"),
            "analyst": (
                "ANALYST_DATABASE_URL",
                "READONLY_DATABASE_URL",
                "DATABASE_URL",
                "SUPABASE_DB_URL",
            ),
            "default": ("DATABASE_URL", "SUPABASE_DB_URL"),
        }
        candidate_keys = role_env_keys.get(role, role_env_keys["default"])

        db_url: str | None = None
        for key in candidate_keys:
            val = os.getenv(key)
            if val and val.strip():
                db_url = val.strip()
                break

        if require_remote_url and not use_test_db:
            validated_url = validate_production_database_url(db_url)
            cfg = cls.from_url(validated_url)
            cfg.validate_for_production()
            return cfg

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

        role_user_env = {
            "admin": "POSTGRES_ADMIN_USER",
            "etl": "POSTGRES_ETL_USER",
            "analyst": "POSTGRES_ANALYST_USER",
        }.get(role)
        role_pass_env = {
            "admin": "POSTGRES_ADMIN_PASSWORD",
            "etl": "POSTGRES_ETL_PASSWORD",
            "analyst": "POSTGRES_ANALYST_PASSWORD",
        }.get(role)

        user = (
            (os.getenv(role_user_env) if role_user_env else None)
            or os.getenv("POSTGRES_USER")
            or ("postgres" if is_supabase else "grid_admin")
        )
        password = (
            (os.getenv(role_pass_env) if role_pass_env else None)
            or os.getenv("POSTGRES_PASSWORD")
            or ""
        )

        return cls(
            host=host,
            port=port,
            dbname=os.getenv(db_key) or ("postgres" if is_supabase else default_db),
            user=user,
            password=password,
            sslmode="require" if is_supabase else (os.getenv("POSTGRES_SSLMODE") or "disable"),
            connect_timeout=int(os.getenv("DB_TIMEOUT_SECONDS", "30")),
            sslrootcert=os.getenv("PGSSLROOTCERT") or None,
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
