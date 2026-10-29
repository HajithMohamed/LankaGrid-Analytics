"""
Wait until PostgreSQL accepts connections before proceeding with container or CI commands.
"""
from __future__ import annotations

import sys
import time

from src.common.config import DatabaseConfig
from src.common.db import test_connection


def wait_for_database(max_attempts: int = 30, delay_seconds: float = 1.0) -> bool:
    """Poll PostgreSQL until ready or max_attempts is exhausted."""
    config = DatabaseConfig.from_env()
    for attempt in range(1, max_attempts + 1):
        ok, err = test_connection(config)
        if ok:
            print(f"PostgreSQL ready on {config.host}:{config.port}/{config.dbname} (attempt {attempt}).")
            return True
        print(f"Waiting for PostgreSQL ({attempt}/{max_attempts}): {err}")
        time.sleep(delay_seconds)
    return False


if __name__ == "__main__":
    sys.exit(0 if wait_for_database() else 1)
