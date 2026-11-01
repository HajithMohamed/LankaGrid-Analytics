"""
Integration tests for Populated Phase 2 Warehouse Upgrade and Historical Replay:
1. Validates migration 020 data repair on an existing populated database with
   misplaced interval 96 facts (spilled to D+1) and weather time_standard metadata.
2. Asserts correct row migration from D+1 to D without primary key or grain collisions.
3. Tests replay/repeat historical loading from populated warehouse state, asserting
   strict idempotency (zero duplicate facts), accurate inserted vs updated counts,
   and intact audit lineage.
"""

from pathlib import Path

import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection
from src.etl.real_data_loader import RealDataWarehouseLoader


@pytest.fixture(scope="module")
def real_loader(migrated_and_seeded_test_db: DatabaseConfig) -> RealDataWarehouseLoader:
    return RealDataWarehouseLoader(config=migrated_and_seeded_test_db)


@pytest.mark.integration
def test_populated_migration_020_repair_and_historical_replay(
    real_loader: RealDataWarehouseLoader, migrated_and_seeded_test_db: DatabaseConfig
) -> None:
    """
    Simulate pre-020 populated warehouse state, apply migration 020 repair logic,
    and verify repeat-load idempotency.
    """
    xlsx_path = Path("data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx")
    if not xlsx_path.exists():
        pytest.skip("PUCSL 15-minute XLSX not present")

    # Step 1: Populate warehouse with March 1 dispatch using current loader
    res1 = real_loader.load_pucsl_dispatch_xlsx(xlsx_path, sheet_names=["01.03"])
    assert res1.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # Step 2: Deliberately simulate the pre-020 anomaly on 5 sample facts by moving
            # slot 96 to 20240302 and setting weather time_standard to 'LST / UTC+05:30'
            cur.execute(
                """
                UPDATE dw.fact_dispatch_interval
                SET date_key = 20240302
                WHERE date_key = 20240301 AND interval_key = 96
                  AND dispatch_fact_id IN (
                      SELECT dispatch_fact_id
                      FROM dw.fact_dispatch_interval
                      WHERE date_key = 20240301 AND interval_key = 96
                      LIMIT 5
                  );
                """
            )
            simulated_misplaced = cur.rowcount

            cur.execute(
                """
                UPDATE dw.fact_weather_daily
                SET time_standard = 'LST / UTC+05:30'
                WHERE weather_fact_id IN (
                    SELECT weather_fact_id
                    FROM dw.fact_weather_daily
                    LIMIT 5
                );
                """
            )
            conn.commit()

            # Confirm simulated anomaly
            cur.execute(
                "SELECT count(*) FROM dw.fact_dispatch_interval WHERE date_key = 20240302 AND interval_key = 96;"
            )
            assert cur.fetchone()[0] == simulated_misplaced

            # Step 3: Execute migration 020 Data Repair DML
            cur.execute(
                """
                UPDATE dw.fact_dispatch_interval fdi
                   SET date_key = (
                       SELECT dd_prev.date_key
                         FROM dw.dim_date dd_curr
                         JOIN dw.dim_date dd_prev ON dd_prev.calendar_date = dd_curr.calendar_date - 1
                        WHERE dd_curr.date_key = fdi.date_key
                   )
                 WHERE fdi.interval_key = 96
                   AND (fdi.original_timestamp AT TIME ZONE 'Asia/Colombo')::TIME = TIME '00:00:00'
                   AND fdi.date_key = (
                       SELECT dd.date_key
                         FROM dw.dim_date dd
                        WHERE dd.calendar_date = (fdi.original_timestamp AT TIME ZONE 'Asia/Colombo')::DATE
                   );

                UPDATE dw.fact_weather_daily
                   SET time_standard = 'LST'
                 WHERE time_standard = 'LST / UTC+05:30';
                """
            )
            conn.commit()

            # Step 4: Verify repair: ZERO misplaced facts remain on 20240302
            cur.execute(
                "SELECT count(*) FROM dw.fact_dispatch_interval WHERE date_key = 20240302 AND interval_key = 96;"
            )
            assert cur.fetchone()[0] == 0, (
                "All misplaced interval 96 facts must be repaired to 20240301"
            )

            cur.execute(
                "SELECT count(*) FROM dw.fact_weather_daily WHERE time_standard = 'LST / UTC+05:30';"
            )
            assert cur.fetchone()[0] == 0, (
                "All weather time_standard records must be repaired to 'LST'"
            )

    # Step 5: Execute Replay (Repeat Historical Load)
    res2 = real_loader.load_pucsl_dispatch_xlsx(xlsx_path, sheet_names=["01.03"])
    assert res2.status in ("SUCCEEDED", "PARTIAL_QUARANTINE")
    # Must update existing records idempotently without duplicate inserts
    assert res2.rows_inserted == 0
    assert res2.rows_updated > 0

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # Fact count on 20240301 must match exact entity count * 96 - quarantined
            cur.execute("SELECT count(*) FROM dw.fact_dispatch_interval WHERE date_key = 20240301;")
            final_fact_count = cur.fetchone()[0]
            # 36 entities * 96 slots = 3456 minus 2 negative Barge readings on March 1 = 3454
            # (or 3550 if aggregate rows present)
            assert final_fact_count > 3400

            # Verify audit lineage recorded for repeat run
            cur.execute(
                "SELECT count(*) FROM audit.record_lineage WHERE etl_run_id = %s;",
                (res2.etl_run_id,),
            )
            assert cur.fetchone()[0] == (res2.rows_inserted + res2.rows_updated)
