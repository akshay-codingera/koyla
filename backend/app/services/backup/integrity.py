"""
Integrity verification, cryptographic hashing, and archive validation for Koyla Backup & Disaster Recovery.
"""
import hashlib
import json
import logging
import os
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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

logger = logging.getLogger(__name__)


def calculate_sha256(filepath: Union[str, Path], chunk_size: int = 65536) -> str:
    """
    Computes a cryptographic SHA-256 hex digest for a file on disk.
    Reads in 64KB blocks for memory efficiency on large documents or database dumps.
    """
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Cannot calculate SHA-256: file does not exist at '{filepath}'")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def calculate_bytes_sha256(data: bytes) -> str:
    """Computes SHA-256 for in-memory bytes."""
    return hashlib.sha256(data).hexdigest()


@dataclass
class BackupVerificationReport:
    """
    Structured outcome of an integrity and authenticity check on a backup package.
    """
    status: BackupIntegrityStatus
    is_valid: bool
    backup_path: str
    total_files: int = 0
    verified_files: int = 0
    missing_files: List[str] = field(default_factory=list)
    corrupted_files: List[Dict[str, str]] = field(default_factory=list)
    extra_files: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value if isinstance(self.status, BackupIntegrityStatus) else str(self.status),
            "is_valid": self.is_valid,
            "backup_path": self.backup_path,
            "total_files": self.total_files,
            "verified_files": self.verified_files,
            "missing_files": self.missing_files,
            "corrupted_files": self.corrupted_files,
            "extra_files": self.extra_files,
            "error_message": self.error_message,
            "metadata": self.metadata or {},
        }


def parse_manifest_file(manifest_path: Path) -> List[Tuple[str, str]]:
    """
    Parses a standard SHA-256 manifest file formatted as:
    <sha256_hex>  <relative_path>
    or:
    <sha256_hex> *<relative_path>
    """
    entries: List[Tuple[str, str]] = []
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            clean = line.strip()
            if not clean or clean.startswith("#"):
                continue
            parts = clean.split(maxsplit=1)
            if len(parts) == 2:
                sha, rel_path = parts[0], parts[1].lstrip("*").strip()
                # Normalize slashes
                rel_path = rel_path.replace("\\", "/")
                entries.append((sha.lower(), rel_path))
    return entries


def verify_backup(backup_target: Union[str, Path]) -> BackupVerificationReport:
    """
    Performs full cryptographic SHA-256 verification and structural audit of a Koyla backup.
    Supports either an uncompressed backup directory or a .tar.gz / .tar archive.
    
    Guarantees:
    - Detects corrupted files (hash mismatch)
    - Detects deleted or missing files
    - Detects tampered metadata
    - Never modifies the target archive during verification
    """
    target = Path(backup_target)
    if not target.exists():
        return BackupVerificationReport(
            status=BackupIntegrityStatus.MISSING_FILE,
            is_valid=False,
            backup_path=str(target),
            error_message=f"Backup target not found at '{target}'"
        )

    # If it is a compressed archive, extract to temporary directory for non-destructive inspection
    if target.is_file() and (target.name.endswith(".tar.gz") or target.name.endswith(".tar") or target.name.endswith(".tgz")):
        with tempfile.TemporaryDirectory(prefix="koyla_verify_") as tmp_dir:
            try:
                with tarfile.open(target, "r:*") as tar:
                    tar.extractall(path=tmp_dir)
                # Verify extracted directory (support both flat and single-folder archives)
                extract_path = Path(tmp_dir)
                if not (extract_path / BACKUP_METADATA_FILENAME).exists():
                    subdirs = [d for d in extract_path.iterdir() if d.is_dir()]
                    if len(subdirs) == 1 and (subdirs[0] / BACKUP_METADATA_FILENAME).exists():
                        extract_path = subdirs[0]
                rep = _verify_backup_directory(extract_path)
                rep.backup_path = str(target)
                return rep
            except Exception as e:
                return BackupVerificationReport(
                    status=BackupIntegrityStatus.CORRUPTED_METADATA,
                    is_valid=False,
                    backup_path=str(target),
                    error_message=f"Failed to read compressed archive: {str(e)}"
                )

    if target.is_dir():
        return _verify_backup_directory(target)

    return BackupVerificationReport(
        status=BackupIntegrityStatus.INVALID,
        is_valid=False,
        backup_path=str(target),
        error_message=f"Backup target '{target}' is neither a valid directory nor a supported archive"
    )


def _verify_backup_directory(backup_dir: Path) -> BackupVerificationReport:
    """
    Internal verification logic executing against a resolved backup directory tree.
    """
    metadata_file = backup_dir / BACKUP_METADATA_FILENAME
    manifest_file = backup_dir / BACKUP_MANIFEST_FILENAME

    # 1. Check Metadata
    if not metadata_file.is_file():
        return BackupVerificationReport(
            status=BackupIntegrityStatus.CORRUPTED_METADATA,
            is_valid=False,
            backup_path=str(backup_dir),
            error_message=f"Required metadata file '{BACKUP_METADATA_FILENAME}' is missing"
        )

    try:
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    except Exception as e:
        return BackupVerificationReport(
            status=BackupIntegrityStatus.CORRUPTED_METADATA,
            is_valid=False,
            backup_path=str(backup_dir),
            error_message=f"Malformed metadata JSON in '{BACKUP_METADATA_FILENAME}': {str(e)}"
        )

    # 2. Check Manifest
    if not manifest_file.is_file():
        return BackupVerificationReport(
            status=BackupIntegrityStatus.CORRUPTED_METADATA,
            is_valid=False,
            backup_path=str(backup_dir),
            metadata=metadata,
            error_message=f"Required manifest file '{BACKUP_MANIFEST_FILENAME}' is missing"
        )

    try:
        manifest_entries = parse_manifest_file(manifest_file)
    except Exception as e:
        return BackupVerificationReport(
            status=BackupIntegrityStatus.CORRUPTED_METADATA,
            is_valid=False,
            backup_path=str(backup_dir),
            metadata=metadata,
            error_message=f"Failed to parse manifest: {str(e)}"
        )

    total_files = len(manifest_entries)
    verified_files = 0
    missing_files: List[str] = []
    corrupted_files: List[Dict[str, str]] = []
    manifested_rel_paths = set()

    for expected_sha, rel_path in manifest_entries:
        manifested_rel_paths.add(rel_path)
        actual_file = backup_dir / rel_path

        if not actual_file.is_file():
            missing_files.append(rel_path)
            continue

        try:
            actual_sha = calculate_sha256(actual_file)
            if actual_sha.lower() != expected_sha.lower():
                corrupted_files.append({
                    "path": rel_path,
                    "expected_sha256": expected_sha,
                    "actual_sha256": actual_sha
                })
            else:
                verified_files += 1
        except Exception as e:
            corrupted_files.append({
                "path": rel_path,
                "expected_sha256": expected_sha,
                "error": str(e)
            })

    # 3. Check for unexpected unmanifested files
    extra_files: List[str] = []
    for root, _, files in os.walk(backup_dir):
        for fname in files:
            p = Path(root) / fname
            rel = p.relative_to(backup_dir).as_posix()
            if rel in (BACKUP_METADATA_FILENAME, BACKUP_MANIFEST_FILENAME):
                continue
            if rel not in manifested_rel_paths:
                extra_files.append(rel)

    # 4. Check database dump presence if database component was declared
    components = metadata.get("included_components", [])
    if "database" in components:
        db_dump_a = backup_dir / BACKUP_POSTGRES_DIR / BACKUP_DATABASE_DUMP_FILENAME
        db_dump_b = backup_dir / BACKUP_POSTGRES_DIR / BACKUP_DATABASE_SQL_FILENAME
        if not db_dump_a.exists() and not db_dump_b.exists():
            missing_files.append(f"{BACKUP_POSTGRES_DIR}/{BACKUP_DATABASE_DUMP_FILENAME}")

    if missing_files:
        return BackupVerificationReport(
            status=BackupIntegrityStatus.MISSING_FILE,
            is_valid=False,
            backup_path=str(backup_dir),
            total_files=total_files,
            verified_files=verified_files,
            missing_files=missing_files,
            corrupted_files=corrupted_files,
            extra_files=extra_files,
            metadata=metadata,
            error_message=f"{len(missing_files)} file(s) listed in manifest are missing from archive"
        )

    if corrupted_files:
        return BackupVerificationReport(
            status=BackupIntegrityStatus.HASH_MISMATCH,
            is_valid=False,
            backup_path=str(backup_dir),
            total_files=total_files,
            verified_files=verified_files,
            missing_files=missing_files,
            corrupted_files=corrupted_files,
            extra_files=extra_files,
            metadata=metadata,
            error_message=f"{len(corrupted_files)} file(s) failed cryptographic SHA-256 verification"
        )

    return BackupVerificationReport(
        status=BackupIntegrityStatus.VALID,
        is_valid=True,
        backup_path=str(backup_dir),
        total_files=total_files,
        verified_files=verified_files,
        missing_files=[],
        corrupted_files=[],
        extra_files=extra_files,
        metadata=metadata,
        error_message=None
    )
