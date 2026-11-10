"""
GridLens Automated Source Acquisition Package.

Provides automated discovery and ingestion clients for official upstream providers:
- NASA POWER Daily REST API (Meteorological & Solar Irradiance observations)
- PUCSL Web Discovery (15-Minute Generation Dispatch workbooks)
- CEB Publication Discovery (Statistical Digest annual provincial & tariff sales)
"""

from __future__ import annotations

from src.acquisition.ceb_discovery import CebDiscoveryClient, DiscoveredDocument
from src.acquisition.nasa_power_client import (
    SRI_LANKA_WEATHER_NODES,
    NasaPowerClient,
    NasaSyncResult,
)
from src.acquisition.pucsl_discovery import PucslDiscoveryClient

__all__ = [
    "CebDiscoveryClient",
    "DiscoveredDocument",
    "NasaPowerClient",
    "NasaSyncResult",
    "PucslDiscoveryClient",
    "SRI_LANKA_WEATHER_NODES",
]
