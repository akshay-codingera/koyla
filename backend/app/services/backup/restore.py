"""
Safe, verified restore orchestrator for Koyla.
Guarantees:
- Strict safety barrier: Refuses restoration into non-empty targets unless force=True.
- Pre-restore cryptographic validation: Verifies manifest and all file hashes before touching destination.
- Atomic-like extraction into isolated temporary workspaces.
- Post-restoration verification of restored durable assets.
- Structured logging with audit traceability.
"""
import json
import logging
import os
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.config import settings
from app.core.logging.timing import timed_operation
from app.services.backup.constants import (
    BACKUP_DATABASE_DUMP_FILENAME,
    BACKUP_DATABASE_SQL_FILENAME,
    BACKUP_DOCUMENTS_DIR,
    BACKUP_MANIFEST_FILENAME,
    BACKUP_METADATA_FILENAME,
    BACKUP_POSTGRES_DIR,
    BACKUP_REPORTS_DIR,
    BackupIntegrityStatus,
)
from app.services.backup.integrity import calculate_sha256, parse_manifest_file, verify_backup
from app.services.backup.manifest import BackupMetadata
from app.services.backup.postgres import PostgresBackupEngine, parse_db_url

logger = logging.getLogger(__name__)

# Type alias for return value of check_target_safety
TupleCheckResult = Tuple[bool, List[str]]


class BackupRestoreService:
    """
    Subsystem responsible for restoring database, durable documents, and reports
    from a verified Koyla backup archive or directory.
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
        db_engine: Optional[PostgresBackupEngine] = None,
    ):
        self.storage_dir = Path(storage_dir or settings.STORAGE_DIR)
        self.reports_dir = Path(reports_dir or settings.REPORTS_DIR)
        self.db_engine = db_engine or PostgresBackupEngine()

    def check_target_safety(
        self,
        dest_storage: Path,
        dest_reports: Path,
        target_db_url: Optional[str] = None
    ) -> TupleCheckResult:
        """
        Evaluates whether destination storage, reports, or database contain existing data.
        Returns (is_occupied, list_of_conflicts).
        """
        conflicts: List[str] = []

        # Check documents directory
        if dest_storage.exists() and any(dest_storage.iterdir()):
            file_count = sum(1 for f in dest_storage.glob("**/*") if f.is_file())
            if file_count > 0:
                conflicts.append(f"Document storage directory '{dest_storage}' contains {file_count} existing file(s)")

        # Check reports directory
        if dest_reports.exists() and any(dest_reports.iterdir()):
            file_count = sum(1 for f in dest_reports.glob("**/*") if f.is_file())
            if file_count > 0:
                conflicts.append(f"Reports directory '{dest_reports}' contains {file_count} existing file(s)")

        # Check target database
        target_params = parse_db_url(target_db_url) if target_db_url else self.db_engine.db_params
        if self.db_engine.check_target_has_tables(target_params):
            conflicts.append(f"Target database '{target_params['raw_url']}' already contains existing tables")

        is_occupied = len(conflicts) > 0
        return is_occupied, conflicts

    def restore_backup(
        self,
        backup_target: Union[str, Path],
        force: bool = False,
        target_storage_dir: Optional[Path] = None,
        target_reports_dir: Optional[Path] = None,
        target_db_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a verified restoration from backup_target.
        Requires force=True if any destination data exists.
        """
        target = Path(backup_target)
        if not target.exists():
            raise FileNotFoundError(f"Backup target '{target}' does not exist.")

        dest_storage = Path(target_storage_dir or self.storage_dir)
        dest_reports = Path(target_reports_dir or self.reports_dir)

        # 1. Safety barrier check
        is_occupied, conflicts = self.check_target_safety(dest_storage, dest_reports, target_db_url)
        if is_occupied and not force:
            err_msg = (
                "Safety barrier triggered: Target environment is not empty. Restoration refused unless force=True. "
                f"Existing conflicts: {'; '.join(conflicts)}"
            )
            logger.warning(
                "Restoration refused: %s", err_msg,
                extra={"event": "restore_refused", "status": BackupIntegrityStatus.RESTORE_REFUSED.value}
            )
            raise RuntimeError(err_msg)

        # 2. Cryptographic Pre-Verification
        logger.info("Executing pre-restore cryptographic verification on '%s'", target)
        verification_report = verify_backup(target)
        if not verification_report.is_valid:
            err_msg = (
                f"Pre-restore cryptographic verification failed ({verification_report.status.value}): "
                f"{verification_report.error_message}"
            )
            logger.error(err_msg, extra={"event": "restore_verification_failed", "status": verification_report.status.value})
            raise ValueError(err_msg)

        # 3. Execution inside isolated workspace
        extra_log = {"backup_path": str(target), "force": force}
        with timed_operation(logger, "restore_started", extra=extra_log) as metrics:
            with tempfile.TemporaryDirectory(prefix="koyla_restore_work_") as tmp_work:
                work_dir = Path(tmp_work)

                # Unpack if compressed archive
                if target.is_file() and target.name.endswith((".tar.gz", ".tar", ".tgz")):
                    with tarfile.open(target, "r:*") as tar:
                        tar.extractall(path=work_dir)
                    resolved_dir = work_dir
                    if not (resolved_dir / BACKUP_METADATA_FILENAME).exists():
                        subdirs = [d for d in resolved_dir.iterdir() if d.is_dir()]
                        if len(subdirs) == 1 and (subdirs[0] / BACKUP_METADATA_FILENAME).exists():
                            resolved_dir = subdirs[0]
                else:
                    resolved_dir = target

                # Load metadata & manifest
                meta_file = resolved_dir / BACKUP_METADATA_FILENAME
                manifest_file = resolved_dir / BACKUP_MANIFEST_FILENAME
                with open(meta_file, "r", encoding="utf-8") as f:
                    metadata_dict = json.load(f)

                manifest_entries = parse_manifest_file(manifest_file)
                manifest_map = {rel_path: sha for sha, rel_path in manifest_entries}

                restored_components = []
                restored_files_count = 0

                # 4. Restore Database
                db_dump = resolved_dir / BACKUP_POSTGRES_DIR / BACKUP_DATABASE_SQL_FILENAME
                if not db_dump.exists():
                    db_dump = resolved_dir / BACKUP_POSTGRES_DIR / BACKUP_DATABASE_DUMP_FILENAME

                if db_dump.exists():
                    logger.info("Restoring database from %s", db_dump)
                    self.db_engine.restore(db_dump, force=force, target_db_url=target_db_url)
                    restored_components.append("database")
                    restored_files_count += 1

                # 5. Restore Documents
                docs_src = resolved_dir / BACKUP_DOCUMENTS_DIR
                if docs_src.exists() and docs_src.is_dir():
                    dest_storage.mkdir(parents=True, exist_ok=True)
                    count = self._copy_tree_verified(docs_src, dest_storage, manifest_map, BACKUP_DOCUMENTS_DIR)
                    restored_components.append("documents")
                    restored_files_count += count
                    logger.info("Restored %d document file(s) into %s", count, dest_storage)

                # 6. Restore Reports
                reports_src = resolved_dir / BACKUP_REPORTS_DIR
                if reports_src.exists() and reports_src.is_dir():
                    dest_reports.mkdir(parents=True, exist_ok=True)
                    count = self._copy_tree_verified(reports_src, dest_reports, manifest_map, BACKUP_REPORTS_DIR)
                    restored_components.append("reports")
                    restored_files_count += count
                    logger.info("Restored %d report file(s) into %s", count, dest_reports)

                metrics["files_restored"] = restored_files_count
                metrics["components"] = restored_components
                metrics["backup_id"] = metadata_dict.get("backup_id")

                logger.info(
                    "Restoration completed successfully from %s (%d files, components: %s)",
                    target,
                    restored_files_count,
                    ", ".join(restored_components),
                    extra={
                        "event": "restore_completed",
                        "backup_id": metadata_dict.get("backup_id"),
                        "files_restored": restored_files_count,
                        "duration_ms": metrics.get("duration_ms", 0),
                    }
                )

                return {
                    "status": "RESTORE_SUCCESS",
                    "backup_id": metadata_dict.get("backup_id"),
                    "files_restored": restored_files_count,
                    "components_restored": restored_components,
                    "verification": verification_report.to_dict(),
                }

    def _copy_tree_verified(
        self,
        src_dir: Path,
        dest_dir: Path,
        manifest_map: Dict[str, str],
        component_prefix: str
    ) -> int:
        """
        Copies all files from src_dir to dest_dir and validates post-copy SHA-256 checksums.
        """
        copied_count = 0
        for root, _, files in os.walk(src_dir):
            rel_dir = Path(root).relative_to(src_dir)
            target_subdir = dest_dir / rel_dir
            target_subdir.mkdir(parents=True, exist_ok=True)

            for f in files:
                src_file = Path(root) / f
                dest_file = target_subdir / f
                shutil.copy2(src_file, dest_file)

                # Compute manifest lookup key: e.g. "documents/subfolder/file.pdf"
                manifest_key = f"{component_prefix}/{(rel_dir / f).as_posix()}"
                expected_sha = manifest_map.get(manifest_key)
                if expected_sha:
                    actual_sha = calculate_sha256(dest_file)
                    if actual_sha.lower() != expected_sha.lower():
                        raise RuntimeError(
                            f"Post-copy verification failure for '{dest_file}': "
                            f"expected {expected_sha}, got {actual_sha}"
                        )
                copied_count += 1

        return copied_count
