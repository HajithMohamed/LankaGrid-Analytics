"""
Phase 1 TDD Integration Tests for Advanced PostgreSQL 18 Objects:
- SQL / PLpgSQL Functions (unit conversion, period validation, 15m interval normalization, YoY, DQ summary)
- Stored Procedures (ETL run lifecycle, staged generation validation, approved alias check, fact load, reconciliation, MV refresh)
- Triggers (updated_at, verification evidence guard on ref.plant_alias, resolution audit guard on audit.data_quality_issue)
- Views & Materialized Views (grain separation, revision deduplication, no double counting between operational and published facts)
- Least-Privilege Database Roles (grid_analyst read-only enforcement, grid_etl restricted from DDL/TRUNCATE)
"""
from __future__ import annotations

import os
from decimal import Decimal

import psycopg
import pytest

from src.common.config import DatabaseConfig
from src.common.db import get_connection
from tests.integration.test_phase1_schema_and_constraints import _create_synthetic_lineage


@pytest.mark.integration
def test_plpgsql_functions_contracts(migrated_and_seeded_test_db: DatabaseConfig) -> None:
    """Verify safe unit conversion, reporting period validation, 15m normalization, and YoY functions."""
    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # 1. GWh -> MWh = * 1000
            cur.execute("SELECT etl.fn_convert_unit(1.5, 'GWh', 'MWh', NULL);")
            assert cur.fetchone()[0] == Decimal("1500.000000")  # type: ignore[index]

            # 2. NULL input preserved as NULL (never 0)
            cur.execute("SELECT etl.fn_convert_unit(NULL, 'GWh', 'MWh', NULL);")
            assert cur.fetchone()[0] is None  # type: ignore[index]

            # 3. MW -> MWh requires explicit interval_hours (e.g. 0.25h for 15-min dispatch)
            cur.execute("SELECT etl.fn_convert_unit(200.0, 'MW', 'MWh', 0.25);")
            assert cur.fetchone()[0] == Decimal("50.000000")  # type: ignore[index]

            # 4. MW -> MWh without interval_hours MUST raise InvalidParameterValue
            with pytest.raises(psycopg.errors.InvalidParameterValue):
                with conn.transaction():
                    cur.execute("SELECT etl.fn_convert_unit(200.0, 'MW', 'MWh', NULL);")

            # 5. Reporting period validation
            cur.execute("SELECT etl.fn_validate_reporting_period('DAILY', DATE '2024-01-15', DATE '2024-01-15');")
            assert cur.fetchone()[0] is True  # type: ignore[index]
            cur.execute("SELECT etl.fn_validate_reporting_period('DAILY', DATE '2024-01-01', DATE '2024-12-31');")
            assert cur.fetchone()[0] is False  # type: ignore[index]
            cur.execute("SELECT etl.fn_validate_reporting_period('MONTHLY', DATE '2024-02-01', DATE '2024-02-29');")
            assert cur.fetchone()[0] is True  # type: ignore[index]
            cur.execute("SELECT etl.fn_validate_reporting_period('ANNUAL', DATE '2024-01-01', DATE '2024-12-31');")
            assert cur.fetchone()[0] is True  # type: ignore[index]

            # 6. 15-minute interval normalization in Asia/Colombo (+05:30)
            # 13:35 UTC = 19:05 Asia/Colombo -> slot 77 (19:00), PEAK block
            cur.execute("SELECT colombo_date, date_key, interval_index, tariff_block FROM etl.fn_normalize_interval_15min('2024-01-15T13:35:00Z'::timestamptz);")
            norm_row = cur.fetchone()
            assert norm_row is not None
            assert norm_row[1] == 20240115
            assert norm_row[2] == 77
            assert norm_row[3] == "PEAK"

            # 7. YoY percentage change calculation
            cur.execute("SELECT etl.fn_calculate_yoy_change(1100.0, 1000.0);")
            assert cur.fetchone()[0] == Decimal("10.0000")  # type: ignore[index]
            cur.execute("SELECT etl.fn_calculate_yoy_change(1100.0, 0.0);")
            assert cur.fetchone()[0] is None  # type: ignore[index]


@pytest.mark.integration
def test_triggers_guard_alias_evidence_and_dq_resolution(
    migrated_and_seeded_test_db: DatabaseConfig,
) -> None:
    """
    Verify:
    - ref.plant_alias blocks VERIFIED status when verification_evidence is missing/blank.
    - audit.data_quality_issue blocks 'corrected' / 'accepted' status without resolved_by & justification,
      and auto-populates resolved_at when provided.
    """
    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            # 1. Unverified plant merge attempt without evidence must fail trigger check
            with pytest.raises(psycopg.errors.RaiseException):
                with conn.transaction():
                    cur.execute(
                        """
                        INSERT INTO ref.plant_alias (
                            source_code, alias_name, canonical_plant_code,
                            verification_status, verification_evidence
                        ) VALUES ('PUCSL', 'Unproven Mystery Station', 'VICTORIA', 'VERIFIED', '');
                        """
                    )

            # 2. PENDING_EVIDENCE is permitted while awaiting verification
            with conn.transaction():
                cur.execute(
                    """
                    INSERT INTO ref.plant_alias (
                        source_code, alias_name, canonical_plant_code,
                        verification_status, verification_evidence
                    ) VALUES ('PUCSL', 'Candidate Station Variant', 'VICTORIA', 'PENDING_EVIDENCE', NULL)
                    RETURNING alias_id, updated_at;
                    """
                )
                alias_id, initial_ts = cur.fetchone()  # type: ignore[misc]
                assert alias_id is not None
                assert initial_ts is not None

            # 3. DQ issue resolution trigger
            doc_id, raw_rec_id, etl_run_id = _create_synthetic_lineage(cur, "TRIGGERS")
            with conn.transaction():
                cur.execute(
                    """
                    INSERT INTO audit.data_quality_issue (
                        etl_run_id, source_document_id, raw_record_id,
                        staging_table_name, staging_record_ref, rule_code,
                        issue_classification, severity, original_value, issue_status
                    ) VALUES (
                        %s, %s, %s, 'staging.stg_generation_report', 'stg_id=1',
                        'DQ_GEN_MISSING_ENERGY', 'MISSING_VALUE', 'ERROR', 'N/A', 'unresolved'
                    ) RETURNING issue_id;
                    """,
                    (etl_run_id, doc_id, raw_rec_id),
                )
                issue_id = cur.fetchone()[0]  # type: ignore[index]

            # Resolving without justification must fail trigger
            with pytest.raises(psycopg.errors.RaiseException):
                with conn.transaction():
                    cur.execute(
                        "UPDATE audit.data_quality_issue SET issue_status = 'accepted' WHERE issue_id = %s;",
                        (issue_id,),
                    )

            # Resolving with reviewer and justification succeeds and sets resolved_at
            with conn.transaction():
                cur.execute(
                    """
                    UPDATE audit.data_quality_issue
                    SET issue_status = 'quarantined'
                    WHERE issue_id = %s;
                    """,
                    (issue_id,),
                )
                cur.execute(
                    """
                    UPDATE audit.data_quality_issue
                    SET issue_status = 'accepted',
                        resolved_by = 'qa_engineer_1',
                        resolution_justification = 'Confirmed plant offline for scheduled maintenance; NULL retained.'
                    WHERE issue_id = %s
                    RETURNING resolved_at;
                    """,
                    (issue_id,),
                )
                resolved_at = cur.fetchone()[0]  # type: ignore[index]
                assert resolved_at is not None

        conn.rollback()


@pytest.mark.integration
def test_procedures_views_mvs_reconciliation_and_no_double_counting(
    migrated_and_seeded_test_db: DatabaseConfig,
) -> None:
    """
    Exercise:
    - Staging -> Validation Procedure -> Fact Load Procedure -> Revision Superseding -> MV Concurrent Refresh
    - Reconciliation procedure detecting conflicting source values
    - Analytical views preventing double-counting across revisions (v1 vs v2), granularities (DAILY vs MONTHLY),
      and published summaries (fact_published_metric kept strictly separate from fact_generation_period).
    """
    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            doc_id, raw_rec_id, _ = _create_synthetic_lineage(cur, "PROC_MV")
            cur.execute("SELECT batch_id FROM raw.extracted_record WHERE raw_record_id = %s;", (raw_rec_id,))
            batch_id = int(cur.fetchone()[0])  # type: ignore[index]

            # Start ETL run via stored procedure
            cur.execute(
                "CALL etl.sp_start_etl_run('test_gen_load', 'dw', 'fact_generation_period', %s, %s, NULL);",
                (doc_id, batch_id),
            )
            etl_run_id = int(cur.fetchone()[0])  # type: ignore[index]

            # Stage 1 valid daily row (v1), 1 valid monthly row (v1), and 1 invalid negative row
            cur.execute(
                """
                INSERT INTO staging.stg_generation_report (
                    batch_id, source_document_id, raw_record_id, source_code,
                    raw_plant_name, period_type_code, period_start_date, period_end_date,
                    raw_generation_text, parsed_generation_value, reported_unit_code,
                    generation_boundary, dataset_revision
                ) VALUES
                (%s, %s, %s, 'PUCSL', 'Victoria', 'DAILY', DATE '2024-01-15', DATE '2024-01-15', '1200.0', 1200.0, 'MWh', 'GROSS', 'v1'),
                (%s, %s, %s, 'CEB', 'Victoria', 'MONTHLY', DATE '2024-01-01', DATE '2024-01-31', '35.0', 35.0, 'GWh', 'GROSS', 'v1'),
                (%s, %s, %s, 'PUCSL', 'Victoria', 'DAILY', DATE '2024-01-16', DATE '2024-01-16', '-50.0', -50.0, 'MWh', 'GROSS', 'v1');
                """,
                (batch_id, doc_id, raw_rec_id, batch_id, doc_id, raw_rec_id, batch_id, doc_id, raw_rec_id),
            )

            # Validate staged rows
            cur.execute(
                "CALL etl.sp_validate_staged_generation(%s, %s, 0, 0);",
                (batch_id, etl_run_id),
            )
            valid_cnt, quar_cnt = cur.fetchone()  # type: ignore[misc]
            assert valid_cnt == 2
            assert quar_cnt == 1

            # Load approved valid rows into dw.fact_generation_period
            cur.execute(
                "CALL etl.sp_load_generation_period(%s, %s, 0, 0);",
                (batch_id, etl_run_id),
            )
            ins_cnt, upd_cnt = cur.fetchone()  # type: ignore[misc]
            assert ins_cnt == 2
            assert upd_cnt == 0

            # Now stage a revised v2 for 2024-01-15 DAILY (1250.0 MWh replacing 1200.0 MWh as current revision)
            cur.execute(
                """
                INSERT INTO staging.stg_generation_report (
                    batch_id, source_document_id, raw_record_id, source_code,
                    raw_plant_name, period_type_code, period_start_date, period_end_date,
                    raw_generation_text, parsed_generation_value, reported_unit_code,
                    generation_boundary, dataset_revision, validation_status
                ) VALUES
                (%s, %s, %s, 'PUCSL', 'Victoria', 'DAILY', DATE '2024-01-15', DATE '2024-01-15', '1250.0', 1250.0, 'MWh', 'GROSS', 'v2', 'valid');
                """,
                (batch_id, doc_id, raw_rec_id),
            )
            cur.execute(
                "CALL etl.sp_load_generation_period(%s, %s, 0, 0);",
                (batch_id, etl_run_id),
            )

            # Insert an official published aggregate into dw.fact_published_metric for Jan 2024
            # to verify mart views NEVER double-count fact_published_metric with fact_generation_period!
            cur.execute(
                """
                INSERT INTO dw.fact_published_metric (
                    metric_key, period_type_code, period_start_date_key, period_end_date_key,
                    region_key, energy_source_key, source_system_key, dataset_revision,
                    standardized_value, standardized_unit_code, published_value, published_unit_code,
                    value_nature, source_document_id, raw_record_id, etl_run_id
                ) VALUES (
                    (SELECT metric_key FROM dw.dim_metric WHERE metric_code = 'GROSS_GENERATION_MWH'),
                    'MONTHLY', 20240101, 20240131,
                    (SELECT region_key FROM dw.dim_region WHERE region_code = 'LK'),
                    (SELECT energy_source_key FROM dw.dim_energy_source WHERE energy_source_code = 'MAJOR_HYDRO'),
                    (SELECT source_system_key FROM dw.dim_source_system WHERE source_code = 'CEB'),
                    'v1', 35000.0, 'MWh', 35.0, 'GWh', 'AUDITED_FINAL', %s, %s, %s
                );
                """,
                (doc_id, raw_rec_id, etl_run_id),
            )

            # Check mart.vw_generation_by_energy_source:
            # - DAILY total for 2024-01 must be 1250.0 MWh (ONLY v2, NOT 1200 + 1250 = 2450!)
            # - MONTHLY total for 2024-01 must be 35000.0 MWh (35 GWh converted to MWh, kept separate from DAILY and NOT doubled to 70000 by fact_published_metric!)
            cur.execute(
                """
                SELECT period_type_code, total_generation_mwh
                FROM mart.vw_generation_by_energy_source
                WHERE calendar_year = 2024 AND month_number = 1 AND energy_source_code = 'MAJOR_HYDRO'
                ORDER BY period_type_code;
                """
            )
            rows = cur.fetchall()
            by_period = {r[0]: Decimal(str(r[1])) for r in rows}
            assert by_period["DAILY"] == Decimal("1250.0000")
            assert by_period["MONTHLY"] == Decimal("35000.0000")

            # Record a cross-source reconciliation conflict (> 2% variance)
            cur.execute(
                """
                CALL etl.sp_record_reconciliation_case(
                    %s, 'GROSS_GENERATION_MWH', 'MONTHLY',
                    DATE '2024-01-01', DATE '2024-01-31',
                    'MAJOR_HYDRO', 'MWh',
                    'CEB', 35000.0, 'PUCSL', 33800.0, 1.5, NULL
                );
                """,
                (etl_run_id,),
            )
            recon_id = cur.fetchone()[0]  # type: ignore[index]
            assert recon_id is not None

            cur.execute("SELECT reconciliation_status FROM mart.vw_conflicting_source_metrics WHERE reconciliation_id = %s;", (recon_id,))
            assert cur.fetchone()[0] == "CONFLICT_FLAGGED"  # type: ignore[index]

            # Finalize ETL run
            cur.execute(
                "CALL etl.sp_finalize_etl_run(%s, 'PARTIAL_QUARANTINE', 3, 2, 0, 1, NULL);",
                (etl_run_id,),
            )

            # Check DQ summary view
            cur.execute("SELECT SUM(issue_count) FROM audit.data_quality_summary WHERE etl_run_id = %s;", (etl_run_id,))
            assert int(cur.fetchone()[0]) >= 1  # type: ignore[index]

        # Commit temporarily to exercise CONCURRENT materialized view refresh (which cannot run inside a dirty tx block with uncommitted DDL, or runs cleanly on committed data), then clean up synthetic records!
        conn.commit()
        try:
            with get_connection(migrated_and_seeded_test_db, autocommit=True) as ac_conn:
                with ac_conn.cursor() as ac_cur:
                    ac_cur.execute("CALL etl.sp_refresh_mart_views(TRUE);")
                    ac_cur.execute(
                        """
                        SELECT total_generation_mwh
                        FROM mart.mv_monthly_generation_summary
                        WHERE calendar_year = 2024 AND month_number = 1
                          AND energy_source_code = 'MAJOR_HYDRO'
                          AND period_type_code = 'MONTHLY';
                        """
                    )
                    mv_val = ac_cur.fetchone()
                    assert mv_val is not None
                    assert Decimal(str(mv_val[0])) == Decimal("35000.0000")
        finally:
            with get_connection(migrated_and_seeded_test_db, autocommit=True) as cleanup_conn:
                with cleanup_conn.cursor() as c_cur:
                    c_cur.execute("DELETE FROM audit.record_lineage WHERE source_document_id = %s;", (doc_id,))
                    c_cur.execute("DELETE FROM audit.reconciliation_case WHERE etl_run_id = %s;", (etl_run_id,))
                    c_cur.execute("DELETE FROM audit.data_quality_issue WHERE source_document_id = %s;", (doc_id,))
                    c_cur.execute("DELETE FROM dw.fact_published_metric WHERE source_document_id = %s;", (doc_id,))
                    c_cur.execute("DELETE FROM dw.fact_generation_period WHERE source_document_id = %s;", (doc_id,))
                    c_cur.execute("DELETE FROM staging.stg_generation_report WHERE source_document_id = %s;", (doc_id,))
                    c_cur.execute("DELETE FROM audit.etl_run WHERE source_document_id = %s;", (doc_id,))
                    c_cur.execute("DELETE FROM raw.extracted_record WHERE source_document_id = %s;", (doc_id,))
                    c_cur.execute("DELETE FROM raw.ingestion_batch WHERE source_document_id = %s;", (doc_id,))
                    c_cur.execute("DELETE FROM raw.source_document WHERE source_document_id = %s;", (doc_id,))
                    c_cur.execute("CALL etl.sp_refresh_mart_views(TRUE);")


@pytest.mark.integration
def test_least_privilege_database_roles(migrated_and_seeded_test_db: DatabaseConfig) -> None:
    """
    Verify:
    - grid_analyst can SELECT from dw.* and mart.*, but CANNOT INSERT/UPDATE/DELETE on dw.fact_* or staging.*.
    - grid_etl can read/insert staging and call ETL procedures, but CANNOT DROP warehouse tables.
    """
    analyst_pw = os.getenv("POSTGRES_ANALYST_PASSWORD")
    if analyst_pw:
        analyst_cfg = migrated_and_seeded_test_db.with_credentials(
            os.getenv("POSTGRES_ANALYST_USER", "grid_analyst"),
            analyst_pw,
        )
        with get_connection(analyst_cfg) as a_conn:
            with a_conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM dw.dim_energy_source;")
                assert int(cur.fetchone()[0]) >= 7  # type: ignore[index]

                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with a_conn.transaction():
                        cur.execute("DELETE FROM dw.dim_energy_source;")

    # Also test via SET ROLE on admin session so test works even without password env vars
    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            cur.execute("SET ROLE grid_analyst;")
            cur.execute("SELECT COUNT(*) FROM mart.vw_generation_by_energy_source;")
            assert cur.fetchone() is not None
            cur.execute("SELECT COUNT(*) FROM mart.mv_monthly_generation_summary;")
            assert cur.fetchone() is not None

            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    cur.execute("SET LOCAL ROLE grid_analyst;")
                    cur.execute("DELETE FROM dw.fact_generation_period;")

            cur.execute("RESET ROLE;")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    cur.execute("SET LOCAL ROLE grid_etl;")
                    cur.execute("DROP TABLE dw.fact_capacity_period;")
            cur.execute("RESET ROLE;")
        conn.rollback()
