"""
Phase 1 TDD Integration Tests for Transactional ETL Batch Execution:
- Atomic batch commit on valid synthetic fixture
- Batch re-execution idempotency (zero duplicate fact rows)
- Complete transaction rollback on mid-batch failure (zero partial fact inserts)
- Audit evidence preserved in audit.etl_run even when data transaction rolls back
"""
from __future__ import annotations

import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection
from src.etl.batch_loader import SyntheticGenerationBatchItem, TransactionalGenerationBatchLoader


@pytest.mark.integration
def test_transactional_batch_commit_idempotency_and_rollback(
    migrated_and_seeded_test_db: DatabaseConfig,
) -> None:
    """
    Exercise one successful ETL batch (and re-run for idempotency) and one failing ETL batch,
    verifying commit, idempotency, complete fact rollback on error, and preserved audit log.
    """
    loader = TransactionalGenerationBatchLoader(migrated_and_seeded_test_db)

    valid_items = [
        SyntheticGenerationBatchItem(
            plant_name="Victoria",
            report_date="2024-03-01",
            generation_mwh=1150.25,
            peak_mw=180.0,
        ),
        SyntheticGenerationBatchItem(
            plant_name="Kotmale",
            report_date="2024-03-01",
            generation_mwh=890.50,
            peak_mw=145.0,
        ),
    ]

    doc_code_ok = "SYNTH-TX-SUCCESS-2024-03-01"
    doc_code_fail = "SYNTH-TX-FAIL-2024-03-02"

    try:
        # 1. Successful batch commit
        result_1 = loader.execute_batch(
            document_code=doc_code_ok,
            batch_code="BATCH-OK-1",
            items=valid_items,
        )
        assert result_1.status == "SUCCEEDED"
        assert result_1.rows_inserted == 2

        # 2. Re-executing identical batch is strictly idempotent (total fact rows for doc remains 2)
        result_2 = loader.execute_batch(
            document_code=doc_code_ok,
            batch_code="BATCH-OK-2",
            items=valid_items,
        )
        assert result_2.status == "SUCCEEDED"

        with get_connection(migrated_and_seeded_test_db) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM dw.fact_generation_period fg
                    JOIN raw.source_document sd ON fg.source_document_id = sd.source_document_id
                    WHERE sd.document_code = %s;
                    """,
                    (doc_code_ok,),
                )
                assert int(cur.fetchone()[0]) == 2  # type: ignore[index]

        # 3. Failing batch: first item is valid, second item has impossible negative generation (-999 MWh)
        #    forcing a database CHECK constraint violation mid-transaction!
        failing_items = [
            SyntheticGenerationBatchItem(
                plant_name="Victoria",
                report_date="2024-03-02",
                generation_mwh=1100.00,
                peak_mw=175.0,
            ),
            SyntheticGenerationBatchItem(
                plant_name="Kotmale",
                report_date="2024-03-02",
                generation_mwh=-999.00,  # Triggers ck_fact_gen_period_non_negative!
                peak_mw=140.0,
            ),
        ]

        with pytest.raises(RuntimeError, match="rolled back"):
            loader.execute_batch(
                document_code=doc_code_fail,
                batch_code="BATCH-FAIL-1",
                items=failing_items,
                bypass_prevalidation_for_tx_test=True,
            )

        # Verify ZERO partial fact rows were committed for the failed batch,
        # AND audit.etl_run recorded ROLLED_BACK / FAILED audit evidence!
        with get_connection(migrated_and_seeded_test_db) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM dw.fact_generation_period fg
                    JOIN raw.source_document sd ON fg.source_document_id = sd.source_document_id
                    WHERE sd.document_code = %s;
                    """,
                    (doc_code_fail,),
                )
                assert int(cur.fetchone()[0]) == 0  # type: ignore[index]

                cur.execute(
                    """
                    SELECT run_status, error_message
                    FROM audit.etl_run er
                    JOIN raw.source_document sd ON er.source_document_id = sd.source_document_id
                    WHERE sd.document_code = %s
                    ORDER BY etl_run_id DESC LIMIT 1;
                    """,
                    (doc_code_fail,),
                )
                audit_row = cur.fetchone()
                assert audit_row is not None
                assert audit_row[0] == "ROLLED_BACK"
                assert audit_row[1] is not None
    finally:
        loader.cleanup_synthetic_documents([doc_code_ok, doc_code_fail])

