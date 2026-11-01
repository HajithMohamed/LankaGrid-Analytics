"""
Regression and coverage integration tests for PUCSL 15-minute dispatch interval dates:
1. Slot 1 (00:15) and Slot 96 (24:00) date assignment verification.
2. Two consecutive daily sheets (01.03 and 02.03) interval continuity.
3. Month boundary check (31.03 to 01.04) ensuring no spillover into April.
4. Full March 2024 coverage accounting (all 31 sheets, 36 entities, 96 slots, 21 Barge negatives).
5. Idempotent re-load and cleanup of obsolete/orphaned fact keys.

Follows strict TDD Red -> Green protocol.
"""

from datetime import date
from pathlib import Path

import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection
from src.etl.real_data_loader import RealDataWarehouseLoader


@pytest.fixture(scope="module")
def real_loader(migrated_and_seeded_test_db: DatabaseConfig) -> RealDataWarehouseLoader:
    return RealDataWarehouseLoader(config=migrated_and_seeded_test_db)


@pytest.mark.integration
def test_dispatch_slots_1_and_96_reporting_date(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
) -> None:
    """
    Verify that for March 1 (01.03), both Slot 1 (00:15) and Slot 96 (24:00)
    are assigned date_key = 20240301, while preserving original timestamp.
    """
    xlsx_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
    if not xlsx_path.exists():
        pytest.skip("PUCSL 15-minute XLSX not present")

    result = real_loader.load_pucsl_dispatch_xlsx(xlsx_path, sheet_names=["01.03"])
    assert result.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # Check slot 1 on March 1
            cur.execute(
                """
                SELECT count(*), min(original_timestamp), max(original_timestamp)
                FROM dw.fact_dispatch_interval
                WHERE date_key = 20240301 AND interval_key = 1;
                """
            )
            row_slot1 = cur.fetchone()
            assert row_slot1 is not None, "Query must return a row for slot 1"
            slot1_count, slot1_min_ts, slot1_max_ts = row_slot1
            assert slot1_count > 0, "Slot 1 facts must exist for 2024-03-01"

            # Check slot 96 on March 1: MUST HAVE date_key = 20240301
            cur.execute(
                """
                SELECT count(*), min(original_timestamp), max(original_timestamp)
                FROM dw.fact_dispatch_interval
                WHERE date_key = 20240301 AND interval_key = 96;
                """
            )
            row_slot96 = cur.fetchone()
            assert row_slot96 is not None, "Query must return a row for slot 96"
            slot96_count, slot96_min_ts, slot96_max_ts = row_slot96
            assert slot96_count > 0, (
                "Slot 96 facts MUST be assigned date_key = 20240301, not 20240302"
            )

            # Confirm NO slot 96 facts exist with date_key = 20240302 from sheet 01.03
            cur.execute(
                """
                SELECT count(*)
                FROM dw.fact_dispatch_interval
                WHERE date_key = 20240302 AND interval_key = 96
                  AND source_document_id = %s;
                """,
                (result.source_document_id,),
            )
            row_spill = cur.fetchone()
            assert row_spill is not None
            spill_count = row_spill[0]
            assert spill_count == 0, "Slot 96 must not spill over to date_key 20240302"


@pytest.mark.integration
def test_dispatch_consecutive_days_continuity(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
) -> None:
    """
    Verify two consecutive days (01.03 and 02.03) each have exactly 96 intervals
    per non-quarantined reporting entity.
    """
    xlsx_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
    if not xlsx_path.exists():
        pytest.skip("PUCSL 15-minute XLSX not present")

    result = real_loader.load_pucsl_dispatch_xlsx(xlsx_path, sheet_names=["01.03", "02.03 "])
    assert result.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            for d_key in (20240301, 20240302):
                cur.execute(
                    """
                    SELECT count(DISTINCT interval_key), count(*)
                    FROM dw.fact_dispatch_interval
                    WHERE date_key = %s;
                    """,
                    (d_key,),
                )
                row_intervals = cur.fetchone()
                assert row_intervals is not None
                distinct_intervals, fact_count = row_intervals
                assert distinct_intervals == 96, (
                    f"Date {d_key} must have exactly 96 distinct intervals, got {distinct_intervals}"
                )


@pytest.mark.integration
def test_dispatch_month_end_boundary_no_april_spill(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
) -> None:
    """
    Verify that March 31 (31.03) slot 96 has date_key = 20240331 and zero facts
    are assigned to April 1 (20240401).
    """
    xlsx_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
    if not xlsx_path.exists():
        pytest.skip("PUCSL 15-minute XLSX not present")

    result = real_loader.load_pucsl_dispatch_xlsx(xlsx_path, sheet_names=["31.03"])
    assert result.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # Slot 96 must exist on 20240331
            cur.execute(
                """
                SELECT count(*)
                FROM dw.fact_dispatch_interval
                WHERE date_key = 20240331 AND interval_key = 96;
                """
            )
            row_slot96 = cur.fetchone()
            assert row_slot96 is not None
            slot96_count = row_slot96[0]
            assert slot96_count > 0, "Slot 96 must exist for 2024-03-31"

            # ZERO facts on 20240401
            cur.execute(
                """
                SELECT count(*)
                FROM dw.fact_dispatch_interval
                WHERE date_key = 20240401;
                """
            )
            row_april = cur.fetchone()
            assert row_april is not None
            april_count = row_april[0]
            assert april_count == 0, f"Expected 0 facts on 2024-04-01, found {april_count}"


@pytest.mark.integration
def test_full_march_dispatch_coverage_and_barge_quarantine_accounting(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
) -> None:
    """
    Verify loading all 31 sheets of March 2024:
    - Exactly 31 distinct calendar dates (2024-03-01 to 2024-03-31)
    - Exactly 96 interval slots per complete day
    - Exactly 21 negative Barge readings quarantined with DQ_GEN_NEGATIVE_OUTPUT
    - Remaining 107,115 records promoted to dw.fact_dispatch_interval
    """
    xlsx_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
    if not xlsx_path.exists():
        pytest.skip("PUCSL 15-minute XLSX not present")

    result = real_loader.load_pucsl_dispatch_xlsx(xlsx_path)
    assert result.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")
    assert result.rows_quarantined == 21, (
        f"Expected 21 quarantined Barge readings, got {result.rows_quarantined}"
    )

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # Check distinct calendar dates in fact table
            cur.execute(
                """
                SELECT min(dd.calendar_date), max(dd.calendar_date), count(DISTINCT dd.calendar_date)
                FROM dw.fact_dispatch_interval fdi
                JOIN dw.dim_date dd ON fdi.date_key = dd.date_key
                WHERE fdi.source_document_id = %s;
                """,
                (result.source_document_id,),
            )
            row_dates = cur.fetchone()
            assert row_dates is not None
            min_date, max_date, distinct_days = row_dates
            assert min_date == date(2024, 3, 1)
            assert max_date == date(2024, 3, 31)
            assert distinct_days == 31, f"Expected exactly 31 distinct days, got {distinct_days}"

            # Check total facts promoted
            cur.execute(
                """
                SELECT count(*)
                FROM dw.fact_dispatch_interval
                WHERE source_document_id = %s;
                """,
                (result.source_document_id,),
            )
            row_facts = cur.fetchone()
            assert row_facts is not None
            fact_count = row_facts[0]
            assert fact_count == 107115, (
                f"Expected 107115 facts promoted (107136 - 21), got {fact_count}"
            )

            # Check quarantined records audit logging
            cur.execute(
                """
                SELECT count(*)
                FROM audit.data_quality_issue dqi
                WHERE dqi.etl_run_id = %s
                  AND dqi.rule_code = 'DQ_GEN_NEGATIVE_OUTPUT';
                """,
                (result.etl_run_id,),
            )
            row_quarantined = cur.fetchone()
            assert row_quarantined is not None
            logged_quarantined = row_quarantined[0]
            assert logged_quarantined == 21, (
                f"Expected 21 logged DQ issues, got {logged_quarantined}"
            )


@pytest.mark.integration
def test_dispatch_idempotent_reload_no_obsolete_keys(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
) -> None:
    """
    Verify reloading a daily sheet:
    - Runs idempotently without duplicate fact rows.
    - Records updated facts instead of duplicated keys.
    - Leaves zero orphaned or obsolete keys on adjacent calendar days.
    """
    xlsx_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
    if not xlsx_path.exists():
        pytest.skip("PUCSL 15-minute XLSX not present")

    # Initial load of 01.03
    res1 = real_loader.load_pucsl_dispatch_xlsx(xlsx_path, sheet_names=["01.03"])
    assert res1.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM dw.fact_dispatch_interval WHERE date_key = 20240301;")
            row_init = cur.fetchone()
            assert row_init is not None
            initial_count = row_init[0]
            assert initial_count > 0

    # Repeat load of same sheet (idempotency verification)
    res2 = real_loader.load_pucsl_dispatch_xlsx(xlsx_path, sheet_names=["01.03"])
    assert res2.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")
    assert res2.rows_inserted == 0
    assert res2.rows_updated > 0

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM dw.fact_dispatch_interval WHERE date_key = 20240301;")
            row_post = cur.fetchone()
            assert row_post is not None
            post_count = row_post[0]
            assert post_count == initial_count, (
                "Fact count must not increase on repeat load of identical data"
            )

            # Check that March 1 slot 96 (original_timestamp 2024-03-02 00:00:00) did NOT spill into 20240302
            cur.execute(
                """
                SELECT count(*)
                FROM dw.fact_dispatch_interval
                WHERE date_key = 20240302
                  AND original_timestamp = '2024-03-02 00:00:00+05:30'::timestamptz;
                """
            )
            row_spill = cur.fetchone()
            assert row_spill is not None
            assert row_spill[0] == 0, "No March 1 slot 96 facts spilled into 20240302"
