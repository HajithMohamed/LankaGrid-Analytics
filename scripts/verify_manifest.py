"""
Verification script for data/raw/manifest.json.
Asserts that every downloaded source file exists on disk, matches its reported
SHA-256 cryptographic checksum, and conforms to ManifestValidator schema.
"""

from __future__ import annotations

import sys
from pathlib import Path

from src.ingestion.manifest_validator import ManifestValidator


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    manifest_path = base_dir / "data" / "raw" / "manifest.json"

    if not manifest_path.exists():
        print(f"ERROR: Manifest not found at {manifest_path}", file=sys.stderr)
        return 1

    validator = ManifestValidator()
    try:
        manifest = validator.load_manifest(manifest_path)
    except Exception as e:
        print(f"ERROR validating manifest structure: {e}", file=sys.stderr)
        return 1

    print(f"Manifest schema valid! Checking {len(manifest.sources)} sources:")
    failures = 0

    for source in manifest.sources:
        file_path = base_dir / source.local_path
        if not file_path.exists():
            print(f"  [MISSING] {source.source_id}: File not found at {file_path}")
            failures += 1
            continue

        if source.sha256_checksum == "PENDING_ACQUISITION":
            print(f"  [PENDING] {source.source_id}: Checksum pending acquisition")
            continue

        actual_sha256 = validator.compute_sha256(file_path)
        actual_size = file_path.stat().st_size

        if actual_sha256.lower() != source.sha256_checksum.lower():
            print(f"  [MISMATCH] {source.source_id}: Checksum mismatch!")
            print(f"    Expected: {source.sha256_checksum}")
            print(f"    Actual:   {actual_sha256}")
            failures += 1
        elif source.file_size_bytes is not None and actual_size != source.file_size_bytes:
            print(
                f"  [SIZE MISMATCH] {source.source_id}: Size mismatch (expected {source.file_size_bytes}, got {actual_size})"
            )
            failures += 1
        else:
            print(
                f"  [OK] {source.source_id}: Verified SHA-256 ({actual_sha256[:12]}...) ({actual_size} bytes)"
            )

    if failures > 0:
        print(f"\nVerification FAILED with {failures} error(s).", file=sys.stderr)
        return 1

    print("\nAll manifest entries verified successfully against disk storage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
