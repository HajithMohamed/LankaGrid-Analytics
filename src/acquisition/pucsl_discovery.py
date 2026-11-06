"""
GridLens — PUCSL Generation Dispatch Web Discovery & Acquisition.

Scrapes official Public Utilities Commission of Sri Lanka (PUCSL) generation report portal:
    https://www.pucsl.gov.lk/electricity/daily-generation-reports-2/

Discovers monthly 15-minute generation dispatch workbooks (.xlsx), verifies OpenXML
integrity, and synchronizes files immutably to data/raw/pucsl/<year>/.
"""

from __future__ import annotations

import logging
import re
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from src.common.config import DatabaseConfig
from src.common.source_identity import DocumentSyncStatus, SourceDocumentIdentity

logger = logging.getLogger("gridlens.acquisition.pucsl")

PUCSL_PORTAL_URL = "https://www.pucsl.gov.lk/electricity/daily-generation-reports-2/"

MONTH_NAME_TO_NUM = {
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


@dataclass
class DiscoveredDocument:
    """Represents an official document discovered from an upstream web portal."""

    document_code: str
    source_code: str
    dataset_type: str
    reporting_period: str
    original_filename: str
    source_url: str
    file_format: str
    local_path: Path | None = None
    sha256_checksum: str | None = None
    file_size_bytes: int | None = None
    sync_status: DocumentSyncStatus = DocumentSyncStatus.NEW


class PucslDiscoveryClient:
    """Discovers and downloads authentic 15-minute dispatch workbooks from PUCSL."""

    def __init__(
        self,
        portal_url: str = PUCSL_PORTAL_URL,
        download_dir: Path | None = None,
        db_config: DatabaseConfig | None = None,
        timeout_sec: int = 45,
    ) -> None:
        self.portal_url = portal_url
        self.download_dir = download_dir or Path("data/raw/pucsl")
        self.db_config = db_config
        self.timeout_sec = timeout_sec
        self.ssl_context = ssl.create_default_context()
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GridLens-Acquisition/1.0"

    @staticmethod
    def validate_magic_bytes(path: Path) -> bool:
        """Validate ZIP/OpenXML magic bytes (PK\\x03\\x04)."""
        try:
            with path.open("rb") as f:
                header = f.read(4)
                return header == b"PK\x03\x04"
        except Exception:
            return False

    def parse_page_html(self, html: str) -> list[DiscoveredDocument]:
        """Extract all 15-minute dispatch workbook links and normalize periods."""
        # Match href pointing to 15-Minutes-Report*.xlsx
        link_pattern = re.compile(
            r'href=["\']([^"\']*?15-Minutes-Report-[^"\']*?\.xlsx)["\']',
            re.IGNORECASE,
        )
        matches = link_pattern.findall(html)

        discovered: list[DiscoveredDocument] = []
        seen_urls: set[str] = set()

        for raw_link in matches:
            full_url = urllib.parse.urljoin(self.portal_url, raw_link)
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            filename = Path(urllib.parse.urlparse(full_url).path).name

            # Extract month and year from filename:
            # e.g., 15-Minutes-Report-31-Mar2024.xlsx or 15-Minutes-Report-March-2024.xlsx
            period_match = re.search(
                r"15-Minutes-Report-(?:3[01]|[12][0-9]|0?[1-9])?-?([A-Za-z]{3,9})-?(\d{4})",
                filename,
                re.IGNORECASE,
            )

            if period_match:
                month_str = period_match.group(1).lower()
                year_str = period_match.group(2)
                month_num = MONTH_NAME_TO_NUM.get(month_str, "01")
                period = f"{year_str}-M{month_num}"
            else:
                period = "UNKNOWN"

            doc_code = f"PUCSL-DISPATCH-15MIN-{period}"

            discovered.append(
                DiscoveredDocument(
                    document_code=doc_code,
                    source_code="PUCSL",
                    dataset_type="DISPATCH_15MIN",
                    reporting_period=period,
                    original_filename=filename,
                    source_url=full_url,
                    file_format="XLSX",
                )
            )

        return discovered

    def fetch_portal_html(self) -> str:
        """Fetch live HTML of the PUCSL generation reports page."""
        req = urllib.request.Request(
            self.portal_url,
            headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
        )
        with urllib.request.urlopen(
            req, context=self.ssl_context, timeout=self.timeout_sec
        ) as resp:
            content = resp.read()
            return str(content.decode("utf-8", errors="ignore"))

    def discover(self) -> list[DiscoveredDocument]:
        """Fetch PUCSL portal and return all discovered dispatch workbooks."""
        html = self.fetch_portal_html()
        return self.parse_page_html(html)

    def download_document(self, doc: DiscoveredDocument) -> Path:
        """Download and verify a single PUCSL dispatch workbook."""
        year = doc.reporting_period.split("-")[0] if "-" in doc.reporting_period else "2024"
        dest_dir = self.download_dir / year
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / doc.original_filename

        req = urllib.request.Request(
            doc.source_url,
            headers={"User-Agent": self.user_agent},
        )
        logger.info(f"Downloading PUCSL dispatch: {doc.source_url} -> {dest_path}")
        with urllib.request.urlopen(
            req, context=self.ssl_context, timeout=self.timeout_sec
        ) as resp:
            content = resp.read()

        dest_path.write_bytes(content)

        if not self.validate_magic_bytes(dest_path):
            dest_path.unlink(missing_ok=True)
            raise ValueError(f"Corrupted or invalid XLSX downloaded from {doc.source_url}")

        doc.local_path = dest_path
        doc.file_size_bytes = len(content)
        doc.sha256_checksum = SourceDocumentIdentity.compute_file_sha256(dest_path)
        return dest_path
