"""
GridLens — Centralized Source Document Identity & Provenance Registry.

Provides consistent, deterministic document codes, batch identifiers, and
provenance hashing across acquisition, staging, and dimensional ETL pipelines.
"""

from __future__ import annotations

import enum
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycopg import Cursor


class DocumentSyncStatus(enum.StrEnum):
    """Categorization of source document relative to warehouse state."""

    NEW = "NEW"
    UNCHANGED = "UNCHANGED"
    REVISED = "REVISED"


@dataclass(frozen=True)
class SourceDocumentIdentity:
    """Canonical identifier for an official grid or meteorological source document."""

    source_code: str  # e.g., 'PUCSL', 'CEB', 'NASA_POWER'
    dataset_type: str  # e.g., 'DISPATCH_15MIN', 'SALES_ANNUAL', 'WEATHER_DAILY', 'GEN_DAILY'
    reporting_period: str  # e.g., '2024-M03', '2024', '2024-03-31', '2020-2024'
    document_code: str  # e.g., 'PUCSL-DISPATCH-15MIN-2024-M03'
    revision: str = "v1"
    sha256_checksum: str | None = None
    original_filename: str | None = None
    source_url: str | None = None

    @classmethod
    def create(
        cls,
        source_code: str,
        dataset_type: str,
        reporting_period: str,
        revision: str = "v1",
        sha256_checksum: str | None = None,
        original_filename: str | None = None,
        source_url: str | None = None,
    ) -> SourceDocumentIdentity:
        """Construct canonical identity ensuring clean formatting and naming."""
        clean_source = re.sub(r"[^A-Za-z0-9_-]", "-", source_code.strip()).upper()
        clean_type = re.sub(r"[^A-Za-z0-9_-]", "-", dataset_type.strip()).upper()
        clean_period = re.sub(r"[^A-Za-z0-9_-]", "-", reporting_period.strip()).upper()
        clean_rev = revision.strip().lower()

        doc_source = clean_source.replace("_", "-")
        doc_type = clean_type.replace("_", "-")
        doc_period = clean_period.replace("_", "-")
        doc_code = f"{doc_source}-{doc_type}-{doc_period}"
        doc_code = re.sub(r"-+", "-", doc_code).strip("-")
        return cls(
            source_code=clean_source,
            dataset_type=clean_type,
            reporting_period=clean_period,
            document_code=doc_code,
            revision=clean_rev,
            sha256_checksum=sha256_checksum,
            original_filename=original_filename,
            source_url=source_url,
        )

    @property
    def batch_code(self) -> str:
        """Construct deterministic batch code for raw.ingestion_batch."""
        return f"BATCH-{self.document_code}-{self.revision}"

    @staticmethod
    def compute_file_sha256(path: Path) -> str:
        """Compute SHA-256 hash in streaming 64KB chunks."""
        hasher = hashlib.sha256()
        with path.open("rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def check_existing_document(
        cur: Cursor[Any], document_code: str, sha256_checksum: str | None = None
    ) -> tuple[DocumentSyncStatus, int | None]:
        """
        Check database state to determine if document is new, unchanged, or revised.
        Returns (Status, source_document_id).
        """
        cur.execute(
            """
            SELECT source_document_id, sha256_checksum, dataset_revision
            FROM raw.source_document
            WHERE document_code = %s;
            """,
            (document_code,),
        )
        row = cur.fetchone()
        if not row:
            return DocumentSyncStatus.NEW, None

        doc_id, existing_hash, _ = row
        if sha256_checksum and existing_hash == sha256_checksum:
            return DocumentSyncStatus.UNCHANGED, int(doc_id)
        return DocumentSyncStatus.REVISED, int(doc_id)
