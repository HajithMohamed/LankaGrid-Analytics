"""
Tests for Phase 3 OLAP Multidimensional Aggregations (ROLLUP, CUBE, GROUPING SETS).
Verifies that multidimensional cubes calculate mathematically consistent subtotals and grand totals.
"""

from __future__ import annotations

from pathlib import Path
from typing import LiteralString, cast

import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection


@pytest.mark.integration
def test_olap_rollup_consistency_q01(populated_analytics_db: DatabaseConfig) -> None:
    """Verify that Q01 ROLLUP subtotals equal sum of individual technology entries and grand total matches."""
    sql = cast(
        LiteralString,
        Path("database/queries/phase3/member_01_generation/Q01.sql").read_text(encoding="utf-8"),
    )
    with get_connection(populated_analytics_db) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            assert len(rows) > 0

            # Find Grand Total (grp_cat = 1, grp_src = 1)
            grand_total_row = [r for r in rows if r[5] == 1 and r[6] == 1]
            assert len(grand_total_row) == 1, "Expected exactly one Grand Total row in ROLLUP"
            grand_total_mwh = float(grand_total_row[0][2])
            grand_total_share = float(grand_total_row[0][3])
            assert grand_total_share == 100.0, "Grand total share must equal 100.0%"

            # Verify that sum of detailed entries (grp_cat = 0, grp_src = 0) equals Grand Total
            detailed_sum = sum(float(r[2]) for r in rows if r[5] == 0 and r[6] == 0)
            assert abs(detailed_sum - grand_total_mwh) < 1.0, (
                f"Detailed sum {detailed_sum} does not match Grand Total {grand_total_mwh}"
            )


@pytest.mark.integration
def test_olap_cube_consistency_q15(populated_analytics_db: DatabaseConfig) -> None:
    """Verify that Q15 CUBE computes consistent 2D cube cells for locations and monsoon seasons."""
    sql = cast(
        LiteralString,
        Path("database/queries/phase3/member_04_weather/Q15.sql").read_text(encoding="utf-8"),
    )
    with get_connection(populated_analytics_db) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            assert len(rows) == 15, "Expected 15 cube cells (2 locations + 1) * (4 seasons + 1)"

            # Grand Total Cell: grp_loc = 1, grp_season = 1
            grand_total_cell = [r for r in rows if r[8] == 1 and r[9] == 1]
            assert len(grand_total_cell) == 1
            total_rainfall = float(grand_total_cell[0][3])
            assert total_rainfall > 10000.0, "5-year national rainfall total must exceed 10,000 mm"

            # Check that sum of individual locations' annual rain equals grand total rain
            loc_totals = sum(float(r[3]) for r in rows if r[8] == 0 and r[9] == 1)
            assert abs(loc_totals - total_rainfall) < 1.0


@pytest.mark.integration
def test_olap_grouping_sets_q21(populated_analytics_db: DatabaseConfig) -> None:
    """Verify that Q21 GROUPING SETS computes exact annual subtotals and 5-year grand total."""
    sql = cast(
        LiteralString,
        Path("database/queries/phase3/member_06_grid_efficiency/Q21.sql").read_text(
            encoding="utf-8"
        ),
    )
    with get_connection(populated_analytics_db) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

            # Find 5-year grand total (grp_year = 1, grp_class = 1)
            grand_total_rows = [r for r in rows if r[4] == 1 and r[5] == 1]
            assert len(grand_total_rows) == 1
            grand_total_gwh = float(grand_total_rows[0][2])
            grand_total_share = float(grand_total_rows[0][3])
            assert grand_total_share == 100.0, (
                f"Grand total share must be 100.0%, got {grand_total_share}%"
            )
            assert 70000.0 <= grand_total_gwh <= 75000.0, (
                f"Expected 5-year sales around 73,365 GWh, got {grand_total_gwh}"
            )

            # Sum of annual subtotals (grp_year = 0, grp_class = 1)
            annual_subtotal_rows = [r for r in rows if r[4] == 0 and r[5] == 1]
            assert len(annual_subtotal_rows) == 5, (
                f"Expected 5 annual subtotals, got {len(annual_subtotal_rows)}"
            )
            for sub in annual_subtotal_rows:
                yr, _sub_gwh, sub_pct = sub[0], float(sub[2]), float(sub[3])
                assert sub_pct == 100.0, f"Year {yr} subtotal pct must be 100.0%, got {sub_pct}%"

            annual_subtotals = sum(float(r[2]) for r in annual_subtotal_rows)
            assert abs(annual_subtotals - grand_total_gwh) < 0.1

            # Verify that detailed sector shares for each year sum to 100.0% (verifying no 50% denominator bug)
            for yr_str in ("2020", "2021", "2022", "2023", "2024"):
                yr_details = [r for r in rows if r[0] == yr_str and r[4] == 0 and r[5] == 0]
                assert len(yr_details) == 4, f"Year {yr_str} must have 4 economic classes"
                pct_sum = sum(float(r[3]) for r in yr_details)
                assert abs(pct_sum - 100.0) < 0.05, (
                    f"Year {yr_str} detail shares sum to {pct_sum}%, expected 100%"
                )
