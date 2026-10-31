"""
Source-specific extractor for Ceylon Electricity Board (CEB) Statistical Digest PDFs.
Extracts billed electricity sales by distribution division/province and by consumer tariff class,
converting GWh to canonical warehouse MWh (1 GWh = 1,000 MWh).
Supports historical annual digests across 2020-2024.
"""

from __future__ import annotations

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
                val = row[2] if len(row) > 2 else None

                if val is None:
                    continue

                cleaned_val = self._clean_numeric(val)
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

    def extract_tariff_sales(
        self, pdf_path: Path, target_year: int | None = None
    ) -> list[TariffSalesRecord]:
        """Extract sales by consumer tariff group with version-aware multi-year support."""
        year = target_year if target_year is not None else self.reporting_year
        records: list[TariffSalesRecord] = []

        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) < 5:
                return []

            p5 = pdf.pages[4]
            tables = p5.extract_tables()
            if not tables:
                return []

            # Format 1: 2020 Digest (Page 5 single combined table of 52 rows)
            if len(tables) == 1 and len(tables[0]) >= 50:
                t = tables[0]
                col = 3 if year == 2020 else 2
                for r in t[29:51]:
                    name = r[0]
                    val = r[col] if col < len(r) else None
                    if name and name.strip():
                        n_str = name.strip()
                        if n_str == "Bulk Supply to LECO" and len(t) > 48:
                            val = t[48][col]
                        cleaned_val = self._clean_numeric(val)
                        if cleaned_val is not None:
                            records.append(
                                TariffSalesRecord(
                                    reporting_year=year,
                                    tariff_group=n_str,
                                    sales_gwh=cleaned_val,
                                    sales_mwh=round(cleaned_val * 1000.0, 4),
                                    reported_unit_code="GWh",
                                )
                            )
                return records

            # Format 2: 2022 Digest (Table 1 has 16 rows, columns: Col 1 = 2021, Col 2 = 2022)
            if len(tables) > 1 and len(tables[1]) == 16:
                t = tables[1]
                col = 2 if year == 2022 else 1
                # Row 2 contains Domestic & Religious concatenated with newline
                if t[2][col]:
                    dom_rel = str(t[2][col]).split("\n")
                    if len(dom_rel) >= 2:
                        d_val = self._clean_numeric(dom_rel[0])
                        r_val = self._clean_numeric(dom_rel[1])
                        if d_val is not None:
                            records.append(
                                TariffSalesRecord(year, "Domestic", d_val, round(d_val * 1000.0, 4))
                            )
                        if r_val is not None:
                            records.append(
                                TariffSalesRecord(
                                    year, "Religious", r_val, round(r_val * 1000.0, 4)
                                )
                            )

                # Standard category rows in 2022 Table 1
                for idx in [3, 5, 7, 9, 11, 14, 15]:
                    name = str(t[idx][0]).strip()
                    cat_val = self._clean_numeric(t[idx][col])
                    if cat_val is not None:
                        records.append(
                            TariffSalesRecord(year, name, cat_val, round(cat_val * 1000.0, 4))
                        )

                # LECO is located in row 13
                leco_val = self._clean_numeric(t[13][col])
                if leco_val is not None:
                    records.append(
                        TariffSalesRecord(
                            year, "Bulk Supply to LECO", leco_val, round(leco_val * 1000.0, 4)
                        )
                    )
                return records

            # Format 3: 2024 Digest (Table 1 has 25 rows, Col 2 = 2023, Col 3 = 2024)
            if len(tables) > 1 and len(tables[1]) >= 20:
                t = tables[1]
                col = 3 if year == 2024 else 2
                for idx, row in enumerate(t[3:], start=3):
                    if not row or len(row) <= col:
                        continue
                    tariff_name = row[0] or row[1]
                    val = row[col]

                    # Row 22 in 2024 Table 1 is Bulk Supply to LECO
                    if idx == 22 and val is not None:
                        tariff_name = "Bulk Supply to LECO"

                    if not tariff_name or val is None:
                        continue

                    cleaned_val = self._clean_numeric(val)
                    if cleaned_val is None:
                        continue

                    t_str = str(tariff_name).strip()
                    if t_str.upper() in ("TARIFF", "SALES (GWH)"):
                        continue

                    records.append(
                        TariffSalesRecord(
                            reporting_year=year,
                            tariff_group=t_str,
                            sales_gwh=cleaned_val,
                            sales_mwh=round(cleaned_val * 1000.0, 4),
                            reported_unit_code="GWh",
                        )
                    )
                return records

        return records
