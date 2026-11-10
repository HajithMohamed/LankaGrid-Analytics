"""
PostgreSQL 18 connection management using psycopg v3.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import psycopg

from src.common.config import DatabaseConfig

REQUIRED_WAREHOUSE_SCHEMAS: tuple[str, ...] = (
    "raw",
    "staging",
    "ref",
    "dw",
    "mart",
    "audit",
    "etl",
)


@dataclass(frozen=True)
class PreflightCheckResult:
    """Result of a read-only database preflight health and readiness check."""

    ok: bool
    database_name: str = ""
    current_user: str = ""
    ssl_in_use: bool = False
    schemas_present: tuple[str, ...] = field(default_factory=tuple)
    missing_schemas: tuple[str, ...] = field(default_factory=tuple)
    migrations_count: int = 0
    latest_migration: str | None = None
    has_required_privileges: bool = False
    errors: tuple[str, ...] = field(default_factory=tuple)

    def summary(self) -> str:
        """Return a safe, credential-free summary string."""
        if self.ok:
            return (
                f"Preflight OK: db={self.database_name}, user={self.current_user}, "
                f"ssl={self.ssl_in_use}, schemas={len(self.schemas_present)}/7, "
                f"migrations={self.migrations_count} (latest={self.latest_migration})"
            )
        return f"Preflight FAILED: {'; '.join(self.errors)}"


@contextmanager
def get_connection(
    config: DatabaseConfig | None = None,
    autocommit: bool = False,
) -> Iterator[psycopg.Connection[Any]]:
    """
    Open a managed PostgreSQL connection standardized to Asia/Colombo (+05:30) session timezone.
    Closes cleanly upon context exit.
    """
    resolved = config or DatabaseConfig.from_env()
    conn = psycopg.connect(**resolved.to_conn_kwargs(), autocommit=autocommit)
    try:
        with conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'Asia/Colombo';")
        if not autocommit:
            conn.commit()
        yield conn
    finally:
        conn.close()


def test_connection(config: DatabaseConfig | None = None) -> tuple[bool, str | None]:
    """
    Verify connectivity to PostgreSQL and return (is_connected, error_message).
    """
    resolved = config or DatabaseConfig.from_env()
    try:
        with psycopg.connect(**resolved.to_conn_kwargs()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True, None
    except psycopg.Error as exc:
        return False, str(exc)
    except OSError as exc:
        return False, str(exc)


def verify_warehouse_preflight(
    config: DatabaseConfig | None = None,
    require_write_privileges: bool = True,
    require_remote: bool = False,
) -> PreflightCheckResult:
    """Execute a read-only database health and readiness check before starting ETL.

    Verifies:
    1. Production URL / remote host constraint (when require_remote=True).
    2. Database connectivity and target database identity.
    3. Active SSL/TLS encryption when sslmode requires TLS.
    4. Presence of all 7 required warehouse schemas (raw, staging, ref, dw, mart, audit, etl).
    5. Presence of applied schema migrations in public.schema_migrations.
    6. Required schema and table privileges for the connected role.
    """
    errors: list[str] = []
    try:
        resolved = config or DatabaseConfig.from_env(
            role="etl" if require_write_privileges else "analyst",
            require_remote_url=require_remote,
        )
        if require_remote:
            resolved.validate_for_production()
    except ValueError as exc:
        return PreflightCheckResult(ok=False, errors=(str(exc),))

    try:
        with psycopg.connect(**resolved.to_conn_kwargs(), autocommit=True) as conn:
            with conn.cursor() as cur:
                # 1. Basic identity & SSL check (read-only)
                cur.execute(
                    """
                    SELECT
                        current_database(),
                        current_user,
                        COALESCE(
                            (SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()),
                            FALSE
                        ) AS ssl_active
                    """
                )
                row = cur.fetchone()
                db_name = str(row[0]) if row else ""
                db_user = str(row[1]) if row else ""
                ssl_active = bool(row[2]) if row else False

                if resolved.sslmode in {"require", "verify-ca", "verify-full"} and not ssl_active:
                    errors.append(
                        f"SSL/TLS was required (sslmode={resolved.sslmode!r}) "
                        "but pg_stat_ssl reports ssl=false."
                    )

                # 2. Verify required schemas exist
                cur.execute(
                    """
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name = ANY(%s)
                    ORDER BY schema_name
                    """,
                    (list(REQUIRED_WAREHOUSE_SCHEMAS),),
                )
                present_schemas = tuple(str(r[0]) for r in cur.fetchall())
                missing_schemas = tuple(
                    s for s in REQUIRED_WAREHOUSE_SCHEMAS if s not in present_schemas
                )
                if missing_schemas:
                    errors.append(
                        f"Target database {db_name!r} is missing required warehouse schemas: "
                        f"{', '.join(missing_schemas)}."
                    )

                # 3. Verify migration history exists
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = 'schema_migrations'
                    )
                    """
                )
                has_migrations_table_row = cur.fetchone()
                has_migrations_table = (
                    bool(has_migrations_table_row[0]) if has_migrations_table_row else False
                )
                migrations_count = 0
                latest_migration: str | None = None
                if not has_migrations_table:
                    errors.append(
                        "Migration tracking table 'public.schema_migrations' does not exist."
                    )
                else:
                    cur.execute(
                        """
                        SELECT COUNT(*), MAX(version)
                        FROM public.schema_migrations
                        """
                    )
                    mig_row = cur.fetchone()
                    migrations_count = int(mig_row[0]) if mig_row and mig_row[0] else 0
                    latest_migration = str(mig_row[1]) if mig_row and mig_row[1] else None
                    if migrations_count == 0:
                        errors.append(
                            "Table 'public.schema_migrations' contains 0 applied migrations."
                        )

                # 4. Verify privileges
                has_privs = True
                if not missing_schemas:
                    if require_write_privileges:
                        cur.execute(
                            """
                            SELECT
                                has_schema_privilege(current_user, 'raw', 'USAGE')
                                AND has_schema_privilege(current_user, 'dw', 'USAGE')
                                AND has_schema_privilege(current_user, 'mart', 'USAGE')
                                AND has_schema_privilege(current_user, 'audit', 'USAGE')
                                AND has_table_privilege(current_user, 'raw.source_document', 'INSERT, SELECT, UPDATE')
                                AND has_table_privilege(current_user, 'dw.fact_weather_daily', 'INSERT, SELECT, UPDATE')
                                AND has_table_privilege(current_user, 'audit.etl_run', 'INSERT, SELECT, UPDATE')
                            """
                        )
                    else:
                        cur.execute(
                            """
                            SELECT
                                has_schema_privilege(current_user, 'dw', 'USAGE')
                                AND has_schema_privilege(current_user, 'mart', 'USAGE')
                                AND has_table_privilege(current_user, 'dw.fact_weather_daily', 'SELECT')
                            """
                        )
                    priv_row = cur.fetchone()
                    has_privs = bool(priv_row[0]) if priv_row else False
                    if not has_privs:
                        mode_label = "ETL write" if require_write_privileges else "read-only"
                        errors.append(
                            f"Database user {db_user!r} lacks required {mode_label} privileges "
                            "on warehouse schemas/tables."
                        )

                return PreflightCheckResult(
                    ok=len(errors) == 0,
                    database_name=db_name,
                    current_user=db_user,
                    ssl_in_use=ssl_active,
                    schemas_present=present_schemas,
                    missing_schemas=missing_schemas,
                    migrations_count=migrations_count,
                    latest_migration=latest_migration,
                    has_required_privileges=has_privs,
                    errors=tuple(errors),
                )
    except (psycopg.Error, OSError) as exc:
        # Sanitize any accidental password appearance in low-level error strings
        err_msg = str(exc)
        if resolved.password and resolved.password in err_msg:
            err_msg = err_msg.replace(resolved.password, "******")
        return PreflightCheckResult(
            ok=False,
            errors=(
                f"Database connection failed to {resolved.host}:{resolved.port}/{resolved.dbname} "
                f"(user={resolved.user}): {err_msg}",
            ),
        )


# Prevent pytest from collecting the imported helper function as a test case
test_connection.__test__ = False  # type: ignore[attr-defined]
