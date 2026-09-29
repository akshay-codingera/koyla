"""
Constants, status codes, and configuration standards for Koyla Backup & Disaster Recovery.
"""
from enum import Enum
from typing import List, Set


BACKUP_SCHEMA_VERSION = "1.0"
BACKUP_METADATA_FILENAME = "metadata.json"
BACKUP_MANIFEST_FILENAME = "manifest.sha256"

# Canonical subdirectories inside a backup archive
BACKUP_POSTGRES_DIR = "postgres"
BACKUP_DOCUMENTS_DIR = "documents"
BACKUP_REPORTS_DIR = "reports"

BACKUP_DATABASE_DUMP_FILENAME = "database.dump"
BACKUP_DATABASE_SQL_FILENAME = "database.sql"


class BackupIntegrityStatus(str, Enum):
    """
    Deterministic integrity verification states for backup archives.
    """
    VALID = "VALID"
    INVALID = "INVALID"
    MISSING_FILE = "MISSING_FILE"
    HASH_MISMATCH = "HASH_MISMATCH"
    CORRUPTED_METADATA = "CORRUPTED_METADATA"
    RESTORE_REFUSED = "RESTORE_REFUSED"


# Standard exclude patterns for transient, cache, and non-durable files
EXCLUDED_PATTERNS: Set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "venv",
    ".venv",
    "dist",
    "build",
    ".cache",
    ".tmp",
    ".temp",
    "quarantine",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    "*.tmp",
    "*.swp",
    "*~",
    ".DS_Store",
    "Thumbs.db",
}
