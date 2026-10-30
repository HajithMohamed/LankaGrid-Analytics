"""
PostgreSQL 18 connection management using psycopg v3.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg

from src.common.config import DatabaseConfig


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


# Prevent pytest from collecting the imported helper function as a test case
test_connection.__test__ = False  # type: ignore[attr-defined]
