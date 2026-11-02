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
