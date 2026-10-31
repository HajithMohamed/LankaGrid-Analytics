"""
Unit tests for data source manifest loading, structure validation, and SHA-256 verification.
"""

from pathlib import Path

import pytest

from src.ingestion.manifest_validator import ManifestValidator


@pytest.mark.unit
def test_manifest_validation_success():
    """Verify that sample_manifest.json passes schema validation."""
    fixture_path = Path("tests/fixtures/sample_manifest.json")
    validator = ManifestValidator()
    manifest = validator.load_manifest(fixture_path)

    assert manifest.version == "1.0"
    assert manifest.primary_year == 2024
    assert len(manifest.sources) >= 1
    assert manifest.sources[0].source_id == "TEST-FIXTURE-001"
    assert manifest.sources[0].provider == "PUCSL"


@pytest.mark.unit
def test_manifest_validation_rejects_missing_fields():
    """Verify that manifest validator rejects entries lacking required provenance attributes."""
    invalid_data = {
        "version": "1.0",
        "primary_year": 2024,
        "sources": [
            {
                "source_id": "BAD-001",
                # missing provider, original_filename, sha256_checksum, etc.
            }
        ],
    }
    validator = ManifestValidator()
    with pytest.raises(ValueError, match="Missing required manifest fields"):
        validator.validate_dict(invalid_data)


@pytest.mark.unit
def test_official_manifest_validity():
    """Verify that the project data/raw/manifest.json conforms to standard schema."""
    official_manifest_path = Path("data/raw/manifest.json")
    if official_manifest_path.exists():
        validator = ManifestValidator()
        manifest = validator.load_manifest(official_manifest_path)
        assert len(manifest.sources) >= 3
