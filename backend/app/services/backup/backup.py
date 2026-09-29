"""
Backup creation service and retention lifecycle manager for Koyla.
Coordinates database export, document storage harvesting, report archiving,
cryptographic manifest calculation, packaging, and retention pruning.
"""
import fnmatch
import logging
import os
import shutil
import tarfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.core.config import settings
from app.core.logging.timing import timed_operation
from app.services.backup.constants import (
    BACKUP_DATABASE_SQL_FILENAME,
    BACKUP_DOCUMENTS_DIR,
    BACKUP_MANIFEST_FILENAME,
    BACKUP_METADATA_FILENAME,
    BACKUP_POSTGRES_DIR,
    BACKUP_REPORTS_DIR,
    EXCLUDED_PATTERNS,
)
from app.services.backup.integrity import verify_backup
from app.services.backup.manifest import BackupManifest, BackupMetadata
from app.services.backup.postgres import PostgresBackupEngine

logger = logging.getLogger(__name__)


class BackupService:
    """
    Primary coordinator for generating Koyla system backups.
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
        retention_count: Optional[int] = None,
        db_engine: Optional[PostgresBackupEngine] = None,
    ):
        self.storage_dir = Path(storage_dir or settings.STORAGE_DIR)
        self.reports_dir = Path(reports_dir or settings.REPORTS_DIR)
        self.backup_dir = Path(backup_dir or settings.BACKUP_DIR)
        self.retention_count = retention_count or settings.BACKUP_RETENTION_COUNT
        self.db_engine = db_engine or PostgresBackupEngine()

        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        target_dir: Optional[Path] = None,
        compress: bool = True,
        include_db: Optional[bool] = None,
        include_docs: Optional[bool] = None,
        include_reports: Optional[bool] = None,
        custom_retention: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes a complete, verifiable system backup.
        """
        do_db = settings.BACKUP_INCLUDE_DATABASE if include_db is None else include_db
        do_docs = settings.BACKUP_INCLUDE_DOCUMENTS if include_docs is None else include_docs
        do_reports = settings.BACKUP_INCLUDE_REPORTS if include_reports is None else include_reports

        now = datetime.now(timezone.utc)
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        backup_id = f"koyla_backup_{timestamp_str}_{uuid.uuid4().hex[:6]}"

        base_dest = Path(target_dir) if target_dir else self.backup_dir
        base_dest.mkdir(parents=True, exist_ok=True)
        work_dir = base_dest / backup_id
        work_dir.mkdir(parents=True, exist_ok=True)

        included_components = []
        extra_log = {"backup_id": backup_id, "compress": compress}

        with timed_operation(logger, "backup_started", extra=extra_log) as metrics:
            try:
                # 1. Database dump
                if do_db:
                    db_dir = work_dir / BACKUP_POSTGRES_DIR
                    db_dir.mkdir(parents=True, exist_ok=True)
                    db_dump_file = db_dir / BACKUP_DATABASE_SQL_FILENAME
                    self.db_engine.dump(db_dump_file)
                    included_components.append("database")

                # 2. Document storage copy
                if do_docs and self.storage_dir.exists():
                    docs_target = work_dir / BACKUP_DOCUMENTS_DIR
                    docs_target.mkdir(parents=True, exist_ok=True)
                    self._copy_directory_contents(self.storage_dir, docs_target, EXCLUDED_PATTERNS)
                    included_components.append("documents")

                # 3. Reports storage copy
                if do_reports and self.reports_dir.exists():
                    reports_target = work_dir / BACKUP_REPORTS_DIR
                    reports_target.mkdir(parents=True, exist_ok=True)
                    self._copy_directory_contents(self.reports_dir, reports_target, EXCLUDED_PATTERNS)
                    included_components.append("reports")

                # 4. Generate manifest
                manifest = BackupManifest()
                manifest.discover_and_add_directory(work_dir, work_dir, component="backup_tree")
                manifest.write_manifest_file(work_dir)

                # 5. Generate sanitized metadata
                metadata = BackupMetadata(
                    backup_id=backup_id,
                    created_at=now.isoformat(),
                    db_engine="postgresql" if self.db_engine.is_postgres else "sqlite",
                    included_components=included_components,
                    file_count=manifest.file_count,
                    total_bytes=manifest.total_bytes,
                    is_compressed=compress,
                    compression_format="tar.gz" if compress else None,
                    koyla_environment=settings.ENVIRONMENT,
                )
                metadata.write_metadata_file(work_dir)

                # 6. Archive compression if enabled
                final_path: Path
                if compress:
                    archive_path = base_dest / f"{backup_id}.tar.gz"
                    with tarfile.open(archive_path, "w:gz") as tar:
                        for item in work_dir.iterdir():
                            tar.add(item, arcname=item.name)
                    # Cleanup uncompressed working directory
                    shutil.rmtree(work_dir, ignore_errors=True)
                    final_path = archive_path
                else:
                    final_path = work_dir

                # 7. Post-backup immediate verification
                verification_report = verify_backup(final_path)
                if not verification_report.is_valid:
                    raise RuntimeError(
                        f"Post-backup integrity self-check failed for {backup_id}: "
                        f"{verification_report.error_message}"
                    )

                # 8. Apply retention policy
                retention_to_use = custom_retention if custom_retention is not None else self.retention_count
                pruned_items = self.apply_retention_policy(keep_count=retention_to_use)

                # Metrics update
                metrics["total_files"] = manifest.file_count
                metrics["total_bytes"] = manifest.total_bytes
                metrics["backup_path"] = str(final_path)
                metrics["pruned_count"] = len(pruned_items)

                logger.info(
                    "System backup %s created successfully (%d files, %d bytes) at %s",
                    backup_id,
                    manifest.file_count,
                    manifest.total_bytes,
                    final_path,
                    extra={
                        "event": "backup_completed",
                        "backup_id": backup_id,
                        "file_count": manifest.file_count,
                        "total_bytes": manifest.total_bytes,
                        "duration_ms": metrics.get("duration_ms", 0),
                    }
                )

                return {
                    "backup_id": backup_id,
                    "path": str(final_path),
                    "created_at": now.isoformat(),
                    "is_compressed": compress,
                    "compression_format": "tar.gz" if compress else None,
                    "file_count": manifest.file_count,
                    "total_bytes": manifest.total_bytes,
                    "included_components": included_components,
                    "integrity_status": verification_report.status.value,
                    "pruned_backups": pruned_items,
                }

            except Exception as exc:
                # Cleanup on failure
                if work_dir.exists():
                    shutil.rmtree(work_dir, ignore_errors=True)
                logger.error(
                    "System backup generation failed for %s: %s",
                    backup_id,
                    str(exc),
                    extra={"event": "backup_failed", "backup_id": backup_id, "error": str(exc)}
                )
                raise

    def apply_retention_policy(self, keep_count: Optional[int] = None) -> List[str]:
        """
        Enforces retention policy by removing the oldest backups beyond keep_count.
        Never removes the current active backup.
        """
        limit = keep_count if keep_count is not None else self.retention_count
        if limit <= 0:
            return []

        all_backups = self._discover_backup_artifacts(self.backup_dir)
        if len(all_backups) <= limit:
            return []

        # Sort by modification time ascending (oldest first)
        all_backups.sort(key=lambda p: p.stat().st_mtime)
        excess_count = len(all_backups) - limit
        to_prune = all_backups[:excess_count]

        pruned: List[str] = []
        for item in to_prune:
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                pruned.append(item.name)
                logger.info("Pruned old backup artifact according to retention limit (%d): %s", limit, item.name)
            except Exception as e:
                logger.warning("Failed to prune backup artifact %s: %s", item.name, str(e))

        return pruned

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Lists all available backup packages in the backup directory with basic metadata.
        """
        artifacts = self._discover_backup_artifacts(self.backup_dir)
        # Sort by mtime descending (newest first)
        artifacts.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        results: List[Dict[str, Any]] = []
        for art in artifacts:
            stat = art.stat()
            created_iso = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            is_comp = art.is_file() and art.name.endswith((".tar.gz", ".tar"))
            backup_id = art.name.replace(".tar.gz", "").replace(".tar", "")
            size = stat.st_size if art.is_file() else sum(f.stat().st_size for f in art.glob("**/*") if f.is_file())

            results.append({
                "backup_id": backup_id,
                "path": str(art),
                "name": art.name,
                "is_compressed": is_comp,
                "size_bytes": size,
                "created_at": created_iso,
            })

        return results

    def _discover_backup_artifacts(self, directory: Path) -> List[Path]:
        """Finds all valid backup candidates (tarballs or backup directories)."""
        if not directory.exists():
            return []
        items = []
        for p in directory.iterdir():
            if p.name.startswith("koyla_backup_") or p.name.startswith("backup_"):
                if p.is_file() and p.name.endswith((".tar.gz", ".tar")):
                    items.append(p)
                elif p.is_dir():
                    items.append(p)
        return items

    def _copy_directory_contents(self, src: Path, dest: Path, exclude_patterns: Set[str]) -> None:
        """Copies durable files recursively, filtering out transient / non-durable files."""
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pat) for pat in exclude_patterns)]
            rel_dir = Path(root).relative_to(src)
            target_subdir = dest / rel_dir
            target_subdir.mkdir(parents=True, exist_ok=True)

            for f in files:
                if any(fnmatch.fnmatch(f, pat) for pat in exclude_patterns):
                    continue
                src_file = Path(root) / f
                if src_file.is_file():
                    shutil.copy2(src_file, target_subdir / f)
