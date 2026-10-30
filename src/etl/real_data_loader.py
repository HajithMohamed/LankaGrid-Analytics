"""
Authentic File-Based Real Data ETL Loader.
Implements the 3-Boundary Transaction Protocol:
- Boundary A: Register raw document provenance and start audit.etl_run (autocommit)
- Boundary B: Atomic raw extraction, staging insertion, validation, and fact loading
- Boundary C: Audit finalization with exact error diagnostics and rollback guarantees
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from src.common.config import DatabaseConfig
from src.common.db import get_connection
from src.etl.batch_loader import BatchExecutionResult
from src.ingestion.ceb_digest_parser import CebDigestParser
from src.ingestion.manifest_validator import ManifestValidator
from src.ingestion.nasa_power_parser import NasaPowerParser
from src.ingestion.pucsl_dispatch_parser import PucslDispatchParser
from src.ingestion.pucsl_pdf_parser import PucslPdfParser


def _fetch_scalar(cur: Any) -> Any:
    row = cur.fetchone()
    if row is None:
        raise ValueError("Expected query result row, got None")
    return row[0]


def _fetch_row(cur: Any) -> tuple[Any, ...]:
    row = cur.fetchone()
    if row is None:
        raise ValueError("Expected query result row, got None")
    return tuple(row)


class RealDataWarehouseLoader:
    """Loads authentic official CEB, PUCSL, and NASA POWER datasets into PostgreSQL warehouse."""

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        self.config = config or DatabaseConfig.from_env()

    @staticmethod
    def _compute_sha256(path: Path) -> str:
        return ManifestValidator.compute_sha256(path)

    def load_pucsl_daily_pdf(
        self, pdf_path: Path, reporting_date: date, revision: str = "v1"
    ) -> BatchExecutionResult:
        """Load PUCSL daily generation report into dw.fact_generation_period."""
        parser = PucslPdfParser(default_date=reporting_date)
        plant_records = parser.extract_plant_dispatch_table(pdf_path)
        if not plant_records:
            raise ValueError(f"No plant generation records extracted from {pdf_path}")

        doc_code = f"PUCSL-GEN-DAILY-{reporting_date.strftime('%Y-%m-%d')}"
        batch_code = f"BATCH-{doc_code}-{revision}"
        file_sha256 = self._compute_sha256(pdf_path)

        with get_connection(self.config, autocommit=True) as conn:
            # Boundary A: Register document, batch, and RUNNING audit record
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT source_system_id FROM raw.source_system WHERE source_code = 'PUCSL';"
                    )
                    sys_id = _fetch_scalar(cur)

                    cur.execute(
                        """
                        INSERT INTO raw.source_document (
                            source_system_id, document_code, source_url, original_filename,
                            local_storage_path, file_format, sha256_checksum,
                            reporting_period_type, reporting_period_start, reporting_period_end,
                            dataset_revision, acquisition_status
                        ) VALUES (
                            %s, %s, 'https://www.pucsl.gov.lk/daily-generation-reports-2/', %s,
                            %s, 'PDF', %s, 'DAILY', %s, %s, %s, 'DOWNLOADED_VERIFIED'
                        ) ON CONFLICT (document_code) DO UPDATE SET
                            sha256_checksum = EXCLUDED.sha256_checksum,
                            dataset_revision = EXCLUDED.dataset_revision
                        RETURNING source_document_id;
                        """,
                        (
                            sys_id,
                            doc_code,
                            pdf_path.name,
                            str(pdf_path),
                            file_sha256,
                            reporting_date,
                            reporting_date,
                            revision,
                        ),
                    )
                    doc_id = _fetch_scalar(cur)

                    cur.execute(
                        """
                        INSERT INTO raw.ingestion_batch (
                            batch_code, source_document_id, extraction_method, batch_status, records_extracted
                        ) VALUES (%s, %s, 'pucsl_pdf_parser', 'EXTRACTED', %s)
                        ON CONFLICT (batch_code) DO UPDATE SET records_extracted = EXCLUDED.records_extracted
                        RETURNING batch_id;
                        """,
                        (batch_code, doc_id, len(plant_records)),
                    )
                    batch_id = _fetch_scalar(cur)

                    cur.execute(
                        "CALL etl.sp_start_etl_run('pucsl_daily_pdf_loader', 'dw', 'fact_generation_period', %s, %s, NULL);",
                        (doc_id, batch_id),
                    )
                    etl_run_id = _fetch_scalar(cur)

            # Boundary B: Atomic Staging + Fact Promotion
            try:
                with conn.transaction():
                    with conn.cursor() as cur:
                        for idx, rec in enumerate(plant_records, start=1):
                            payload_json = json.dumps(rec.__dict__, default=str)
                            payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
                            cur.execute(
                                """
                                INSERT INTO raw.extracted_record (
                                    batch_id, source_document_id, source_row_locator,
                                    raw_payload, content_sha256
                                ) VALUES (%s, %s, %s, %s::jsonb, %s)
                                ON CONFLICT (batch_id, source_row_locator) DO UPDATE SET
                                    raw_payload = EXCLUDED.raw_payload
                                RETURNING raw_record_id;
                                """,
                                (batch_id, doc_id, f"p4_row={idx}", payload_json, payload_hash),
                            )
                            raw_rec_id = _fetch_scalar(cur)

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
                                    %s, 'DAILY', %s, %s,
                                    %s, %s, %s, %s,
                                    'MWh', 'GROSS', %s, 'pending'
                                );
                                """,
                                (
                                    batch_id,
                                    doc_id,
                                    raw_rec_id,
                                    rec.plant_name,
                                    reporting_date,
                                    reporting_date,
                                    str(rec.generation_mwh),
                                    rec.generation_mwh,
                                    str(rec.night_peak_mw),
                                    rec.night_peak_mw,
                                    revision,
                                ),
                            )

                        # Validate and Load via stored procedures
                        cur.execute(
                            "CALL etl.sp_validate_staged_generation(%s, %s, 0, 0);",
                            (batch_id, etl_run_id),
                        )
                        val_res = _fetch_row(cur)
                        quar_cnt = int(val_res[1])

                        cur.execute(
                            "CALL etl.sp_load_generation_period(%s, %s, 0, 0);",
                            (batch_id, etl_run_id),
                        )
                        load_res = _fetch_row(cur)
                        ins_cnt = int(load_res[0])
                        upd_cnt = int(load_res[1])

                # Boundary C (Success)
                final_status = "PARTIAL_QUARANTINE" if quar_cnt > 0 else "SUCCEEDED"
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "CALL etl.sp_finalize_etl_run(%s, %s, %s, %s, %s, %s, NULL);",
                            (
                                etl_run_id,
                                final_status,
                                len(plant_records),
                                ins_cnt,
                                upd_cnt,
                                quar_cnt,
                            ),
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
            except Exception as exc:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "CALL etl.sp_finalize_etl_run(%s, 'ROLLED_BACK', %s, 0, 0, 0, %s);",
                            (etl_run_id, len(plant_records), str(exc)),
                        )
                raise

    def load_pucsl_dispatch_xlsx(
        self, xlsx_path: Path, sheet_names: list[str] | None = None, revision: str = "v1"
    ) -> BatchExecutionResult:
        """Load PUCSL 15-minute dispatch spreadsheet into dw.fact_dispatch_interval."""
        parser = PucslDispatchParser()
        sheets_to_parse = sheet_names or parser.get_sheet_names(xlsx_path)

        all_records = []
        for s in sheets_to_parse:
            all_records.extend(parser.parse_sheet(xlsx_path, s))

        if not all_records:
            raise ValueError(f"No dispatch records parsed from {xlsx_path}")

        first_date = all_records[0].observation_date
        last_date = all_records[-1].observation_date
        doc_code = "PUCSL-DISPATCH-15MIN-2024-M03"
        batch_code = f"BATCH-{doc_code}-{revision}"
        file_sha256 = self._compute_sha256(xlsx_path)

        with get_connection(self.config, autocommit=True) as conn:
            # Boundary A: Register document and batch
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT source_system_id FROM raw.source_system WHERE source_code = 'PUCSL';"
                    )
                    sys_id = _fetch_scalar(cur)

                    cur.execute(
                        """
                        INSERT INTO raw.source_document (
                            source_system_id, document_code, source_url, original_filename,
                            local_storage_path, file_format, sha256_checksum,
                            reporting_period_type, reporting_period_start, reporting_period_end,
                            dataset_revision, acquisition_status
                        ) VALUES (
                            %s, %s, 'https://www.pucsl.gov.lk/15-minutes-reports/', %s,
                            %s, 'XLSX', %s, 'INTERVAL_15MIN', %s, %s, %s, 'DOWNLOADED_VERIFIED'
                        ) ON CONFLICT (document_code) DO UPDATE SET
                            sha256_checksum = EXCLUDED.sha256_checksum
                        RETURNING source_document_id;
                        """,
                        (
                            sys_id,
                            doc_code,
                            xlsx_path.name,
                            str(xlsx_path),
                            file_sha256,
                            first_date,
                            last_date,
                            revision,
                        ),
                    )
                    doc_id = _fetch_scalar(cur)

                    cur.execute(
                        """
                        INSERT INTO raw.ingestion_batch (
                            batch_code, source_document_id, extraction_method, batch_status, records_extracted
                        ) VALUES (%s, %s, 'pucsl_dispatch_parser', 'EXTRACTED', %s)
                        ON CONFLICT (batch_code) DO UPDATE SET records_extracted = EXCLUDED.records_extracted
                        RETURNING batch_id;
                        """,
                        (batch_code, doc_id, len(all_records)),
                    )
                    batch_id = _fetch_scalar(cur)

                    cur.execute(
                        "CALL etl.sp_start_etl_run('pucsl_dispatch_loader', 'dw', 'fact_dispatch_interval', %s, %s, NULL);",
                        (doc_id, batch_id),
                    )
                    etl_run_id = _fetch_scalar(cur)

            # Boundary B: Atomic Staging + Load
            try:
                with conn.transaction():
                    with conn.cursor() as cur:
                        for _idx, rec in enumerate(all_records, start=1):
                            row_loc = f"{rec.sheet_name}:r{rec.row_index}:c{rec.column_index}"
                            payload_json = json.dumps(
                                {
                                    "date": rec.observation_date.isoformat(),
                                    "slot": rec.interval_slot_number,
                                    "timestamp": rec.observation_timestamp.isoformat(),
                                    "station": rec.raw_entity_name,
                                    "power_mw": rec.power_mw,
                                }
                            )
                            cur.execute(
                                """
                                INSERT INTO raw.extracted_record (
                                    batch_id, source_document_id, source_row_locator, raw_payload, content_sha256
                                ) VALUES (%s, %s, %s, %s::jsonb, %s)
                                ON CONFLICT (batch_id, source_row_locator) DO UPDATE SET raw_payload = EXCLUDED.raw_payload
                                RETURNING raw_record_id;
                                """,
                                (
                                    batch_id,
                                    doc_id,
                                    row_loc,
                                    payload_json,
                                    hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
                                ),
                            )
                            raw_rec_id = _fetch_scalar(cur)

                            cur.execute(
                                """
                                INSERT INTO staging.stg_dispatch_observation (
                                    batch_id, source_document_id, raw_record_id, source_code,
                                    raw_entity_name, raw_timestamp_text, parsed_timestamp,
                                    interval_duration_minutes, raw_power_text, parsed_power_mw,
                                    reported_unit_code, metric_code, dataset_revision, validation_status
                                ) VALUES (
                                    %s, %s, %s, 'PUCSL',
                                    %s, %s, %s,
                                    15, %s, %s,
                                    'MW', 'PLANT_DISPATCH_MW', %s, 'pending'
                                );
                                """,
                                (
                                    batch_id,
                                    doc_id,
                                    raw_rec_id,
                                    rec.raw_entity_name,
                                    rec.observation_timestamp.isoformat(),
                                    rec.observation_timestamp,
                                    str(rec.power_mw),
                                    rec.power_mw,
                                    revision,
                                ),
                            )

                        cur.execute(
                            "CALL etl.sp_validate_staged_dispatch(%s, %s, 0, 0);",
                            (batch_id, etl_run_id),
                        )
                        val_res = _fetch_row(cur)
                        quar_cnt = int(val_res[1])

                        cur.execute(
                            "CALL etl.sp_load_dispatch_interval(%s, %s, 0, 0);",
                            (batch_id, etl_run_id),
                        )
                        load_res = _fetch_row(cur)
                        ins_cnt = int(load_res[0])
                        upd_cnt = int(load_res[1])

                final_status = "PARTIAL_QUARANTINE" if quar_cnt > 0 else "SUCCEEDED"
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "CALL etl.sp_finalize_etl_run(%s, %s, %s, %s, %s, %s, NULL);",
                            (
                                etl_run_id,
                                final_status,
                                len(all_records),
                                ins_cnt,
                                upd_cnt,
                                quar_cnt,
                            ),
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
            except Exception as exc:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "CALL etl.sp_finalize_etl_run(%s, 'ROLLED_BACK', %s, 0, 0, 0, %s);",
                            (etl_run_id, len(all_records), str(exc)),
                        )
                raise

    def load_nasa_weather_json(self, json_path: Path, revision: str = "v1") -> BatchExecutionResult:
        """Load NASA POWER meteorological observations into dw.fact_weather_daily."""
        parser = NasaPowerParser()
        records = parser.parse_file(json_path)
        if not records:
            raise ValueError(f"No weather observations parsed from {json_path}")

        first_date = records[0].observation_date
        last_date = records[-1].observation_date
        doc_code = "NASA-POWER-DAILY-2024-M01"
        batch_code = f"BATCH-{doc_code}-{revision}"
        file_sha256 = self._compute_sha256(json_path)

        with get_connection(self.config, autocommit=True) as conn:
            # Boundary A
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT source_system_id FROM raw.source_system WHERE source_code = 'NASA_POWER';"
                    )
                    sys_id = _fetch_scalar(cur)

                    cur.execute(
                        """
                        INSERT INTO raw.source_document (
                            source_system_id, document_code, source_url, original_filename,
                            local_storage_path, file_format, sha256_checksum,
                            reporting_period_type, reporting_period_start, reporting_period_end,
                            dataset_revision, acquisition_status
                        ) VALUES (
                            %s, %s, 'https://power.larc.nasa.gov/api/temporal/daily/point', %s,
                            %s, 'JSON', %s, 'DAILY', %s, %s, %s, 'DOWNLOADED_VERIFIED'
                        ) ON CONFLICT (document_code) DO UPDATE SET
                            sha256_checksum = EXCLUDED.sha256_checksum
                        RETURNING source_document_id;
                        """,
                        (
                            sys_id,
                            doc_code,
                            json_path.name,
                            str(json_path),
                            file_sha256,
                            first_date,
                            last_date,
                            revision,
                        ),
                    )
                    doc_id = _fetch_scalar(cur)

                    cur.execute(
                        """
                        INSERT INTO raw.ingestion_batch (
                            batch_code, source_document_id, extraction_method, batch_status, records_extracted
                        ) VALUES (%s, %s, 'nasa_power_parser', 'EXTRACTED', %s)
                        ON CONFLICT (batch_code) DO UPDATE SET records_extracted = EXCLUDED.records_extracted
                        RETURNING batch_id;
                        """,
                        (batch_code, doc_id, len(records)),
                    )
                    batch_id = _fetch_scalar(cur)

                    cur.execute(
                        "CALL etl.sp_start_etl_run('nasa_weather_loader', 'dw', 'fact_weather_daily', %s, %s, NULL);",
                        (doc_id, batch_id),
                    )
                    etl_run_id = _fetch_scalar(cur)

            # Boundary B: Staging + Load
            try:
                with conn.transaction():
                    with conn.cursor() as cur:
                        for _idx, rec in enumerate(records, start=1):
                            row_loc = f"{rec.location_code}:{rec.source_variable_name}:{rec.observation_date.isoformat()}"
                            payload_json = json.dumps(rec.__dict__, default=str)
                            cur.execute(
                                """
                                INSERT INTO raw.extracted_record (
                                    batch_id, source_document_id, source_row_locator, raw_payload, content_sha256
                                ) VALUES (%s, %s, %s, %s::jsonb, %s)
                                ON CONFLICT (batch_id, source_row_locator) DO UPDATE SET raw_payload = EXCLUDED.raw_payload
                                RETURNING raw_record_id;
                                """,
                                (
                                    batch_id,
                                    doc_id,
                                    row_loc,
                                    payload_json,
                                    hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
                                ),
                            )
                            raw_rec_id = _fetch_scalar(cur)

                            cur.execute(
                                """
                                INSERT INTO staging.stg_weather_observation (
                                    batch_id, source_document_id, raw_record_id, source_code,
                                    location_code, observation_date, source_variable_name,
                                    raw_value_text, parsed_value, original_unit_code,
                                    missing_value_code, dataset_revision, validation_status
                                ) VALUES (
                                    %s, %s, %s, 'NASA_POWER',
                                    %s, %s, %s,
                                    %s, %s, %s,
                                    %s, %s, 'pending'
                                );
                                """,
                                (
                                    batch_id,
                                    doc_id,
                                    raw_rec_id,
                                    rec.location_code,
                                    rec.observation_date,
                                    rec.source_variable_name,
                                    str(rec.parsed_value),
                                    rec.parsed_value,
                                    rec.reported_unit_code,
                                    rec.missing_value_code,
                                    revision,
                                ),
                            )

                        cur.execute(
                            "CALL etl.sp_validate_staged_weather(%s, %s, 0, 0);",
                            (batch_id, etl_run_id),
                        )
                        val_res = _fetch_row(cur)
                        quar_cnt = int(val_res[1])

                        cur.execute(
                            "CALL etl.sp_load_weather_daily(%s, %s, 0, 0);", (batch_id, etl_run_id)
                        )
                        load_res = _fetch_row(cur)
                        ins_cnt = int(load_res[0])
                        upd_cnt = int(load_res[1])

                final_status = "PARTIAL_QUARANTINE" if quar_cnt > 0 else "SUCCEEDED"
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "CALL etl.sp_finalize_etl_run(%s, %s, %s, %s, %s, %s, NULL);",
                            (etl_run_id, final_status, len(records), ins_cnt, upd_cnt, quar_cnt),
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
            except Exception as exc:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "CALL etl.sp_finalize_etl_run(%s, 'ROLLED_BACK', %s, 0, 0, 0, %s);",
                            (etl_run_id, len(records), str(exc)),
                        )
                raise

    def load_ceb_sales_pdf(
        self, pdf_path: Path, reporting_year: int = 2024, revision: str = "v1"
    ) -> BatchExecutionResult:
        """Load CEB Statistical Digest billed electricity sales into dw.fact_electricity_sales."""
        parser = CebDigestParser(reporting_year=reporting_year)
        tariff_records = parser.extract_tariff_sales(pdf_path)
        if not tariff_records:
            raise ValueError(f"No tariff sales parsed from {pdf_path}")

        start_date = date(reporting_year, 1, 1)
        end_date = date(reporting_year, 12, 31)
        doc_code = f"CEB-STAT-DIGEST-{reporting_year}"
        batch_code = f"BATCH-{doc_code}-{revision}"
        file_sha256 = self._compute_sha256(pdf_path)

        with get_connection(self.config, autocommit=True) as conn:
            # Boundary A
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT source_system_id FROM raw.source_system WHERE source_code = 'CEB';"
                    )
                    sys_id = _fetch_scalar(cur)

                    cur.execute(
                        """
                        INSERT INTO raw.source_document (
                            source_system_id, document_code, source_url, original_filename,
                            local_storage_path, file_format, sha256_checksum,
                            reporting_period_type, reporting_period_start, reporting_period_end,
                            dataset_revision, acquisition_status
                        ) VALUES (
                            %s, %s, 'https://ceb.lk/publication-media/other-publications/en', %s,
                            %s, 'PDF', %s, 'ANNUAL', %s, %s, %s, 'DOWNLOADED_VERIFIED'
                        ) ON CONFLICT (document_code) DO UPDATE SET
                            sha256_checksum = EXCLUDED.sha256_checksum
                        RETURNING source_document_id;
                        """,
                        (
                            sys_id,
                            doc_code,
                            pdf_path.name,
                            str(pdf_path),
                            file_sha256,
                            start_date,
                            end_date,
                            revision,
                        ),
                    )
                    doc_id = _fetch_scalar(cur)

                    cur.execute(
                        """
                        INSERT INTO raw.ingestion_batch (
                            batch_code, source_document_id, extraction_method, batch_status, records_extracted
                        ) VALUES (%s, %s, 'ceb_digest_parser', 'EXTRACTED', %s)
                        ON CONFLICT (batch_code) DO UPDATE SET records_extracted = EXCLUDED.records_extracted
                        RETURNING batch_id;
                        """,
                        (batch_code, doc_id, len(tariff_records)),
                    )
                    batch_id = _fetch_scalar(cur)

                    cur.execute(
                        "CALL etl.sp_start_etl_run('ceb_sales_loader', 'dw', 'fact_electricity_sales', %s, %s, NULL);",
                        (doc_id, batch_id),
                    )
                    etl_run_id = _fetch_scalar(cur)

            # Boundary B: Staging + Load
            try:
                with conn.transaction():
                    with conn.cursor() as cur:
                        for _idx, rec in enumerate(tariff_records, start=1):
                            row_loc = f"p5_tariff={rec.tariff_group}"
                            payload_json = json.dumps(rec.__dict__, default=str)
                            cur.execute(
                                """
                                INSERT INTO raw.extracted_record (
                                    batch_id, source_document_id, source_row_locator, raw_payload, content_sha256
                                ) VALUES (%s, %s, %s, %s::jsonb, %s)
                                ON CONFLICT (batch_id, source_row_locator) DO UPDATE SET raw_payload = EXCLUDED.raw_payload
                                RETURNING raw_record_id;
                                """,
                                (
                                    batch_id,
                                    doc_id,
                                    row_loc,
                                    payload_json,
                                    hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
                                ),
                            )
                            raw_rec_id = _fetch_scalar(cur)

                            cur.execute(
                                """
                                INSERT INTO staging.stg_electricity_sales (
                                    batch_id, source_document_id, raw_record_id, source_code,
                                    raw_region_name, raw_sector_name, period_type_code,
                                    period_start_date, period_end_date, raw_energy_sold_text,
                                    parsed_energy_sold, reported_unit_code, dataset_revision, validation_status
                                ) VALUES (
                                    %s, %s, %s, 'CEB',
                                    'LK', %s, 'ANNUAL',
                                    %s, %s, %s,
                                    %s, 'GWh', %s, 'pending'
                                );
                                """,
                                (
                                    batch_id,
                                    doc_id,
                                    raw_rec_id,
                                    rec.tariff_group,
                                    start_date,
                                    end_date,
                                    str(rec.sales_gwh),
                                    rec.sales_gwh,
                                    revision,
                                ),
                            )

                        cur.execute(
                            "CALL etl.sp_validate_staged_sales(%s, %s, 0, 0);",
                            (batch_id, etl_run_id),
                        )
                        val_res = _fetch_row(cur)
                        quar_cnt = int(val_res[1])

                        cur.execute(
                            "CALL etl.sp_load_electricity_sales(%s, %s, 0, 0);",
                            (batch_id, etl_run_id),
                        )
                        load_res = _fetch_row(cur)
                        ins_cnt = int(load_res[0])
                        upd_cnt = int(load_res[1])

                final_status = "PARTIAL_QUARANTINE" if quar_cnt > 0 else "SUCCEEDED"
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "CALL etl.sp_finalize_etl_run(%s, %s, %s, %s, %s, %s, NULL);",
                            (
                                etl_run_id,
                                final_status,
                                len(tariff_records),
                                ins_cnt,
                                upd_cnt,
                                quar_cnt,
                            ),
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
            except Exception as exc:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            "CALL etl.sp_finalize_etl_run(%s, 'ROLLED_BACK', %s, 0, 0, 0, %s);",
                            (etl_run_id, len(tariff_records), str(exc)),
                        )
                raise
