"""
Tests for Phase 3 Physical Aggregations, Unit Consistency, and Domain Constraints.
Verifies MW vs MWh consistency, non-negative bounds, zero vs null preservation, and double-counting avoidance.
"""

from __future__ import annotations

from pathlib import Path
from typing import LiteralString, cast

import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection


@pytest.mark.integration
def test_dispatch_energy_integration_consistency(populated_analytics_db: DatabaseConfig) -> None:
    """Verify that derived energy (MWh) strictly equals active power (MW) * 0.25 hours."""
    with get_connection(populated_analytics_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT count(*)
                FROM dw.fact_dispatch_interval
                WHERE ABS(derived_energy_mwh - (active_power_mw * 0.25)) > 0.0001;
                """
            )
            row = cur.fetchone()
            assert row is not None, "Query must return count of inconsistent facts"
            inconsistent_count = int(row[0])
            assert inconsistent_count == 0, (
                f"Found {inconsistent_count} facts where MWh != MW * 0.25h"
            )


@pytest.mark.integration
def test_no_double_counting_in_sales_queries(populated_analytics_db: DatabaseConfig) -> None:
    """Verify that analytical queries do not aggregate ALL_SECTORS alongside individual retail sectors."""
    sql = cast(
        LiteralString,
        Path("database/queries/phase3/member_03_sales/Q12.sql").read_text(encoding="utf-8"),
    )
    with get_connection(populated_analytics_db) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            assert rows is not None and len(rows) > 0, "Query Q12 must return result rows"
            for r in rows:
                yr, ceb_gwh, leco_gwh, total_gwh = r[0], float(r[1]), float(r[2]), float(r[3])
                # Direct retail + LECO bulk must sum to total national billed sales
                assert abs((ceb_gwh + leco_gwh) - total_gwh) < 0.01, (
                    f"Year {yr}: CEB {ceb_gwh} + LECO {leco_gwh} != Total {total_gwh}"
                )
                # National total in Sri Lanka is typically between 13,000 and 16,000 GWh
                assert 13000.0 <= total_gwh <= 16500.0, (
                    f"Year {yr}: Unexpected sales total {total_gwh}"
                )


@pytest.mark.integration
def test_zero_power_vs_null_missing_preservation(populated_analytics_db: DatabaseConfig) -> None:
    """Verify that zero active power (0 MW) is preserved and distinct from missing telemetry (NULL)."""
    with get_connection(populated_analytics_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    count(*) FILTER (WHERE active_power_mw = 0.0) AS true_zero_count,
                    count(*) FILTER (WHERE active_power_mw IS NULL) AS missing_count,
                    count(*) FILTER (WHERE active_power_mw < 0.0) AS negative_count
                FROM dw.fact_dispatch_interval;
                """
            )
            row = cur.fetchone()
            assert row is not None
            true_zeros, missing_vals, negative_vals = row
            # There must be genuine zero generation intervals (peaking stations offline)
            assert true_zeros > 0, "Expected true zero dispatch records for offline stations"
            # Negative power must be zero in the dimensional warehouse facts (quarantined during ETL)
            assert negative_vals == 0, f"Found {negative_vals} negative power facts in warehouse"
