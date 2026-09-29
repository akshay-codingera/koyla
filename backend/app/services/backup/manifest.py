"""
Manifest builder, file discovery, and cryptographic metadata generation for Koyla Backup.
"""
import fnmatch
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from app.services.backup.constants import (
    BACKUP_MANIFEST_FILENAME,
    BACKUP_METADATA_FILENAME,
    BACKUP_SCHEMA_VERSION,
    EXCLUDED_PATTERNS,
)
from app.services.backup.integrity import calculate_sha256

logger = logging.getLogger(__name__)


@dataclass
class ManifestEntry:
    """
    Canonical representation of a single file in the backup manifest.
    """
    relative_path: str
    size_bytes: int
    sha256: str
    component: str

    def to_manifest_line(self) -> str:
        """Standard sha256sum line format."""
        return f"{self.sha256}  {self.relative_path}\n"


@dataclass
class BackupManifest:
    """
    Cryptographic inventory of all files included within a backup archive.
    """
    entries: List[ManifestEntry] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return len(self.entries)

    @property
    def total_bytes(self) -> int:
        return sum(e.size_bytes for e in self.entries)

    def add_file(self, base_dir: Path, file_path: Path, component: str) -> Optional[ManifestEntry]:
        """
        Computes SHA-256 for a file on disk and adds it to the manifest.
        """
        if not file_path.is_file():
            return None
        rel_path = file_path.relative_to(base_dir).as_posix()
        size = file_path.stat().st_size
        sha = calculate_sha256(file_path)
        entry = ManifestEntry(
            relative_path=rel_path,
            size_bytes=size,
            sha256=sha,
            component=component
        )
        self.entries.append(entry)
        return entry

    def discover_and_add_directory(
        self,
        base_dir: Path,
        source_dir: Path,
        component: str,
        excluded_patterns: Optional[Set[str]] = None
    ) -> int:
        """
        Recursively scans source_dir, skips non-durable and excluded files,
        and registers durable files into the manifest.
        """
        if not source_dir.exists() or not source_dir.is_dir():
            return 0

        excludes = set(EXCLUDED_PATTERNS)
        if excluded_patterns:
            excludes.update(excluded_patterns)

        added = 0
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pat) for pat in excludes)]
            for f in sorted(files):
                if any(fnmatch.fnmatch(f, pat) for pat in excludes):
                    continue
                file_path = Path(root) / f
                if file_path.is_file():
                    self.add_file(base_dir, file_path, component=component)
                    added += 1

        return added

    def write_manifest_file(self, target_dir: Path) -> Path:
        """
        Writes canonical manifest.sha256 to the backup directory.
        Entries are sorted by relative path for deterministic reproducibility.
        """
        manifest_path = target_dir / BACKUP_MANIFEST_FILENAME
        sorted_entries = sorted(self.entries, key=lambda e: e.relative_path)
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(f"# Koyla Backup SHA-256 Manifest v{BACKUP_SCHEMA_VERSION}\n")
            f.write(f"# Generated: {datetime.now(timezone.utc).isoformat()}\n")
            f.write(f"# Total Files: {len(sorted_entries)}\n\n")
            for entry in sorted_entries:
                f.write(entry.to_manifest_line())
        return manifest_path

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [asdict(e) for e in sorted(self.entries, key=lambda x: x.relative_path)]


@dataclass
class BackupMetadata:
    """
    Sanitized, non-sensitive metadata for a Koyla backup package.
    Strictly forbids inclusion of credentials, tokens, or private secrets.
    """
    backup_id: str
    created_at: str
    backup_schema_version: str = BACKUP_SCHEMA_VERSION
    app_version: str = "1.0.0"
    db_engine: str = "postgresql"
    pg_version: Optional[str] = None
    included_components: List[str] = field(default_factory=list)
    file_count: int = 0
    total_bytes: int = 0
    is_compressed: bool = False
    compression_format: Optional[str] = None
    koyla_environment: str = "on-premise"
    extra_properties: Dict[str, Any] = field(default_factory=dict)

    def write_metadata_file(self, target_dir: Path) -> Path:
        """
        Writes sanitized metadata.json to the target backup directory.
        """
        meta_path = target_dir / BACKUP_METADATA_FILENAME
        payload = asdict(self)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return meta_path

    @classmethod
    def load(cls, file_path: Path) -> "BackupMetadata":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
