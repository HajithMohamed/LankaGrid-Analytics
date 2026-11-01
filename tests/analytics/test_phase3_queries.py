"""
Tests for Phase 3 Business Analytical Queries (Q01-Q24).
Verifies that all 24 SQL queries execute cleanly and return valid schema columns.
"""

from __future__ import annotations

from pathlib import Path
from typing import LiteralString, cast

import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection

QUERY_FILES = [
    ("Q01", "database/queries/phase3/member_01_generation/Q01.sql", 5),
    ("Q02", "database/queries/phase3/member_01_generation/Q02.sql", 8),
    ("Q03", "database/queries/phase3/member_01_generation/Q03.sql", 10),
    ("Q04", "database/queries/phase3/member_01_generation/Q04.sql", 10),
    ("Q05", "database/queries/phase3/member_02_dispatch/Q05.sql", 10),
    ("Q06", "database/queries/phase3/member_02_dispatch/Q06.sql", 11),
    ("Q07", "database/queries/phase3/member_02_dispatch/Q07.sql", 11),
    ("Q08", "database/queries/phase3/member_02_dispatch/Q08.sql", 7),
    ("Q09", "database/queries/phase3/member_03_sales/Q09.sql", 8),
    ("Q10", "database/queries/phase3/member_03_sales/Q10.sql", 12),
    ("Q11", "database/queries/phase3/member_03_sales/Q11.sql", 8),
    ("Q12", "database/queries/phase3/member_03_sales/Q12.sql", 8),
    ("Q13", "database/queries/phase3/member_04_weather/Q13.sql", 9),
    ("Q14", "database/queries/phase3/member_04_weather/Q14.sql", 11),
    ("Q15", "database/queries/phase3/member_04_weather/Q15.sql", 9),
    ("Q16", "database/queries/phase3/member_04_weather/Q16.sql", 10),
    ("Q17", "database/queries/phase3/member_05_plant_operations/Q17.sql", 10),
    ("Q18", "database/queries/phase3/member_05_plant_operations/Q18.sql", 10),
    ("Q19", "database/queries/phase3/member_05_plant_operations/Q19.sql", 8),
    ("Q20", "database/queries/phase3/member_05_plant_operations/Q20.sql", 9),
    ("Q21", "database/queries/phase3/member_06_grid_efficiency/Q21.sql", 5),
    ("Q22", "database/queries/phase3/member_06_grid_efficiency/Q22.sql", 7),
    ("Q23", "database/queries/phase3/member_06_grid_efficiency/Q23.sql", 8),
    ("Q24", "database/queries/phase3/member_06_grid_efficiency/Q24.sql", 12),
]


@pytest.mark.integration
@pytest.mark.parametrize("query_id,file_path,expected_min_cols", QUERY_FILES)
def test_phase3_query_execution_and_schema(
    populated_analytics_db: DatabaseConfig,
    query_id: str,
    file_path: str,
    expected_min_cols: int,
) -> None:
    """Verify that each analytical query parses, executes, and returns expected projection columns."""
    sql_path = Path(file_path)
    assert sql_path.exists(), f"Query file not found: {file_path}"

    sql_text = cast(LiteralString, sql_path.read_text(encoding="utf-8"))
    assert len(sql_text.strip()) > 50, f"Query file is empty or trivial: {file_path}"

    with get_connection(populated_analytics_db) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text)
            assert cur.description is not None, f"Query {query_id} returned no cursor description"
            col_names = [desc[0] for desc in cur.description]
            assert len(col_names) >= expected_min_cols, (
                f"Query {query_id} returned {len(col_names)} columns; expected at least {expected_min_cols}"
            )
            # Fetch at least one row
            rows = cur.fetchall()
            assert len(rows) > 0, f"Query {query_id} returned 0 rows"
