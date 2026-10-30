"""
Source-specific extractor for Ceylon Electricity Board (CEB) Statistical Digest 2024 PDF.
Extracts billed electricity sales by distribution division/province and by consumer tariff class,
converting GWh to canonical warehouse MWh (1 GWh = 1,000 MWh).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pdfplumber


@dataclass(frozen=True)
class ProvincialSalesRecord:
    """Billed electricity sales for a geographic province or distribution division."""

    reporting_year: int
    region_raw: str
    sales_gwh: float
    sales_mwh: float
    consumer_count: int | None = None
    revenue_lkr_mn: float | None = None
    reported_unit_code: str = "GWh"


@dataclass(frozen=True)
class TariffSalesRecord:
    """Billed electricity sales for an official consumer tariff class."""

    reporting_year: int
    tariff_group: str
    sales_gwh: float
    sales_mwh: float
    consumer_count: int | None = None
    reported_unit_code: str = "GWh"


class CebDigestParser:
    """Parses CEB Statistical Digest annual operational and commercial summary tables."""

    def __init__(self, reporting_year: int = 2024) -> None:
        self.reporting_year = reporting_year

    @staticmethod
    def _clean_numeric(text: Any) -> float | None:
        if text is None:
            return None
        cleaned = str(text).replace(",", "").replace("*", "").replace(" ", "").strip()
        if not cleaned or cleaned in ("-", "N/A", "null"):
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    def extract_provincial_sales(self, pdf_path: Path) -> list[ProvincialSalesRecord]:
        """Extract sales by province/division from Page 5 Table 0."""
        records: list[ProvincialSalesRecord] = []
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) < 5:
                return []

            p5 = pdf.pages[4]
            tables = p5.extract_tables()
            if not tables:
                return []

            tbl0 = tables[0]
            # Table 0 columns: [Region, 2023 sales, 2024 sales, % change, % total, avg sales]
            for row in tbl0[3:]:
                if not row or len(row) < 3:
                    continue
                region_name = row[0]
                val_2024 = row[2] if len(row) > 2 else None

                if val_2024 is None:
                    continue

                cleaned_val = self._clean_numeric(val_2024)
                if cleaned_val is None:
                    continue

                reg_str = str(region_name).strip() if region_name else "Unknown Division"
                records.append(
                    ProvincialSalesRecord(
                        reporting_year=self.reporting_year,
                        region_raw=reg_str,
                        sales_gwh=cleaned_val,
                        sales_mwh=round(cleaned_val * 1000.0, 4),
                        reported_unit_code="GWh",
                    )
                )

        return records

    def extract_tariff_sales(self, pdf_path: Path) -> list[TariffSalesRecord]:
        """Extract sales by consumer tariff group from Page 5 Table 1."""
        records: list[TariffSalesRecord] = []
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) < 5:
                return []

            p5 = pdf.pages[4]
            tables = p5.extract_tables()
            if len(tables) < 2:
                return []

            tbl1 = tables[1]
            # Table 1 columns: [Tariff, Sub-tariff, 2023 sales, 2024 sales, ...]
            for row in tbl1[3:]:
                if not row or len(row) < 4:
                    continue
                tariff_name = row[0] or row[1]
                val_2024 = row[3] if len(row) > 3 else None

                if not tariff_name or val_2024 is None:
                    continue

                cleaned_val = self._clean_numeric(val_2024)
                if cleaned_val is None:
                    continue

                t_str = str(tariff_name).strip()
                if t_str.upper() in ("TARIFF", "SALES (GWH)"):
                    continue

                records.append(
                    TariffSalesRecord(
                        reporting_year=self.reporting_year,
                        tariff_group=t_str,
                        sales_gwh=cleaned_val,
                        sales_mwh=round(cleaned_val * 1000.0, 4),
                        reported_unit_code="GWh",
                    )
                )

        return records
