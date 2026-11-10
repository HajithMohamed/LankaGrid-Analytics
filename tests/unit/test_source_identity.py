"""
Unit tests for SourceDocumentIdentity and provenance tracking.
Following TDD protocol and .agents/rules/testing.md.
"""

from __future__ import annotations

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

        status, doc_id = SourceDocumentIdentity.check_existing_document(
            mock_cur, "PUCSL-DISPATCH-15MIN-2025-M01"
        )
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

    def test_canonical_factory_methods_match_across_pipeline(self) -> None:
        """Ensure NASA, CEB, and PUCSL canonical document codes never drift."""
        nasa_id = SourceDocumentIdentity.for_nasa_daily(2020, 2024)
        assert nasa_id.document_code == "NASA-POWER-DAILY-2020-2024"
        assert nasa_id.batch_code == "BATCH-NASA-POWER-DAILY-2020-2024-v1"

        ceb_id = SourceDocumentIdentity.for_ceb_digest(2025)
        assert ceb_id.document_code == "CEB-STAT-DIGEST-2025"

        pucsl_id = SourceDocumentIdentity.for_pucsl_dispatch("2025-M01")
        assert pucsl_id.document_code == "PUCSL-DISPATCH-15MIN-2025-M01"

    def test_infer_ceb_year_and_pucsl_period_from_filenames(self, tmp_path: Path) -> None:
        """Verify dynamic year and reporting period inference from filenames."""
        assert (
            SourceDocumentIdentity.infer_ceb_year_from_path(
                tmp_path / "ceb_statistical_digest_2025.pdf"
            )
            == 2025
        )
        assert (
            SourceDocumentIdentity.infer_ceb_year_from_path(
                tmp_path / "1751344341Statistical_Digest_2024.pdf"
            )
            == 2024
        )
        assert (
            SourceDocumentIdentity.infer_pucsl_period_from_filename(
                "15-Minutes-Report-31-Jan2025.xlsx"
            )
            == "2025-M01"
        )
        assert (
            SourceDocumentIdentity.infer_pucsl_period_from_filename("pucsl_dispatch_2024_04.xlsx")
            == "2024-M04"
        )

    def test_verify_file_checksum_and_duplicate_detection(self, tmp_path: Path) -> None:
        """Verify checksum verification and duplicate payload detection."""
        f = tmp_path / "payload.bin"
        f.write_bytes(b"verified-grid-telemetry")
        digest = SourceDocumentIdentity.compute_file_sha256(f)

        assert SourceDocumentIdentity.verify_file_checksum(f, digest) == (True, digest)
        assert SourceDocumentIdentity.verify_file_checksum(f, "0" * 64) == (False, digest)

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (99, "PUCSL-DISPATCH-15MIN-2024-M03")
        is_dup, dup_id, dup_code = SourceDocumentIdentity.check_duplicate_checksum(
            mock_cur,
            sha256_checksum=digest,
            exclude_document_code="PUCSL-DISPATCH-15MIN-2024-M04",
        )
        assert is_dup is True
        assert dup_id == 99
        assert dup_code == "PUCSL-DISPATCH-15MIN-2024-M03"
