# Koyla Backup, Restore & Disaster Recovery (H9) Runbook

## 1. Subsystem Mission & Scope

The Koyla Backup & Disaster Recovery subsystem provides a deterministic, local/on-premise mechanism to preserve and restore the platform's state into a clean installation.

### Recovered Subsystems
A canonical Koyla backup archive encapsulates three pillars of application state:
1. **Relational Database (`postgres/database.sql`)**: Full schema, table records, roles, organizations, document metadata, chunk text, pgvector neural embeddings, topic models, visual assets, and audit logs.
2. **Durable Document Storage (`documents/`)**: Original ingested source files (PDFs, XLSX, DOCX, scans, CSVs) preserving relative directory hierarchies.
3. **Generated Reports (`reports/`)**: Historical and statutory generated derivative reports and briefs (`.docx`).

---

## 2. Cryptographic Integrity & Architecture

```
backup_YYYYMMDD_HHMMSS_<id>/
├── postgres/
│   └── database.sql           # Native PostgreSQL dump (--clean --if-exists --no-owner --no-privileges)
├── documents/                 # Durable ingested document files
├── reports/                   # Durable generated reports
├── manifest.sha256            # Cryptographic SHA-256 manifest of all files (64KB chunked)
└── metadata.json              # Sanitized package metadata (ZERO credentials/secrets)
```

### Deterministic Integrity Verification States
Every backup package is verified using `verify_backup(path)` against the cryptographic manifest:

| Status Code | Meaning | Restore Permitted? |
| :--- | :--- | :--- |
| `VALID` | All files present, SHA-256 matches manifest exactly, metadata intact. | **Yes** |
| `MISSING_FILE` | One or more files listed in `manifest.sha256` are missing on disk. | **No** |
| `HASH_MISMATCH` | A file was tampered with, corrupted, or altered after manifest calculation. | **No** |
| `CORRUPTED_METADATA` | `metadata.json` or `manifest.sha256` is missing, unreadable, or malformed. | **No** |
| `INVALID` | Target is neither a valid directory nor a valid `.tar.gz` / `.tar` archive. | **No** |
| `RESTORE_REFUSED` | Safety barrier triggered: destination is non-empty and `force=False`. | **No** |

### Zero-Secret Guarantee
`metadata.json` strictly forbids passwords, tokens, API keys, LDAP credentials, or JWT secrets. Passwords are never written to disk or logs; database credentials are provided exclusively at runtime via process environment variables (`PGPASSWORD`).

---

## 3. Configuration Parameters

The following environment variables control the backup subsystem in `.env` / `backend/app/core/config.py`:

```bash
# Directory where local backup archives are stored
BACKUP_DIR="data/backups"

# Maximum number of backup archives retained before automatic pruning
BACKUP_RETENTION_COUNT=5

# Subsystem inclusion flags
BACKUP_INCLUDE_DATABASE=True
BACKUP_INCLUDE_DOCUMENTS=True
BACKUP_INCLUDE_REPORTS=True

# Durable directories
STORAGE_DIR="storage/documents"
REPORTS_DIR="data/reports"
```

---

## 4. Operational Procedures

### 4.1 Creating a Backup

#### A. Via Admin REST API
```http
POST /api/v1/admin/backup/create
Authorization: Bearer <SYSTEM_ADMIN_JWT>
Content-Type: application/json

{
  "compress": true,
  "include_db": true,
  "include_docs": true,
  "include_reports": true,
  "retention_count": 5
}
```

#### B. Via Python Service / CLI
```python
from app.services.backup import BackupService

service = BackupService()
result = service.create_backup(compress=True)
print(f"Created backup: {result['backup_id']} at {result['path']}")
```

#### C. Native Docker Command
```bash
docker exec -e PGPASSWORD=postgres koyla-backend-1 \
  pg_dump -h postgres -p 5432 -U postgres -d koyla \
  --no-owner --no-privileges --clean --if-exists -f /app/data/backups/manual_db.sql
```

---

### 4.2 Verifying Backup Integrity

Always verify an archive prior to initiating disaster recovery:

#### A. Via Admin REST API
```http
POST /api/v1/admin/backup/verify
Authorization: Bearer <SYSTEM_ADMIN_JWT>
Content-Type: application/json

{
  "backup_path": "data/backups/koyla_backup_20260929_023000_abc123.tar.gz"
}
```

#### B. Programmatic Verification
```python
from app.services.backup import verify_backup

report = verify_backup("data/backups/koyla_backup_20260929_023000_abc123.tar.gz")
if report.is_valid:
    print(f"Backup is VALID ({report.verified_files} files verified)")
else:
    print(f"Integrity check failed: {report.status} - {report.error_message}")
```

---

### 4.3 Restoring from a Backup (Disaster Recovery)

#### Safety Barrier Rule
> **IMPORTANT**: If destination storage contains files or the target database contains tables, restoration **WILL BE REFUSED** (`RESTORE_REFUSED`) unless `force=True` is explicitly specified. This prevents accidental destruction of live data.

#### Clean-Environment Restoration Procedure
1. **Provision Clean Target**: Start clean PostgreSQL and backend containers.
2. **Verify Archive**: Run `verify_backup(archive_path)`.
3. **Execute Restore**:
```python
from app.services.backup import BackupRestoreService

restore_svc = BackupRestoreService()
restore_svc.restore_backup(
    backup_target="data/backups/koyla_backup_20260929_023000_abc123.tar.gz",
    force=False  # Clean target is empty, so force=False succeeds
)
```
4. **Validate Restored System**:
   - Check container health: `GET /api/v1/system/health`
   - Check readiness: `GET /api/v1/system/ready`
   - Test login and view document counts on the dashboard.

---

## 5. Recovery Objectives (RPO & RTO): Measured vs. Targets

### 5.1 Measured Prototype Benchmarks
The backup, verification, and clean-environment restoration cycle was measured using the isolated PostgreSQL test suite (`test_postgres_dr_cycle.py`) on the running Docker stack.

* **Test Conditions & Hardware Profile**:
  * **OS / Runtime**: Debian Linux container (`koyla-backend-1`, Python 3.11.16, `postgresql-client` 17).
  * **Database Engine**: PostgreSQL 16.15 with `pgvector` 0.8.6 (`koyla-postgres-1`).
  * **Test Dataset**: Representative Koyla state comprising relational tables (`organizations`, `users`, `roles`, `documents`, `document_versions`, `document_pages`, `chunks`, `embeddings` with 384-dimensional vector data, `audit_events`, `report_formats`, `reports`, `visual_assets`, `topics`, `topic_analyses`) plus durable document storage (PDF) and statutory reports (DOCX).
* **Empirical Measurements**:
  * **Dataset / Backup Archive Size**: 96,178 bytes (compressed `.tar.gz`).
  * **PostgreSQL Dump Duration (`pg_dump`)**: **132.7 ms**.
  * **Cryptographic SHA-256 Verification (`verify_backup`)**: **2.7 ms**.
  * **Clean PostgreSQL Restore Duration (`psql` + verified file deployment)**: **1,130.7 ms**.
  * **Total Recovery Cycle (Excluding container provision)**: **1,266.1 ms (~1.27 seconds)**.

---

### 5.2 Operational Targets & Illustrative Estimates
The following operational metrics are architectural targets and unbenchmarked estimates:

* **Recovery Point Objective (RPO)**:
  * *Target RPO (Daily Cron)*: **<= 24 hours** (Operational target; actual data loss window depends entirely on the administrator's backup schedule frequency).
  * *Target RPO (Hourly Cron)*: **<= 1 hour** (Operational target for high-frequency operational deployments).
* **Recovery Time Objective (RTO)**:
  * *Clean Container Re-provisioning*: **Target ~1–2 minutes** (Estimated container startup time for `docker compose up -d`).
  * *Prototype Dataset Restoration*: **Measured at 1.27 seconds** (Proven in automated clean-environment test).
  * *Enterprise Scale (~50 GB)*: **Unbenchmarked illustrative estimate of ~5–15 minutes** (Theoretical extrapolation; actual RTO depends on disk I/O throughput, CPU cores, PostgreSQL indexing speed, network transfer bandwidth, and database size. Not verified with a real 50GB dataset in this prototype).

---

## 6. Audit Trail & Traceability

Every backup creation and restore operation generates:
1. **Structured Log Telemetry**: Events `backup_started`, `backup_completed`, `restore_started`, `restore_completed` with `duration_ms`, `backup_id`, `file_count`, and `total_bytes`.
2. **Database Audit Records**: Registered in `audit_events` with `action="BACKUP_CREATE"` or `action="BACKUP_RESTORE"`, tracking the `SYSTEM_ADMIN` actor ID, timestamp, and IP address.
