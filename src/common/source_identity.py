"""
GridLens — Centralized Source Document Identity & Provenance Registry.

Provides consistent, deterministic document codes, batch identifiers, and
provenance hashing across acquisition, staging, and dimensional ETL pipelines.
"""

from __future__ import annotations

import enum
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from psycopg import Cursor

MONTH_LOOKUP: dict[str, str] = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}


class DocumentSyncStatus(enum.StrEnum):
    """Categorization of source document relative to warehouse state."""

    NEW = "NEW"
    UNCHANGED = "UNCHANGED"
    REVISED = "REVISED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"
    INVALID_CHECKSUM = "INVALID_CHECKSUM"


def _parse_revision_number(revision: str) -> int:
    m = re.search(r"(\d+)", revision)
    return int(m.group(1)) if m else 1


@dataclass(frozen=True)
class SourceDocumentIdentity:
    """Canonical identifier for an official grid or meteorological source document."""

    source_code: str  # e.g., 'PUCSL', 'CEB', 'NASA_POWER'
    dataset_type: str  # e.g., 'DISPATCH_15MIN', 'STAT_DIGEST', 'DAILY', 'GEN_DAILY'
    reporting_period: str  # e.g., '2024-M03', '2024', '2024-03-31', '2020-2024'
    document_code: str  # e.g., 'PUCSL-DISPATCH-15MIN-2024-M03'
    revision: str = "v1"
    sha256_checksum: str | None = None
    original_filename: str | None = None
    source_url: str | None = None
    file_size_bytes: int | None = None
    acquired_at: str | None = None
    revision_number: int = 1
    legacy_aliases: tuple[str, ...] = ()

    @property
    def source_system(self) -> str:
        """Alias for source_code matching the warehouse schema terminology."""
        return self.source_code

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
        file_size_bytes: int | None = None,
        acquired_at: str | None = None,
        revision_number: int | None = None,
        legacy_aliases: tuple[str, ...] = (),
    ) -> SourceDocumentIdentity:
        """Construct canonical identity ensuring clean formatting and naming."""
        clean_source = re.sub(r"[^A-Za-z0-9_-]", "-", source_code.strip()).upper()
        clean_type = re.sub(r"[^A-Za-z0-9_-]", "-", dataset_type.strip()).upper()
        clean_period = re.sub(r"[^A-Za-z0-9_-]", "-", reporting_period.strip()).upper()
        clean_rev = revision.strip().lower()
        rev_num = (
            revision_number if revision_number is not None else _parse_revision_number(clean_rev)
        )

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
            file_size_bytes=file_size_bytes,
            acquired_at=acquired_at or datetime.now(UTC).isoformat(),
            revision_number=rev_num,
            legacy_aliases=legacy_aliases,
        )

    @classmethod
    def for_nasa_daily(
        cls,
        start_date: date | int,
        end_date: date | int,
        revision: str = "v1",
        sha256_checksum: str | None = None,
        original_filename: str | None = None,
        source_url: str = "https://power.larc.nasa.gov/api/temporal/daily/point",
        file_size_bytes: int | None = None,
    ) -> SourceDocumentIdentity:
        """Construct canonical identity for NASA POWER daily weather datasets.

        Unifies historical multi-year and incremental daily/monthly identities:
        - Multi-year historical window (e.g., 2020-2024): NASA-POWER-DAILY-2020-2024
          (with backward-compatible alias NASA-POWER-DAILY-5YR-2020-2024).
        - Single calendar month window starting day 1: NASA-POWER-DAILY-YYYY-MM
        - Arbitrary incremental date range: NASA-POWER-DAILY-YYYYMMDD-YYYYMMDD
        """
        s_date = date(start_date, 1, 1) if isinstance(start_date, int) else start_date
        e_date = date(end_date, 12, 31) if isinstance(end_date, int) else end_date
        aliases: tuple[str, ...] = ()
        if s_date.year != e_date.year:
            period = f"{s_date.year}-{e_date.year}"
            aliases = (f"NASA-POWER-DAILY-5YR-{s_date.year}-{e_date.year}",)
        elif s_date.day == 1 and s_date.month == e_date.month and (e_date - s_date).days >= 27:
            period = f"{s_date.year}-M{s_date.month:02d}"
        else:
            period = f"{s_date.strftime('%Y%m%d')}-{e_date.strftime('%Y%m%d')}"

        return cls.create(
            source_code="NASA_POWER",
            dataset_type="DAILY",
            reporting_period=period,
            revision=revision,
            sha256_checksum=sha256_checksum,
            original_filename=original_filename,
            source_url=source_url,
            file_size_bytes=file_size_bytes,
            legacy_aliases=aliases,
        )

    @classmethod
    def for_ceb_digest(
        cls,
        reporting_year: int | str,
        revision: str = "v1",
        sha256_checksum: str | None = None,
        original_filename: str | None = None,
        source_url: str = "https://ceb.lk/publication-media/other-publications/en",
        file_size_bytes: int | None = None,
    ) -> SourceDocumentIdentity:
        """Construct canonical identity for CEB Statistical Digest annual sales."""
        return cls.create(
            source_code="CEB",
            dataset_type="STAT_DIGEST",
            reporting_period=str(reporting_year),
            revision=revision,
            sha256_checksum=sha256_checksum,
            original_filename=original_filename,
            source_url=source_url,
            file_size_bytes=file_size_bytes,
        )

    @classmethod
    def for_pucsl_dispatch(
        cls,
        reporting_period: str,
        revision: str = "v1",
        sha256_checksum: str | None = None,
        original_filename: str | None = None,
        source_url: str = "https://www.pucsl.gov.lk/electricity/daily-generation-reports-2/",
        file_size_bytes: int | None = None,
    ) -> SourceDocumentIdentity:
        """Construct canonical identity for PUCSL 15-minute monthly dispatch workbooks."""
        return cls.create(
            source_code="PUCSL",
            dataset_type="DISPATCH_15MIN",
            reporting_period=reporting_period,
            revision=revision,
            sha256_checksum=sha256_checksum,
            original_filename=original_filename,
            source_url=source_url,
            file_size_bytes=file_size_bytes,
        )

    @classmethod
    def for_pucsl_daily_gen(
        cls,
        reporting_date: date,
        revision: str = "v1",
        sha256_checksum: str | None = None,
        original_filename: str | None = None,
        source_url: str = "https://www.pucsl.gov.lk/daily-generation-reports-2/",
        file_size_bytes: int | None = None,
    ) -> SourceDocumentIdentity:
        """Construct canonical identity for PUCSL daily generation PDF reports."""
        return cls.create(
            source_code="PUCSL",
            dataset_type="GEN_DAILY",
            reporting_period=reporting_date.strftime("%Y-%m-%d"),
            revision=revision,
            sha256_checksum=sha256_checksum,
            original_filename=original_filename,
            source_url=source_url,
            file_size_bytes=file_size_bytes,
        )

    @staticmethod
    def infer_ceb_year_from_path(pdf_path: Path, default_year: int = 2024) -> int:
        """Infer reporting year from a CEB Statistical Digest filename or parent path."""
        name = pdf_path.name
        m = re.search(
            r"(?:Statistical_Digest|Statistical-Digest|SD)[-_]?(\d{4})",
            name,
            re.IGNORECASE,
        )
        if m:
            return int(m.group(1))
        m_generic = re.search(r"(20[0-3]\d)", name)
        if m_generic:
            return int(m_generic.group(1))
        for part in reversed(pdf_path.parts[:-1]):
            if re.fullmatch(r"20[0-3]\d", part):
                return int(part)
        return default_year

    @staticmethod
    def infer_pucsl_period_from_filename(filename: str) -> str | None:
        """Infer canonical YYYY-MXX reporting period from a PUCSL workbook filename."""
        m = re.search(
            r"15-Minutes-Report-(?:3[01]|[12][0-9]|0?[1-9])?-?([A-Za-z]{3,9})-?(\d{4})",
            filename,
            re.IGNORECASE,
        )
        if m:
            month_str = m.group(1).lower()
            year_str = m.group(2)
            month_num = MONTH_LOOKUP.get(month_str)
            if month_num:
                return f"{year_str}-M{month_num}"
        m_iso = re.search(r"(20[0-3]\d)[-_]?M?(\d{2})", filename, re.IGNORECASE)
        if m_iso and 1 <= int(m_iso.group(2)) <= 12:
            return f"{m_iso.group(1)}-M{int(m_iso.group(2)):02d}"
        return None

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
    def verify_file_checksum(path: Path, expected_sha256: str | None = None) -> tuple[bool, str]:
        """Compute SHA-256 checksum and verify against an optional expected hash."""
        if not path.exists() or path.stat().st_size == 0:
            return False, ""
        actual = SourceDocumentIdentity.compute_file_sha256(path)
        if expected_sha256 and actual.lower() != expected_sha256.lower():
            return False, actual
        return True, actual

    @staticmethod
    def check_existing_document(
        cur: Cursor[Any],
        document_code: str,
        sha256_checksum: str | None = None,
        legacy_aliases: tuple[str, ...] = (),
    ) -> tuple[DocumentSyncStatus, int | None]:
        """
        Check database state to determine if document is NEW, UNCHANGED, REVISED, or DUPLICATE.
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
        if not row and legacy_aliases:
            for alias in legacy_aliases:
                cur.execute(
                    """
                    SELECT source_document_id, sha256_checksum, dataset_revision
                    FROM raw.source_document
                    WHERE document_code = %s;
                    """,
                    (alias,),
                )
                row = cur.fetchone()
                if row:
                    break

        if not row:
            return DocumentSyncStatus.NEW, None

        doc_id, existing_hash, _ = row
        if sha256_checksum and existing_hash == sha256_checksum:
            return DocumentSyncStatus.UNCHANGED, int(doc_id)
        return DocumentSyncStatus.REVISED, int(doc_id)

    @staticmethod
    def check_duplicate_checksum(
        cur: Cursor[Any],
        sha256_checksum: str,
        exclude_document_code: str | None = None,
    ) -> tuple[bool, int | None, str | None]:
        """Check whether an identical SHA-256 checksum already exists under another document code."""
        if exclude_document_code:
            cur.execute(
                """
                SELECT source_document_id, document_code
                FROM raw.source_document
                WHERE sha256_checksum = %s
                  AND document_code <> %s
                LIMIT 1;
                """,
                (sha256_checksum, exclude_document_code),
            )
        else:
            cur.execute(
                """
                SELECT source_document_id, document_code
                FROM raw.source_document
                WHERE sha256_checksum = %s
                LIMIT 1;
                """,
                (sha256_checksum,),
            )
        row = cur.fetchone()
        if row:
            return True, int(row[0]), str(row[1])
        return False, None, None

    @staticmethod
    def next_revision_label(existing_revision: str | None) -> tuple[str, int]:
        """Increment a revision label such as 'v1' -> ('v2', 2)."""
        if not existing_revision:
            return "v1", 1
        num = _parse_revision_number(existing_revision) + 1
        return f"v{num}", num

    def to_manifest_dict(
        self, local_path: Path | None = None, status: str = "VERIFIED"
    ) -> dict[str, Any]:
        """Serialize provenance metadata for durable storage in data/raw/manifest.json."""
        return {
            "source_system": self.source_code,
            "dataset_type": self.dataset_type,
            "document_code": self.document_code,
            "original_filename": self.original_filename
            or (local_path.name if local_path else None),
            "local_path": str(local_path).replace("\\", "/") if local_path else None,
            "source_url": self.source_url,
            "reporting_period": self.reporting_period,
            "sha256_checksum": self.sha256_checksum,
            "file_size_bytes": self.file_size_bytes
            or (local_path.stat().st_size if local_path and local_path.exists() else None),
            "acquired_at": self.acquired_at or datetime.now(UTC).isoformat(),
            "revision": self.revision,
            "revision_number": self.revision_number,
            "status": status,
        }

    @staticmethod
    def update_manifest_file(
        manifest_path: Path,
        identity: SourceDocumentIdentity,
        local_path: Path | None = None,
        status: str = "VERIFIED",
    ) -> None:
        """Record or update document provenance in data/raw/manifest.json idempotently."""
        manifest_data: dict[str, Any] = {"version": "1.1", "documents": {}}
        if manifest_path.exists():
            try:
                loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    manifest_data = loaded
                    if "documents" not in manifest_data or not isinstance(
                        manifest_data["documents"], dict
                    ):
                        manifest_data["documents"] = {}
            except Exception:
                manifest_data = {"version": "1.1", "documents": {}}

        manifest_data["updated_at"] = datetime.now(UTC).isoformat()
        manifest_data["documents"][identity.document_code] = identity.to_manifest_dict(
            local_path=local_path, status=status
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
