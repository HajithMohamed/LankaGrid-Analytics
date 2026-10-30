"""
Phase 1 TDD Integration Tests for Idempotent Reference Seeding and Zero-Fabrication Policy.
"""
from __future__ import annotations

import pytest

from scripts.seed_reference import ReferenceSeeder
from src.common.config import DatabaseConfig
from src.common.db import get_connection

SEEDED_TABLES: tuple[str, ...] = (
    "ref.unit",
    "ref.unit_conversion",
    "ref.reporting_period_type",
    "ref.energy_source_mapping",
    "ref.plant_alias",
    "ref.region_alias",
    "ref.metric_mapping",
    "ref.data_quality_rule",
    "ref.source_precedence",
    "raw.source_system",
    "dw.dim_date",
    "dw.dim_interval",
    "dw.dim_source_system",
    "dw.dim_energy_source",
    "dw.dim_region",
    "dw.dim_consumption_sector",
    "dw.dim_power_plant",
    "dw.dim_weather_location",
    "dw.dim_metric",
)

WAREHOUSE_FACT_TABLES: tuple[str, ...] = (
    "dw.fact_dispatch_interval",
    "dw.fact_generation_period",
    "dw.fact_capacity_period",
    "dw.fact_electricity_sales",
    "dw.fact_weather_daily",
    "dw.fact_published_metric",
)


@pytest.mark.integration
def test_reference_seeding_idempotency_and_zero_fabricated_facts(
    migrated_and_seeded_test_db: DatabaseConfig,
) -> None:
    """
    Verify:
    1. Every reference and conformed dimension table is populated with verified metadata.
    2. Re-executing ReferenceSeeder.seed_all() produces identical row counts (zero duplicates).
    3. All 6 warehouse fact tables contain 0 rows after seeding (no fabricated measurements).
    """
    seeder = ReferenceSeeder()

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            counts_before: dict[str, int] = {}
            for tbl in SEEDED_TABLES:
                cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                cnt = int(cur.fetchone()[0])  # type: ignore[index]
                assert cnt > 0, f"Expected seeded rows in {tbl}, found 0"
                counts_before[tbl] = cnt

            for fact_tbl in WAREHOUSE_FACT_TABLES:
                cur.execute(f"SELECT COUNT(*) FROM {fact_tbl};")
                fact_cnt = int(cur.fetchone()[0])  # type: ignore[index]
                assert fact_cnt == 0, f"Fact table {fact_tbl} must have 0 rows after seeding, got {fact_cnt}"

    # Re-run seed_all() to prove strict idempotency
    seeder.seed_all(migrated_and_seeded_test_db)

    with get_connection(migrated_and_seeded_test_db) as conn:
        with conn.cursor() as cur:
            for tbl in SEEDED_TABLES:
                cur.execute(f"SELECT COUNT(*) FROM {tbl};")
                cnt_after = int(cur.fetchone()[0])  # type: ignore[index]
                assert cnt_after == counts_before[tbl], (
                    f"Non-idempotent seed detected on {tbl}: "
                    f"before={counts_before[tbl]}, after={cnt_after}"
                )

