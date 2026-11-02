"""
Automated unit tests for GridLens Next.js Light-Mode Analytics Dashboard Integrity.
Verifies all 24 query snapshots, query registry coverage, and unit integrity rules.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SNAPSHOT_DIR = REPO_ROOT / "web" / "public" / "data" / "snapshots"
SQL_DIR = REPO_ROOT / "database" / "queries" / "phase3"


def test_all_24_query_snapshots_exist_and_are_valid():
    """Verify that all 24 queries (Q01-Q24) have valid snapshot JSON files."""
    assert SNAPSHOT_DIR.exists(), f"Snapshot directory {SNAPSHOT_DIR} does not exist"

    for i in range(1, 25):
        query_id = f"Q{i:02d}"
        json_path = SNAPSHOT_DIR / f"{query_id}.json"
        csv_path = SNAPSHOT_DIR / f"{query_id}.csv"

        assert json_path.exists(), f"Snapshot JSON missing for {query_id}"
        assert csv_path.exists(), f"Snapshot CSV missing for {query_id}"

        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, list), f"{query_id}.json should contain a JSON array"
            assert len(data) > 0, f"{query_id}.json should not be empty"


def test_all_24_sql_files_exist():
    """Verify that all 24 SQL files are present in their corresponding member folders."""
    member_dirs = [
        "member_01_generation",
        "member_02_dispatch",
        "member_03_sales",
        "member_04_weather",
        "member_05_plant_operations",
        "member_06_grid_efficiency",
    ]

    for i in range(1, 25):
        query_id = f"Q{i:02d}"
        member_idx = (i - 1) // 4
        member_dir = member_dirs[member_idx]
        sql_path = SQL_DIR / member_dir / f"{query_id}.sql"

        assert sql_path.exists(), f"SQL file missing for {query_id} at {sql_path}"
        with open(sql_path, encoding="utf-8") as f:
            sql_content = f.read().strip()
            assert len(sql_content) > 20, f"SQL file for {query_id} appears empty or trivial"
            assert "SELECT" in sql_content.upper(), (
                f"SQL file for {query_id} must contain SELECT statement"
            )


def test_snapshot_loader_covers_provenance():
    """Verify execution summary snapshot records total execution metrics."""
    summary_path = SNAPSHOT_DIR / "execution_summary.json"
    assert summary_path.exists(), "execution_summary.json snapshot missing"

    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)
        assert isinstance(summary, list), (
            "execution_summary.json must contain a list of query execution records"
        )
        assert len(summary) == 24, "execution_summary.json must contain exactly 24 query records"
        for record in summary:
            assert "query_id" in record
            assert "execution_time_ms" in record
            assert "row_count" in record


def test_security_zero_hardcoded_credentials_in_web():
    """Verify web client pool has no hardcoded database passwords."""
    client_path = REPO_ROOT / "web" / "src" / "lib" / "db" / "client.ts"
    assert client_path.exists(), f"client.ts not found at {client_path}"

    with open(client_path, encoding="utf-8") as f:
        content = f.read()

    # Disallow fallback password assignments
    assert "HAzi@" not in content, "Exposed credential signature detected in client.ts"
    assert 'password: process.env.POSTGRES_PASSWORD || "' not in content, (
        "Hardcoded fallback password string detected in client.ts"
    )

    env_example = REPO_ROOT / "web" / ".env.example"
    assert env_example.exists(), "web/.env.example must exist"
    with open(env_example, encoding="utf-8") as f:
        example_content = f.read()
    assert "HAzi@" not in example_content, "Exposed password in .env.example"
    assert "grid_analyst" in example_content, "web/.env.example must specify grid_analyst"


def test_q06_ramp_rate_accuracy():
    """Verify authoritative Q06 maximum upward ramp rate is 141.00 MW on March 17, 2024 at 18:30."""
    q06_path = SNAPSHOT_DIR / "Q06.json"
    with open(q06_path, encoding="utf-8") as f:
        q06_records = json.load(f)

    assert len(q06_records) > 0
    top_event = q06_records[0]
    assert top_event["calendar_date"] == "2024-03-17"
    assert top_event["start_time"] == "18:30:00"
    assert top_event["ramp_rate_mw"] == 141.0, (
        "Q06 peak ramp must be 141.00 MW (previous 142.50 MW was invalid hardcoding)"
    )
    assert top_event["severity_rank"] == 1


def test_q22_multi_tier_reconciliation_accuracy():
    """Verify Q22 reconciles CEB sales and PUCSL dispatch without unsupported claims."""
    q22_path = SNAPSHOT_DIR / "Q22.json"
    with open(q22_path, encoding="utf-8") as f:
        q22_records = json.load(f)

    tiers = [r["reconciliation_tier"] for r in q22_records]
    assert "CEB_SALES_DIGEST_ANNUAL" in tiers
    assert "PUCSL_DISPATCH_TELEMETRY_DAILY" in tiers

    # Check rounding precision reconciliation for CEB sales (variance <= 0.05%)
    ceb_recons = [r for r in q22_records if r["reconciliation_tier"] == "CEB_SALES_DIGEST_ANNUAL"]
    assert len(ceb_recons) >= 5
    for r in ceb_recons:
        assert float(r["variance_pct"]) <= 0.05, f"CEB sales variance exceeded precision: {r}"


def test_dashboard_security_migration_022_exists():
    """Verify migration 022 applies read-only grid_analyst safeguards."""
    migration_path = (
        REPO_ROOT / "database" / "migrations" / "022_dashboard_readonly_role_and_security.sql"
    )
    rollback_path = (
        REPO_ROOT
        / "database"
        / "migrations"
        / "rollbacks"
        / "022_dashboard_readonly_role_and_security_rollback.sql"
    )
    assert migration_path.exists(), "Migration 022 missing"
    assert rollback_path.exists(), "Migration 022 rollback missing"

    with open(migration_path, encoding="utf-8") as f:
        sql_text = f.read()

    assert "grid_analyst" in sql_text
    assert "statement_timeout" in sql_text
    assert "default_transaction_read_only" in sql_text
