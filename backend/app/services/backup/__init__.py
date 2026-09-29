"""
Koyla Backup, Restore & Disaster Recovery Subsystem.
Provides cryptographic verification, native PostgreSQL dumps, durable document
and report archival, retention management, and safe restore orchestration.
"""
from app.services.backup.backup import BackupService
from app.services.backup.constants import (
    BACKUP_DATABASE_DUMP_FILENAME,
    BACKUP_DATABASE_SQL_FILENAME,
    BACKUP_DOCUMENTS_DIR,
    BACKUP_MANIFEST_FILENAME,
    BACKUP_METADATA_FILENAME,
    BACKUP_POSTGRES_DIR,
    BACKUP_REPORTS_DIR,
    BACKUP_SCHEMA_VERSION,
    BackupIntegrityStatus,
)
from app.services.backup.integrity import (
    BackupVerificationReport,
    calculate_bytes_sha256,
    calculate_sha256,
    parse_manifest_file,
    verify_backup,
)
from app.services.backup.manifest import BackupManifest, BackupMetadata, ManifestEntry
from app.services.backup.postgres import PostgresBackupEngine, parse_db_url, redact_database_url
from app.services.backup.restore import BackupRestoreService

__all__ = [
    "BackupService",
    "BackupRestoreService",
    "PostgresBackupEngine",
    "BackupManifest",
    "ManifestEntry",
    "BackupMetadata",
    "BackupIntegrityStatus",
    "BackupVerificationReport",
    "calculate_sha256",
    "calculate_bytes_sha256",
    "parse_manifest_file",
    "verify_backup",
    "parse_db_url",
    "redact_database_url",
    "BACKUP_SCHEMA_VERSION",
    "BACKUP_METADATA_FILENAME",
    "BACKUP_MANIFEST_FILENAME",
    "BACKUP_POSTGRES_DIR",
    "BACKUP_DOCUMENTS_DIR",
    "BACKUP_REPORTS_DIR",
    "BACKUP_DATABASE_SQL_FILENAME",
    "BACKUP_DATABASE_DUMP_FILENAME",
]
