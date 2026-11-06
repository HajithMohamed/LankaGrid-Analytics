"""
Unit tests for automated official source acquisition clients (NASA POWER, PUCSL, CEB).
Following TDD protocol and .agents/rules/testing.md.
"""

from __future__ import annotations

import io
import json
import urllib.error
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.acquisition.ceb_discovery import CebDiscoveryClient, DiscoveredDocument
from src.acquisition.nasa_power_client import (
    SRI_LANKA_WEATHER_NODES,
    NasaPowerClient,
    NasaSyncResult,
)
from src.acquisition.pucsl_discovery import PucslDiscoveryClient
from src.common.source_identity import DocumentSyncStatus


@pytest.mark.unit
class TestNasaPowerClient:
    """Test suite for NASA POWER REST API acquisition client."""

    def test_weather_nodes_configuration(self) -> None:
        """Verify all 6 verified Sri Lanka meteorological locations are present with accurate bounds."""
        assert len(SRI_LANKA_WEATHER_NODES) == 6
        expected_nodes = {
            "victoria_hydro",
            "laxapana_catchment",
            "mannar_wind",
            "puttalam_coal",
            "hambantota_solar",
            "colombo_load",
        }
        assert set(SRI_LANKA_WEATHER_NODES.keys()) == expected_nodes

        for node_id, node in SRI_LANKA_WEATHER_NODES.items():
            assert "location_code" in node
            assert node["location_code"].startswith("LOC_")
            assert 5.80 <= node["lat"] <= 10.00, f"Latitude {node['lat']} outside Sri Lanka for {node_id}"
            assert 79.40 <= node["lon"] <= 82.00, f"Longitude {node['lon']} outside Sri Lanka for {node_id}"

    def test_build_url_parameters(self) -> None:
        """Verify URL query parameters comply with NASA POWER daily point API specs."""
        client = NasaPowerClient()
        url = client.build_url(lat=7.24, lon=80.785, start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))

        assert "https://power.larc.nasa.gov/api/temporal/daily/point?" in url
        assert "community=RE" in url
        assert "format=JSON" in url
        assert "latitude=7.24" in url
        assert "longitude=80.785" in url
        assert "start=20240101" in url
        assert "end=20240131" in url
        for param in ["ALLSKY_SFC_SW_DWN", "T2M", "RH2M", "PRECTOTCORR", "WS10M", "WS50M"]:
            assert param in url

    def test_fetch_node_data_with_mock_response(self) -> None:
        """Verify HTTP response deserialization and payload parsing."""
        mock_response_data = {
            "header": {"api_version": "v2.0"},
            "properties": {
                "parameter": {
                    "T2M": {"20240101": 26.5, "20240102": -999.0},
                    "ALLSKY_SFC_SW_DWN": {"20240101": 5.4, "20240102": 4.8},
                }
            },
        }
        mock_resp_bytes = json.dumps(mock_response_data).encode("utf-8")

        client = NasaPowerClient()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_cm = MagicMock()
            mock_cm.__enter__.return_value = io.BytesIO(mock_resp_bytes)
            mock_urlopen.return_value = mock_cm

            payload = client.fetch_node(
                lat=7.24, lon=80.785, start_date=date(2024, 1, 1), end_date=date(2024, 1, 2)
            )

            assert "properties" in payload
            assert payload["properties"]["parameter"]["T2M"]["20240101"] == 26.5
            assert payload["properties"]["parameter"]["T2M"]["20240102"] == -999.0

    def test_fetch_node_retry_on_transient_error(self) -> None:
        """Ensure client retries upon 503 transient server errors and succeeds."""
        mock_response_data = {
            "header": {"api_version": "v2.0"},
            "properties": {"parameter": {"T2M": {"20240101": 25.0}}},
        }
        mock_resp_bytes = json.dumps(mock_response_data).encode("utf-8")

        client = NasaPowerClient(max_retries=3, retry_delay_sec=0.01)

        err_503 = urllib.error.HTTPError(
            url="http://dummy", code=503, msg="Service Unavailable", hdrs=MagicMock(), fp=io.BytesIO(b"error")
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_success = MagicMock()
            mock_success.__enter__.return_value = io.BytesIO(mock_resp_bytes)
            # Fail first time with 503, succeed second time
            mock_urlopen.side_effect = [err_503, mock_success]

            payload = client.fetch_node(
                lat=7.24, lon=80.785, start_date=date(2024, 1, 1), end_date=date(2024, 1, 1)
            )
            assert "properties" in payload
            assert mock_urlopen.call_count == 2

    def test_sync_date_range_up_to_date_returns_no_change(self) -> None:
        """When warehouse already has latest data, sync returns NO_CHANGE without API calls."""
        client = NasaPowerClient()
        # End date earlier than start date
        res = client.acquire_range(
            start_date=date(2025, 2, 1),
            end_date=date(2025, 1, 31),
        )
        assert res.status == "NO_CHANGE"
        assert res.output_path is None


@pytest.mark.unit
class TestPucslDiscoveryClient:
    """Test suite for PUCSL web discovery and dispatch workbook acquisition."""

    SAMPLE_PUCSL_HTML = """
    <html>
    <body>
        <div class="entry-content">
            <p><a href="https://www.pucsl.gov.lk/wp-content/uploads/2024/04/15-Minutes-Report-31-Mar2024.xlsx">
               15 Minutes Report - March 2024</a></p>
            <p><a href="https://www.pucsl.gov.lk/wp-content/uploads/2024/05/15-Minutes-Report-30-Apr2024.xlsx">
               15 Minutes Report - April 2024</a></p>
            <p><a href="https://www.pucsl.gov.lk/wp-content/uploads/2025/02/15-Minutes-Report-31-Jan2025.xlsx">
               15 Minutes Report - January 2025</a></p>
            <p><a href="https://www.pucsl.gov.lk/wp-content/uploads/other/annual_report.pdf">
               Annual Report 2023</a></p>
        </div>
    </body>
    </html>
    """

    def test_parse_dispatch_links_from_html(self) -> None:
        """Ensure monthly dispatch .xlsx links are extracted and non-relevant links ignored."""
        client = PucslDiscoveryClient()
        docs = client.parse_page_html(self.SAMPLE_PUCSL_HTML)

        assert len(docs) == 3
        urls = [d.source_url for d in docs]
        assert any("15-Minutes-Report-31-Mar2024.xlsx" in u for u in urls)
        assert any("15-Minutes-Report-30-Apr2024.xlsx" in u for u in urls)
        assert any("15-Minutes-Report-31-Jan2025.xlsx" in u for u in urls)

    def test_period_extraction(self) -> None:
        """Verify reporting period extracted accurately as YYYY-MXX."""
        client = PucslDiscoveryClient()
        docs = client.parse_page_html(self.SAMPLE_PUCSL_HTML)

        period_map = {d.original_filename: d.reporting_period for d in docs}
        assert period_map["15-Minutes-Report-31-Mar2024.xlsx"] == "2024-M03"
        assert period_map["15-Minutes-Report-30-Apr2024.xlsx"] == "2024-M04"
        assert period_map["15-Minutes-Report-31-Jan2025.xlsx"] == "2025-M01"

    def test_magic_byte_validation_xlsx(self, tmp_path: Path) -> None:
        """Validate ZIP/OpenXML PK magic bytes check."""
        client = PucslDiscoveryClient()
        valid_xlsx = tmp_path / "valid.xlsx"
        valid_xlsx.write_bytes(b"PK\x03\x04\x14\x00\x06\x00...")

        invalid_file = tmp_path / "corrupt.xlsx"
        invalid_file.write_bytes(b"<html>404 Not Found</html>")

        assert client.validate_magic_bytes(valid_xlsx) is True
        assert client.validate_magic_bytes(invalid_file) is False


@pytest.mark.unit
class TestCebDiscoveryClient:
    """Test suite for CEB publication portal discovery of Statistical Digest PDFs."""

    SAMPLE_CEB_HTML = """
    <html>
    <body>
        <div class="report-list">
            <a href="/front_img/img_reports/1751344341Statistical_Digest_2024.pdf">Statistical Digest 2024</a>
            <a href="/front_img/img_reports/1689234123Statistical_Digest_2023.pdf">Statistical Digest 2023</a>
            <a href="/front_img/img_reports/1712398471SD-2025-Finalized-(Web-Edition).pdf">Statistical Digest 2025 Web Edition</a>
            <a href="/front_img/img_reports/1234567890General_Presentation.pdf">General Presentation</a>
        </div>
    </body>
    </html>
    """

    def test_parse_statistical_digest_links_from_html(self) -> None:
        """Ensure CEB Statistical Digest PDFs are extracted and relative URLs normalized."""
        client = CebDiscoveryClient(base_url="https://ceb.lk")
        docs = client.parse_page_html(self.SAMPLE_CEB_HTML)

        assert len(docs) == 3
        years = {d.reporting_period for d in docs}
        assert years == {"2023", "2024", "2025"}

        for d in docs:
            assert d.source_url.startswith("https://ceb.lk/")
            assert d.file_format == "PDF"
            assert d.document_code == f"CEB-STAT-DIGEST-{d.reporting_period}"

    def test_magic_byte_validation_pdf(self, tmp_path: Path) -> None:
        """Validate %PDF magic byte check."""
        client = CebDiscoveryClient()
        valid_pdf = tmp_path / "test.pdf"
        valid_pdf.write_bytes(b"%PDF-1.4\n...")

        invalid_pdf = tmp_path / "invalid.pdf"
        invalid_pdf.write_bytes(b"Error: Internal Server Error")

        assert client.validate_magic_bytes(valid_pdf) is True
        assert client.validate_magic_bytes(invalid_pdf) is False
