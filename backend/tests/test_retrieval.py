import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import uuid
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.database import SessionLocal
from app.models.user import User, Role
from app.models.organization import Organization
from app.models.document import Document, DocumentVersion
from app.models.chunk import Chunk, Embedding
from app.models.audit import AuditEvent
from app.core.security import create_access_token, get_password_hash
from app.services.embedding import get_embedding_provider, DeterministicLocalEmbeddingProvider
from app.services.indexing import indexing_service
from app.services.retrieval.query_normalizer import query_normalizer
from app.services.retrieval.keyword_search import keyword_search_engine
from app.services.retrieval.dense_search import dense_search_engine
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.reranker import local_reranker
from app.services.retrieval.service import retrieval_service

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def retrieval_test_setup(db_session: Session):
    # Ensure test organizations exist
    org_bccl = db_session.query(Organization).filter(Organization.code == "BCCL_TEST").first()
    if not org_bccl:
        org_bccl = Organization(
            id=str(uuid.uuid4()),
            code="BCCL_TEST",
            name="Bharat Coking Coal Limited (Test)",
            org_type="SUBSIDIARY"
        )
        db_session.add(org_bccl)

    org_ecl = db_session.query(Organization).filter(Organization.code == "ECL_TEST").first()
    if not org_ecl:
        org_ecl = Organization(
            id=str(uuid.uuid4()),
            code="ECL_TEST",
            name="Eastern Coalfields Limited (Test)",
            org_type="SUBSIDIARY"
        )
        db_session.add(org_ecl)

    db_session.commit()

    # Ensure roles exist
    role_analyst = db_session.query(Role).filter(Role.code == "SUBSIDIARY_ANALYST").first()
    if not role_analyst:
        role_analyst = Role(
            id=str(uuid.uuid4()),
            code="SUBSIDIARY_ANALYST",
            name="Subsidiary Analyst",
            permissions=["SUBSIDIARY_ANALYST"]
        )
        db_session.add(role_analyst)

    role_hq = db_session.query(Role).filter(Role.code == "CMPDI_HQ_OFFICER").first()
    if not role_hq:
        role_hq = Role(
            id=str(uuid.uuid4()),
            code="CMPDI_HQ_OFFICER",
            name="HQ Officer",
            permissions=["CMPDI_HQ_OFFICER"]
        )
        db_session.add(role_hq)

    db_session.commit()

    # Users
    user_ecl = db_session.query(User).filter(User.username == "ecl_test_user").first()
    if not user_ecl:
        user_ecl = User(
            id=str(uuid.uuid4()),
            username="ecl_test_user",
            email="ecl_user@koyla.local",
            full_name="ECL Test Analyst",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_ecl.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        user_ecl.roles.append(role_analyst)
        db_session.add(user_ecl)

    user_hq = db_session.query(User).filter(User.username == "hq_test_user").first()
    if not user_hq:
        user_hq = User(
            id=str(uuid.uuid4()),
            username="hq_test_user",
            email="hq_user@koyla.local",
            full_name="HQ Test Officer",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_bccl.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        user_hq.roles.append(role_hq)
        db_session.add(user_hq)

    db_session.commit()

    # Documents & Chunks
    doc_bccl = Document(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        title="Moonidih Geological Survey Report FY2024-25",
        document_type="GEOLOGICAL_REPORT",
        source_tier="TIER_A",
        original_filename="moonidih_geo_2025.pdf",
        file_path="storage/test/moonidih_geo_2025.pdf",
        mime_type="application/pdf",
        file_size_bytes=10240,
        sha256_hash="abc123bcclmoonidih" + str(uuid.uuid4())[:8],
        status="COMPLETED",
        created_by=user_hq.id,
        created_at=datetime.utcnow()
    )
    db_session.add(doc_bccl)
    db_session.flush()

    chunk_narrative = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_bccl.id,
        chunk_index=1,
        page_number=1,
        chunk_type="TEXT",
        content="BCCL Moonidih Colliery conducted borehole drilling BH-04 targeting Seam-III in FY2024-25.",
        section_heading="Borehole Exploration Summary",
        metadata_json={"page": 1, "type": "text"}
    )
    db_session.add(chunk_narrative)

    # Logical multi-page table chunk (Part 2 of 2 on Page 3)
    chunk_table = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_bccl.id,
        chunk_index=2,
        page_number=3,
        chunk_type="TABLE",
        content="[TABLE: Seam Stratigraphy Analysis (Pages 2-3) - Part 2/2]\nHeaders: Seam | Depth (m) | Thickness (m) | Ash %\n[P.3] Seam-III | 210.5 | 4.80 | 18.2%",
        section_heading="Seam Stratigraphy Analysis (Part 2/2)",
        metadata_json={
            "logical_table_id": "log_tbl_moonidih_01",
            "table_index": 1,
            "caption": "Seam Stratigraphy Analysis",
            "part": 2,
            "total_parts": 2,
            "pages": [2, 3],
            "headers": ["Seam", "Depth (m)", "Thickness (m)", "Ash %"],
            "row_count": 1,
            "type": "table"
        }
    )
    db_session.add(chunk_table)

    # ECL Document
    doc_ecl = Document(
        id=str(uuid.uuid4()),
        organization_id=org_ecl.id,
        title="Rajmahal Open Cast Production Summary FY2023-24",
        document_type="PRODUCTION_SUMMARY",
        source_tier="TIER_B",
        original_filename="rajmahal_prod_2024.pdf",
        file_path="storage/test/rajmahal_prod_2024.pdf",
        mime_type="application/pdf",
        file_size_bytes=8192,
        sha256_hash="xyz789eclrajmahal" + str(uuid.uuid4())[:8],
        status="COMPLETED",
        created_by=user_ecl.id,
        created_at=datetime.utcnow()
    )
    db_session.add(doc_ecl)
    db_session.flush()

    chunk_ecl = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_ecl.id,
        chunk_index=1,
        page_number=2,
        chunk_type="TEXT",
        content="ECL Rajmahal Mine achieved total coal production of 14.50 MT during FY2023-24 with stripping ratio 2.10.",
        section_heading="Annual Operational Production",
        metadata_json={"page": 2, "type": "text"}
    )
    db_session.add(chunk_ecl)
    db_session.commit()

    return {
        "org_bccl": org_bccl,
        "org_ecl": org_ecl,
        "user_ecl": user_ecl,
        "user_hq": user_hq,
        "doc_bccl": doc_bccl,
        "doc_ecl": doc_ecl,
        "chunk_narrative": chunk_narrative,
        "chunk_table": chunk_table,
        "chunk_ecl": chunk_ecl
    }


def test_embedding_provider_dimension_and_normalization():
    """Verify local embedding providers return 384-dimensional unit-normalized vectors."""
    # 1. Deterministic local fallback provider
    det_provider = DeterministicLocalEmbeddingProvider(dimension=384)
    vec_det = det_provider.embed_text("Coal India Limited geological exploration Moonidih")
    assert len(vec_det) == 384
    norm_det = math.sqrt(sum(x * x for x in vec_det))
    assert abs(norm_det - 1.0) < 1e-4

    info_det = det_provider.model_info()
    assert info_det["dimension"] == 384
    assert info_det["is_local"] is True
    assert info_det["is_neural"] is False
    assert info_det["model_type"] == "DETERMINISTIC_FEATURE_HASHING"
    assert info_det["model_name"] == "koyla-deterministic-hash-384"

    # 2. Genuine neural SentenceTransformer BAAI/bge-small-en-v1.5 provider
    from app.services.embedding.sentence_transformer import LocalSentenceTransformerProvider
    neural_provider = LocalSentenceTransformerProvider()
    health = neural_provider.health()
    if health.get("available"):
        vec_neural = neural_provider.embed_text("Coal India Limited geological exploration Moonidih")
        assert len(vec_neural) == 384
        norm_neural = math.sqrt(sum(x * x for x in vec_neural))
        assert abs(norm_neural - 1.0) < 1e-4

        batch_neural = neural_provider.embed_batch(["Text A", "Text B"])
        assert len(batch_neural) == 2
        assert len(batch_neural[0]) == 384

        info_neural = neural_provider.model_info()
        assert info_neural["dimension"] == 384
        assert info_neural["is_local"] is True
        assert info_neural["is_neural"] is True
        assert info_neural["model_name"] == "BAAI/bge-small-en-v1.5"
        assert info_neural["model_type"] == "NEURAL_TRANSFORMER"

    # Neural SentenceTransformer Provider checks
    from app.services.embedding.sentence_transformer import LocalSentenceTransformerProvider
    st_provider = LocalSentenceTransformerProvider(model_name="all-MiniLM-L6-v2")
    assert st_provider.model_name == "all-MiniLM-L6-v2"
    st_info = st_provider.model_info()
    assert st_info["is_neural"] is True
    assert st_info["model_type"] == "NEURAL_TRANSFORMER"
    # When unprovisioned in test environment, reports EMBEDDING_MODEL_UNAVAILABLE without crashing
    st_health = st_provider.health()
    if not st_info.get("loaded"):
        assert st_health["status"] == "EMBEDDING_MODEL_UNAVAILABLE"
        assert st_health["available"] is False


def test_chunk_indexing_and_duplicate_prevention(db_session: Session, retrieval_test_setup):
    """Verify chunk embedding persistence, duplicate prevention, and force re-indexing."""
    doc_id = retrieval_test_setup["doc_bccl"].id
    
    # 1. First indexing run
    res1 = indexing_service.index_document_chunks(db_session, doc_id, force=False)
    assert res1["status"] == "COMPLETED"
    assert res1["indexed_count"] == 2
    assert res1["skipped_count"] == 0

    # 2. Second indexing run without force: should skip existing
    res2 = indexing_service.index_document_chunks(db_session, doc_id, force=False)
    assert res2["indexed_count"] == 0
    assert res2["skipped_count"] == 2

    # 3. Third run with force=True: replaces safely without duplicate key violation
    res3 = indexing_service.index_document_chunks(db_session, doc_id, force=True)
    assert res3["indexed_count"] == 2
    assert res3["skipped_count"] == 0


def test_keyword_retrieval_exact_terms(db_session: Session, retrieval_test_setup):
    """Verify keyword engine matches exact technical codes: borehole ID, seam, mine."""
    indexing_service.index_document_chunks(db_session, retrieval_test_setup["doc_bccl"].id, force=True)

    results = keyword_search_engine.search(
        db=db_session,
        query="BH-04 Seam-III Moonidih",
        filters={"document_id": retrieval_test_setup["doc_bccl"].id},
        top_k=5
    )
    assert len(results) > 0
    assert results[0]["chunk_id"] == retrieval_test_setup["chunk_narrative"].id


def test_dense_semantic_retrieval(db_session: Session, retrieval_test_setup):
    """Verify pgvector dense search retrieves semantically relevant chunk."""
    indexing_service.index_document_chunks(db_session, retrieval_test_setup["doc_bccl"].id, force=True)

    results = dense_search_engine.search(
        db=db_session,
        query="drilling exploration strata report in Moonidih",
        filters={"document_id": retrieval_test_setup["doc_bccl"].id},
        top_k=5
    )
    assert len(results) > 0
    assert any(r["document_id"] == retrieval_test_setup["doc_bccl"].id for r in results)


def test_reciprocal_rank_fusion():
    """Verify RRF formula combines candidate ranks and weights correctly."""
    kw_candidates = [
        {"chunk_id": "c1", "document_id": "d1", "page_number": 1, "chunk_type": "TEXT", "content": "A", "score": 0.9, "rank": 1, "organization_id": "o1"},
        {"chunk_id": "c2", "document_id": "d1", "page_number": 2, "chunk_type": "TEXT", "content": "B", "score": 0.8, "rank": 2, "organization_id": "o1"},
    ]
    dense_candidates = [
        {"chunk_id": "c2", "document_id": "d1", "page_number": 2, "chunk_type": "TEXT", "content": "B", "score": 0.95, "rank": 1, "organization_id": "o1"},
        {"chunk_id": "c3", "document_id": "d1", "page_number": 3, "chunk_type": "TEXT", "content": "C", "score": 0.70, "rank": 2, "organization_id": "o1"},
    ]

    # c2 appears in both keyword (rank 2) and dense (rank 1)
    fused = reciprocal_rank_fusion.fuse(kw_candidates, dense_candidates, top_k=5)
    assert len(fused) == 3
    # c2 should have highest combined RRF score
    assert fused[0]["chunk_id"] == "c2"
    assert fused[0]["retrieval_method"] == "HYBRID"
    assert fused[0]["dense_rank"] == 1
    assert fused[0]["keyword_rank"] == 2


def test_local_reranker_fallback():
    """Verify reranker gracefully falls back when disabled or weights unavailable."""
    candidates = [
        {"chunk_id": "c1", "content": "Candidate 1", "rrf_score": 0.05},
        {"chunk_id": "c2", "content": "Candidate 2", "rrf_score": 0.03}
    ]
    local_reranker.enabled = False
    reranked, status = local_reranker.rerank("test query", candidates, top_k=2)
    assert status == "DISABLED"
    assert reranked[0]["chunk_id"] == "c1"
    assert reranked[0]["reranker_score"] is None
    local_reranker.enabled = True


def test_query_normalization_entities_and_temporality():
    """Verify deterministic query normalizer extracts subsidiaries, mines, and fiscal periods."""
    q1 = query_normalizer.normalize("What was production at Moonidih during FY2024-25?")
    assert "Moonidih" in q1.entities
    assert "production" in q1.metrics
    assert "FY2024-25" in q1.fiscal_years

    q2 = query_normalizer.normalize("Compare exploration activity between FY2022-23 and FY2024-25")
    assert "exploration" in q2.topics
    assert q2.period_start == "FY2022-23"
    assert q2.period_end == "FY2024-25"

    q3 = query_normalizer.normalize("What documents discuss borehole drilling at Rajmahal?")
    assert "Rajmahal" in q3.entities
    assert "drilling" in q3.topics


def test_temporal_and_metadata_filtering(db_session: Session, retrieval_test_setup):
    """Verify search filters on FY, document type, and source tier."""
    indexing_service.index_document_chunks(db_session, retrieval_test_setup["doc_bccl"].id, force=True)
    indexing_service.index_document_chunks(db_session, retrieval_test_setup["doc_ecl"].id, force=True)

    # Filter by FY2024-25 -> should include BCCL document and strictly exclude ECL document
    res_fy = retrieval_service.retrieve(
        db=db_session,
        query="Moonidih mining report",
        allowed_org_ids=[retrieval_test_setup["org_bccl"].id, retrieval_test_setup["org_ecl"].id],
        filters={"fiscal_year": "FY2024-25"},
        top_k=10
    )
    assert len(res_fy["results"]) > 0
    for r in res_fy["results"]:
        assert r["organization_id"] == retrieval_test_setup["org_bccl"].id
        assert r["document_id"] != retrieval_test_setup["doc_ecl"].id

    # Filter by document_type = PRODUCTION_SUMMARY -> should include ECL document and strictly exclude BCCL document
    res_type = retrieval_service.retrieve(
        db=db_session,
        query="Rajmahal production",
        allowed_org_ids=[retrieval_test_setup["org_bccl"].id, retrieval_test_setup["org_ecl"].id],
        filters={"document_type": "PRODUCTION_SUMMARY"},
        top_k=10
    )
    assert len(res_type["results"]) > 0
    for r in res_type["results"]:
        assert r["document_type"] == "PRODUCTION_SUMMARY"
        assert r["organization_id"] == retrieval_test_setup["org_ecl"].id
        assert r["document_id"] != retrieval_test_setup["doc_bccl"].id


def test_multipage_table_provenance_preservation(db_session: Session, retrieval_test_setup):
    """Verify retrieved multi-page table chunk preserves physical source page (Page 3) and logical table ID."""
    indexing_service.index_document_chunks(db_session, retrieval_test_setup["doc_bccl"].id, force=True)

    res = retrieval_service.retrieve(
        db=db_session,
        query="Seam Stratigraphy Analysis Thickness Ash",
        filters={"document_id": retrieval_test_setup["doc_bccl"].id},
        search_mode="KEYWORD",
        top_k=5
    )
    table_results = [r for r in res["results"] if r["chunk_type"] == "TABLE"]
    assert len(table_results) > 0
    tbl_result = table_results[0]
    
    # Check physical page provenance
    assert tbl_result["page_number"] == 3
    # Check table provenance lineage
    assert tbl_result["provenance"]["table"]["logical_table_id"] == "log_tbl_moonidih_01"
    assert tbl_result["provenance"]["table"]["part_number"] == 2
    assert tbl_result["provenance"]["table"]["total_parts"] == 2


def test_server_side_organization_security_isolation(db_session: Session, retrieval_test_setup):
    """Verify non-HQ user cannot query or leak cross-organization evidence."""
    indexing_service.index_document_chunks(db_session, retrieval_test_setup["doc_bccl"].id, force=True)
    indexing_service.index_document_chunks(db_session, retrieval_test_setup["doc_ecl"].id, force=True)

    ecl_user = retrieval_test_setup["user_ecl"]
    token = create_access_token(ecl_user.username)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Attempting to query with another organization's ID -> 403 Forbidden
    res_forbidden = client.post(
        "/api/v1/search/query",
        headers=headers,
        json={
            "query": "Moonidih Seam",
            "organization_id": retrieval_test_setup["org_bccl"].id
        }
    )
    assert res_forbidden.status_code == 403
    assert "Access denied" in res_forbidden.json()["detail"]

    # 2. General search without org parameter -> strictly scoped to ECL
    res_scoped = client.post(
        "/api/v1/search/query",
        headers=headers,
        json={"query": "Moonidih borehole drilling", "top_k": 10}
    )
    assert res_scoped.status_code == 200
    # No BCCL results leaked
    for r in res_scoped.json()["results"]:
        assert r["organization_id"] == retrieval_test_setup["org_ecl"].id


def test_api_search_query_and_trace(db_session: Session, retrieval_test_setup):
    """Verify /api/v1/search/query returns results, trace, positive latencies, and logs audit event."""
    indexing_service.index_document_chunks(db_session, retrieval_test_setup["doc_bccl"].id, force=True)

    hq_user = retrieval_test_setup["user_hq"]
    token = create_access_token(hq_user.username)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/api/v1/search/query",
        headers=headers,
        json={"query": "Moonidih borehole drilling BH-04", "search_mode": "HYBRID", "top_k": 5}
    )
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert "trace" in data
    assert data["trace"]["search_mode"] == "HYBRID"
    assert data["trace"]["timings_ms"]["total"] > 0

    # Verify audit event persisted
    audit_evt = db_session.query(AuditEvent).filter(
        AuditEvent.action == "SEARCH_QUERY_EXECUTED",
        AuditEvent.actor_id == hq_user.id
    ).order_by(AuditEvent.created_at.desc()).first()
    assert audit_evt is not None
    assert audit_evt.details["search_mode"] == "HYBRID"


def test_api_search_status_and_reindex(db_session: Session, retrieval_test_setup):
    """Verify /api/v1/search/status and /api/v1/search/reindex endpoints."""
    hq_user = retrieval_test_setup["user_hq"]
    token = create_access_token(hq_user.username)
    headers = {"Authorization": f"Bearer {token}"}

    # Status check
    res_status = client.get("/api/v1/search/status", headers=headers)
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert "total_chunks" in status_data
    assert "total_embeddings" in status_data
    assert status_data["health"]["status"] == "UP"
    assert status_data["provider_info"]["model_name"] == "BAAI/bge-small-en-v1.5"
    assert status_data["provider_info"]["is_neural"] is True
    assert status_data["neural_model_availability"]["target_model"] == "BAAI/bge-small-en-v1.5"
    assert status_data["neural_model_availability"]["available"] is True

    # Reindex endpoint
    res_reindex = client.post("/api/v1/search/reindex?force=false", headers=headers)
    assert res_reindex.status_code == 200
    reindex_data = res_reindex.json()
    assert "total_documents" in reindex_data
    assert "total_indexed" in reindex_data
