"""
Sequential PostgreSQL migration runner with SHA-256 immutability verification.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from psycopg import sql

from src.common.config import DatabaseConfig
from src.common.db import get_connection


@dataclass(frozen=True)
class MigrationStatus:
    """Status record for a discovered SQL migration file."""

    version: str
    filename: str
    checksum: str
    is_applied: bool
    applied_at: str | None = None


class MigrationRunner:
    """Discovers, validates, and applies sequential forward SQL migrations."""

    def __init__(self, migrations_dir: Path = Path("database/migrations")) -> None:
        self.migrations_dir = migrations_dir

    def discover_migrations(self) -> list[Path]:
        """Return sorted forward .sql migration files in migrations_dir."""
        if not self.migrations_dir.exists():
            return []
        files = [
            p
            for p in self.migrations_dir.iterdir()
            if p.is_file() and p.suffix.lower() == ".sql" and p.name[0].isdigit()
        ]
        return sorted(files, key=lambda p: p.name)

    @staticmethod
    def compute_normalized_checksum(file_path: Path) -> tuple[str, str]:
        """Read SQL text, normalize CRLF to LF for cross-platform hash stability, and return (sql_text, sha256)."""
        raw_text = file_path.read_text(encoding="utf-8")
        normalized = raw_text.replace("\r\n", "\n")
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return normalized, digest

    @staticmethod
    def _extract_description(version: str, sql_text: str) -> str:
        """Extract human-readable description from SQL header or derive from version."""
        for line in sql_text.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("-- purpose"):
                parts = stripped.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    return parts[1].strip()
        slug = version.split("_", 1)[1] if "_" in version else version
        return slug.replace("_", " ").capitalize()

    @staticmethod
    def _ensure_tracking_table(conn: object) -> None:
        from psycopg import Connection

        assert isinstance(conn, Connection)
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public.schema_migrations (
                        version VARCHAR(255) CONSTRAINT pk_schema_migrations PRIMARY KEY,
                        description TEXT NOT NULL,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        checksum VARCHAR(64) NOT NULL,
                        execution_ms INTEGER
                    );
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE public.schema_migrations
                    ADD COLUMN IF NOT EXISTS execution_ms INTEGER;
                    """
                )

    def get_status(self, config: DatabaseConfig | None = None) -> list[MigrationStatus]:
        """Return applied/pending status of all discovered migrations and verify checksums."""
        resolved = config or DatabaseConfig.from_env()
        files = self.discover_migrations()
        with get_connection(resolved, autocommit=True) as conn:
            self._ensure_tracking_table(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT version, checksum, applied_at::TEXT FROM public.schema_migrations ORDER BY version;"
                )
                applied_map = {row[0]: (row[1], row[2]) for row in cur.fetchall()}

        statuses: list[MigrationStatus] = []
        for file_path in files:
            version = file_path.stem
            _, checksum = self.compute_normalized_checksum(file_path)
            if version in applied_map:
                recorded_checksum, applied_at = applied_map[version]
                if recorded_checksum != checksum:
                    raise RuntimeError(
                        f"Migration checksum mismatch for '{version}': "
                        f"recorded={recorded_checksum}, current={checksum}. "
                        "Applied migrations are immutable."
                    )
                statuses.append(
                    MigrationStatus(
                        version=version,
                        filename=file_path.name,
                        checksum=checksum,
                        is_applied=True,
                        applied_at=applied_at,
                    )
                )
            else:
                statuses.append(
                    MigrationStatus(
                        version=version,
                        filename=file_path.name,
                        checksum=checksum,
                        is_applied=False,
                    )
                )
        return statuses

    def apply_migrations(self, config: DatabaseConfig | None = None) -> int:
        """Apply all pending migrations sequentially inside atomic per-file transactions."""
        resolved = config or DatabaseConfig.from_env()
        files = self.discover_migrations()
        applied_count = 0

        with get_connection(resolved, autocommit=True) as conn:
            self._ensure_tracking_table(conn)
            with conn.cursor() as cur:
                cur.execute("SELECT version, checksum FROM public.schema_migrations;")
                applied_map = {row[0]: row[1] for row in cur.fetchall()}

            for file_path in files:
                version = file_path.stem
                sql_text, checksum = self.compute_normalized_checksum(file_path)

                if version in applied_map:
                    if applied_map[version] != checksum:
                        raise RuntimeError(
                            f"Migration checksum mismatch for '{version}': "
                            f"recorded={applied_map[version]}, current={checksum}. "
                            "Never modify an already applied migration."
                        )
                    continue

                description = self._extract_description(version, sql_text)
                start_ns = time.perf_counter_ns()
                with conn.transaction():
                    with conn.cursor() as cur:
                        # pyrefly: ignore[no-matching-overload]
                        cur.execute(sql_text)
                        elapsed_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)
                        cur.execute(
                            """
                            INSERT INTO public.schema_migrations (version, description, checksum, execution_ms)
                            VALUES (%s, %s, %s, %s);
                            """,
                            (version, description, checksum, elapsed_ms),
                        )
                applied_count += 1

        return applied_count

    @staticmethod
    def configure_role_passwords_from_env(config: DatabaseConfig | None = None) -> list[str]:
        """
        Optionally assign passwords to grid_etl and grid_analyst from environment variables
        without ever storing credentials in SQL migration files.
        """
        resolved = config or DatabaseConfig.from_env()
        role_env_pairs = [
            (os.getenv("POSTGRES_ETL_USER", "grid_etl"), os.getenv("POSTGRES_ETL_PASSWORD")),
            (
                os.getenv("POSTGRES_ANALYST_USER", "grid_analyst"),
                os.getenv("POSTGRES_ANALYST_PASSWORD"),
            ),
        ]
        updated_roles: list[str] = []
        with get_connection(resolved, autocommit=True) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    for role_name, role_password in role_env_pairs:
                        if not role_password:
                            continue
                        cur.execute(
                            "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = %s);",
                            (role_name,),
                        )
                        row = cur.fetchone()
                        if row and row[0]:
                            stmt = sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {};").format(
                                sql.Identifier(role_name),
                                sql.Literal(role_password),
                            )
                            cur.execute(stmt)
                            updated_roles.append(role_name)
        return updated_roles


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for running migrations or checking migration status."""
    parser = argparse.ArgumentParser(description="PostgreSQL Warehouse Migration Runner")
    parser.add_argument(
        "command",
        choices=["up", "status", "configure-roles"],
        help="Migration action to perform",
    )
    parser.add_argument(
        "--test-db",
        action="store_true",
        help="Target POSTGRES_TEST_DB instead of primary POSTGRES_DB",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=Path("database/migrations"),
        help="Directory containing sequential .sql migration files",
    )
    args = parser.parse_args(argv)

    config = DatabaseConfig.from_env(use_test_db=args.test_db)
    runner = MigrationRunner(migrations_dir=args.migrations_dir)

    if args.command == "up":
        count = runner.apply_migrations(config)
        print(f"Applied {count} migration(s) to database '{config.dbname}'.")
        return 0

    if args.command == "configure-roles":
        updated = runner.configure_role_passwords_from_env(config)
        print(f"Configured login credentials from environment for roles: {updated}")
        return 0

    statuses = runner.get_status(config)
    for st in statuses:
        marker = "APPLIED" if st.is_applied else "PENDING"
        ts = f" ({st.applied_at})" if st.applied_at else ""
        print(f"[{marker}] {st.version}  sha256={st.checksum[:12]}...{ts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
