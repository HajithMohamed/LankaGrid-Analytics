"""
Unit tests for SourceDocumentIdentity and provenance tracking.
Following TDD protocol and .agents/rules/testing.md.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.common.source_identity import DocumentSyncStatus, SourceDocumentIdentity


@pytest.mark.unit
class TestSourceDocumentIdentity:
    """Test suite for SourceDocumentIdentity behavior."""

    def test_create_canonical_identity(self) -> None:
        """Verify normalization, document code, and batch code construction."""
        ident = SourceDocumentIdentity.create(
            source_code="pucsl",
            dataset_type="dispatch_15min",
            reporting_period="2024-M03",
            revision="v1",
        )

        assert ident.source_code == "PUCSL"
        assert ident.dataset_type == "DISPATCH_15MIN"
        assert ident.reporting_period == "2024-M03"
        assert ident.document_code == "PUCSL-DISPATCH-15MIN-2024-M03"
        assert ident.revision == "v1"
        assert ident.batch_code == "BATCH-PUCSL-DISPATCH-15MIN-2024-M03-v1"

    def test_compute_file_sha256(self, tmp_path: Path) -> None:
        """Ensure streaming SHA-256 matches exact hash of content."""
        sample_file = tmp_path / "test.txt"
        sample_file.write_bytes(b"Sri Lanka National Electricity Grid Analytics")

        import hashlib

        expected = hashlib.sha256(b"Sri Lanka National Electricity Grid Analytics").hexdigest()
        assert SourceDocumentIdentity.compute_file_sha256(sample_file) == expected

    def test_check_existing_document_new(self) -> None:
        """Verify check_existing_document returns NEW when no record exists in database."""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = None

        status, doc_id = SourceDocumentIdentity.check_existing_document(mock_cur, "PUCSL-DISPATCH-15MIN-2025-M01")
        assert status == DocumentSyncStatus.NEW
        assert doc_id is None

    def test_check_existing_document_unchanged(self) -> None:
        """Verify check_existing_document returns UNCHANGED when hashes match."""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (42, "abc123sha", "v1")

        status, doc_id = SourceDocumentIdentity.check_existing_document(
            mock_cur, "PUCSL-DISPATCH-15MIN-2024-M03", sha256_checksum="abc123sha"
        )
        assert status == DocumentSyncStatus.UNCHANGED
        assert doc_id == 42

    def test_check_existing_document_revised(self) -> None:
        """Verify check_existing_document returns REVISED when hashes differ."""
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (42, "oldhash123", "v1")

        status, doc_id = SourceDocumentIdentity.check_existing_document(
            mock_cur, "PUCSL-DISPATCH-15MIN-2024-M03", sha256_checksum="newhash456"
        )
        assert status == DocumentSyncStatus.REVISED
        assert doc_id == 42
