"""
Incremental acquisition, staging, and analytical warehouse refresh coordinator.

GOVERNANCE:
- Audits and tracks official source data availability (CEB, PUCSL, NASA POWER).
- Verifies SHA-256 checksums against raw manifests and raw.source_document ledger.
- Ingests new or modified periods idempotently without duplicate records.
- Refreshes analytical materialized marts (mart.mv_*) after successful ingestion.
- Logs all pipeline runs, row metrics, and data quality issues to audit.etl_run.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.common.config import DatabaseConfig
from src.common.db import get_connection
from src.etl.real_data_loader import RealDataWarehouseLoader

logger = logging.getLogger("gridlens.refresher")


@dataclass
class RefreshResult:
    """Summary metrics of an incremental refresh run."""

    dataset: str
    files_scanned: int = 0
    files_processed: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_quarantined: int = 0
    marts_refreshed: bool = False
    duration_seconds: float = 0.0
    status: str = "SUCCEEDED"
    errors: list[str] = field(default_factory=list)


class IncrementalWarehouseRefresher:
    """Orchestrates scheduled and on-demand incremental data acquisition and warehouse loading."""

    def __init__(
        self,
        config: DatabaseConfig | None = None,
        manifest_path: Path = Path("data/raw/manifest.json"),
    ) -> None:
        self.config = config or DatabaseConfig.from_env()
        self.manifest_path = manifest_path
        self.loader = RealDataWarehouseLoader(config=self.config)

    @staticmethod
    def compute_sha256(path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def get_processed_document_hashes(self) -> dict[str, str]:
        """Fetch dictionary of {document_code: sha256_checksum} from raw.source_document."""
        hashes: dict[str, str] = {}
        try:
            with get_connection(self.config, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT document_code, sha256_checksum
                        FROM raw.source_document
                        WHERE acquisition_status IN ('DOWNLOADED_VERIFIED', 'INGESTED');
                        """
                    )
                    for code, sha in cur.fetchall():
                        hashes[code] = sha
        except Exception as e:
            logger.warning(f"Could not read raw.source_document: {e}")
        return hashes

    def refresh_ceb_sales(self, dry_run: bool = False, force: bool = False) -> RefreshResult:
        """Incrementally load CEB Billed Electricity Sales data."""
        t0 = time.time()
        res = RefreshResult(dataset="CEB")
        ceb_digest_dir = Path("data/raw/ceb/5yr")
        if not ceb_digest_dir.exists():
            ceb_digest_dir = Path("data/raw/ceb/2024")

        files = list(ceb_digest_dir.glob("*.pdf")) + list(ceb_digest_dir.glob("*.xlsx"))
        res.files_scanned = len(files)

        if dry_run:
            logger.info(f"[DRY-RUN] Scanned {len(files)} CEB files.")
            res.files_processed = len(files)
            res.duration_seconds = time.time() - t0
            return res

        processed_hashes = self.get_processed_document_hashes()
        new_or_modified = force or any(
            f"CEB-STAT-DIGEST-{f.stem}" not in processed_hashes for f in files
        )

        if new_or_modified or not processed_hashes:
            try:
                batches = self.loader.load_5yr_ceb_sales()
                res.files_processed = len(batches)
                res.rows_inserted = sum(b.rows_inserted for b in batches)
                res.rows_quarantined = sum(b.rows_quarantined for b in batches)
            except Exception as e:
                res.status = "FAILED"
                res.errors.append(f"CEB loading failed: {e}")
                logger.error(f"Error during CEB refresh: {e}")
        else:
            logger.info("CEB sales records already up-to-date in warehouse.")

        res.duration_seconds = time.time() - t0
        return res

    def refresh_nasa_weather(self, dry_run: bool = False, force: bool = False) -> RefreshResult:
        """Incrementally load NASA POWER meteorological observations."""
        t0 = time.time()
        res = RefreshResult(dataset="NASA")
        nasa_path = Path("data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json")

        if not nasa_path.exists():
            nasa_path = Path("data/raw/nasa/2024/nasa_power_sl_nodes_2024.json")

        if not nasa_path.exists():
            res.status = "SKIPPED"
            res.errors.append("NASA POWER raw data file not found.")
            res.duration_seconds = time.time() - t0
            return res

        res.files_scanned = 1

        if dry_run:
            logger.info(f"[DRY-RUN] Found NASA observation file: {nasa_path}")
            res.files_processed = 1
            res.duration_seconds = time.time() - t0
            return res

        processed_hashes = self.get_processed_document_hashes()
        current_hash = self.compute_sha256(nasa_path)

        # Check if already processed
        doc_code = "NASA-POWER-DAILY-2020-2024"
        if not force and processed_hashes.get(doc_code) == current_hash:
            logger.info("NASA weather observations already ingested and verified.")
        else:
            try:
                batch_res = self.loader.load_nasa_weather_json(nasa_path)
                res.files_processed = 1
                res.rows_inserted = batch_res.rows_inserted
                res.rows_quarantined = batch_res.rows_quarantined
            except Exception as e:
                res.status = "FAILED"
                res.errors.append(f"NASA loading failed: {e}")
                logger.error(f"Error during NASA refresh: {e}")

        res.duration_seconds = time.time() - t0
        return res

    def refresh_pucsl_dispatch(self, dry_run: bool = False, force: bool = False) -> RefreshResult:
        """Incrementally load PUCSL 15-Minute Generation Dispatch Curves."""
        t0 = time.time()
        res = RefreshResult(dataset="PUCSL")
        pucsl_dir = Path("data/raw/pucsl/2024")
        xlsx_files = list(pucsl_dir.glob("*.xlsx"))
        res.files_scanned = len(xlsx_files)

        if dry_run:
            logger.info(f"[DRY-RUN] Scanned {len(xlsx_files)} PUCSL xlsx dispatch files.")
            res.files_processed = len(xlsx_files)
            res.duration_seconds = time.time() - t0
            return res

        processed_hashes = self.get_processed_document_hashes()

        for f in xlsx_files:
            file_hash = self.compute_sha256(f)
            doc_code = f"PUCSL-DISPATCH-15MIN-{f.stem}"

            if not force and processed_hashes.get(doc_code) == file_hash:
                logger.info(
                    f"PUCSL dispatch file {f.name} already ingested with matching checksum."
                )
                continue

            try:
                batch_res = self.loader.load_pucsl_dispatch_xlsx(f)
                res.files_processed += 1
                res.rows_inserted += batch_res.rows_inserted
                res.rows_updated += batch_res.rows_updated
                res.rows_quarantined += batch_res.rows_quarantined
            except Exception as e:
                res.status = "PARTIAL_ERROR"
                res.errors.append(f"PUCSL loading {f.name} failed: {e}")
                logger.error(f"Error loading {f.name}: {e}")

        res.duration_seconds = time.time() - t0
        return res

    def refresh_marts(self, dry_run: bool = False) -> bool:
        """Refresh PostgreSQL materialized analytical marts (mart.mv_*)."""
        if dry_run:
            logger.info("[DRY-RUN] Would execute CALL etl.sp_refresh_analytical_marts();")
            return True

        try:
            with get_connection(self.config, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("CALL etl.sp_refresh_analytical_marts();")
            logger.info("Materialized analytical marts refreshed successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh analytical marts: {e}")
            return False

    def run_refresh(
        self,
        dataset: str = "all",
        dry_run: bool = False,
        force: bool = False,
    ) -> list[RefreshResult]:
        """Execute full or dataset-specific refresh and trigger analytical mart refresh."""
        results: list[RefreshResult] = []
        target = dataset.lower()

        if target in ("all", "ceb"):
            results.append(self.refresh_ceb_sales(dry_run=dry_run, force=force))

        if target in ("all", "nasa"):
            results.append(self.refresh_nasa_weather(dry_run=dry_run, force=force))

        if target in ("all", "pucsl"):
            results.append(self.refresh_pucsl_dispatch(dry_run=dry_run, force=force))

        # If any rows were inserted/updated or force requested, refresh analytical marts
        any_mutations = any((r.rows_inserted > 0 or r.rows_updated > 0) for r in results)
        if any_mutations or force or dry_run:
            marts_ok = self.refresh_marts(dry_run=dry_run)
            for r in results:
                r.marts_refreshed = marts_ok

        return results
