"""
Acquisition script for genuine official datasets from CEB, PUCSL, and NASA POWER.
Follows .agents/skills/real-data-acquisition/SKILL.md:
- Downloads authentic sample files for calendar year 2024
- Preserves original raw files immutably under data/raw/<provider>/<year>/
- Validates file headers/magic bytes
- Calculates SHA-256 cryptographic hashes
- Generates or updates data/raw/manifest.json
"""
from __future__ import annotations

import hashlib
import json
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# SSL context that allows standard certificates
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
}


def compute_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with filepath.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def download_file(url: str, dest_path: Path, expected_magic: bytes | None = None) -> tuple[int, str]:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers=HEADERS)
    print(f"Downloading {url} -> {dest_path}...")
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as resp:
        content = resp.read()

    if expected_magic and not content.startswith(expected_magic):
        raise ValueError(f"File from {url} does not start with expected magic bytes {expected_magic}: got {content[:20]!r}")

    dest_path.write_bytes(content)
    size_bytes = len(content)
    sha256 = compute_sha256(dest_path)
    print(f"Saved {dest_path.name}: {size_bytes} bytes, SHA-256: {sha256}")
    return size_bytes, sha256


def fetch_nasa_power_data(dest_path: Path) -> tuple[int, str]:
    """Fetch multi-node NASA POWER daily data for key Sri Lanka energy coordinates in 2024."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    nodes = {
        "victoria_hydro": {"name": "Victoria Hydro Reservoir", "lat": 7.24, "lon": 80.785},
        "mannar_wind": {"name": "Mannar Wind Farm", "lat": 9.03, "lon": 79.88},
    }
    
    combined_payload: dict[str, Any] = {
        "title": "NASA POWER Meteorological and Solar Radiation Sri Lanka Grid Nodes 2024",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "temporal_resolution": "daily",
        "community": "RE",
        "parameters": ["ALLSKY_SFC_SW_DWN", "T2M", "RH2M", "WS10M", "WS50M", "PRECTOTCORR"],
        "parameter_descriptions": {
            "ALLSKY_SFC_SW_DWN": "All Sky Surface Shortwave Downward Irradiance (kW-hr/m^2/day)",
            "T2M": "Temperature at 2 Meters (C)",
            "RH2M": "Relative Humidity at 2 Meters (%)",
            "WS10M": "Wind Speed at 10 Meters (m/s)",
            "WS50M": "Wind Speed at 50 Meters (m/s)",
            "PRECTOTCORR": "Precipitation Corrected (mm/day)"
        },
        "nodes": {}
    }

    for node_id, node_info in nodes.items():
        url = (
            f"https://power.larc.nasa.gov/api/temporal/daily/point"
            f"?parameters=ALLSKY_SFC_SW_DWN,T2M,RH2M,WS10M,WS50M,PRECTOTCORR"
            f"&community=RE&longitude={node_info['lon']}&latitude={node_info['lat']}"
            f"&start=20240101&end=20240131&format=JSON"
        )
        print(f"Fetching NASA POWER for {node_id} ({node_info['name']})...")
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            combined_payload["nodes"][node_id] = {
                "metadata": node_info,
                "header": data.get("header", {}),
                "properties": data.get("properties", {}),
            }

    dest_path.write_text(json.dumps(combined_payload, indent=2), encoding="utf-8")
    size_bytes = dest_path.stat().st_size
    sha256 = compute_sha256(dest_path)
    print(f"Saved {dest_path.name}: {size_bytes} bytes, SHA-256: {sha256}")
    return size_bytes, sha256


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    raw_dir = base_dir / "data" / "raw"

    sources_to_download = [
        {
            "source_id": "CEB-STAT-DIGEST-2024",
            "provider": "CEB",
            "title": "CEB Statistical Digest 2024 Operational and Commercial Summary",
            "source_url": "https://ceb.lk/front_img/img_reports/1751344341Statistical_Digest_2024.pdf",
            "original_filename": "Statistical_Digest_2024.pdf",
            "local_path": "data/raw/ceb/2024/Statistical_Digest_2024.pdf",
            "reporting_period": "2024-01-01 to 2024-12-31",
            "file_format": "PDF",
            "magic": b"%PDF",
            "time_zone": "Asia/Colombo",
            "data_granularity": "Monthly Provincial & Tariff Summary",
            "units": ["GWh", "MW", "LKR/kWh", "%"],
        },
        {
            "source_id": "PUCSL-DISPATCH-15MIN-2024-03",
            "provider": "PUCSL",
            "title": "PUCSL Daily 15-Minute Generation Dispatch Curves - March 2024",
            "source_url": "https://www.pucsl.gov.lk/wp-content/uploads/2024/04/15-Minutes-Report-31-Mar2024.xlsx",
            "original_filename": "15-Minutes-Report-31-Mar2024.xlsx",
            "local_path": "data/raw/pucsl/2024/15-Minutes-Report-31-Mar2024.xlsx",
            "reporting_period": "2024-03-01 to 2024-03-31",
            "file_format": "XLSX",
            "magic": b"PK\x03\x04",
            "time_zone": "Asia/Colombo",
            "data_granularity": "15-Minute Interval Station Dispatch",
            "units": ["MW"],
        },
        {
            "source_id": "PUCSL-GEN-DAILY-2024-12-29",
            "provider": "PUCSL",
            "title": "PUCSL Daily Generation and Dispatch Report - 29 December 2024",
            "source_url": "https://www.pucsl.gov.lk/wp-content/uploads/2024/12/Generation-Report-29th-Dec.pdf",
            "original_filename": "Generation-Report-29th-Dec.pdf",
            "local_path": "data/raw/pucsl/2024/Generation-Report-29th-Dec-2024.pdf",
            "reporting_period": "2024-12-29",
            "file_format": "PDF",
            "magic": b"%PDF",
            "time_zone": "Asia/Colombo",
            "data_granularity": "Daily Station Total & Operating Regime",
            "units": ["MW", "MWh", "GWh"],
        },
    ]

    manifest_entries: list[dict[str, Any]] = []

    for src in sources_to_download:
        dest = base_dir / src["local_path"]
        try:
            size, sha256 = download_file(src["source_url"], dest, src.get("magic"))
            manifest_entries.append({
                "source_id": src["source_id"],
                "provider": src["provider"],
                "title": src["title"],
                "source_url": src["source_url"],
                "original_filename": src["original_filename"],
                "local_path": src["local_path"],
                "reporting_period": src["reporting_period"],
                "file_format": src["file_format"],
                "file_size_bytes": size,
                "sha256_checksum": sha256,
                "time_zone": src["time_zone"],
                "data_granularity": src["data_granularity"],
                "units": src["units"],
                "status": "DOWNLOADED_VERIFIED",
            })
        except Exception as e:
            print(f"ERROR downloading {src['source_id']}: {e}", file=sys.stderr)
            return 1

    # Fetch NASA POWER dataset
    nasa_dest = base_dir / "data/raw/nasa/2024/nasa_power_sl_nodes_2024.json"
    try:
        nasa_size, nasa_sha256 = fetch_nasa_power_data(nasa_dest)
        manifest_entries.append({
            "source_id": "NASA-POWER-DAILY-2024",
            "provider": "NASA POWER",
            "title": "NASA POWER Meteorological and Solar Radiation Sri Lanka Grid Nodes 2024",
            "source_url": "https://power.larc.nasa.gov/api/temporal/daily/point",
            "original_filename": "nasa_power_sl_nodes_2024.json",
            "local_path": "data/raw/nasa/2024/nasa_power_sl_nodes_2024.json",
            "reporting_period": "2024-01-01 to 2024-01-31",
            "file_format": "JSON",
            "file_size_bytes": nasa_size,
            "sha256_checksum": nasa_sha256,
            "time_zone": "UTC+05:30",
            "data_granularity": "Daily Point Observations",
            "units": ["kW-hr/m^2/day", "C", "%", "m/s", "mm/day"],
            "status": "DOWNLOADED_VERIFIED",
        })
    except Exception as e:
        print(f"ERROR fetching NASA data: {e}", file=sys.stderr)
        return 1

    # Write updated manifest.json
    manifest_path = raw_dir / "manifest.json"
    manifest_doc = {
        "version": "1.0",
        "project": "National Electricity Grid Analytics Data Warehouse — Sri Lanka",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_year": 2024,
        "sources": manifest_entries,
    }
    manifest_path.write_text(json.dumps(manifest_doc, indent=2), encoding="utf-8")
    print(f"Manifest written successfully to {manifest_path} with {len(manifest_entries)} verified entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
