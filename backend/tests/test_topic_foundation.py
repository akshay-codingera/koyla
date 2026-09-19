"""
Unit and Integration Test Suite for Phase 8.1: Topic Analysis Foundation.
Tests cover:
1. Corpus filtering by organization (strict boundary isolation)
2. Mine and block filtering
3. Fiscal year filtering
4. Document type filtering
5. Deterministic text preprocessing and legal/statutory terminology preservation
6. Original chunk text preservation (database raw text remains untouched)
7. Deterministic corpus hashing (SHA-256 fingerprint reproducibility and divergence)
8. Analysis persistence and structural tables (topic_analyses created, topics table empty)
9. Job lifecycle and progress tracking
10. Server-side security and organization isolation (RBAC & tenant separation)
"""

import uuid
from datetime import datetime
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db, SessionLocal
from app.models.organization import Organization
from app.models.user import User, Role
from app.models.document import Document
from app.models.chunk import Chunk, Embedding
from app.models.extraction import ExtractedField
from app.models.topic import TopicAnalysis, Topic, TopicTerm, TopicDocument, TopicEvidence
from app.models.audit import AuditEvent
from app.core.security import get_password_hash, create_access_token
from app.services.topics.preprocessor import preprocess_text, TextPreprocessor, PREPROCESSOR_VERSION
from app.services.topics.hashing import compute_corpus_hash
from app.services.topics.corpus_service import corpus_service
from app.services.topics.foundation_job import foundation_job

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def topic_test_setup(db_session: Session):
    """Provision isolated test organizations, users, documents, and chunks."""
    # 1. Organizations
    org_bccl = db_session.query(Organization).filter(Organization.code == "BCCL_TOPIC_TEST").first()
    if not org_bccl:
        org_bccl = Organization(
            id=str(uuid.uuid4()),
            code="BCCL_TOPIC_TEST",
            name="Bharat Coking Coal Limited (Topic Test)",
            org_type="SUBSIDIARY",
        )
        db_session.add(org_bccl)

    org_ecl = db_session.query(Organization).filter(Organization.code == "ECL_TOPIC_TEST").first()
    if not org_ecl:
        org_ecl = Organization(
            id=str(uuid.uuid4()),
            code="ECL_TOPIC_TEST",
            name="Eastern Coalfields Limited (Topic Test)",
            org_type="SUBSIDIARY",
        )
        db_session.add(org_ecl)

    db_session.commit()

    # 2. Roles
    role_analyst = db_session.query(Role).filter(Role.code == "SUBSIDIARY_ANALYST").first()
    if not role_analyst:
        role_analyst = Role(
            id=str(uuid.uuid4()),
            code="SUBSIDIARY_ANALYST",
            name="Subsidiary Analyst",
            permissions=["SUBSIDIARY_ANALYST"],
        )
        db_session.add(role_analyst)

    role_hq = db_session.query(Role).filter(Role.code == "CMPDI_HQ_OFFICER").first()
    if not role_hq:
        role_hq = Role(
            id=str(uuid.uuid4()),
            code="CMPDI_HQ_OFFICER",
            name="HQ Officer",
            permissions=["CMPDI_HQ_OFFICER"],
        )
        db_session.add(role_hq)

    db_session.commit()

    # 3. Users
    user_bccl = db_session.query(User).filter(User.username == "bccl_topic_analyst").first()
    if not user_bccl:
        user_bccl = User(
            id=str(uuid.uuid4()),
            username="bccl_topic_analyst",
            email="bccl_analyst@koyla.local",
            full_name="BCCL Topic Analyst",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_bccl.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user_bccl.roles.append(role_analyst)
        db_session.add(user_bccl)

    user_ecl = db_session.query(User).filter(User.username == "ecl_topic_analyst").first()
    if not user_ecl:
        user_ecl = User(
            id=str(uuid.uuid4()),
            username="ecl_topic_analyst",
            email="ecl_analyst@koyla.local",
            full_name="ECL Topic Analyst",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_ecl.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user_ecl.roles.append(role_analyst)
        db_session.add(user_ecl)

    user_hq = db_session.query(User).filter(User.username == "hq_topic_officer").first()
    if not user_hq:
        user_hq = User(
            id=str(uuid.uuid4()),
            username="hq_topic_officer",
            email="hq_officer@koyla.local",
            full_name="CMPDI HQ Topic Officer",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_bccl.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user_hq.roles.append(role_hq)
        db_session.add(user_hq)

    db_session.commit()

    # 4. Documents & Chunks
    # Document 1: BCCL Mining Plan for Moonidih Colliery, FY2024-25
    doc_bccl_mp = Document(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        title="Mining Plan for Moonidih Colliery Jharia Block II FY2024-25",
        document_type="MINING_PLAN",
        source_tier="TIER_A",
        original_filename="moonidih_mp_2025.pdf",
        file_path="storage/test/moonidih_mp_2025.pdf",
        mime_type="application/pdf",
        file_size_bytes=10240,
        sha256_hash="hash_bccl_mp_" + str(uuid.uuid4())[:8],
        status="COMPLETED",
        created_by=user_hq.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(doc_bccl_mp)
    db_session.flush()

    chunk_bccl_1 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_bccl_mp.id,
        chunk_index=1,
        page_number=1,
        chunk_type="TEXT",
        content="Moonidih Underground Mine is operated by Bharat Coking Coal Limited. Geological reserve is 45.20 MT.",
        section_heading="1.1 Mine Identification",
        metadata_json={"mine_name": "Moonidih", "block_name": "Jharia Block II", "fiscal_year": "FY2024-25"},
    )
    chunk_bccl_2 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_bccl_mp.id,
        chunk_index=2,
        page_number=2,
        chunk_type="TEXT",
        content="Mining is carried out using longwall retreating method with continuous miner. Stripping ratio is not applicable for underground workings.",
        section_heading="2.1 Method of Mining",
        metadata_json={"mine_name": "Moonidih", "block_name": "Jharia Block II", "fiscal_year": "FY2024-25"},
    )
    db_session.add_all([chunk_bccl_1, chunk_bccl_2])

    # Document 2: BCCL Geological Report for Jharia Block
    doc_bccl_gr = Document(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        title="Geological Exploration Report on Jharia Block II FY2023-24",
        document_type="GEOLOGICAL_REPORT",
        source_tier="TIER_A",
        original_filename="jharia_geo_2024.pdf",
        file_path="storage/test/jharia_geo_2024.pdf",
        mime_type="application/pdf",
        file_size_bytes=15360,
        sha256_hash="hash_bccl_gr_" + str(uuid.uuid4())[:8],
        status="COMPLETED",
        created_by=user_hq.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(doc_bccl_gr)
    db_session.flush()

    chunk_bccl_3 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_bccl_gr.id,
        chunk_index=1,
        page_number=1,
        chunk_type="TEXT",
        content="Exploration in Jharia Block II identified 12 persistent seams with Prime Coking Coal grades.",
        section_heading="Exploration Highlights",
        metadata_json={"mine_name": "Moonidih", "block_name": "Jharia Block II", "fiscal_year": "FY2023-24"},
    )
    db_session.add(chunk_bccl_3)

    # Document 3: ECL Production Summary for Rajmahal Opencast
    doc_ecl_ps = Document(
        id=str(uuid.uuid4()),
        organization_id=org_ecl.id,
        title="Annual Production Summary for Rajmahal Opencast Mine FY2024-25",
        document_type="PRODUCTION_SUMMARY",
        source_tier="TIER_B",
        original_filename="rajmahal_prod_2025.pdf",
        file_path="storage/test/rajmahal_prod_2025.pdf",
        mime_type="application/pdf",
        file_size_bytes=8192,
        sha256_hash="hash_ecl_ps_" + str(uuid.uuid4())[:8],
        status="COMPLETED",
        created_by=user_ecl.id,
        created_at=datetime.utcnow(),
    )
    db_session.add(doc_ecl_ps)
    db_session.flush()

    chunk_ecl_1 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_ecl_ps.id,
        chunk_index=1,
        page_number=1,
        chunk_type="TEXT",
        content="Rajmahal Opencast project achieved total coal production of 17.50 MT of grade G11 in FY2024-25. Stripping ratio was 2.15 cum/tonne.",
        section_heading="Annual Performance",
        metadata_json={"mine_name": "Rajmahal", "block_name": "Rajmahal Block", "fiscal_year": "FY2024-25"},
    )
    db_session.add(chunk_ecl_1)

    # Add ExtractedField for mine_name and fiscal_year to verify field-assisted resolution
    field_mine = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        document_id=doc_bccl_mp.id,
        field_name="mine_name",
        raw_value="Moonidih",
        normalized_value="Moonidih",
        extraction_method="RULE_BASED",
        confidence_score=1.0,
    )
    field_fy = ExtractedField(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        document_id=doc_bccl_mp.id,
        field_name="fiscal_year",
        raw_value="FY2024-25",
        normalized_value="2024-2025",
        extraction_method="RULE_BASED",
        confidence_score=1.0,
    )
    db_session.add_all([field_mine, field_fy])

    db_session.commit()

    return {
        "org_bccl": org_bccl,
        "org_ecl": org_ecl,
        "user_bccl": user_bccl,
        "user_ecl": user_ecl,
        "user_hq": user_hq,
        "doc_bccl_mp": doc_bccl_mp,
        "doc_bccl_gr": doc_bccl_gr,
        "doc_ecl_ps": doc_ecl_ps,
        "chunk_bccl_1": chunk_bccl_1,
        "chunk_bccl_2": chunk_bccl_2,
        "chunk_bccl_3": chunk_bccl_3,
        "chunk_ecl_1": chunk_ecl_1,
    }


def test_01_corpus_filtering_by_org(db_session: Session, topic_test_setup):
    """Verify filtering by organization isolates strictly that organization's documents and chunks."""
    org_bccl = topic_test_setup["org_bccl"]
    org_ecl = topic_test_setup["org_ecl"]

    # Query BCCL only
    res_bccl = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[org_bccl.id],
        filters={"organization_id": org_bccl.id},
    )
    assert res_bccl["total_chunks"] >= 3
    for item in res_bccl["items"]:
        assert item["organization_id"] == org_bccl.id
        assert item["organization_id"] != org_ecl.id

    # Query ECL only
    res_ecl = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[org_ecl.id],
        filters={"organization_id": org_ecl.id},
    )
    assert res_ecl["total_chunks"] >= 1
    for item in res_ecl["items"]:
        assert item["organization_id"] == org_ecl.id
        assert item["organization_id"] != org_bccl.id


def test_02_mine_and_block_filtering(db_session: Session, topic_test_setup):
    """Verify corpus filtering by mine_name and block_name."""
    org_bccl = topic_test_setup["org_bccl"]

    # Filter by mine_name = 'Moonidih'
    res_mine = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[org_bccl.id],
        filters={"mine_name": "Moonidih"},
    )
    assert res_mine["total_chunks"] >= 2
    for item in res_mine["items"]:
        assert item["organization_id"] == org_bccl.id

    # Filter by block_name = 'Jharia Block II'
    res_block = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[org_bccl.id],
        filters={"block_name": "Jharia Block II"},
    )
    assert res_block["total_chunks"] >= 2
    for item in res_block["items"]:
        assert "Jharia" in item["cleaned_text"] or "Jharia" in str(item.get("block_name")) or "Moonidih" in item["cleaned_text"]


def test_03_fiscal_year_filtering(db_session: Session, topic_test_setup):
    """Verify corpus filtering by fiscal_year."""
    org_bccl = topic_test_setup["org_bccl"]

    res_fy = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[org_bccl.id],
        filters={"fiscal_year": "FY2024-25"},
    )
    assert res_fy["total_chunks"] > 0
    # Must include Moonidih MP chunks
    doc_ids = set(res_fy["document_ids"])
    assert topic_test_setup["doc_bccl_mp"].id in doc_ids


def test_04_document_type_filtering(db_session: Session, topic_test_setup):
    """Verify corpus filtering by document_type strictly includes only matching document types."""
    org_bccl = topic_test_setup["org_bccl"]
    org_ecl = topic_test_setup["org_ecl"]

    res_mp = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[org_bccl.id, org_ecl.id],
        filters={"document_type": "MINING_PLAN"},
    )
    assert res_mp["total_chunks"] >= 2
    for item in res_mp["items"]:
        assert item["document_type"] == "MINING_PLAN"

    res_ps = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[org_bccl.id, org_ecl.id],
        filters={"document_type": "PRODUCTION_SUMMARY"},
    )
    assert res_ps["total_chunks"] >= 1
    for item in res_ps["items"]:
        assert item["document_type"] == "PRODUCTION_SUMMARY"


def test_05_text_preprocessing_and_legal_term_preservation():
    """Verify running headers, page numbers, and OCR artifacts are stripped while statutory/mining terms are preserved."""
    sample_text = (
        "Page 14 of 50\n"
        "CONFIDENTIAL\n"
        "===---===\n"
        "As per Rule 24A of Mineral Concession Rules 1960 and Section 18 of Mines Act 1952, "
        "the environmental clearance (EC) was obtained from MoEFCC for Moonidih Colliery. "
        "The stripping ratio is 2.15 cum/tonne with proved reserve of 45.20 MT of grade G11 coking coal. "
        "~^| Table 2.1 Page - 14"
    )

    result = preprocess_text(sample_text)
    cleaned = result["cleaned_text"]

    # Verify running page markers and dividers are stripped
    assert "Page 14 of 50" not in cleaned
    assert "Page - 14" not in cleaned
    assert "CONFIDENTIAL" not in cleaned
    assert "===---===" not in cleaned
    assert "~^|" not in cleaned

    # Verify statutory terminology is preserved
    assert "Rule 24A" in cleaned or "Rule" in cleaned
    assert "Section 18" in cleaned or "Section" in cleaned
    assert "Mines Act 1952" in cleaned or "Mines Act" in cleaned
    assert "environmental clearance" in cleaned or "EC" in cleaned
    assert "MoEFCC" in cleaned

    # Verify mining technical terms are preserved
    assert "stripping ratio" in cleaned
    assert "proved reserve" in cleaned
    assert "grade G11" in cleaned or "G11" in cleaned
    assert "coking coal" in cleaned

    assert result["token_count"] > 0
    assert result["reduction_ratio"] > 0.0
    assert result["preprocessor_version"] == PREPROCESSOR_VERSION


def test_06_original_text_preservation(db_session: Session, topic_test_setup):
    """Verify that running corpus construction and preprocessing never alters raw chunk text in DB."""
    chunk = topic_test_setup["chunk_bccl_1"]
    original_raw_content = chunk.content

    # Run corpus assembly
    res = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[topic_test_setup["org_bccl"].id],
    )
    assert res["total_chunks"] > 0

    # Refresh chunk from database
    db_session.refresh(chunk)
    assert chunk.content == original_raw_content
    assert chunk.content == "Moonidih Underground Mine is operated by Bharat Coking Coal Limited. Geological reserve is 45.20 MT."


def test_07_deterministic_corpus_hashing():
    """Verify SHA-256 corpus hash is strictly deterministic and diverges on any parameter alteration."""
    chunks = ["chunk-001", "chunk-002", "chunk-003"]
    docs = ["doc-001", "doc-002"]
    filters = {"organization_id": "org-123", "document_type": "MINING_PLAN"}
    params = {"min_df": 2}

    # Hash 1
    h1 = compute_corpus_hash(
        chunk_ids=chunks,
        document_ids=docs,
        filters=filters,
        preprocessor_version="1.0.0",
        embedding_model="BAAI/bge-small-en-v1.5",
        analysis_method="FOUNDATION",
        parameters=params,
    )
    assert len(h1) == 64

    # Hash 2 (identical inputs, unsorted chunks to test internal sorting)
    h2 = compute_corpus_hash(
        chunk_ids=["chunk-003", "chunk-001", "chunk-002"],
        document_ids=["doc-002", "doc-001"],
        filters=filters,
        preprocessor_version="1.0.0",
        embedding_model="BAAI/bge-small-en-v1.5",
        analysis_method="FOUNDATION",
        parameters=params,
    )
    assert h1 == h2, "Deterministic hash must match regardless of input ordering"

    # Hash 3: Altered chunk list
    h3 = compute_corpus_hash(
        chunk_ids=chunks + ["chunk-004"],
        document_ids=docs,
        filters=filters,
        preprocessor_version="1.0.0",
        embedding_model="BAAI/bge-small-en-v1.5",
        analysis_method="FOUNDATION",
        parameters=params,
    )
    assert h1 != h3

    # Hash 4: Altered filter
    h4 = compute_corpus_hash(
        chunk_ids=chunks,
        document_ids=docs,
        filters={"organization_id": "org-123", "document_type": "GEOLOGICAL_REPORT"},
        preprocessor_version="1.0.0",
        embedding_model="BAAI/bge-small-en-v1.5",
        analysis_method="FOUNDATION",
        parameters=params,
    )
    assert h1 != h4


def test_08_analysis_persistence_and_structural_tables(db_session: Session, topic_test_setup):
    """Verify TopicAnalysis record persistence and confirm topics table remains empty in Phase 8.1."""
    org_bccl = topic_test_setup["org_bccl"]
    user_hq = topic_test_setup["user_hq"]

    analysis = TopicAnalysis(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        corpus_filters={"subsidiary": "BCCL", "document_type": "MINING_PLAN"},
        corpus_hash="pending",
        embedding_model="BAAI/bge-small-en-v1.5",
        analysis_method="FOUNDATION",
        parameters={},
        status="QUEUED",
        progress_pct=0,
        created_by=user_hq.id,
    )
    db_session.add(analysis)
    db_session.commit()

    # Execute foundation job
    res = foundation_job.execute(
        db=db_session,
        analysis_id=analysis.id,
        allowed_org_ids=[org_bccl.id],
    )

    assert res.status == "COMPLETED"
    assert res.progress_pct == 100
    assert len(res.corpus_hash) == 64
    assert res.document_count >= 1
    assert res.chunk_count >= 2
    assert res.runtime_seconds is not None and res.runtime_seconds >= 0.0

    # Strict Phase 8.1 constraint: topics table remains empty
    topic_count = db_session.query(Topic).filter(Topic.analysis_id == analysis.id).count()
    assert topic_count == 0, "Phase 8.1 Foundation ONLY must leave topics table empty"


def test_09_job_lifecycle_and_progress(db_session: Session, topic_test_setup):
    """Verify job lifecycle transitions and error handling for missing analysis ID."""
    with pytest.raises(ValueError) as exc:
        foundation_job.execute(
            db=db_session,
            analysis_id="non-existent-uuid-999",
            allowed_org_ids=[topic_test_setup["org_bccl"].id],
        )
    assert "not found" in str(exc.value)


def test_10_server_side_security_and_org_isolation(db_session: Session, topic_test_setup):
    """Verify non-HQ subsidiary user cannot analyze or access another subsidiary's corpus, and audit trail is logged."""
    org_bccl = topic_test_setup["org_bccl"]
    org_ecl = topic_test_setup["org_ecl"]
    user_ecl = topic_test_setup["user_ecl"]
    user_hq = topic_test_setup["user_hq"]

    token_ecl = create_access_token(user_ecl.username)
    headers_ecl = {"Authorization": f"Bearer {token_ecl}"}

    token_hq = create_access_token(user_hq.username)
    headers_hq = {"Authorization": f"Bearer {token_hq}"}

    # 1. ECL user attempts to trigger analysis targeting BCCL -> Must fail with 403 Forbidden
    res_unauth = client.post(
        "/api/v1/topics/analyze",
        headers=headers_ecl,
        json={
            "organization_id": org_bccl.id,
            "corpus_filters": {"mine_name": "Moonidih"},
            "embedding_model": "BAAI/bge-small-en-v1.5",
        },
    )
    assert res_unauth.status_code == 403
    assert "outside your authorized organization scope" in res_unauth.json()["detail"]

    # 2. ECL user triggers analysis on their own authorized organization -> Must succeed
    res_auth = client.post(
        "/api/v1/topics/analyze",
        headers=headers_ecl,
        json={
            "organization_id": org_ecl.id,
            "corpus_filters": {"mine_name": "Rajmahal"},
            "embedding_model": "BAAI/bge-small-en-v1.5",
        },
    )
    assert res_auth.status_code == 200
    analysis_data = res_auth.json()
    assert analysis_data["status"] == "COMPLETED"
    assert analysis_data["organization_id"] == org_ecl.id
    analysis_id = analysis_data["id"]

    # 3. Verify audit event was recorded
    audit_evt = db_session.query(AuditEvent).filter(
        AuditEvent.action == "TOPIC_ANALYSIS_CREATED",
        AuditEvent.object_id == analysis_id,
    ).first()
    assert audit_evt is not None
    assert audit_evt.actor_id == user_ecl.id
    assert audit_evt.organization_id == org_ecl.id

    # 4. Central HQ user can inspect the analysis
    res_inspect = client.get(f"/api/v1/topics/{analysis_id}", headers=headers_hq)
    assert res_inspect.status_code == 200
    assert res_inspect.json()["id"] == analysis_id

    # 5. Corpus inspection endpoint
    res_corpus = client.get(f"/api/v1/topics/{analysis_id}/corpus", headers=headers_ecl)
    assert res_corpus.status_code == 200
    corpus_json = res_corpus.json()
    assert corpus_json["analysis_id"] == analysis_id
    assert "items" in corpus_json
