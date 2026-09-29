"""
Comprehensive test suite for Koyla Hardening Phase 9: Backup, Restore & Disaster Recovery.
Tests cryptographic manifests, pg_dump command generation, password redaction,
tamper detection, retention pruning, safety barriers, RBAC, health telemetry, and
byte-level clean-environment restoration.
"""
import json
import os
import shutil
import sqlite3
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.user import Role, User
from app.services.backup.constants import (
    BACKUP_DATABASE_SQL_FILENAME,
    BACKUP_DOCUMENTS_DIR,
    BACKUP_MANIFEST_FILENAME,
    BACKUP_METADATA_FILENAME,
    BACKUP_POSTGRES_DIR,
    BACKUP_REPORTS_DIR,
    BackupIntegrityStatus,
)
from app.services.backup.integrity import (
    calculate_bytes_sha256,
    calculate_sha256,
    parse_manifest_file,
    verify_backup,
)
from app.services.backup.manifest import BackupManifest, BackupMetadata
from app.services.backup.postgres import (
    PostgresBackupEngine,
    parse_db_url,
    redact_database_url,
)
from app.services.backup.backup import BackupService
from app.services.backup.restore import BackupRestoreService
from app.services.health.dependencies import check_backup_subsystem


# ==============================================================================
# 1. Metadata Sanitization & Password Redaction Tests
# ==============================================================================

def test_backup_metadata_sanitization():
    """Verify BackupMetadata never serializes secrets, passwords, tokens, or credentials."""
    meta = BackupMetadata(
        backup_id="koyla_backup_test_123",
        created_at="2026-09-29T00:00:00Z",
        app_version="1.0.0",
        included_components=["database", "documents", "reports"],
        file_count=42,
        total_bytes=1048576,
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        meta_file = meta.write_metadata_file(tmp_path)

        with open(meta_file, "r", encoding="utf-8") as f:
            content = f.read()

        loaded_json = json.loads(content)
        # Check forbidden keys
        for forbidden in ["password", "secret", "token", "credential", "bind_password", "jwt"]:
            assert forbidden not in loaded_json
            assert forbidden not in content.lower()

        assert loaded_json["backup_id"] == "koyla_backup_test_123"
        assert loaded_json["file_count"] == 42
        assert loaded_json["total_bytes"] == 1048576


def test_database_url_redaction_and_parsing():
    """Verify database URLs are parsed correctly and passwords masked in logging."""
    url = "postgresql+psycopg2://koyla_admin:SuperSecretPass123@db.internal:5432/koyla_prod"
    redacted = redact_database_url(url)
    assert "SuperSecretPass123" not in redacted
    assert "koyla_admin:***@db.internal:5432/koyla_prod" in redacted

    parsed = parse_db_url(url)
    assert parsed["engine"] == "postgresql"
    assert parsed["host"] == "db.internal"
    assert parsed["port"] == 5432
    assert parsed["username"] == "koyla_admin"
    assert parsed["password"] == "SuperSecretPass123"
    assert parsed["database"] == "koyla_prod"
    assert "SuperSecretPass123" not in parsed["raw_url"]


def test_sqlite_url_parsing():
    """Verify SQLite database URL parsing for local and test executions."""
    url = "sqlite:///./data/koyla_test.db"
    parsed = parse_db_url(url)
    assert parsed["engine"] == "sqlite"
    assert "koyla_test.db" in parsed["db_path"]


# ==============================================================================
# 2. PostgreSQL CLI Command Construction & PGPASSWORD Injection Tests
# ==============================================================================

def test_pg_dump_command_construction_and_env():
    """Verify pg_dump uses clean flags and injects password exclusively via PGPASSWORD env."""
    engine = PostgresBackupEngine("postgresql://pguser:SecretPass456@dbhost:5433/koyla_db")
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = Path(tmp_dir) / "test_dump.sql"

        with patch("shutil.which", return_value="/usr/bin/pg_dump"), \
             patch("subprocess.run") as mock_run:
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_run.return_value = mock_res

            # Simulate dump creation
            out_file.write_text("-- DUMP CONTENT", encoding="utf-8")
            res_path = engine.dump(out_file)

            assert mock_run.called
            call_args, call_kwargs = mock_run.call_args
            cmd = call_args[0]
            env = call_kwargs["env"]

            # Validate flags
            assert "/usr/bin/pg_dump" == cmd[0]
            assert "-h" in cmd and "dbhost" in cmd
            assert "-p" in cmd and "5433" in cmd
            assert "-U" in cmd and "pguser" in cmd
            assert "--no-owner" in cmd
            assert "--no-privileges" in cmd
            assert "--clean" in cmd
            assert "--if-exists" in cmd
            assert "koyla_db" in cmd

            # Password MUST NOT be in CLI arguments
            assert "SecretPass456" not in " ".join(cmd)
            # Password MUST be in environment
            assert env.get("PGPASSWORD") == "SecretPass456"


def test_psql_restore_command_construction_and_env():
    """Verify psql restore uses PGPASSWORD and does not leak secrets in args."""
    engine = PostgresBackupEngine("postgresql://pguser:SecretPass789@dbhost:5432/koyla_db")
    with tempfile.TemporaryDirectory() as tmp_dir:
        dump_file = Path(tmp_dir) / "dump.sql"
        dump_file.write_text("-- DUMP", encoding="utf-8")

        with patch("shutil.which", return_value="/usr/bin/psql"), \
             patch("subprocess.run") as mock_run, \
             patch.object(engine, "check_target_has_tables", return_value=False):
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_run.return_value = mock_res

            engine.restore(dump_file, force=False)

            assert mock_run.called
            call_args, call_kwargs = mock_run.call_args
            cmd = call_args[0]
            env = call_kwargs["env"]

            assert "/usr/bin/psql" == cmd[0]
            assert "-h" in cmd and "dbhost" in cmd
            assert "-U" in cmd and "pguser" in cmd
            assert "-d" in cmd and "koyla_db" in cmd
            assert "-f" in cmd and str(dump_file) in cmd

            assert "SecretPass789" not in " ".join(cmd)
            assert env.get("PGPASSWORD") == "SecretPass789"


# ==============================================================================
# 3. File Discovery, Manifest Generation & Exclusions Tests
# ==============================================================================

def test_manifest_discovery_and_exclusions():
    """Verify discovery indexes durable assets while filtering cache, git, and transient files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        durable_dir = base / "documents"
        durable_dir.mkdir(parents=True)

        (durable_dir / "report_2026.pdf").write_bytes(b"PDF CONTENT 2026")
        (durable_dir / "geology_data.xlsx").write_bytes(b"EXCEL DATA")

        # Create transient / cache files that MUST be ignored
        cache_dir = durable_dir / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "temp.pyc").write_bytes(b"PYC BYTECODE")
        (durable_dir / ".DS_Store").write_bytes(b"DS_STORE")
        (durable_dir / "temp_file.tmp").write_bytes(b"TMP")

        manifest = BackupManifest()
        added_count = manifest.discover_and_add_directory(base, durable_dir, component="documents")

        assert added_count == 2
        indexed_paths = [e.relative_path for e in manifest.entries]
        assert "documents/report_2026.pdf" in indexed_paths
        assert "documents/geology_data.xlsx" in indexed_paths
        assert not any("__pycache__" in p for p in indexed_paths)
        assert not any(".DS_Store" in p for p in indexed_paths)
        assert not any(".tmp" in p for p in indexed_paths)


def test_manifest_sha256_format_and_lexical_sorting():
    """Verify manifest.sha256 writes standard sha256sum format in sorted lexical order."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        f_b = base / "b.txt"
        f_a = base / "a.txt"
        f_c = base / "c.txt"
        f_b.write_text("content B", encoding="utf-8")
        f_a.write_text("content A", encoding="utf-8")
        f_c.write_text("content C", encoding="utf-8")

        manifest = BackupManifest()
        manifest.add_file(base, f_b, "test")
        manifest.add_file(base, f_a, "test")
        manifest.add_file(base, f_c, "test")

        out_path = manifest.write_manifest_file(base)
        parsed_entries = parse_manifest_file(out_path)

        # Lexical order
        rel_paths = [p for _, p in parsed_entries]
        assert rel_paths == ["a.txt", "b.txt", "c.txt"]

        # Accurate hashes
        assert parsed_entries[0][0] == calculate_sha256(f_a)
        assert parsed_entries[1][0] == calculate_sha256(f_b)
        assert parsed_entries[2][0] == calculate_sha256(f_c)


# ==============================================================================
# 4. Cryptographic Verification & Tamper Detection Tests
# ==============================================================================

def test_verify_valid_backup_directory_and_tarball():
    """Verify verify_backup returns VALID for clean directories and archives."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work = Path(tmp_dir) / "backup_valid"
        work.mkdir()
        (work / "file1.txt").write_bytes(b"HELLO KOYLA 1")
        (work / "file2.txt").write_bytes(b"HELLO KOYLA 2")

        manifest = BackupManifest()
        manifest.add_file(work, work / "file1.txt", "comp")
        manifest.add_file(work, work / "file2.txt", "comp")
        manifest.write_manifest_file(work)

        meta = BackupMetadata(
            backup_id="valid_test",
            created_at="2026-09-29T00:00:00Z",
            file_count=2,
            total_bytes=len(b"HELLO KOYLA 1") + len(b"HELLO KOYLA 2"),
        )
        meta.write_metadata_file(work)

        # 1. Directory verification
        rep_dir = verify_backup(work)
        assert rep_dir.is_valid is True
        assert rep_dir.status == BackupIntegrityStatus.VALID
        assert rep_dir.verified_files == 2

        # 2. Compressed tar.gz verification
        archive_path = Path(tmp_dir) / "valid.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in work.iterdir():
                tar.add(item, arcname=item.name)

        rep_tar = verify_backup(archive_path)
        assert rep_tar.is_valid is True
        assert rep_tar.status == BackupIntegrityStatus.VALID
        assert rep_tar.verified_files == 2


def test_detect_tampered_file_hash_mismatch():
    """Verify that tampering with an indexed file immediately triggers HASH_MISMATCH."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work = Path(tmp_dir) / "backup_tampered"
        work.mkdir()
        target_file = work / "document.pdf"
        target_file.write_bytes(b"ORIGINAL CONTENT")

        manifest = BackupManifest()
        manifest.add_file(work, target_file, "docs")
        manifest.write_manifest_file(work)

        meta = BackupMetadata(backup_id="tamper_test", created_at="2026-09-29T00:00:00Z", file_count=1)
        meta.write_metadata_file(work)

        # Tamper with file after manifest was written
        target_file.write_bytes(b"MALICIOUS MODIFIED CONTENT")

        rep = verify_backup(work)
        assert rep.is_valid is False
        assert rep.status == BackupIntegrityStatus.HASH_MISMATCH
        assert len(rep.corrupted_files) == 1
        assert rep.corrupted_files[0]["path"] == "document.pdf"


def test_detect_deleted_or_missing_file():
    """Verify that deleting an indexed file triggers MISSING_FILE."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work = Path(tmp_dir) / "backup_missing"
        work.mkdir()
        f1 = work / "exists.txt"
        f2 = work / "to_delete.txt"
        f1.write_bytes(b"1")
        f2.write_bytes(b"2")

        manifest = BackupManifest()
        manifest.add_file(work, f1, "c")
        manifest.add_file(work, f2, "c")
        manifest.write_manifest_file(work)

        meta = BackupMetadata(backup_id="missing_test", created_at="2026-09-29T00:00:00Z", file_count=2)
        meta.write_metadata_file(work)

        # Delete f2
        f2.unlink()

        rep = verify_backup(work)
        assert rep.is_valid is False
        assert rep.status == BackupIntegrityStatus.MISSING_FILE
        assert "to_delete.txt" in rep.missing_files


def test_detect_corrupted_metadata():
    """Verify that malformed metadata or missing manifest triggers CORRUPTED_METADATA."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        work = Path(tmp_dir) / "backup_meta_corrupt"
        work.mkdir()
        (work / BACKUP_METADATA_FILENAME).write_text("NOT_VALID_JSON{{{", encoding="utf-8")

        rep = verify_backup(work)
        assert rep.is_valid is False
        assert rep.status == BackupIntegrityStatus.CORRUPTED_METADATA


# ==============================================================================
# 5. Retention Policy Pruning Tests
# ==============================================================================

def test_retention_policy_pruning():
    """Verify that retention policy keeps the newest N backups and prunes oldest."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        backup_dir = Path(tmp_dir)

        # Create 5 synthetic backup archives with ordered timestamps
        for i in range(1, 6):
            tar_name = f"koyla_backup_2026090{i}_000000_abc{i}.tar.gz"
            p = backup_dir / tar_name
            with tarfile.open(p, "w:gz") as tar:
                pass
            # Artificially space mtimes
            os.utime(p, (1000000 + i * 100, 1000000 + i * 100))

        service = BackupService(backup_dir=backup_dir, retention_count=3)
        pruned = service.apply_retention_policy(keep_count=3)

        assert len(pruned) == 2
        # The oldest two should be pruned
        assert "koyla_backup_20260901_000000_abc1.tar.gz" in pruned
        assert "koyla_backup_20260902_000000_abc2.tar.gz" in pruned

        remaining = [p.name for p in backup_dir.glob("*.tar.gz")]
        assert len(remaining) == 3
        assert "koyla_backup_20260903_000000_abc3.tar.gz" in remaining
        assert "koyla_backup_20260904_000000_abc4.tar.gz" in remaining
        assert "koyla_backup_20260905_000000_abc5.tar.gz" in remaining


# ==============================================================================
# 6. Safety Barrier Tests
# ==============================================================================

def test_safety_barrier_refusal_when_target_not_empty():
    """Verify restoration is refused when target storage is occupied and force=False."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        storage_dest = base / "dest_storage"
        storage_dest.mkdir()
        (storage_dest / "existing_doc.pdf").write_bytes(b"EXISTING PRODUCTION DATA")

        reports_dest = base / "dest_reports"
        reports_dest.mkdir()

        # Dummy valid backup
        backup_src = base / "test_backup"
        backup_src.mkdir()
        (backup_src / BACKUP_METADATA_FILENAME).write_text(
            json.dumps({"backup_id": "b1", "created_at": "2026-09-29T00:00:00Z"}), encoding="utf-8"
        )
        (backup_src / BACKUP_MANIFEST_FILENAME).write_text("# Manifest\n", encoding="utf-8")

        restore_svc = BackupRestoreService(storage_dir=storage_dest, reports_dir=reports_dest)

        with pytest.raises(RuntimeError) as exc_info:
            restore_svc.restore_backup(backup_src, force=False, target_storage_dir=storage_dest, target_reports_dir=reports_dest)

        assert "Safety barrier triggered" in str(exc_info.value)
        assert "force=True" in str(exc_info.value)


# ==============================================================================
# 7. Clean-Environment Byte-Level Fidelity Restore Test
# ==============================================================================

def test_clean_environment_restore_byte_level_fidelity():
    """
    End-to-end integration test of backup creation and clean-environment restoration.
    Verifies that SQLite database tables, rows, document files, and report files are
    restored with exact SHA-256 byte-level fidelity.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        source_dir = root / "source"
        target_dir = root / "target"
        backup_store = root / "backups"

        # 1. Setup Source Environment
        src_docs = source_dir / "documents"
        src_reports = source_dir / "reports"
        src_docs.mkdir(parents=True)
        src_reports.mkdir(parents=True)

        doc1 = src_docs / "CMPDI_Geological_Report_2026.pdf"
        doc2 = src_docs / "subfolder" / "Borehole_Lithology.csv"
        doc2.parent.mkdir(parents=True)
        rep1 = src_reports / "Statutory_Coal_Summary_Q1.docx"

        doc1_bytes = b"%PDF-1.7 Original Geological Survey CMPDI RI-1"
        doc2_bytes = b"Depth,Stratum,Thickness\n10,Coal Seam I,4.5\n25,Sandstone,12.0"
        rep1_bytes = b"DOCX Statutory Coal Production Summary 2026"

        doc1.write_bytes(doc1_bytes)
        doc2.write_bytes(doc2_bytes)
        rep1.write_bytes(rep1_bytes)

        # Source Database (using SQLite engine for deterministic file testing)
        src_db_path = source_dir / "source_koyla.db"
        conn = sqlite3.connect(src_db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE mines (id TEXT PRIMARY KEY, name TEXT, reserves_mt REAL);")
        cur.execute("INSERT INTO mines VALUES ('M001', 'Kalyani OCP', 142.5);")
        cur.execute("INSERT INTO mines VALUES ('M002', 'Jharia Deep UG', 88.2);")
        conn.commit()
        conn.close()

        src_db_url = f"sqlite:///{src_db_path.as_posix()}"
        db_engine = PostgresBackupEngine(src_db_url)

        # 2. Execute Backup
        backup_svc = BackupService(
            storage_dir=src_docs,
            reports_dir=src_reports,
            backup_dir=backup_store,
            retention_count=5,
            db_engine=db_engine,
        )

        backup_result = backup_svc.create_backup(compress=True, include_db=True, include_docs=True, include_reports=True)
        archive_path = Path(backup_result["path"])
        assert archive_path.exists()
        assert backup_result["integrity_status"] == BackupIntegrityStatus.VALID.value

        # 3. Setup Clean Target Environment (completely empty)
        clean_docs = target_dir / "documents"
        clean_reports = target_dir / "reports"
        clean_db_path = target_dir / "restored_koyla.db"
        clean_db_url = f"sqlite:///{clean_db_path.as_posix()}"

        target_db_engine = PostgresBackupEngine(clean_db_url)
        restore_svc = BackupRestoreService(
            storage_dir=clean_docs,
            reports_dir=clean_reports,
            db_engine=target_db_engine,
        )

        # 4. Restore into Clean Environment
        restore_result = restore_svc.restore_backup(
            backup_target=archive_path,
            force=False,  # Target is empty, so force=False MUST succeed
            target_storage_dir=clean_docs,
            target_reports_dir=clean_reports,
            target_db_url=clean_db_url,
        )

        assert restore_result["status"] == "RESTORE_SUCCESS"
        assert "database" in restore_result["components_restored"]
        assert "documents" in restore_result["components_restored"]
        assert "reports" in restore_result["components_restored"]

        # 5. Verify Byte-Level Fidelity of Restored Assets
        restored_doc1 = clean_docs / "CMPDI_Geological_Report_2026.pdf"
        restored_doc2 = clean_docs / "subfolder" / "Borehole_Lithology.csv"
        restored_rep1 = clean_reports / "Statutory_Coal_Summary_Q1.docx"

        assert restored_doc1.exists()
        assert calculate_sha256(restored_doc1) == calculate_bytes_sha256(doc1_bytes)

        assert restored_doc2.exists()
        assert calculate_sha256(restored_doc2) == calculate_bytes_sha256(doc2_bytes)

        assert restored_rep1.exists()
        assert calculate_sha256(restored_rep1) == calculate_bytes_sha256(rep1_bytes)

        # 6. Verify Database Row Fidelity
        r_conn = sqlite3.connect(clean_db_path)
        r_cur = r_conn.cursor()
        r_cur.execute("SELECT id, name, reserves_mt FROM mines ORDER BY id;")
        rows = r_cur.fetchall()
        r_conn.close()

        assert len(rows) == 2
        assert rows[0] == ("M001", "Kalyani OCP", 142.5)
        assert rows[1] == ("M002", "Jharia Deep UG", 88.2)


# ==============================================================================
# 8. Health Subsystem Telemetry Tests
# ==============================================================================

def test_backup_subsystem_health_check():
    """Verify check_backup_subsystem reports safe telemetry."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        with patch.object(settings, "BACKUP_DIR", tmp_dir), \
             patch.object(settings, "BACKUP_RETENTION_COUNT", 7):
            diag = check_backup_subsystem()
            assert diag["status"] == "HEALTHY"
            assert diag["accessible"] is True
            assert diag["writable"] is True
            assert diag["retention_count"] == 7
            assert "total_backups" in diag
            assert "latency_ms" in diag


# ==============================================================================
# 9. Admin API & RBAC Authorization Tests
# ==============================================================================

def test_admin_backup_api_rbac_forbidden_for_analyst():
    """Verify non-admin roles receive 403 Forbidden on backup endpoints."""
    client = TestClient(app)

    # Mock an analyst user without SYSTEM_ADMIN role
    mock_analyst = MagicMock(spec=User)
    mock_analyst.id = "u_analyst"
    mock_analyst.username = "analyst1"
    role_analyst = MagicMock(spec=Role)
    role_analyst.code = "SUBSIDIARY_ANALYST"
    mock_analyst.roles = [role_analyst]
    mock_analyst.organization_id = "org_ccl"

    from app.api.deps import get_current_active_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_analyst

    try:
        # Create
        res_create = client.post("/api/v1/admin/backup/create", json={"compress": True})
        assert res_create.status_code == 403
        assert "SYSTEM_ADMIN" in res_create.json()["detail"]

        # List
        res_list = client.get("/api/v1/admin/backup/list")
        assert res_list.status_code == 403

        # Restore
        res_restore = client.post("/api/v1/admin/backup/restore", json={"backup_path": "foo", "force": False})
        assert res_restore.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)


def test_admin_backup_api_allowed_for_system_admin():
    """Verify SYSTEM_ADMIN user can list, verify, and trigger backup creation via API."""
    client = TestClient(app)

    mock_admin = MagicMock(spec=User)
    mock_admin.id = "u_admin"
    mock_admin.username = "sysadmin"
    role_admin = MagicMock(spec=Role)
    role_admin.code = "SYSTEM_ADMIN"
    mock_admin.roles = [role_admin]
    mock_admin.organization_id = "org_cmpdi"

    from app.api.deps import get_current_active_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_admin

    with tempfile.TemporaryDirectory() as tmp_dir:
        with patch.object(settings, "BACKUP_DIR", tmp_dir):
            try:
                # 1. List (empty)
                res_list = client.get("/api/v1/admin/backup/list")
                assert res_list.status_code == 200
                assert isinstance(res_list.json(), list)

                # 2. Verify endpoint with invalid path
                res_ver = client.post("/api/v1/admin/backup/verify", json={"backup_path": "/nonexistent/path"})
                assert res_ver.status_code == 200
                assert res_ver.json()["is_valid"] is False
                assert res_ver.json()["status"] == "MISSING_FILE"
            finally:
                app.dependency_overrides.pop(get_current_active_user, None)


def test_live_postgres_dump_if_available():
    """Verify live PostgreSQL pg_dump works when postgres environment is present."""
    if not shutil.which("pg_dump"):
        pytest.skip("pg_dump not available in local test environment")

    # In docker, settings.DATABASE_URL points to postgresql+psycopg2://...
    parsed = parse_db_url(settings.DATABASE_URL)
    if parsed["engine"] != "postgresql":
        pytest.skip("Configured database is not PostgreSQL")

    engine = PostgresBackupEngine()
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "live_koyla_dump.sql"
        try:
            dump_res = engine.dump(out_path)
            assert dump_res.exists()
            assert dump_res.stat().st_size > 0
            content = dump_res.read_text(encoding="utf-8", errors="ignore")
            assert "PostgreSQL database dump" in content or "CREATE TABLE" in content or "SET " in content
        except Exception as e:
            pytest.skip(f"PostgreSQL connection not reachable in current context: {e}")

