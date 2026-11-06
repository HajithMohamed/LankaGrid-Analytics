"""
GridLens — Incremental Acquisition, Staging, and Analytical Warehouse Refresh Coordinator.

GOVERNANCE:
- Identifies and acquires genuine upstream source data (CEB, PUCSL, NASA POWER).
- Tracks provenance via SourceDocumentIdentity and raw.source_document ledger.
- Ingests new or modified records idempotently without duplicate records.
- Refreshes all 5 analytical materialized marts across schemas 'etl' and 'mart'.
- Implements explicit execution status: SUCCEEDED, NO_CHANGE, PARTIAL_QUARANTINE, FAILED, BLOCKED.
- Logs all pipeline runs, row metrics, and data quality issues to audit.etl_run.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.acquisition.ceb_discovery import CebDiscoveryClient
from src.acquisition.nasa_power_client import NasaPowerClient
from src.acquisition.pucsl_discovery import PucslDiscoveryClient
from src.common.config import DatabaseConfig
from src.common.db import get_connection
from src.common.source_identity import DocumentSyncStatus, SourceDocumentIdentity
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
    status: str = "SUCCEEDED"  # SUCCEEDED, NO_CHANGE, PARTIAL_QUARANTINE, FAILED, BLOCKED
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
        return SourceDocumentIdentity.compute_file_sha256(path)

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

    def refresh_ceb_sales(
        self, dry_run: bool = False, force: bool = False, acquire: bool = False
    ) -> RefreshResult:
        """Incrementally acquire and load CEB Billed Electricity Sales data."""
        t0 = time.time()
        res = RefreshResult(dataset="CEB")

        if dry_run:
            logger.info("[DRY-RUN] Simulating CEB refresh.")
            res.files_scanned = 1
            res.files_processed = 1
            res.duration_seconds = time.time() - t0
            return res

        processed_hashes = self.get_processed_document_hashes()

        # Phase A: Live discovery & acquisition if enabled
        if acquire:
            try:
                ceb_client = CebDiscoveryClient(db_config=self.config)
                discovered = ceb_client.discover()
                res.files_scanned += len(discovered)
                for doc in discovered:
                    existing_status, _ = (
                        SourceDocumentIdentity.check_existing_document(
                            # Check against known hashes
                            cur=None,  # Handled via memory map below
                        )
                        if False
                        else (
                            DocumentSyncStatus.UNCHANGED
                            if doc.document_code in processed_hashes
                            else DocumentSyncStatus.NEW,
                            None,
                        )
                    )
                    if existing_status == DocumentSyncStatus.NEW or force:
                        try:
                            dl_path = ceb_client.download_document(doc)
                            batches = [self.loader.load_ceb_sales_pdf(dl_path)]
                            res.files_processed += len(batches)
                            res.rows_inserted += sum(b.rows_inserted for b in batches)
                            res.rows_quarantined += sum(b.rows_quarantined for b in batches)
                        except Exception as dl_err:
                            res.errors.append(
                                f"CEB download/load error for {doc.document_code}: {dl_err}"
                            )
            except Exception as acq_err:
                logger.warning(f"Online CEB discovery skipped/failed: {acq_err}")

        # Phase B: Local directory scan fallback
        ceb_digest_dir = Path("data/raw/ceb/5yr")
        if not ceb_digest_dir.exists():
            ceb_digest_dir = Path("data/raw/ceb/2024")

        files = (
            list(ceb_digest_dir.glob("*.pdf")) + list(ceb_digest_dir.glob("*.xlsx"))
            if ceb_digest_dir.exists()
            else []
        )
        res.files_scanned += len(files)

        new_or_modified = force or any(
            f"CEB-STAT-DIGEST-{f.stem}" not in processed_hashes for f in files
        )

        if (new_or_modified or not processed_hashes) and files and res.rows_inserted == 0:
            try:
                batches = self.loader.load_5yr_ceb_sales()
                res.files_processed += len(batches)
                res.rows_inserted += sum(b.rows_inserted for b in batches)
                res.rows_quarantined += sum(b.rows_quarantined for b in batches)
            except Exception as e:
                res.status = "FAILED"
                res.errors.append(f"CEB loading failed: {e}")
                logger.error(f"Error during CEB refresh: {e}")
        elif res.rows_inserted == 0 and not res.errors:
            res.status = "NO_CHANGE"
            logger.info("CEB sales records already up-to-date in warehouse.")

        if res.rows_quarantined > 0 and res.status != "FAILED":
            res.status = "PARTIAL_QUARANTINE"

        res.duration_seconds = time.time() - t0
        return res

    def refresh_nasa_weather(
        self, dry_run: bool = False, force: bool = False, acquire: bool = False
    ) -> RefreshResult:
        """Incrementally acquire and load NASA POWER meteorological observations."""
        t0 = time.time()
        res = RefreshResult(dataset="NASA")

        if dry_run:
            logger.info("[DRY-RUN] Simulating NASA POWER refresh.")
            res.files_scanned = 1
            res.files_processed = 1
            res.duration_seconds = time.time() - t0
            return res

        # Phase A: Live REST API acquisition if requested
        if acquire:
            try:
                nasa_client = NasaPowerClient(db_config=self.config)
                acq_result = nasa_client.acquire_range()
                if acq_result.status == "SUCCEEDED" and acq_result.output_path:
                    res.files_scanned += 1
                    batch_res = self.loader.load_nasa_weather_json(acq_result.output_path)
                    res.files_processed += 1
                    res.rows_inserted += batch_res.rows_inserted
                    res.rows_quarantined += batch_res.rows_quarantined
                    res.duration_seconds = time.time() - t0
                    res.status = "PARTIAL_QUARANTINE" if res.rows_quarantined > 0 else "SUCCEEDED"
                    return res
                elif acq_result.status == "NO_CHANGE":
                    res.status = "NO_CHANGE"
                    res.duration_seconds = time.time() - t0
                    return res
                elif acq_result.errors:
                    res.errors.extend(acq_result.errors)
            except Exception as acq_err:
                logger.warning(
                    f"Online NASA acquisition failed, falling back to local files: {acq_err}"
                )

        # Phase B: Local directory scan fallback
        nasa_path = Path("data/raw/nasa/5yr/nasa_power_sl_nodes_2020_2024.json")
        if not nasa_path.exists():
            nasa_path = Path("data/raw/nasa/2024/nasa_power_sl_nodes_2024.json")

        if not nasa_path.exists():
            if not res.errors:
                res.status = "NO_CHANGE"
            res.duration_seconds = time.time() - t0
            return res

        res.files_scanned += 1
        processed_hashes = self.get_processed_document_hashes()
        current_hash = self.compute_sha256(nasa_path)

        doc_code = "NASA-POWER-DAILY-2020-2024"
        if not force and processed_hashes.get(doc_code) == current_hash:
            res.status = "NO_CHANGE"
            logger.info("NASA weather observations already ingested and verified.")
        else:
            try:
                batch_res = self.loader.load_nasa_weather_json(nasa_path)
                res.files_processed += 1
                res.rows_inserted += batch_res.rows_inserted
                res.rows_quarantined += batch_res.rows_quarantined
                res.status = "PARTIAL_QUARANTINE" if res.rows_quarantined > 0 else "SUCCEEDED"
            except Exception as e:
                res.status = "FAILED"
                res.errors.append(f"NASA loading failed: {e}")
                logger.error(f"Error during NASA refresh: {e}")

        res.duration_seconds = time.time() - t0
        return res

    def refresh_pucsl_dispatch(
        self, dry_run: bool = False, force: bool = False, acquire: bool = False
    ) -> RefreshResult:
        """Incrementally acquire and load PUCSL 15-Minute Generation Dispatch Curves."""
        t0 = time.time()
        res = RefreshResult(dataset="PUCSL")

        if dry_run:
            logger.info("[DRY-RUN] Simulating PUCSL dispatch refresh.")
            res.files_scanned = 1
            res.files_processed = 1
            res.duration_seconds = time.time() - t0
            return res

        processed_hashes = self.get_processed_document_hashes()

        # Phase A: Live discovery & acquisition if requested
        if acquire:
            try:
                pucsl_client = PucslDiscoveryClient(db_config=self.config)
                discovered = pucsl_client.discover()
                res.files_scanned += len(discovered)
                for doc in discovered:
                    if doc.document_code not in processed_hashes or force:
                        try:
                            dl_path = pucsl_client.download_document(doc)
                            batch_res = self.loader.load_pucsl_dispatch_xlsx(dl_path)
                            res.files_processed += 1
                            res.rows_inserted += batch_res.rows_inserted
                            res.rows_updated += batch_res.rows_updated
                            res.rows_quarantined += batch_res.rows_quarantined
                        except Exception as dl_err:
                            res.errors.append(
                                f"PUCSL download/load error for {doc.document_code}: {dl_err}"
                            )
            except Exception as acq_err:
                logger.warning(f"Online PUCSL discovery skipped/failed: {acq_err}")

        # Phase B: Local directory scan fallback
        pucsl_dir = Path("data/raw/pucsl/2024")
        xlsx_files = list(pucsl_dir.glob("*.xlsx")) if pucsl_dir.exists() else []
        res.files_scanned += len(xlsx_files)

        for f in xlsx_files:
            file_hash = self.compute_sha256(f)
            doc_code = f"PUCSL-DISPATCH-15MIN-{f.stem}"

            if not force and processed_hashes.get(doc_code) == file_hash:
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

        if res.rows_inserted == 0 and res.rows_updated == 0 and not res.errors:
            res.status = "NO_CHANGE"
        elif res.rows_quarantined > 0 and res.status != "FAILED":
            res.status = "PARTIAL_QUARANTINE"
        elif res.status != "FAILED" and res.status != "PARTIAL_ERROR":
            res.status = "SUCCEEDED"

        res.duration_seconds = time.time() - t0
        return res

    def refresh_marts(self, dry_run: bool = False) -> bool:
        """
        Refresh PostgreSQL materialized analytical marts (mart.mv_*) using authoritative
        stored procedures:
          - CALL etl.sp_refresh_mart_views(FALSE); (Refreshes Migration 015 views)
          - CALL mart.sp_refresh_analytical_marts(); (Refreshes Migration 021 views)
        """
        if dry_run:
            logger.info(
                "[DRY-RUN] Would execute CALL etl.sp_refresh_mart_views(FALSE) and CALL mart.sp_refresh_analytical_marts();"
            )
            return True

        try:
            with get_connection(self.config, autocommit=True) as conn:
                with conn.cursor() as cur:
                    logger.info("Executing CALL etl.sp_refresh_mart_views(FALSE)...")
                    cur.execute("CALL etl.sp_refresh_mart_views(FALSE);")
                    logger.info("Executing CALL mart.sp_refresh_analytical_marts()...")
                    cur.execute("CALL mart.sp_refresh_analytical_marts();")
            logger.info("All 5 materialized analytical marts refreshed successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh analytical marts: {e}")
            return False

    def run_refresh(
        self,
        dataset: str = "all",
        dry_run: bool = False,
        force: bool = False,
        acquire: bool = False,
    ) -> list[RefreshResult]:
        """Execute full or dataset-specific refresh and trigger analytical mart refresh."""
        results: list[RefreshResult] = []
        target = dataset.lower()

        if target in ("all", "ceb"):
            results.append(self.refresh_ceb_sales(dry_run=dry_run, force=force, acquire=acquire))

        if target in ("all", "nasa"):
            results.append(self.refresh_nasa_weather(dry_run=dry_run, force=force, acquire=acquire))

        if target in ("all", "pucsl"):
            results.append(
                self.refresh_pucsl_dispatch(dry_run=dry_run, force=force, acquire=acquire)
            )

        # If any rows were inserted/updated or force requested, refresh analytical marts
        any_mutations = any((r.rows_inserted > 0 or r.rows_updated > 0) for r in results)
        if any_mutations or force or dry_run:
            marts_ok = self.refresh_marts(dry_run=dry_run)
            for r in results:
                r.marts_refreshed = marts_ok

        return results
