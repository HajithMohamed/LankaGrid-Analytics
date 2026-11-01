"""
Tests for Phase 3 Historical Trends and Materialized View Reconciliation.
Verifies YoY calculations, CAGR formulas, and materialized view data consistency with underlying facts.
"""

from __future__ import annotations

from pathlib import Path
from typing import LiteralString, cast

import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection


@pytest.mark.integration
def test_five_year_sales_yoy_calculations_q09(populated_analytics_db: DatabaseConfig) -> None:
    """Verify that Q09 YoY changes correctly compute (Sales_t - Sales_t-1) / Sales_t-1 * 100%."""
    sql = cast(
        LiteralString,
        Path("database/queries/phase3/member_03_sales/Q09.sql").read_text(encoding="utf-8"),
    )
    with get_connection(populated_analytics_db) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            assert rows is not None and len(rows) > 0, "Query Q09 must return result rows"
            for r in rows:
                _yr, _sec, current_sales, prior_sales, yoy_diff, yoy_pct = (
                    r[0], r[1], float(r[4]), r[5], r[6], r[7]
                )
                if prior_sales is not None:
                    prior = float(prior_sales)
                    expected_diff = round(current_sales - prior, 2)
                    assert abs(float(yoy_diff) - expected_diff) < 0.05
                    expected_pct = round(100.0 * (current_sales - prior) / prior, 2)
                    assert abs(float(yoy_pct) - expected_pct) < 0.1


@pytest.mark.integration
def test_materialized_views_reconciliation(populated_analytics_db: DatabaseConfig) -> None:
    """Verify that mart.mv_daily_dispatch_by_source reconciles 100% with dw.fact_dispatch_interval."""
    with get_connection(populated_analytics_db, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Refresh materialized view first
            cur.execute("CALL mart.sp_refresh_analytical_marts();")

            # Compare total energy between MV and base fact table
            cur.execute("SELECT ROUND(SUM(daily_generation_mwh), 2) FROM mart.mv_daily_dispatch_by_source;")
            row_mv = cur.fetchone()
            assert row_mv is not None, "Query on mart.mv_daily_dispatch_by_source must return a row"
            mv_total = row_mv[0]

            cur.execute("SELECT ROUND(SUM(derived_energy_mwh), 2) FROM dw.fact_dispatch_interval;")
            row_fact = cur.fetchone()
            assert row_fact is not None, "Query on dw.fact_dispatch_interval must return a row"
            fact_total = row_fact[0]

            assert mv_total == fact_total, (
                f"Materialized view total {mv_total} does not match underlying fact total {fact_total}"
            )
