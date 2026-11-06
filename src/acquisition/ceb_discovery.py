"""
GridLens — Ceylon Electricity Board (CEB) Publication Discovery & Acquisition.

Scrapes official CEB publication repositories:
    https://ceb.lk/publication-media/other-publications/en

Discovers annual Statistical Digest publications containing official provincial and
tariff-class electricity sales, verifies PDF integrity, and synchronizes files immutably
under data/raw/ceb/<year>/.
"""

from __future__ import annotations

import logging
import re
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

from src.acquisition.pucsl_discovery import DiscoveredDocument
from src.common.config import DatabaseConfig
from src.common.source_identity import SourceDocumentIdentity

logger = logging.getLogger("gridlens.acquisition.ceb")

CEB_PUBLICATIONS_URL = "https://ceb.lk/publication-media/other-publications/en"
CEB_BASE_URL = "https://ceb.lk"


class CebDiscoveryClient:
    """Discovers and downloads official CEB Statistical Digest publications."""

    def __init__(
        self,
        portal_url: str = CEB_PUBLICATIONS_URL,
        base_url: str = CEB_BASE_URL,
        download_dir: Path | None = None,
        db_config: DatabaseConfig | None = None,
        timeout_sec: int = 45,
    ) -> None:
        self.portal_url = portal_url
        self.base_url = base_url
        self.download_dir = download_dir or Path("data/raw/ceb")
        self.db_config = db_config
        self.timeout_sec = timeout_sec
        self.ssl_context = ssl.create_default_context()
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GridLens-Acquisition/1.0"

    @staticmethod
    def validate_magic_bytes(path: Path) -> bool:
        """Validate PDF magic bytes (%PDF)."""
        try:
            with path.open("rb") as f:
                header = f.read(5)
                return header.startswith(b"%PDF")
        except Exception:
            return False

    def parse_page_html(self, html: str) -> list[DiscoveredDocument]:
        """Extract Statistical Digest PDF links and normalize reporting years."""
        pattern = re.compile(
            r'href=["\']([^"\']*?(?:Statistical_Digest|Statistical-Digest|SD)[^"\']*?\.pdf)["\']',
            re.IGNORECASE,
        )
        matches = pattern.findall(html)

        discovered: list[DiscoveredDocument] = []
        seen_years: set[str] = set()

        for raw_link in matches:
            full_url = urllib.parse.urljoin(self.base_url, raw_link)
            filename = Path(urllib.parse.urlparse(full_url).path).name

            # Extract year from filename, e.g., Statistical_Digest_2024.pdf or SD-2025-Finalized.pdf
            year_match = re.search(
                r"(?:Statistical_Digest|Statistical-Digest|SD)[-_]?(\d{4})",
                filename,
                re.IGNORECASE,
            )

            if year_match:
                year = year_match.group(1)
            else:
                # Fallback: any 4 digits in filename between 2000 and 2030
                generic_year = re.search(r"(20[0-3]\d)", filename)
                year = generic_year.group(1) if generic_year else "UNKNOWN"

            if year in seen_years and year != "UNKNOWN":
                continue
            seen_years.add(year)

            doc_code = f"CEB-STAT-DIGEST-{year}"

            discovered.append(
                DiscoveredDocument(
                    document_code=doc_code,
                    source_code="CEB",
                    dataset_type="SALES_ANNUAL",
                    reporting_period=year,
                    original_filename=filename,
                    source_url=full_url,
                    file_format="PDF",
                )
            )

        return discovered

    def fetch_portal_html(self) -> str:
        """Fetch live HTML of the CEB publications page."""
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
        """Fetch CEB publication page and return all discovered Statistical Digest publications."""
        html = self.fetch_portal_html()
        return self.parse_page_html(html)

    def download_document(self, doc: DiscoveredDocument) -> Path:
        """Download and verify a single CEB Statistical Digest PDF."""
        year = doc.reporting_period if doc.reporting_period != "UNKNOWN" else "latest"
        dest_dir = self.download_dir / year
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / doc.original_filename

        req = urllib.request.Request(
            doc.source_url,
            headers={"User-Agent": self.user_agent},
        )
        logger.info(f"Downloading CEB digest: {doc.source_url} -> {dest_path}")
        with urllib.request.urlopen(
            req, context=self.ssl_context, timeout=self.timeout_sec
        ) as resp:
            content = resp.read()

        dest_path.write_bytes(content)

        if not self.validate_magic_bytes(dest_path):
            dest_path.unlink(missing_ok=True)
            raise ValueError(f"Corrupted or invalid PDF downloaded from {doc.source_url}")

        doc.local_path = dest_path
        doc.file_size_bytes = len(content)
        doc.sha256_checksum = SourceDocumentIdentity.compute_file_sha256(dest_path)
        return dest_path
