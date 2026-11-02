"""Unit tests for Mermaid architecture diagrams syntax and schema object consistency."""

from __future__ import annotations

import re
from pathlib import Path

DIAGRAMS_DIR = Path("docs/diagrams")
EXPECTED_DIAGRAMS = [
    "system-architecture.mmd",
    "fact-constellation.mmd",
    "etl-workflow.mmd",
    "schema-architecture.mmd",
    "advanced-database-workflow.mmd",
    "analytical-query-architecture.mmd",
]

OBSOLETE_PATTERNS = [
    r"stg_pucsl",
    r"stg_ceb",
    r"stg_nasa",
    r"power_station_lookup",
    r"sp_load_dispatch_facts",
    r"sp_load_sales_facts",
    r"sp_load_weather_facts",
    r"billed_energy_gwh",
    r"published_metric_fact_id",
]


def test_all_expected_diagrams_exist() -> None:
    """Verify that all six core Mermaid diagrams exist."""
    assert DIAGRAMS_DIR.exists(), f"Directory {DIAGRAMS_DIR} must exist"
    for diag_name in EXPECTED_DIAGRAMS:
        diag_path = DIAGRAMS_DIR / diag_name
        assert diag_path.exists(), f"Diagram {diag_name} must exist"
        content = diag_path.read_text(encoding="utf-8")
        assert len(content.strip()) > 50, f"Diagram {diag_name} must not be empty"


def test_diagram_flowchart_and_block_balance() -> None:
    """Verify that each diagram starts with a valid flowchart header and has balanced subgraphs."""
    for diag_name in EXPECTED_DIAGRAMS:
        content = (DIAGRAMS_DIR / diag_name).read_text(encoding="utf-8")
        lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.strip().startswith("%%")
        ]
        assert len(lines) > 0, f"{diag_name} has no non-comment lines"
        assert lines[0] in ("flowchart TD", "flowchart LR"), (
            f"{diag_name} must start with flowchart TD/LR"
        )

        # Check balanced subgraphs and end statements
        subgraph_count = sum(1 for line in lines if line.startswith("subgraph "))
        end_count = sum(1 for line in lines if line == "end")
        assert subgraph_count == end_count, (
            f"{diag_name} has mismatched subgraphs ({subgraph_count}) vs end ({end_count})"
        )


def test_diagrams_free_of_obsolete_identifiers() -> None:
    """Verify that no obsolete schema or column names exist in any diagram."""
    for diag_name in EXPECTED_DIAGRAMS:
        content = (DIAGRAMS_DIR / diag_name).read_text(encoding="utf-8")
        for pattern in OBSOLETE_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            assert match is None, f"{diag_name} contains obsolete identifier matching '{pattern}'"
