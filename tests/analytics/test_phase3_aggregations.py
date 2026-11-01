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


@pytest.mark.integration
def test_telemetry_reconciliation_q08(populated_analytics_db: DatabaseConfig) -> None:
    """Verify Q08 telemetry integration joins directly to warehouse facts and computes authentic 3.97% variance."""
    sql = cast(
        LiteralString,
        Path("database/queries/phase3/member_02_dispatch/Q08.sql").read_text(encoding="utf-8"),
    )
    with get_connection(populated_analytics_db) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            assert len(rows) == 8, f"Expected 8 reconciliation rows in Q08, got {len(rows)}"

            # Find total system row
            total_rows = [r for r in rows if "TOTAL SYSTEM GENERATION" in r[0]]
            assert len(total_rows) == 1, "Expected exactly one total row in Q08"
            total = total_rows[0]
            pub_mwh, tele_mwh, var_mwh, var_pct = (
                float(total[1]),
                float(total[2]),
                float(total[3]),
                float(total[4]),
            )
            assert pub_mwh == 48223.00, (
                f"Published benchmark total must be 48,223.00 MWh, got {pub_mwh}"
            )
            assert tele_mwh == 46308.00, f"Telemetered sum must be 46,308.00 MWh, got {tele_mwh}"
            assert abs(var_mwh - 1915.00) < 0.1, f"Variance must be 1,915.00 MWh, got {var_mwh}"
            assert abs(var_pct - 3.97) < 0.05, f"Variance pct must be 3.97%, got {var_pct}"

            # Verify that sum of non-total telemetered values equals 46,308.00 MWh
            cat_rows = [r for r in rows if "TOTAL SYSTEM GENERATION" not in r[0]]
            sum_tele = sum(float(r[2]) for r in cat_rows)
            assert abs(sum_tele - tele_mwh) < 0.1, (
                f"Detailed telemetered sums {sum_tele} != total {tele_mwh}"
            )


@pytest.mark.integration
def test_data_quality_quarantine_rates_q23(populated_analytics_db: DatabaseConfig) -> None:
    """Verify Q23 data quality percentages calculate exact 100.00% totals and correct subtotal fractions."""
    sql = cast(
        LiteralString,
        Path("database/queries/phase3/member_06_grid_efficiency/Q23.sql").read_text(
            encoding="utf-8"
        ),
    )
    with get_connection(populated_analytics_db) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            assert len(rows) == 5, f"Expected 5 rows in Q23, got {len(rows)}"

            # Total warehouse issues row (grp_rule = 1, grp_class = 1)
            total_row = [r for r in rows if r[7] == 1 and r[8] == 1]
            assert len(total_row) == 1
            tot_count = int(total_row[0][3])
            tot_pct = float(total_row[0][4])
            assert tot_count > 0, "Expected at least one logged data quality issue"
            assert tot_pct == 100.0, f"Grand total percentage must equal 100.0%, got {tot_pct}"

            # Verify rule subtotals (grp_rule = 0, grp_class = 1)
            subtotal_rows = [r for r in rows if r[7] == 0 and r[8] == 1]
            assert len(subtotal_rows) == 2, f"Expected 2 rule subtotals, got {len(subtotal_rows)}"
            sub_pct_sum = sum(float(r[4]) for r in subtotal_rows)
            assert abs(sub_pct_sum - 100.0) < 0.05, (
                f"Rule subtotal percentages sum to {sub_pct_sum}%, expected 100%"
            )
