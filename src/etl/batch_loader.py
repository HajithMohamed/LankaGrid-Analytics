"""
Transactional ETL Batch Loader with Two-Boundary Audit Persistence.

Transaction Architecture:
1. Metadata & Audit Envelope (Boundary A, autocommit transaction):
   Registers raw.source_document, raw.ingestion_batch, and audit.etl_run ('RUNNING')
   so that audit provenance exists even if the warehouse load transaction fails.
2. Atomic Staging + Warehouse Promotion (Boundary B, single ACID transaction):
   Inserts raw extracted envelopes, stages rows, validates/loads dw.fact_generation_period
   all-or-nothing. Any SQL constraint or validation error rolls back 100% of Boundary B
   so zero partial fact rows remain.
3. Audit Finalization (Boundary C, autocommit transaction):
   Records 'SUCCEEDED' or 'ROLLED_BACK' with exact error diagnostics on audit.etl_run.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import psycopg

from src.common.config import DatabaseConfig
from src.common.db import get_connection


@dataclass(frozen=True)
class SyntheticGenerationBatchItem:
    """Single generation record used for transactional verification."""

    plant_name: str
    report_date: str
    generation_mwh: float
    peak_mw: float
    reported_unit_code: str = "MWh"
    dataset_revision: str = "v1"


@dataclass(frozen=True)
class BatchExecutionResult:
    """Outcome summary of a transactional ETL batch run."""

    etl_run_id: int
    source_document_id: int
    batch_id: int
    status: str
    rows_inserted: int
    rows_updated: int
    rows_quarantined: int


class TransactionalGenerationBatchLoader:
    """Executes atomic generation ETL batches while preserving audit evidence across rollbacks."""

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        self.config = config or DatabaseConfig.from_env()

    def execute_batch(
        self,
        document_code: str,
        batch_code: str,
        items: list[SyntheticGenerationBatchItem],
        acquisition_status: str = "SYNTHETIC_FIXTURE",
        bypass_prevalidation_for_tx_test: bool = False,
    ) -> BatchExecutionResult:
        """
        Execute a batch load atomically. If any row violates warehouse constraints during load,
        roll back the entire data transaction and persist ROLLED_BACK in audit.etl_run.
        """
        if not items:
            raise ValueError("Batch items cannot be empty.")

        first_date = items[0].report_date
        payload_digest = hashlib.sha256(
            json.dumps([item.__dict__ for item in items], sort_keys=True).encode("utf-8")
        ).hexdigest()

        with get_connection(self.config, autocommit=True) as conn:
            # Boundary A: Register document, batch, and RUNNING audit record
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT source_system_id FROM raw.source_system WHERE source_code = 'PUCSL';"
                    )
                    sys_row = cur.fetchone()
                    if sys_row is None:
                        raise RuntimeError(
                            "PUCSL missing in raw.source_system; run ReferenceSeeder first."
                        )
                    source_system_id = int(sys_row[0])

                    cur.execute(
                        """
                        INSERT INTO raw.source_document (
                            source_system_id, document_code, source_url, original_filename,
                            local_storage_path, file_format, sha256_checksum,
                            reporting_period_type, reporting_period_start, reporting_period_end,
                            dataset_revision, acquisition_status
                        ) VALUES (
                            %s, %s, 'https://www.pucsl.gov.lk/fixture-batch.pdf', %s,
                            %s, 'PDF', %s, 'DAILY', %s::DATE, %s::DATE, 'v1', %s
                        )
                        ON CONFLICT (document_code) DO UPDATE SET
                            sha256_checksum = EXCLUDED.sha256_checksum
                        RETURNING source_document_id;
                        """,
                        (
                            source_system_id,
                            document_code,
                            f"{document_code}.pdf",
                            f"tests/fixtures/{document_code}.pdf",
                            payload_digest,
                            first_date,
                            first_date,
                            acquisition_status,
                        ),
                    )
                    doc_row = cur.fetchone()
                    assert doc_row is not None
                    doc_id = int(doc_row[0])

                    cur.execute(
                        """
                        INSERT INTO raw.ingestion_batch (
                            batch_code, source_document_id, extraction_method,
                            batch_status, records_extracted
                        ) VALUES (%s, %s, 'transactional_batch_loader', 'EXTRACTED', %s)
                        ON CONFLICT (batch_code) DO UPDATE SET
                            records_extracted = EXCLUDED.records_extracted
                        RETURNING batch_id;
                        """,
                        (batch_code, doc_id, len(items)),
                    )
                    b_row = cur.fetchone()
                    assert b_row is not None
                    batch_id = int(b_row[0])

                    cur.execute(
                        "CALL etl.sp_start_etl_run('tx_generation_loader', 'dw', 'fact_generation_period', %s, %s, NULL);",
                        (doc_id, batch_id),
                    )
                    run_row = cur.fetchone()
                    assert run_row is not None
                    etl_run_id = int(run_row[0])

            # Boundary B: Atomic Staging + Warehouse Fact Promotion
            try:
                with conn.transaction():
                    with conn.cursor() as cur:
                        for idx, item in enumerate(items, start=1):
                            row_json = json.dumps(item.__dict__, sort_keys=True)
                            row_hash = hashlib.sha256(row_json.encode("utf-8")).hexdigest()
                            cur.execute(
                                """
                                INSERT INTO raw.extracted_record (
                                    batch_id, source_document_id, source_row_locator,
                                    raw_payload, content_sha256
                                ) VALUES (%s, %s, %s, %s::jsonb, %s)
                                ON CONFLICT (batch_id, source_row_locator) DO UPDATE SET
                                    raw_payload = EXCLUDED.raw_payload,
                                    content_sha256 = EXCLUDED.content_sha256
                                RETURNING raw_record_id;
                                """,
                                (batch_id, doc_id, f"row={idx}", row_json, row_hash),
                            )
                            rec_row = cur.fetchone()
                            assert rec_row is not None
                            raw_rec_id = int(rec_row[0])

                            initial_status = (
                                "valid" if bypass_prevalidation_for_tx_test else "pending"
                            )
                            cur.execute(
                                """
                                INSERT INTO staging.stg_generation_report (
                                    batch_id, source_document_id, raw_record_id, source_code,
                                    raw_plant_name, period_type_code, period_start_date, period_end_date,
                                    raw_generation_text, parsed_generation_value,
                                    raw_peak_mw_text, parsed_peak_mw,
                                    reported_unit_code, generation_boundary, dataset_revision,
                                    validation_status
                                ) VALUES (
                                    %s, %s, %s, 'PUCSL',
                                    %s, 'DAILY', %s::DATE, %s::DATE,
                                    %s, %s, %s, %s,
                                    %s, 'GROSS', %s, %s
                                );
                                """,
                                (
                                    batch_id,
                                    doc_id,
                                    raw_rec_id,
                                    item.plant_name,
                                    item.report_date,
                                    item.report_date,
                                    str(item.generation_mwh),
                                    item.generation_mwh,
                                    str(item.peak_mw),
                                    item.peak_mw,
                                    item.reported_unit_code,
                                    item.dataset_revision,
                                    initial_status,
                                ),
                            )

                        quar_cnt = 0
                        if not bypass_prevalidation_for_tx_test:
                            cur.execute(
                                "CALL etl.sp_validate_staged_generation(%s, %s, 0, 0);",
                                (batch_id, etl_run_id),
                            )
                            val_row = cur.fetchone()
                            assert val_row is not None
                            quar_cnt = int(val_row[1])

                        cur.execute(
                            "CALL etl.sp_load_generation_period(%s, %s, 0, 0);",
                            (batch_id, etl_run_id),
                        )
                        load_row = cur.fetchone()
                        assert load_row is not None
                        ins_cnt = int(load_row[0])
                        upd_cnt = int(load_row[1])

                # Boundary C (Success): Record SUCCEEDED / PARTIAL_QUARANTINE
                final_status = "PARTIAL_QUARANTINE" if quar_cnt > 0 else "SUCCEEDED"
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "CALL etl.sp_finalize_etl_run(%s, %s, %s, %s, %s, %s, NULL);",
                            (etl_run_id, final_status, len(items), ins_cnt, upd_cnt, quar_cnt),
                        )

                return BatchExecutionResult(
                    etl_run_id=etl_run_id,
                    source_document_id=doc_id,
                    batch_id=batch_id,
                    status=final_status,
                    rows_inserted=ins_cnt,
                    rows_updated=upd_cnt,
                    rows_quarantined=quar_cnt,
                )

            except psycopg.Error as exc:
                # Boundary C (Failure): Data transaction automatically rolled back; persist audit failure!
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "CALL etl.sp_finalize_etl_run(%s, 'ROLLED_BACK', %s, 0, 0, 0, %s);",
                            (etl_run_id, len(items), str(exc)),
                        )
                raise RuntimeError(
                    f"ETL batch '{batch_code}' failed and rolled back atomically: {exc}"
                ) from exc

    def cleanup_synthetic_documents(self, document_codes: list[str]) -> None:
        """Remove explicitly marked SYNTHETIC_FIXTURE test records after verification."""
        if not document_codes:
            return
        with get_connection(self.config, autocommit=True) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT source_document_id
                        FROM raw.source_document
                        WHERE document_code = ANY(%s)
                          AND acquisition_status = 'SYNTHETIC_FIXTURE';
                        """,
                        (document_codes,),
                    )
                    doc_ids = [int(r[0]) for r in cur.fetchall()]
                    if not doc_ids:
                        return
                    cur.execute(
                        "DELETE FROM audit.record_lineage WHERE source_document_id = ANY(%s);",
                        (doc_ids,),
                    )
                    cur.execute(
                        "DELETE FROM audit.data_quality_issue WHERE source_document_id = ANY(%s);",
                        (doc_ids,),
                    )
                    cur.execute(
                        "DELETE FROM dw.fact_generation_period WHERE source_document_id = ANY(%s);",
                        (doc_ids,),
                    )
                    cur.execute(
                        "DELETE FROM staging.stg_generation_report WHERE source_document_id = ANY(%s);",
                        (doc_ids,),
                    )
                    cur.execute(
                        "DELETE FROM audit.etl_run WHERE source_document_id = ANY(%s);", (doc_ids,)
                    )
                    cur.execute(
                        "DELETE FROM raw.extracted_record WHERE source_document_id = ANY(%s);",
                        (doc_ids,),
                    )
                    cur.execute(
                        "DELETE FROM raw.ingestion_batch WHERE source_document_id = ANY(%s);",
                        (doc_ids,),
                    )
                    cur.execute(
                        "DELETE FROM raw.source_document WHERE source_document_id = ANY(%s);",
                        (doc_ids,),
                    )
