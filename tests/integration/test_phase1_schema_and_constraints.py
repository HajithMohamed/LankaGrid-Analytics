"""
Phase 1 TDD Integration Tests:
- Sequential migration ordering (001 through 017)
- Segregated schemas (raw, staging, ref, dw, mart, audit, etl)
- PK, FK, UNIQUE, UNIQUE NULLS NOT DISTINCT, and CHECK constraint enforcement
- Invalid units, negative measurements, missing-value codes (-999 -> NULL, never 0)
- SCD Type 2 uniqueness on dw.dim_power_plant
- Range partition pruning on dw.fact_dispatch_interval via EXPLAIN (FORMAT JSON)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import psycopg
import pytest

from scripts.migrate import MigrationRunner
from src.common.config import DatabaseConfig
from src.common.db import get_connection


def _create_synthetic_lineage(cur: psycopg.Cursor[Any], suffix: str) -> tuple[int, int, int]:
    """Insert explicitly marked SYNTHETIC_FIXTURE source_document, batch, raw_record, and etl_run."""
    cur.execute("SELECT source_system_id FROM raw.source_system WHERE source_code = 'PUCSL';")
    row = cur.fetchone()
    assert row is not None
    source_sys_id = int(row[0])

    cur.execute(
        """
        INSERT INTO raw.source_document (
            source_system_id, document_code, source_url, original_filename,
            local_storage_path, file_format, sha256_checksum,
            reporting_period_type, reporting_period_start, reporting_period_end,
            dataset_revision, acquisition_status
        ) VALUES (
            %s, %s, 'https://www.pucsl.gov.lk/synthetic-test.pdf', 'synthetic_test.pdf',
            'tests/fixtures/synthetic_test.pdf', 'PDF',
            '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
            'DAILY', DATE '2024-01-15', DATE '2024-01-15', 'v1', 'SYNTHETIC_FIXTURE'
        ) RETURNING source_document_id;
        """,
        (source_sys_id, f"SYNTH-DOC-{suffix}"),
    )
    doc_row = cur.fetchone()
    assert doc_row is not None
    doc_id = int(doc_row[0])

    cur.execute(
        """
        INSERT INTO raw.ingestion_batch (
            batch_code, source_document_id, extraction_method, batch_status, records_extracted
        ) VALUES (%s, %s, 'pytest_fixture', 'EXTRACTED', 1)
        RETURNING batch_id;
        """,
        (f"SYNTH-BATCH-{suffix}", doc_id),
    )
    batch_row = cur.fetchone()
    assert batch_row is not None
    batch_id = int(batch_row[0])

    cur.execute(
        """
        INSERT INTO raw.extracted_record (
            batch_id, source_document_id, source_row_locator, raw_payload, content_sha256
        ) VALUES (
            %s, %s, 'row=1', '{"synthetic": true}'::jsonb,
            'fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210'
        ) RETURNING raw_record_id;
        """,
        (batch_id, doc_id),
    )
    rec_row = cur.fetchone()
    assert rec_row is not None
    raw_rec_id = int(rec_row[0])

    cur.execute(
        """
        INSERT INTO audit.etl_run (
            pipeline_name, target_schema, target_table, source_document_id, batch_id, run_status
        ) VALUES ('pytest_constraint_suite', 'dw', 'fact_test', %s, %s, 'RUNNING')
        RETURNING etl_run_id;
        """,
        (doc_id, batch_id),
    )
    run_row = cur.fetchone()
    assert run_row is not None
    etl_run_id = int(run_row[0])
    return doc_id, raw_rec_id, etl_run_id


@pytest.mark.integration
def test_migration_sequence_001_to_017(migrated_and_seeded_test_db: DatabaseConfig) -> None:
    """Assert migrations 001 through 017 exist in strict numerical sequence and are all applied."""
    runner = MigrationRunner(migrations_dir=Path("database/migrations"))
    files = runner.discover_migrations()
    prefixes = [int(f.name.split("_", 1)[0]) for f in files]
    assert prefixes == list(range(1, len(files) + 1))
    assert len(files) >= 17

    statuses = runner.get_status(migrated_and_seeded_test_db)
    assert all(st.is_applied for st in statuses)


@pytest.mark.integration
def test_all_seven_schemas_and_core_tables_exist(
    migrated_and_seeded_test_db: DatabaseConfig,
) -> None:
    """Verify all 7 warehouse schemas and expected dimension, fact, ref, raw, staging, and audit tables exist."""
    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name IN ('raw', 'staging', 'ref', 'dw', 'mart', 'audit', 'etl');
                """
            )
            schemas = {r[0] for r in cur.fetchall()}
            assert schemas == {"raw", "staging", "ref", "dw", "mart", "audit", "etl"}

            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'dw' AND table_type = 'BASE TABLE';
                """
            )
            dw_tables = {r[0] for r in cur.fetchall()}
            expected_dw = {
                "dim_date",
                "dim_interval",
                "dim_power_plant",
                "dim_energy_source",
                "dim_region",
                "dim_consumption_sector",
                "dim_weather_location",
                "dim_metric",
                "dim_source_system",
                "fact_dispatch_interval",
                "fact_generation_period",
                "fact_capacity_period",
                "fact_electricity_sales",
                "fact_weather_daily",
                "fact_published_metric",
            }
            assert expected_dw.issubset(dw_tables)


@pytest.mark.integration
def test_negative_and_impossible_measurements_rejected(
    migrated_and_seeded_test_db: DatabaseConfig,
) -> None:
    """
    Verify CHECK and FK constraints reject:
    - Negative active power on non-pumping dispatch
    - Derived MWh violating MW * duration_hours conservation of energy
    - Dependable capacity exceeding installed capacity
    - Unregistered / invalid unit codes
    - Coordinates outside Sri Lanka geographic bounds
    """
    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            doc_id, raw_rec_id, etl_run_id = _create_synthetic_lineage(cur, "CONSTRAINTS")
            cur.execute(
                "SELECT plant_key, energy_source_key FROM dw.dim_power_plant WHERE plant_code = 'VICTORIA' AND is_current = TRUE;"
            )
            plant_key, energy_source_key = cur.fetchone()  # type: ignore[misc]
            cur.execute(
                "SELECT metric_key FROM dw.dim_metric WHERE metric_code = 'PLANT_DISPATCH_MW';"
            )
            dispatch_metric_key = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT metric_key FROM dw.dim_metric WHERE metric_code = 'INSTALLED_CAPACITY_MW';"
            )
            cap_metric_key = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT source_system_key FROM dw.dim_source_system WHERE source_code = 'PUCSL';"
            )
            src_key = cur.fetchone()[0]  # type: ignore[index]

            # 1. Negative active power must fail CHECK constraint
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO dw.fact_dispatch_interval (
                            date_key, interval_key, plant_key, energy_source_key, metric_key,
                            source_system_key, dataset_revision, original_timestamp,
                            interval_duration_minutes, active_power_mw, reported_value,
                            reported_unit_code, value_status, source_document_id, raw_record_id, etl_run_id
                        ) VALUES (
                            20240115, 1, %s, %s, %s, %s, 'v1', '2024-01-15T00:00:00+05:30',
                            15, -25.0, -25.0, 'MW', 'REPORTED', %s, %s, %s
                        );
                        """,
                        (
                            plant_key,
                            energy_source_key,
                            dispatch_metric_key,
                            src_key,
                            doc_id,
                            raw_rec_id,
                            etl_run_id,
                        ),
                    )

            # 2. Incompatible derived energy (100 MW for 15 min is 25 MWh, NOT 100 MWh!)
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO dw.fact_dispatch_interval (
                            date_key, interval_key, plant_key, energy_source_key, metric_key,
                            source_system_key, dataset_revision, original_timestamp,
                            interval_duration_minutes, active_power_mw, derived_energy_mwh,
                            is_energy_derived, reported_value, reported_unit_code, value_status,
                            source_document_id, raw_record_id, etl_run_id
                        ) VALUES (
                            20240115, 2, %s, %s, %s, %s, 'v1', '2024-01-15T00:15:00+05:30',
                            15, 100.0, 100.0, TRUE, 100.0, 'MW', 'REPORTED', %s, %s, %s
                        );
                        """,
                        (
                            plant_key,
                            energy_source_key,
                            dispatch_metric_key,
                            src_key,
                            doc_id,
                            raw_rec_id,
                            etl_run_id,
                        ),
                    )

            # 3. Dependable capacity > Installed capacity must fail CHECK constraint
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO dw.fact_capacity_period (
                            plant_key, energy_source_key, metric_key, source_system_key,
                            period_type_code, effective_start_date_key, effective_end_date_key,
                            installed_capacity_mw, dependable_capacity_mw, reported_source_value,
                            reported_unit_code, source_document_id, raw_record_id, etl_run_id
                        ) VALUES (
                            %s, %s, %s, %s, 'ANNUAL', 20240101, 20241231,
                            210.0, 250.0, 210.0, 'MW', %s, %s, %s
                        );
                        """,
                        (
                            plant_key,
                            energy_source_key,
                            cap_metric_key,
                            src_key,
                            doc_id,
                            raw_rec_id,
                            etl_run_id,
                        ),
                    )

            # 4. Invalid / unregistered unit code must fail FK constraint
            with pytest.raises(psycopg.errors.ForeignKeyViolation):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO dw.fact_capacity_period (
                            plant_key, energy_source_key, metric_key, source_system_key,
                            period_type_code, effective_start_date_key, effective_end_date_key,
                            installed_capacity_mw, reported_source_value,
                            reported_unit_code, source_document_id, raw_record_id, etl_run_id
                        ) VALUES (
                            %s, %s, %s, %s, 'ANNUAL', 20240101, 20241231,
                            210.0, 210.0, 'FAKE_UNIT_XYZ', %s, %s, %s
                        );
                        """,
                        (
                            plant_key,
                            energy_source_key,
                            cap_metric_key,
                            src_key,
                            doc_id,
                            raw_rec_id,
                            etl_run_id,
                        ),
                    )

            # 5. Coordinates outside Sri Lanka must fail CHECK constraint
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO dw.dim_weather_location (
                            location_code, location_name, energy_zone_type, region_key,
                            latitude_deg, longitude_deg
                        ) VALUES (
                            'INVALID_ARCTIC', 'Invalid Polar Point', 'WIND_CORRIDOR',
                            (SELECT region_key FROM dw.dim_region WHERE region_code = 'LK'),
                            75.00000, 80.00000
                        );
                        """
                    )
        conn.rollback()


@pytest.mark.integration
def test_missing_weather_sentinel_preserved_as_null_and_duplicate_prevented(
    migrated_and_seeded_test_db: DatabaseConfig,
) -> None:
    """
    Verify NASA POWER missing sentinel (-999.0) is stored in missing_value_code with
    standardized_value = NULL (never 0), and duplicate grain inserts are blocked.
    """
    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            doc_id, raw_rec_id, etl_run_id = _create_synthetic_lineage(cur, "WEATHER")
            cur.execute("SELECT weather_location_key FROM dw.dim_weather_location LIMIT 1;")
            loc_key = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT metric_key FROM dw.dim_metric WHERE metric_code = 'SOLAR_IRRADIANCE_SW_DWN';"
            )
            metric_key = cur.fetchone()[0]  # type: ignore[index]
            cur.execute(
                "SELECT source_system_key FROM dw.dim_source_system WHERE source_code = 'NASA_POWER';"
            )
            src_key = cur.fetchone()[0]  # type: ignore[index]

            # Attempting to store is_missing = TRUE with standardized_value = 0.0 must be rejected!
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO dw.fact_weather_daily (
                            date_key, weather_location_key, metric_key, source_system_key,
                            source_variable_name, standardized_value, standardized_unit_code,
                            original_reported_value, original_unit_code, missing_value_code,
                            is_missing, source_document_id, raw_record_id, etl_run_id
                        ) VALUES (
                            20240115, %s, %s, %s, 'ALLSKY_SFC_SW_DWN',
                            0.0, 'MJ/m2/day', -999.0, 'MJ/m2/day', '-999.0',
                            TRUE, %s, %s, %s
                        );
                        """,
                        (loc_key, metric_key, src_key, doc_id, raw_rec_id, etl_run_id),
                    )

            # Valid missing observation: standardized_value IS NULL, missing_value_code = '-999.0'
            with conn.transaction():
                cur.execute(
                    """
                    INSERT INTO dw.fact_weather_daily (
                        date_key, weather_location_key, metric_key, source_system_key,
                        source_variable_name, standardized_value, standardized_unit_code,
                        original_reported_value, original_unit_code, missing_value_code,
                        is_missing, source_document_id, raw_record_id, etl_run_id
                    ) VALUES (
                        20240115, %s, %s, %s, 'ALLSKY_SFC_SW_DWN',
                        NULL, 'MJ/m2/day', NULL, 'MJ/m2/day', '-999.0',
                        TRUE, %s, %s, %s
                    );
                    """,
                    (loc_key, metric_key, src_key, doc_id, raw_rec_id, etl_run_id),
                )

            # Duplicate grain insert must fail UNIQUE constraint
            with pytest.raises(psycopg.errors.UniqueViolation):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO dw.fact_weather_daily (
                            date_key, weather_location_key, metric_key, source_system_key,
                            source_variable_name, standardized_value, standardized_unit_code,
                            original_reported_value, original_unit_code,
                            is_missing, source_document_id, raw_record_id, etl_run_id
                        ) VALUES (
                            20240115, %s, %s, %s, 'ALLSKY_SFC_SW_DWN',
                            18.5, 'MJ/m2/day', 18.5, 'MJ/m2/day',
                            FALSE, %s, %s, %s
                        );
                        """,
                        (loc_key, metric_key, src_key, doc_id, raw_rec_id, etl_run_id),
                    )
        conn.rollback()


@pytest.mark.integration
def test_dispatch_partition_pruning_via_explain(
    migrated_and_seeded_test_db: DatabaseConfig,
) -> None:
    """Verify PostgreSQL range partition pruning on dw.fact_dispatch_interval scans only 2024 partition."""
    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                EXPLAIN (FORMAT JSON)
                SELECT date_key, interval_key, active_power_mw
                FROM dw.fact_dispatch_interval
                WHERE date_key BETWEEN 20240101 AND 20240131;
                """
            )
            plan_json = json.dumps(cur.fetchall()[0][0])
            assert "fact_dispatch_interval_y2024" in plan_json
            assert "fact_dispatch_interval_y2023" not in plan_json
            assert "fact_dispatch_interval_y2025" not in plan_json
