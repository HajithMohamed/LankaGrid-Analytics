"""
Source-specific extractor for PUCSL Daily Generation Report PDF documents.
Extracts:
1. Technology-wise daily generation mix (MWh) from Table 01
2. Plant-by-plant dispatch and capacity parameters from Table 2
3. System day/night peak demands (MW)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pdfplumber


@dataclass(frozen=True)
class DailyMixRecord:
    """Technology generation mix total for reporting date."""

    reporting_date: date
    category_name: str
    generation_mwh: float
    reported_unit_code: str = "MWh"
    page_number: int = 2


@dataclass(frozen=True)
class PlantGenerationRecord:
    """Station-level daily generation and operating capacity."""

    reporting_date: date
    plant_name: str
    max_capacity_mw: float | None
    available_capacity_mw: float | None
    night_peak_mw: float | None
    generation_mwh: float | None
    reported_unit_code: str = "MWh"
    page_number: int = 4


class PucslPdfParser:
    """Parses PUCSL Daily Generation and Dispatch PDF reports."""

    def __init__(self, default_date: date | None = None) -> None:
        self.default_date = default_date or date(2024, 12, 29)

    @staticmethod
    def _clean_numeric(text: Any) -> float | None:
        if text is None:
            return None
        cleaned = str(text).replace(",", "").replace(" ", "").strip()
        if not cleaned or cleaned in ("-", "N/A", "null"):
            return None
        # Handle parenthesized negative numbers e.g. (424) -> -424
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = f"-{cleaned[1:-1]}"
        try:
            return float(cleaned)
        except ValueError:
            return None

    def extract_daily_generation_mix(self, pdf_path: Path) -> list[DailyMixRecord]:
        """Extract daily generation mix by technology from Page 2 Table 01 (Generation MWh)."""
        records: list[DailyMixRecord] = []
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) < 2:
                return []

            p2 = pdf.pages[1]
            tables = p2.extract_tables()

            # Target Table 1 specifically (Daily Generation MWh), ignoring monthly/yearly GWh tables
            target_table = None
            for tbl in tables:
                header_text = "".join([str(c) for r in tbl[:2] for c in r if c])
                if "Generation (MWh)" in header_text and "Current Month" not in header_text:
                    target_table = tbl
                    break

            if target_table is None and len(tables) > 1:
                target_table = tables[1]

            if target_table:
                for row in target_table:
                    if not row or len(row) < 2:
                        continue
                    cat_candidate = row[0]
                    val_candidate = row[1]
                    if not cat_candidate or not val_candidate:
                        continue

                    cat_str = str(cat_candidate).strip()
                    if "Generation (MWh)" in cat_str or cat_str.upper() in ("CATEGORY", "TOTAL"):
                        continue

                    cleaned_val = self._clean_numeric(val_candidate)
                    if cleaned_val is not None:
                        records.append(
                            DailyMixRecord(
                                reporting_date=self.default_date,
                                category_name=cat_str,
                                generation_mwh=cleaned_val,
                            )
                        )

            # If empty from table extraction, parse raw text lines of Table 01
            if not records:
                text = p2.extract_text() or ""
                lines = text.split("\n")
                in_daily = False
                for line in lines:
                    if "Table 01" in line:
                        in_daily = True
                        continue
                    if "Table 02" in line:
                        in_daily = False
                        break
                    if in_daily:
                        m = re.match(r"^([A-Za-z0-9\s\(\)\+\-\*]+?)\s+([\d,]+(?:\.\d+)?)$", line.strip())
                        if m:
                            cat = m.group(1).strip()
                            val = self._clean_numeric(m.group(2))
                            if val is not None and cat not in ("Generation (MWh)", "Category"):
                                records.append(
                                    DailyMixRecord(
                                        reporting_date=self.default_date,
                                        category_name=cat,
                                        generation_mwh=val,
                                    )
                                )

        return records

    def extract_plant_dispatch_table(self, pdf_path: Path) -> list[PlantGenerationRecord]:
        """Extract plant-by-plant dispatch and capacity from Page 4 Table 2."""
        records: list[PlantGenerationRecord] = []
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) < 4:
                return []

            p4 = pdf.pages[3]
            tables = p4.extract_tables()

            for tbl in tables:
                for row in tbl:
                    if not row or len(row) < 3:
                        continue
                    col0 = row[0]
                    col1 = row[1]
                    col2 = row[2]
                    if not col0 or not col1 or not col2:
                        continue

                    # col0 contains plant name + max capacity, e.g. "Wimalasurendra 50"
                    m0 = re.match(r"^(.*?)\s+([\d,]+(?:\.\d+)?)$", str(col0).strip())
                    if not m0:
                        continue

                    plant_name = m0.group(1).strip()
                    max_cap = self._clean_numeric(m0.group(2))

                    # col1 contains avail cap + night peak, e.g. "50 50" or "54 53"
                    col1_parts = str(col1).strip().split()
                    avail_cap = self._clean_numeric(col1_parts[0]) if col1_parts else None
                    night_peak = self._clean_numeric(col1_parts[1]) if len(col1_parts) > 1 else None

                    # col2 contains plant dispatch MWh, e.g. "311"
                    dispatch_mwh = self._clean_numeric(col2)

                    records.append(
                        PlantGenerationRecord(
                            reporting_date=self.default_date,
                            plant_name=plant_name,
                            max_capacity_mw=max_cap,
                            available_capacity_mw=avail_cap,
                            night_peak_mw=night_peak,
                            generation_mwh=dispatch_mwh,
                            reported_unit_code="MWh",
                            page_number=4,
                        )
                    )

        return records

    def extract_peak_demands(self, pdf_path: Path) -> dict[str, float | None]:
        """Extract night peak demand and day peak demand in MW from Page 5."""
        peaks: dict[str, float | None] = {"night_peak_mw": None, "day_peak_max_mw": None}
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) < 5:
                return peaks

            p5 = pdf.pages[4]
            tables = p5.extract_tables()
            for tbl in tables:
                for row in tbl:
                    if not row or len(row) < 2:
                        continue
                    label = str(row[0]).strip().upper()
                    val = self._clean_numeric(row[1])
                    if val is None:
                        continue

                    if "NIGHT PEAK" in label:
                        peaks["night_peak_mw"] = val
                    elif "DAY PEAK MAXIMUM DEMAND" in label:
                        peaks["day_peak_max_mw"] = val

        return peaks
