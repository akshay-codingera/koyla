"""
Genuine Isolated PostgreSQL Clean-Environment Restore & Disaster Recovery Test.
Exercises the complete production pg_dump -> clean PostgreSQL database -> psql restore -> verification cycle.
Validates tables, relationships, pgvector embeddings, documents, reports, and cryptographic SHA-256 integrity.
"""
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.database import Base
from app.models.audit import AuditEvent
from app.models.chunk import Chunk, Embedding
from app.models.document import Document, DocumentPage, DocumentVersion
from app.models.organization import Organization
from app.models.report import Report, ReportFormat
from app.models.topic import Topic, TopicAnalysis
from app.models.user import Role, User
from app.models.visual import VisualAsset
from app.services.backup.constants import BackupIntegrityStatus
from app.services.backup.integrity import calculate_sha256, verify_backup
from app.services.backup.backup import BackupService
from app.services.backup.postgres import PostgresBackupEngine, parse_db_url
from app.services.backup.restore import BackupRestoreService


def get_admin_postgres_engine():
    """Builds an administrative SQLAlchemy engine targeting the postgres default db."""
    parsed = parse_db_url(settings.DATABASE_URL)
    if parsed["engine"] != "postgresql":
        return None
    admin_url = f"postgresql+psycopg2://{parsed['username']}:{parsed['password']}@{parsed['host']}:{parsed['port']}/postgres"
    return create_engine(admin_url, isolation_level="AUTOCOMMIT")


def create_isolated_database(admin_engine, db_name: str):
    """Creates a temporary, isolated database on the PostgreSQL instance."""
    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {db_name};"))


def drop_isolated_database(admin_engine, db_name: str):
    """Terminates active connections and drops the isolated database."""
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f"""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = '{db_name}' AND pid <> pg_backend_pid();
            """))
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name};"))
    except Exception as e:
        print(f"Warning: Failed to drop test db {db_name}: {e}")


def test_isolated_postgresql_clean_restore_cycle():
    """
    Genuine end-to-end PostgreSQL disaster recovery verification.
    1. Creates isolated source PostgreSQL database.
    2. Inserts representative Koyla persistent records (docs, chunks, pgvector embeddings, audits, reports, visuals, topics).
    3. Executes native pg_dump.
    4. Proves safety barrier refuses restore into occupied PostgreSQL database without force=True.
    5. Creates clean destination PostgreSQL database.
    6. Restores full backup into clean database.
    7. Verifies table rows, relationships, and pgvector embeddings survive restoration.
    8. Verifies durable documents and reports survive with exact matching SHA-256 hashes.
    """
    if not shutil.which("pg_dump") or not shutil.which("psql"):
        pytest.skip("pg_dump / psql not available in current test environment")

    admin_engine = get_admin_postgres_engine()
    if not admin_engine:
        pytest.skip("Configured database is not PostgreSQL")

    # Probe admin connection
    try:
        with admin_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL server not reachable: {exc}")

    parsed = parse_db_url(settings.DATABASE_URL)
    src_db_name = f"koyla_dr_src_{uuid.uuid4().hex[:8]}"
    dst_db_name = f"koyla_dr_dst_{uuid.uuid4().hex[:8]}"

    src_db_url = f"postgresql+psycopg2://{parsed['username']}:{parsed['password']}@{parsed['host']}:{parsed['port']}/{src_db_name}"
    dst_db_url = f"postgresql+psycopg2://{parsed['username']}:{parsed['password']}@{parsed['host']}:{parsed['port']}/{dst_db_name}"

    try:
        # 1. Create isolated source database & pgvector extension
        create_isolated_database(admin_engine, src_db_name)
        src_engine = create_engine(src_db_url)
        with src_engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()

        # Initialize all Koyla persistent tables
        Base.metadata.create_all(bind=src_engine)

        # 2. Populate representative Koyla records
        SrcSession = sessionmaker(bind=src_engine)
        src_session = SrcSession()

        # Organization & User
        org = Organization(
            id=str(uuid.uuid4()),
            code="CMPDI_RI1",
            name="CMPDI Regional Institute I",
            org_type="REGIONAL_INSTITUTE",
            metadata_={"division": "Exploration", "region": "Ranchi"},
        )
        role = Role(id=str(uuid.uuid4()), code="VERIFICATION_OFFICER", name="Verification Officer")
        user = User(
            id=str(uuid.uuid4()),
            username="geologist_dr",
            email="geologist@cmpdi.co.in",
            full_name="Dr. A. K. Sharma",
            hashed_password="[HASHED]",
            organization=org,
            roles=[role],
            is_active=True,
        )
        src_session.add_all([org, role, user])
        src_session.flush()

        # Document & Version
        doc_id = str(uuid.uuid4())
        doc = Document(
            id=doc_id,
            organization_id=org.id,
            title="CMPDI Geological Exploration Borehole Study 2026",
            document_type="GEOLOGICAL_REPORT",
            source_tier="TIER_A",
            original_filename="geology_2026.pdf",
            file_path="storage/documents/geology_2026.pdf",
            mime_type="application/pdf",
            file_size_bytes=524288,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            status="PROCESSED",
            created_by=user.id,
        )
        doc_version = DocumentVersion(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            version_number=1,
            file_path="storage/documents/geology_2026.pdf",
            sha256_hash=doc.sha256_hash,
            change_summary="Initial verified geological submission",
        )
        page = DocumentPage(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            page_number=1,
            extracted_text="Lithological stratum: Coal Seam IV encountered at 42.5m with thickness 3.8m.",
            ocr_applied=False,
            confidence_score=0.98,
        )
        src_session.add_all([doc, doc_version, page])
        src_session.flush()

        # Chunk & pgvector Embedding (384-dimensional)
        chunk = Chunk(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            chunk_index=0,
            page_number=1,
            chunk_type="TEXT",
            content="Lithological stratum: Coal Seam IV encountered at 42.5m with thickness 3.8m.",
            section_heading="Lithology & Seam Sequence",
        )
        src_session.add(chunk)
        src_session.flush()

        test_vector = [0.05] * 384
        embedding = Embedding(
            id=str(uuid.uuid4()),
            chunk_id=chunk.id,
            model_name="BAAI/bge-small-en-v1.5",
            dimensions=384,
            vector_data=test_vector,
        )
        src_session.add(embedding)

        # Audit Event
        audit_event = AuditEvent(
            id=str(uuid.uuid4()),
            action="DOCUMENT_INGEST",
            actor_id=user.id,
            actor_name="geologist_dr",
            role_code="VERIFICATION_OFFICER",
            organization_id=org.id,
            object_type="DOCUMENT",
            object_id=doc_id,
            details={"source": "CMPDI_RI1", "quality": "HIGH"},
        )
        src_session.add(audit_event)

        # Report Format & Report Record
        rep_format = ReportFormat(
            id=str(uuid.uuid4()),
            report_type="PARLIAMENTARY_BRIEF",
            issuing_authority="Ministry of Coal",
            document_title="Official Parliamentary Geological Format",
            om_number="OM-2026/01",
            om_date="2026-01-01",
            guideline_year=2026,
            schema_json={"fields": ["coalfield", "reserves_mt"]},
        )
        src_session.add(rep_format)
        src_session.flush()

        report_record = Report(
            id=str(uuid.uuid4()),
            format_id=rep_format.id,
            organization_id=org.id,
            mine_name="North Karanpura OCP",
            block_name="Block A",
            report_title="Statutory Exploration Summary Q1 2026",
            base_date="2026-03",
        )
        src_session.add(report_record)

        # Visual Asset Record
        visual_asset = VisualAsset(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            page_id=page.id,
            page_number=1,
            visual_type="MINE_PLAN",
            classification_confidence=0.95,
            file_path="storage/documents/visuals/seam_iv_map.png",
            image_hash="b" * 64,
            verification_status="VERIFIED",
        )
        src_session.add(visual_asset)

        # Topic Analysis & Topic Record
        topic_analysis = TopicAnalysis(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            corpus_filters={},
            corpus_hash="c" * 64,
            status="COMPLETED",
            progress_pct=100,
        )
        src_session.add(topic_analysis)
        src_session.flush()

        topic_record = Topic(
            id=str(uuid.uuid4()),
            analysis_id=topic_analysis.id,
            topic_index=0,
            label="Borehole Lithology & Stratigraphy",
            coherence_score=0.89,
        )
        src_session.add(topic_record)

        src_session.commit()
        src_session.close()

        # 3. Setup Durable Document & Report Files in Temporary Workspaces
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            src_storage = tmp_root / "source_storage"
            src_reports = tmp_root / "source_reports"
            backup_vault = tmp_root / "backup_vault"

            src_storage.mkdir(parents=True)
            src_reports.mkdir(parents=True)
            backup_vault.mkdir(parents=True)

            sample_pdf_bytes = b"%PDF-1.7 CMPDI Ranchi Geological Survey Confidential Master Record 2026"
            sample_docx_bytes = b"DOCX Statutory Exploration Summary Brief Signed CMPDI HQ"

            src_doc_file = src_storage / "geology_2026.pdf"
            src_rep_file = src_reports / "jharia_brief.docx"

            src_doc_file.write_bytes(sample_pdf_bytes)
            src_rep_file.write_bytes(sample_docx_bytes)

            expected_doc_sha = calculate_sha256(src_doc_file)
            expected_rep_sha = calculate_sha256(src_rep_file)

            # 4. Execute Real PostgreSQL Backup
            src_engine_backup = PostgresBackupEngine(src_db_url)
            backup_svc = BackupService(
                storage_dir=src_storage,
                reports_dir=src_reports,
                backup_dir=backup_vault,
                retention_count=5,
                db_engine=src_engine_backup,
            )

            t0_backup = time.perf_counter()
            backup_res = backup_svc.create_backup(compress=True, include_db=True, include_docs=True, include_reports=True)
            t_backup_ms = round((time.perf_counter() - t0_backup) * 1000, 2)

            archive_path = Path(backup_res["path"])
            assert archive_path.exists()
            assert backup_res["integrity_status"] == BackupIntegrityStatus.VALID.value

            # 5. Cryptographic Manifest Verification
            t0_verify = time.perf_counter()
            manifest_report = verify_backup(archive_path)
            t_verify_ms = round((time.perf_counter() - t0_verify) * 1000, 2)

            assert manifest_report.is_valid is True
            assert manifest_report.status == BackupIntegrityStatus.VALID
            assert manifest_report.verified_files >= 3

            # 6. Safety Barrier Verification: Attempt restore into occupied source DB without force
            restore_svc_probe = BackupRestoreService(
                storage_dir=src_storage,
                reports_dir=src_reports,
                db_engine=src_engine_backup,
            )
            with pytest.raises(RuntimeError) as exc_safety:
                restore_svc_probe.restore_backup(
                    backup_target=archive_path,
                    force=False,
                    target_db_url=src_db_url,
                    target_storage_dir=src_storage,
                    target_reports_dir=src_reports,
                )
            assert "Safety barrier" in str(exc_safety.value)
            assert "force=True" in str(exc_safety.value)

            # 7. Create CLEAN Destination PostgreSQL Database
            create_isolated_database(admin_engine, dst_db_name)
            dst_engine = create_engine(dst_db_url)

            # Verify destination database starts completely empty (0 tables)
            with dst_engine.connect() as conn:
                res_tables = conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")).scalar()
                assert res_tables == 0, f"Clean target DB was expected to be empty, found {res_tables} tables."

            # Setup empty destination file directories
            dst_storage = tmp_root / "clean_destination_storage"
            dst_reports = tmp_root / "clean_destination_reports"

            dst_engine_restore = PostgresBackupEngine(dst_db_url)
            restore_svc = BackupRestoreService(
                storage_dir=dst_storage,
                reports_dir=dst_reports,
                db_engine=dst_engine_restore,
            )

            # 8. Execute Restoration into Clean Target
            t0_restore = time.perf_counter()
            restore_res = restore_svc.restore_backup(
                backup_target=archive_path,
                force=False,  # Target is empty, so force=False MUST succeed!
                target_db_url=dst_db_url,
                target_storage_dir=dst_storage,
                target_reports_dir=dst_reports,
            )
            t_restore_ms = round((time.perf_counter() - t0_restore) * 1000, 2)

            assert restore_res["status"] == "RESTORE_SUCCESS"
            assert "database" in restore_res["components_restored"]
            assert "documents" in restore_res["components_restored"]
            assert "reports" in restore_res["components_restored"]

            # 9. Verify Restored PostgreSQL Database Records & Relationships
            DstSession = sessionmaker(bind=dst_engine)
            dst_session = DstSession()

            # Organization
            restored_org = dst_session.query(Organization).filter(Organization.code == "CMPDI_RI1").first()
            assert restored_org is not None
            assert restored_org.name == "CMPDI Regional Institute I"
            assert restored_org.metadata_.get("division") == "Exploration"

            # User & Role Relationship
            restored_user = dst_session.query(User).filter(User.username == "geologist_dr").first()
            assert restored_user is not None
            assert restored_user.email == "geologist@cmpdi.co.in"
            assert restored_user.full_name == "Dr. A. K. Sharma"
            assert restored_user.organization_id == restored_org.id
            assert any(r.code == "VERIFICATION_OFFICER" for r in restored_user.roles)

            # Document & Version
            restored_doc = dst_session.query(Document).filter(Document.id == doc_id).first()
            assert restored_doc is not None
            assert restored_doc.title == "CMPDI Geological Exploration Borehole Study 2026"
            assert restored_doc.status == "PROCESSED"
            assert restored_doc.organization_id == restored_org.id

            restored_version = dst_session.query(DocumentVersion).filter(DocumentVersion.document_id == doc_id).first()
            assert restored_version is not None
            assert restored_version.version_number == 1

            restored_page = dst_session.query(DocumentPage).filter(DocumentPage.document_id == doc_id).first()
            assert restored_page is not None
            assert "Coal Seam IV" in restored_page.extracted_text

            # Chunk
            restored_chunk = dst_session.query(Chunk).filter(Chunk.document_id == doc_id).first()
            assert restored_chunk is not None
            assert "Lithological stratum" in restored_chunk.content

            # pgvector Embedding & Vector Query Capability
            restored_embedding = dst_session.query(Embedding).filter(Embedding.chunk_id == restored_chunk.id).first()
            assert restored_embedding is not None
            assert restored_embedding.dimensions == 384
            assert restored_embedding.model_name == "BAAI/bge-small-en-v1.5"

            # Execute live pgvector distance query in restored database
            query_vec_str = str([0.05] * 384)
            dist_res = dst_session.execute(
                text(f"SELECT vector_data <-> '{query_vec_str}'::vector FROM embeddings WHERE id = '{restored_embedding.id}';")
            ).scalar()
            assert dist_res is not None
            assert float(dist_res) < 1e-4, f"Vector distance should be 0.0 for identical vector, got {dist_res}"

            # Audit Event
            restored_audit = dst_session.query(AuditEvent).filter(AuditEvent.object_id == doc_id).first()
            assert restored_audit is not None
            assert restored_audit.action == "DOCUMENT_INGEST"
            assert restored_audit.actor_name == "geologist_dr"

            # Report Record
            restored_rep_record = dst_session.query(Report).filter(Report.organization_id == restored_org.id).first()
            assert restored_rep_record is not None
            assert restored_rep_record.mine_name == "North Karanpura OCP"

            # Visual Asset
            restored_visual = dst_session.query(VisualAsset).filter(VisualAsset.document_id == doc_id).first()
            assert restored_visual is not None
            assert restored_visual.visual_type == "MINE_PLAN"

            # Topic Record
            restored_topic = dst_session.query(Topic).first()
            assert restored_topic is not None
            assert "Borehole" in restored_topic.label

            dst_session.close()

            # 10. Verify Restored Files on Disk with Cryptographic SHA-256
            restored_doc_file = dst_storage / "geology_2026.pdf"
            restored_rep_file = dst_reports / "jharia_brief.docx"

            assert restored_doc_file.exists()
            assert calculate_sha256(restored_doc_file) == expected_doc_sha
            assert restored_doc_file.read_bytes() == sample_pdf_bytes

            assert restored_rep_file.exists()
            assert calculate_sha256(restored_rep_file) == expected_rep_sha
            assert restored_rep_file.read_bytes() == sample_docx_bytes

            # Print measured benchmark timings
            print(f"\n==================== MEASURED POSTGRESQL BENCHMARK ====================")
            print(f"Archive Created: {backup_res.get('backup_id')} ({backup_res.get('total_bytes')} bytes)")
            print(f"PostgreSQL Dump Duration: {t_backup_ms} ms")
            print(f"Cryptographic Verification Duration: {t_verify_ms} ms")
            print(f"Clean PostgreSQL Restore Duration: {t_restore_ms} ms")
            print(f"Total Recovery Cycle: {round(t_backup_ms + t_verify_ms + t_restore_ms, 2)} ms")
            print(f"========================================================================\n")

    finally:
        # Clean up temporary databases so PostgreSQL instance remains pristine
        drop_isolated_database(admin_engine, src_db_name)
        drop_isolated_database(admin_engine, dst_db_name)
