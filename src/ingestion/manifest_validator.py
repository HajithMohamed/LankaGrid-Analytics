"""
Provenance manifest schema validation and SHA-256 verification.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_MANIFEST_TOP_FIELDS: tuple[str, ...] = ("version", "primary_year", "sources")
REQUIRED_SOURCE_FIELDS: tuple[str, ...] = (
    "source_id",
    "provider",
    "title",
    "source_url",
    "original_filename",
    "local_path",
    "reporting_period",
    "file_format",
    "sha256_checksum",
    "time_zone",
    "data_granularity",
    "units",
    "status",
)


@dataclass(frozen=True)
class SourceManifestEntry:
    """Metadata describing an official source file or catalogued dataset."""

    source_id: str
    provider: str
    title: str
    source_url: str
    original_filename: str
    local_path: str
    reporting_period: str
    file_format: str
    sha256_checksum: str
    time_zone: str
    data_granularity: str
    units: list[str]
    status: str
    file_size_bytes: int | None = None


@dataclass(frozen=True)
class DataManifest:
    """Top-level raw data provenance manifest."""

    version: str
    primary_year: int
    sources: list[SourceManifestEntry]
    project: str | None = None
    generated_at: str | None = None


class ManifestValidator:
    """Validates raw data manifest structure and cryptographic file checksums."""

    def validate_dict(self, data: dict[str, Any]) -> DataManifest:
        """Validate a dictionary representation of a manifest file."""
        missing_top = [f for f in REQUIRED_MANIFEST_TOP_FIELDS if f not in data]
        if missing_top:
            raise ValueError(f"Missing required manifest fields: {', '.join(missing_top)}")

        raw_sources = data.get("sources")
        if not isinstance(raw_sources, list):
            raise ValueError("Manifest 'sources' must be a list of source entries.")

        parsed_entries: list[SourceManifestEntry] = []
        for idx, entry in enumerate(raw_sources):
            if not isinstance(entry, dict):
                raise ValueError(f"Manifest source at index {idx} must be an object.")
            missing_entry = [
                f for f in REQUIRED_SOURCE_FIELDS if f not in entry or entry[f] in (None, "")
            ]
            if missing_entry:
                raise ValueError(
                    f"Missing required manifest fields in source[{idx}]: {', '.join(missing_entry)}"
                )
            parsed_entries.append(
                SourceManifestEntry(
                    source_id=str(entry["source_id"]),
                    provider=str(entry["provider"]),
                    title=str(entry["title"]),
                    source_url=str(entry["source_url"]),
                    original_filename=str(entry["original_filename"]),
                    local_path=str(entry["local_path"]),
                    reporting_period=str(entry["reporting_period"]),
                    file_format=str(entry["file_format"]),
                    sha256_checksum=str(entry["sha256_checksum"]),
                    time_zone=str(entry["time_zone"]),
                    data_granularity=str(entry["data_granularity"]),
                    units=[str(u) for u in entry["units"]],
                    status=str(entry["status"]),
                    file_size_bytes=(
                        int(entry["file_size_bytes"])
                        if entry.get("file_size_bytes") is not None
                        else None
                    ),
                )
            )

        return DataManifest(
            version=str(data["version"]),
            primary_year=int(data["primary_year"]),
            sources=parsed_entries,
            project=str(data["project"]) if "project" in data else None,
            generated_at=str(data["generated_at"]) if "generated_at" in data else None,
        )

    def load_manifest(self, manifest_path: Path) -> DataManifest:
        """Read and validate a JSON provenance manifest from disk."""
        with manifest_path.open("r", encoding="utf-8") as handle:
            payload: dict[str, Any] = json.load(handle)
        return self.validate_dict(payload)

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Compute the lowercase hex SHA-256 digest of a file."""
        hasher = hashlib.sha256()
        with file_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
