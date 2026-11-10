"""
GridLens — NASA POWER Meteorological & Solar Radiation Client.

Performs automated retrieval of daily solar irradiance and meteorological observations
for verified Sri Lanka electricity grid nodes from the official NASA POWER API:
    https://power.larc.nasa.gov/api/temporal/daily/point

Adheres to .agents/rules/data-engineering.md:
- Preserves -999.0 fill values as missing / NULL (never treated as 0).
- Computes SHA-256 checksum upon receipt.
- Associates records with conformed dimension dw.dim_weather_location.
"""

from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.common.config import DatabaseConfig
from src.common.db import get_connection
from src.common.source_identity import SourceDocumentIdentity

logger = logging.getLogger("gridlens.acquisition.nasa")

# Authoritative Sri Lanka energy sector meteorological nodes matching dw.dim_weather_location
SRI_LANKA_WEATHER_NODES: dict[str, dict[str, Any]] = {
    "victoria_hydro": {
        "location_code": "LOC_VICTORIA_CATCHMENT",
        "name": "Victoria / Mahaweli Hydro Catchment",
        "lat": 7.24000,
        "lon": 80.78500,
        "elevation_m": 440.0,
        "zone_type": "HYDRO_CATCHMENT",
    },
    "laxapana_catchment": {
        "location_code": "LOC_LAXAPANA_CATCHMENT",
        "name": "Castlereagh / Laxapana Hydro Catchment",
        "lat": 6.89000,
        "lon": 80.52000,
        "elevation_m": 1100.0,
        "zone_type": "HYDRO_CATCHMENT",
    },
    "mannar_wind": {
        "location_code": "LOC_MANNAR_WIND",
        "name": "Mannar Island Wind Corridor",
        "lat": 8.98000,
        "lon": 79.90000,
        "elevation_m": 8.0,
        "zone_type": "WIND_CORRIDOR",
    },
    "puttalam_coal": {
        "location_code": "LOC_PUTTALAM_COAL",
        "name": "Norochcholai / Puttalam Coastal Corridor",
        "lat": 8.01500,
        "lon": 79.72000,
        "elevation_m": 10.0,
        "zone_type": "THERMAL_HUB",
    },
    "hambantota_solar": {
        "location_code": "LOC_HAMBANTOTA_SOLAR",
        "name": "Hambantota Dry-Zone Solar Hub",
        "lat": 6.22000,
        "lon": 81.12000,
        "elevation_m": 32.0,
        "zone_type": "SOLAR_HUB",
    },
    "colombo_load": {
        "location_code": "LOC_COLOMBO_LOAD",
        "name": "Colombo / Kelanitissa Load & Thermal Hub",
        "lat": 6.95500,
        "lon": 79.88000,
        "elevation_m": 12.0,
        "zone_type": "LOAD_CENTER",
    },
}

NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
TARGET_PARAMETERS = ["ALLSKY_SFC_SW_DWN", "T2M", "RH2M", "PRECTOTCORR", "WS10M", "WS50M"]


@dataclass
class NasaSyncResult:
    """Outcome of NASA POWER synchronization attempt."""

    status: str  # 'SUCCEEDED', 'NO_CHANGE', 'FAILED'
    start_date: date | None = None
    end_date: date | None = None
    output_path: Path | None = None
    source_identity: SourceDocumentIdentity | None = None
    days_fetched: int = 0
    file_size_bytes: int = 0
    sha256_checksum: str | None = None
    errors: list[str] = field(default_factory=list)


class NasaPowerClient:
    """Acquisition client for the official NASA POWER Daily REST API."""

    def __init__(
        self,
        output_dir: Path | None = None,
        db_config: DatabaseConfig | None = None,
        max_retries: int = 3,
        retry_delay_sec: float = 2.0,
        timeout_sec: int = 45,
    ) -> None:
        self.output_dir = output_dir or Path("data/raw/nasa/daily")
        self.db_config = db_config
        self.max_retries = max_retries
        self.retry_delay_sec = retry_delay_sec
        self.timeout_sec = timeout_sec
        self.ssl_context = ssl.create_default_context()
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GridLens-Acquisition/1.0"

    def build_url(self, lat: float, lon: float, start_date: date, end_date: date) -> str:
        """Construct parameterized NASA POWER request URL with input validation."""
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Invalid geographic coordinates: lat={lat}, lon={lon}")
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) cannot be after end_date ({end_date})")

        params = {
            "parameters": ",".join(TARGET_PARAMETERS),
            "community": "RE",
            "longitude": f"{lon:.4f}",
            "latitude": f"{lat:.4f}",
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "format": "JSON",
        }
        return f"{NASA_POWER_BASE_URL}?{urllib.parse.urlencode(params)}"

    def fetch_node(
        self, lat: float, lon: float, start_date: date, end_date: date
    ) -> dict[str, Any]:
        """Fetch observations for a single coordinate point with retry & backoff."""
        url = self.build_url(lat, lon, start_date, end_date)
        req = urllib.request.Request(
            url, headers={"User-Agent": self.user_agent, "Accept": "application/json"}
        )

        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with urllib.request.urlopen(
                    req, context=self.ssl_context, timeout=self.timeout_sec
                ) as resp:
                    raw_bytes = resp.read()
                    data: dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))
                    if "properties" not in data or "parameter" not in data.get("properties", {}):
                        raise ValueError("NASA POWER response missing 'properties.parameter' block")
                    return data
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as e:
                last_err = e
                logger.warning(
                    f"NASA POWER attempt {attempt}/{self.max_retries} failed for ({lat}, {lon}): {e}"
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay_sec * (2 ** (attempt - 1)))

        raise RuntimeError(
            f"NASA POWER API request failed after {self.max_retries} attempts: {last_err}"
        )

    def get_latest_warehouse_observation_date(self) -> date | None:
        """Query warehouse for the conservative watermark across all weather locations.

        Uses MIN(loc_max_date) across locations so that if any location lagged behind,
        subsequent runs backfill from the earliest incomplete location date rather than
        advancing past missing locations.
        """
        if not self.db_config:
            return None
        try:
            with get_connection(self.db_config, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT MIN(loc_max_date)
                        FROM (
                            SELECT f.weather_location_key, MAX(d.calendar_date) AS loc_max_date
                            FROM dw.fact_weather_daily f
                            JOIN dw.dim_date d ON f.date_key = d.date_key
                            GROUP BY f.weather_location_key
                        ) per_location;
                        """
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        val = row[0]
                        return val if isinstance(val, date) else None
        except Exception as e:
            logger.warning(f"Could not read latest weather date from warehouse: {e}")
        return None

    def acquire_range(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        manifest_path: Path = Path("data/raw/manifest.json"),
    ) -> NasaSyncResult:
        """
        Synchronize meteorological observations across all 6 nodes for the requested date window.
        If dates are omitted, automatically computes the incremental delta from the warehouse.
        """
        if start_date is None:
            latest_db = self.get_latest_warehouse_observation_date()
            if latest_db:
                start_date = latest_db + timedelta(days=1)
            else:
                start_date = date(2024, 1, 1)

        if end_date is None:
            # NASA POWER has ~2 days publication latency from UTC now
            utc_today = datetime.now(UTC).date()
            end_date = utc_today - timedelta(days=2)
            # Bound batch size to at most 31 days per sync chunk
            if (end_date - start_date).days > 31:
                end_date = start_date + timedelta(days=30)

        if start_date > end_date:
            logger.info(
                f"NASA weather warehouse is up to date (start {start_date} > end {end_date})."
            )
            return NasaSyncResult(status="NO_CHANGE", start_date=start_date, end_date=end_date)

        days_count = (end_date - start_date).days + 1
        logger.info(f"Acquiring NASA POWER data for {days_count} days: {start_date} -> {end_date}")

        combined_payload: dict[str, Any] = {
            "title": "NASA POWER Meteorological and Solar Radiation Sri Lanka Grid Nodes",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "temporal_resolution": "daily",
            "community": "RE",
            "parameters": TARGET_PARAMETERS,
            "parameter_descriptions": {
                "ALLSKY_SFC_SW_DWN": "All Sky Surface Shortwave Downward Irradiance (kW-hr/m^2/day)",
                "T2M": "Temperature at 2 Meters (C)",
                "RH2M": "Relative Humidity at 2 Meters (%)",
                "WS10M": "Wind Speed at 10 Meters (m/s)",
                "WS50M": "Wind Speed at 50 Meters (m/s)",
                "PRECTOTCORR": "Precipitation Corrected (mm/day)",
            },
            "nodes": {},
        }

        errors: list[str] = []
        for node_id, node_info in SRI_LANKA_WEATHER_NODES.items():
            try:
                node_data = self.fetch_node(
                    lat=node_info["lat"],
                    lon=node_info["lon"],
                    start_date=start_date,
                    end_date=end_date,
                )
                combined_payload["nodes"][node_id] = {
                    "metadata": node_info,
                    "header": node_data.get("header", {}),
                    "properties": node_data.get("properties", {}),
                }
            except Exception as e:
                err_msg = f"Failed fetching node {node_id}: {e}"
                logger.error(err_msg)
                errors.append(err_msg)

        # CRITICAL: Never persist or ingest a partially successful multi-location payload.
        # All 6 Sri Lanka weather nodes must succeed before advancing the warehouse watermark.
        if errors or len(combined_payload["nodes"]) != len(SRI_LANKA_WEATHER_NODES):
            return NasaSyncResult(
                status="FAILED",
                start_date=start_date,
                end_date=end_date,
                errors=errors
                or [
                    f"Incomplete node acquisition: expected {len(SRI_LANKA_WEATHER_NODES)} nodes, "
                    f"got {len(combined_payload['nodes'])}."
                ],
            )

        # Save to filesystem under configured output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"nasa_power_sl_nodes_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.json"
        out_path = self.output_dir / filename
        out_path.write_text(json.dumps(combined_payload, indent=2), encoding="utf-8")

        sha256 = SourceDocumentIdentity.compute_file_sha256(out_path)
        size_bytes = out_path.stat().st_size

        identity = SourceDocumentIdentity.for_nasa_daily(
            start_date=start_date,
            end_date=end_date,
            sha256_checksum=sha256,
            original_filename=filename,
            source_url=NASA_POWER_BASE_URL,
            file_size_bytes=size_bytes,
        )
        SourceDocumentIdentity.update_manifest_file(
            manifest_path=manifest_path,
            identity=identity,
            local_path=out_path,
            status="DOWNLOADED_VERIFIED",
        )

        return NasaSyncResult(
            status="SUCCEEDED",
            start_date=start_date,
            end_date=end_date,
            output_path=out_path,
            source_identity=identity,
            days_fetched=days_count,
            file_size_bytes=size_bytes,
            sha256_checksum=sha256,
            errors=errors,
        )
