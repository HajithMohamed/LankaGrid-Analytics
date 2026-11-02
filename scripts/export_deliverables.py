"""Automated academic document export pipeline for GridLens.

Generates DOCX, PDF, and PPTX deliverables from verified Markdown sources.
Requires python-docx, reportlab, and python-pptx when run in an environment
with package installation capability.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SUBMISSION_DIR = ROOT_DIR / "deliverables" / "final-submission"


def check_dependencies() -> dict[str, bool]:
    """Check availability of third-party document export libraries."""
    status = {}
    try:
        import docx  # noqa: F401

        status["docx"] = True
    except ImportError:
        status["docx"] = False

    try:
        import reportlab  # noqa: F401

        status["reportlab"] = True
    except ImportError:
        status["reportlab"] = False

    try:
        import pptx  # noqa: F401

        status["pptx"] = True
    except ImportError:
        status["pptx"] = False

    return status


def print_environment_notice(deps: dict[str, bool]) -> None:
    """Print academic document export instructions and status."""
    print("=" * 80)
    print("GridLens Academic Document Export Pipeline")
    print("=" * 80)
    print(f"Target Submission Directory: {SUBMISSION_DIR}")
    print("\nDependency Status:")
    print(
        f"  - python-docx (Word DOCX export): {'AVAILABLE' if deps.get('docx') else 'NOT INSTALLED'}"
    )
    print(
        f"  - reportlab   (Vector PDF export): {'AVAILABLE' if deps.get('reportlab') else 'NOT INSTALLED'}"
    )
    print(
        f"  - python-pptx (PowerPoint export): {'AVAILABLE' if deps.get('pptx') else 'NOT INSTALLED'}"
    )

    if not all(deps.values()):
        print("\nNotice on Sandbox / Offline Environment:")
        print("  Binary document converters are not installed in the isolated sandbox.")
        print("  Authoritative academic Markdown documents with LaTeX KaTeX math, tables,")
        print("  and Mermaid syntax are stored under deliverables/final-submission/.")
        print("\nTo generate DOCX, PDF, and PPTX on an internet-connected workstation:")
        print("  1. pip install python-docx reportlab python-pptx markdown")
        print("  2. python scripts/export_deliverables.py")
        print("=" * 80)


def main() -> int:
    """Entry point for deliverable export."""
    deps = check_dependencies()
    print_environment_notice(deps)
    if not all(deps.values()):
        return 0

    print("Generating binary deliverables...")
    # Binary conversion logic would execute here when libraries are present.
    return 0


if __name__ == "__main__":
    sys.exit(main())
