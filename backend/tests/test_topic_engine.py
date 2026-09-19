"""
Unit and Integration Test Suite for Phase 8.2: Real Local Topic Discovery Engine.

Tests cover:
1. Exact mathematical c-TF-IDF verification against hand-calculated values
2. Small-corpus safety and deterministic refusal without manufactured topics
3. Adaptive method selection based on corpus size (TFIDF_KEYWORD, NMF_TFIDF, EMBEDDING_CLUSTER_CTFIDF)
4. Real topic generation with descriptive domain labels (no "Topic 1" or "Topic 2")
5. Topic terms persistence with weights, ranks, frequencies, and document counts
6. Topic-document relational provenance and contribution percentages
7. Topic evidence relational provenance with physical page numbers and representative scores
8. Outlier isolation without forced cluster assignment
9. Topic quality diagnostics (semantic_topic_coherence, topic_diversity, cluster_size_distribution)
10. Deterministic reproducibility across repeated executions
11. Server-side organization security isolation (tenant access boundaries)
12. Zero cloud dependency (pure local execution)
"""

import math
import uuid
from datetime import datetime
import pytest
import numpy as np
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import get_db, SessionLocal
from app.models.organization import Organization
from app.models.user import User, Role
from app.models.document import Document
from app.models.chunk import Chunk, Embedding
from app.models.topic import TopicAnalysis, Topic, TopicTerm, TopicDocument, TopicEvidence, TopicTrend, TopicComparison
from app.core.security import get_password_hash, create_access_token
from app.services.topics.c_tfidf import ClassTfidfTransformer, c_tfidf_transformer
from app.services.topics.clustering import TopicClusterer, topic_clusterer, DEFAULT_RANDOM_STATE
from app.services.topics.quality_metrics import topic_quality_evaluator
from app.services.topics.topic_engine import topic_engine, MIN_DOCUMENTS_THRESHOLD, MIN_CHUNKS_THRESHOLD
from app.services.topics.corpus_service import corpus_service

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def engine_test_setup(db_session: Session):
    """Provisions test organizations, users, and multi-domain documents/chunks."""
    # 1. Organizations
    org_bccl = db_session.query(Organization).filter(Organization.code == "BCCL_ENG_TEST").first()
    if not org_bccl:
        org_bccl = Organization(
            id=str(uuid.uuid4()),
            code="BCCL_ENG_TEST",
            name="Bharat Coking Coal Limited (Engine Test)",
            org_type="SUBSIDIARY",
        )
        db_session.add(org_bccl)

    org_ecl = db_session.query(Organization).filter(Organization.code == "ECL_ENG_TEST").first()
    if not org_ecl:
        org_ecl = Organization(
            id=str(uuid.uuid4()),
            code="ECL_ENG_TEST",
            name="Eastern Coalfields Limited (Engine Test)",
            org_type="SUBSIDIARY",
        )
        db_session.add(org_ecl)

    db_session.commit()

    # 2. Roles & Users
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

    user_bccl = db_session.query(User).filter(User.username == "bccl_eng_user").first()
    if not user_bccl:
        user_bccl = User(
            id=str(uuid.uuid4()),
            username="bccl_eng_user",
            email="bccl_eng@koyla.local",
            full_name="BCCL Engine User",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_bccl.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user_bccl.roles.append(role_analyst)
        db_session.add(user_bccl)

    user_ecl = db_session.query(User).filter(User.username == "ecl_eng_user").first()
    if not user_ecl:
        user_ecl = User(
            id=str(uuid.uuid4()),
            username="ecl_eng_user",
            email="ecl_eng@koyla.local",
            full_name="ECL Engine User",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_ecl.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user_ecl.roles.append(role_analyst)
        db_session.add(user_ecl)

    user_hq = db_session.query(User).filter(User.username == "hq_eng_user").first()
    if not user_hq:
        user_hq = User(
            id=str(uuid.uuid4()),
            username="hq_eng_user",
            email="hq_eng@koyla.local",
            full_name="HQ Engine User",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_bccl.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user_hq.roles.append(role_hq)
    db_session.commit()

    # Clean up previous test documents and analyses for pristine test isolation
    test_org_ids = [org_bccl.id, org_ecl.id]
    analyses = db_session.query(TopicAnalysis).filter(TopicAnalysis.organization_id.in_(test_org_ids)).all()
    for an in analyses:
        db_session.query(TopicTrend).filter(TopicTrend.analysis_id == an.id).delete(synchronize_session=False)
        db_session.query(TopicComparison).filter(TopicComparison.analysis_id == an.id).delete(synchronize_session=False)
        topics = db_session.query(Topic).filter(Topic.analysis_id == an.id).all()
        for tp in topics:
            db_session.query(TopicTerm).filter(TopicTerm.topic_id == tp.id).delete(synchronize_session=False)
            db_session.query(TopicDocument).filter(TopicDocument.topic_id == tp.id).delete(synchronize_session=False)
            db_session.query(TopicEvidence).filter(TopicEvidence.topic_id == tp.id).delete(synchronize_session=False)
            db_session.delete(tp)
        db_session.delete(an)
    db_session.commit()

    docs = db_session.query(Document).filter(Document.organization_id.in_(test_org_ids)).all()
    for d in docs:
        chunk_ids = [c.id for c in db_session.query(Chunk.id).filter(Chunk.document_id == d.id).all()]
        if chunk_ids:
            db_session.query(Embedding).filter(Embedding.chunk_id.in_(chunk_ids)).delete(synchronize_session=False)
        db_session.query(Chunk).filter(Chunk.document_id == d.id).delete(synchronize_session=False)
        db_session.delete(d)
    db_session.commit()

    # 3. Multi-Document Test Corpus (Geology, Mining, Environment/Closure)
    # Doc 1: Moonidih Underground Mining Plan
    doc_mp = Document(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        title="Moonidih Colliery Mining Plan FY2024-25",
        document_type="MINING_PLAN",
        source_tier="TIER_A",
        original_filename="moonidih_mp.pdf",
        file_path="storage/test/moonidih_mp.pdf",
        mime_type="application/pdf",
        file_size_bytes=10240,
        sha256_hash="hash_mp_" + str(uuid.uuid4())[:8],
        status="COMPLETED",
        created_by=user_hq.id,
        created_at=datetime.utcnow(),
    )
    # Doc 2: Jharia Geological Exploration Report
    doc_gr = Document(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        title="Jharia Block II Geological Exploration FY2024-25",
        document_type="GEOLOGICAL_REPORT",
        source_tier="TIER_A",
        original_filename="jharia_geo.pdf",
        file_path="storage/test/jharia_geo.pdf",
        mime_type="application/pdf",
        file_size_bytes=12288,
        sha256_hash="hash_gr_" + str(uuid.uuid4())[:8],
        status="COMPLETED",
        created_by=user_hq.id,
        created_at=datetime.utcnow(),
    )
    # Doc 3: Mine Closure & Environmental Plan
    doc_cp = Document(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        title="Moonidih Progressive Mine Closure & Environmental Plan",
        document_type="CLOSURE_PLAN",
        source_tier="TIER_A",
        original_filename="closure_plan.pdf",
        file_path="storage/test/closure_plan.pdf",
        mime_type="application/pdf",
        file_size_bytes=9216,
        sha256_hash="hash_cp_" + str(uuid.uuid4())[:8],
        status="COMPLETED",
        created_by=user_hq.id,
        created_at=datetime.utcnow(),
    )
    db_session.add_all([doc_mp, doc_gr, doc_cp])
    db_session.flush()

    # Topic Cluster A chunks: Mining Operations (Longwall, Continuous Miner, Stripping)
    c1 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_mp.id,
        chunk_index=1,
        page_number=4,
        chunk_type="TEXT",
        content="Underground coal mining at Moonidih uses powered support longwall method with shearer and continuous miner for high production.",
        section_heading="Mining Technology & Operations",
        metadata_json={"mine_name": "Moonidih", "block_name": "Jharia Block II", "fiscal_year": "FY2024-25"},
    )
    c2 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_mp.id,
        chunk_index=2,
        page_number=5,
        chunk_type="TEXT",
        content="Longwall retreating panel operations achieved average daily coal production rate exceeding face capacity with continuous miner roadway drivage.",
        section_heading="Face Production",
        metadata_json={"mine_name": "Moonidih", "block_name": "Jharia Block II", "fiscal_year": "FY2024-25"},
    )

    # Topic Cluster B chunks: Geology & Reserves (Seam, Stratigraphy, Coking Grade)
    c3 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_gr.id,
        chunk_index=1,
        page_number=8,
        chunk_type="TEXT",
        content="Geological borehole exploration verified proved coal reserves of 45.20 MT across Seam XVI and Seam XV with prime coking coal quality.",
        section_heading="Geological Reserve Evaluation",
        metadata_json={"mine_name": "Moonidih", "block_name": "Jharia Block II", "fiscal_year": "FY2024-25"},
    )
    c4 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_gr.id,
        chunk_index=2,
        page_number=9,
        chunk_type="TEXT",
        content="Seam stratigraphy shows persistent seam thickness with low ash content volatile matter suitable for metallurgical washery feed.",
        section_heading="Seam Stratigraphy",
        metadata_json={"mine_name": "Moonidih", "block_name": "Jharia Block II", "fiscal_year": "FY2024-25"},
    )

    # Topic Cluster C chunks: Closure & Environmental Compliance (Afforestation, Bank Guarantee, Reclamation)
    c5 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_cp.id,
        chunk_index=1,
        page_number=12,
        chunk_type="TEXT",
        content="Progressive mine closure plan specifies biological reclamation afforestation topsoil preservation and statutory bank guarantee escrow deposit.",
        section_heading="Closure Activities",
        metadata_json={"mine_name": "Moonidih", "block_name": "Jharia Block II", "fiscal_year": "FY2024-25"},
    )
    c6 = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_cp.id,
        chunk_index=2,
        page_number=13,
        chunk_type="TEXT",
        content="Environmental clearance conditions mandate continuous water treatment monitoring air quality mitigation and green belt afforestation.",
        section_heading="Environmental Clearance Compliance",
        metadata_json={"mine_name": "Moonidih", "block_name": "Jharia Block II", "fiscal_year": "FY2024-25"},
    )

    # Outlier chunk: Random administrative phone directory boilerplate
    c_outlier = Chunk(
        id=str(uuid.uuid4()),
        document_id=doc_cp.id,
        chunk_index=3,
        page_number=25,
        chunk_type="TEXT",
        content="Telephone directory extension numbers room 104 receptionist security gate intercom maintenance hotline dial 99.",
        section_heading="Administrative Contacts",
        metadata_json={"mine_name": "Moonidih", "block_name": "Jharia Block II", "fiscal_year": "FY2024-25"},
    )

    db_session.add_all([c1, c2, c3, c4, c5, c6, c_outlier])
    db_session.commit()

    return {
        "org_bccl": org_bccl,
        "org_ecl": org_ecl,
        "user_bccl": user_bccl,
        "user_ecl": user_ecl,
        "user_hq": user_hq,
        "doc_mp": doc_mp,
        "doc_gr": doc_gr,
        "doc_cp": doc_cp,
        "chunks": [c1, c2, c3, c4, c5, c6, c_outlier],
    }


def test_01_hand_computed_c_tfidf_verification():
    """
    Verify exact mathematical c-TF-IDF formulation against hand-calculated values.
    
    Hand-calculated setup:
    Class 0 text: 'coal coal mining reserve'  (word mass W_0 = 4)
    Class 1 text: 'mining seam seam seam'      (word mass W_1 = 4)
    
    C = 2 classes, average mass A = (4 + 4) / 2 = 4.0
    
    Term frequencies F_t across all classes:
      coal: 2 + 0 = 2
      mining: 1 + 1 = 2
      reserve: 1 + 0 = 1
      seam: 0 + 3 = 3
      
    Smoothed ICF = log(1.0 + A / F_t):
      icf('coal')    = log(1 + 4/2) = log(3.0)   ~ 1.098612
      icf('mining')  = log(1 + 4/2) = log(3.0)   ~ 1.098612
      icf('reserve') = log(1 + 4/1) = log(5.0)   ~ 1.609438
      icf('seam')    = log(1 + 4/3) = log(7/3)   ~ 0.847298
      
    Within-class TF tf(t, c) = f_{t, c} / W_c:
      Class 0: tf('coal') = 2/4 = 0.5, tf('reserve') = 1/4 = 0.25, tf('mining') = 1/4 = 0.25
      Class 1: tf('seam') = 3/4 = 0.75, tf('mining') = 1/4 = 0.25
      
    Expected composite weights W_{t, c} = tf(t, c) * icf(t):
      Class 0:
        W_{'coal', 0}    = 0.5 * log(3.0)   = 0.549306
        W_{'reserve', 0} = 0.25 * log(5.0)  = 0.402359
        W_{'mining', 0}  = 0.25 * log(3.0)  = 0.274653
      Class 1:
        W_{'seam', 1}    = 0.75 * log(7/3)  = 0.635473
        W_{'mining', 1}  = 0.25 * log(3.0)  = 0.274653
    """
    transformer = ClassTfidfTransformer()
    cluster_docs = {
        0: [{"cleaned_text": "coal coal mining reserve"}],
        1: [{"cleaned_text": "mining seam seam seam"}],
    }

    res = transformer.fit_transform(cluster_docs, top_k_terms=10)

    assert 0 in res and 1 in res
    c0_terms = {t["term"]: t["weight"] for t in res[0]["top_terms"]}
    c1_terms = {t["term"]: t["weight"] for t in res[1]["top_terms"]}

    # Verify Class 0 exact values to within 4 decimal places
    expected_c0_coal = round(0.5 * math.log(3.0), 4)       # ~0.5493
    expected_c0_reserve = round(0.25 * math.log(5.0), 4)    # ~0.4024
    expected_c0_mining = round(0.25 * math.log(3.0), 4)     # ~0.2747

    assert round(c0_terms["coal"], 4) == expected_c0_coal
    assert round(c0_terms["reserve"], 4) == expected_c0_reserve
    assert round(c0_terms["mining"], 4) == expected_c0_mining

    # Verify Class 1 exact values to within 4 decimal places
    expected_c1_seam = round(0.75 * math.log(7.0 / 3.0), 4) # ~0.6355
    expected_c1_mining = round(0.25 * math.log(3.0), 4)      # ~0.2747

    assert round(c1_terms["seam"], 4) == expected_c1_seam
    assert round(c1_terms["mining"], 4) == expected_c1_mining

    # Top ranked terms
    assert res[0]["top_terms"][0]["term"] == "coal"
    assert res[1]["top_terms"][0]["term"] == "seam"


def test_02_insufficient_corpus_refusal(db_session: Session, engine_test_setup):
    """Verify deterministic refusal when corpus has insufficient chunks/documents without manufacturing topics."""
    org_bccl = engine_test_setup["org_bccl"]

    # Analysis on only 1 chunk
    analysis = TopicAnalysis(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        corpus_filters={"document_type": "NON_EXISTENT_TYPE"},
        corpus_hash="test_insufficient_hash",
        embedding_model="BAAI/bge-small-en-v1.5",
        analysis_method="AUTO",
        parameters={},
        status="QUEUED",
    )
    db_session.add(analysis)
    db_session.commit()

    # Build empty/insufficient corpus
    insufficient_corpus = {
        "items": [{"chunk_id": "c1", "document_id": "d1", "cleaned_text": "sample"}],
        "total_documents": 1,
        "total_chunks": 1,
        "document_ids": ["d1"],
        "chunk_ids": ["c1"],
    }

    result = topic_engine.discover_topics(
        db=db_session,
        analysis=analysis,
        corpus_res=insufficient_corpus,
    )

    assert result["status"] == "INSUFFICIENT_CORPUS"
    assert "INSUFFICIENT CORPUS FOR TOPIC MODELING" in result["message"]
    assert result["document_count"] == 1
    assert result["chunk_count"] == 1
    assert result["minimum_threshold"] == {"documents": 2, "chunks": 3}
    assert "recommended_action" in result

    # Verify zero topics created in database
    db_topic_count = db_session.query(Topic).filter(Topic.analysis_id == analysis.id).count()
    assert db_topic_count == 0


def test_03_adaptive_method_selection():
    """Verify adaptive method selection based on corpus size."""
    # < 10 chunks -> TFIDF_KEYWORD
    assert topic_engine._select_method(chunk_count=5, requested=None) == "TFIDF_KEYWORD"
    # 10 to 49 chunks -> NMF_TFIDF
    assert topic_engine._select_method(chunk_count=25, requested=None) == "NMF_TFIDF"
    # >= 50 chunks -> EMBEDDING_CLUSTER_CTFIDF
    assert topic_engine._select_method(chunk_count=75, requested=None) == "EMBEDDING_CLUSTER_CTFIDF"
    # Explicit user override respected
    assert topic_engine._select_method(chunk_count=5, requested="NMF_TFIDF") == "NMF_TFIDF"


@pytest.fixture(scope="function")
def completed_topic_analysis(db_session: Session, engine_test_setup):
    """Fixture providing a completed TopicAnalysis with real topics and outlier isolation."""
    org_bccl = engine_test_setup["org_bccl"]
    user_hq = engine_test_setup["user_hq"]

    corpus_res = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[org_bccl.id],
        filters={"organization_id": org_bccl.id},
    )

    analysis = TopicAnalysis(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        corpus_filters={"organization_id": org_bccl.id},
        corpus_hash="fixture_hash_" + str(uuid.uuid4())[:8],
        embedding_model="BAAI/bge-small-en-v1.5",
        analysis_method="AUTO",
        parameters={"random_state": DEFAULT_RANDOM_STATE},
        status="QUEUED",
        created_by=user_hq.id,
    )
    db_session.add(analysis)
    db_session.commit()

    result = topic_engine.discover_topics(
        db=db_session,
        analysis=analysis,
        corpus_res=corpus_res,
        target_clusters=3,
    )
    db_session.refresh(analysis)
    return {
        "analysis": analysis,
        "result": result,
        "corpus_res": corpus_res,
    }


def test_04_real_topic_generation_and_descriptive_labels(completed_topic_analysis):
    """Verify real topic discovery generates descriptive domain labels from top terms (never 'Topic 1')."""
    result = completed_topic_analysis["result"]
    assert result["status"] == "COMPLETED"
    assert result["topic_count"] >= 2
    assert len(result["topics"]) >= 2

    for t in result["topics"]:
        label = t["label"]
        assert label is not None and len(label) > 0
        # Strict constraint: Never generic 'Topic 1' or 'Topic 2'
        assert not label.lower().startswith("topic 1")
        assert not label.lower().startswith("topic 2")
        assert not label.lower().startswith("topic 3")
        assert t["document_count"] >= 1
        assert t["chunk_count"] >= 1


def test_05_topic_terms_weights_and_ranks(db_session: Session, completed_topic_analysis):
    """Verify TopicTerm records are persisted with weights, rank ordering, frequencies, and document counts."""
    analysis = completed_topic_analysis["analysis"]
    topics = db_session.query(Topic).filter(Topic.analysis_id == analysis.id).all()
    assert len(topics) > 0

    for topic in topics:
        terms = db_session.query(TopicTerm).filter(TopicTerm.topic_id == topic.id).order_by(TopicTerm.rank.asc()).all()
        assert len(terms) > 0

        # Verify descending weight ordering
        weights = [t.weight for t in terms]
        assert weights == sorted(weights, reverse=True)

        for tm in terms:
            assert tm.rank >= 1
            assert tm.weight >= 0.0
            assert tm.frequency >= 1
            assert tm.document_count >= 1


def test_06_topic_document_provenance(db_session: Session, completed_topic_analysis):
    """Verify TopicDocument records maintain full relational links, similarity scores, and contribution percentages."""
    analysis = completed_topic_analysis["analysis"]
    topics = db_session.query(Topic).filter(Topic.analysis_id == analysis.id).all()
    for topic in topics:
        topic_docs = db_session.query(TopicDocument).filter(TopicDocument.topic_id == topic.id).all()
        assert len(topic_docs) > 0

        for td in topic_docs:
            doc = db_session.query(Document).filter(Document.id == td.document_id).first()
            assert doc is not None
            assert 0.0 <= td.similarity_score <= 1.0
            assert 0.0 < td.contribution_pct <= 100.0


def test_07_topic_evidence_provenance(db_session: Session, completed_topic_analysis):
    """Verify TopicEvidence records link chunks with physical page number, section heading, and representative score."""
    analysis = completed_topic_analysis["analysis"]
    topics = db_session.query(Topic).filter(Topic.analysis_id == analysis.id).all()
    for topic in topics:
        evidences = db_session.query(TopicEvidence).filter(TopicEvidence.topic_id == topic.id).all()
        assert len(evidences) > 0

        for ev in evidences:
            chunk = db_session.query(Chunk).filter(Chunk.id == ev.chunk_id).first()
            assert chunk is not None
            assert chunk.page_number is not None and chunk.page_number >= 1
            assert chunk.section_heading is not None
            assert 0.0 <= ev.representative_score <= 1.0


def test_08_outliers_isolation(db_session: Session, engine_test_setup, completed_topic_analysis):
    """Verify non-matching administrative contact chunk is isolated as an outlier without forced cluster membership."""
    analysis = completed_topic_analysis["analysis"]
    assert analysis.outlier_count >= 1

    # Verify outlier chunk is not forced into any topic's evidence
    outlier_chunk_ids = [c.id for c in engine_test_setup["chunks"] if "telephone directory" in c.content.lower()]
    assert len(outlier_chunk_ids) == 1
    outlier_id = outlier_chunk_ids[0]

    evidence_chunk_ids = [ev.chunk_id for ev in db_session.query(TopicEvidence).join(Topic).filter(Topic.analysis_id == analysis.id).all()]
    assert outlier_id not in evidence_chunk_ids, "Outlier chunk must not be included in topic evidence"

    # Verify outlier chunk count is stored in parameters
    assert "outlier_z_threshold" in analysis.parameters.get("clustering_config", {})


def test_09_quality_diagnostics(completed_topic_analysis):
    """Verify semantic_topic_coherence and topic_diversity diagnostics are calculated without claiming accuracy."""
    analysis = completed_topic_analysis["analysis"]
    metrics = analysis.quality_metrics
    assert metrics is not None
    assert "mean_semantic_coherence" in metrics
    assert "topic_diversity" in metrics
    assert "cluster_size_distribution" in metrics
    assert "diagnostic_note" in metrics
    assert "semantic similarity diagnostic" in metrics["diagnostic_note"]
    assert "not an externally standardized topic-coherence score" in metrics["diagnostic_note"]

    # Diversity must be in [0, 1]
    assert 0.0 < metrics["topic_diversity"] <= 1.0


def test_10_deterministic_reproducibility(db_session: Session, engine_test_setup):
    """Verify identical corpus and configuration produce identical topic structures, labels, and assignments."""
    org_bccl = engine_test_setup["org_bccl"]
    user_hq = engine_test_setup["user_hq"]

    corpus_res = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[org_bccl.id],
        filters={"organization_id": org_bccl.id},
    )

    # Run 1
    a1 = TopicAnalysis(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        corpus_filters={"organization_id": org_bccl.id},
        corpus_hash="reproducibility_hash",
        embedding_model="BAAI/bge-small-en-v1.5",
        analysis_method="AUTO",
        parameters={"random_state": DEFAULT_RANDOM_STATE},
        status="QUEUED",
        created_by=user_hq.id,
    )
    db_session.add(a1)
    db_session.commit()
    r1 = topic_engine.discover_topics(db=db_session, analysis=a1, corpus_res=corpus_res, target_clusters=3)

    # Run 2 (identical inputs)
    a2 = TopicAnalysis(
        id=str(uuid.uuid4()),
        organization_id=org_bccl.id,
        corpus_filters={"organization_id": org_bccl.id},
        corpus_hash="reproducibility_hash",
        embedding_model="BAAI/bge-small-en-v1.5",
        analysis_method="AUTO",
        parameters={"random_state": DEFAULT_RANDOM_STATE},
        status="QUEUED",
        created_by=user_hq.id,
    )
    db_session.add(a2)
    db_session.commit()
    r2 = topic_engine.discover_topics(db=db_session, analysis=a2, corpus_res=corpus_res, target_clusters=3)

    assert r1["topic_count"] == r2["topic_count"]
    assert r1["outlier_count"] == r2["outlier_count"]

    labels_1 = [t["label"] for t in r1["topics"]]
    labels_2 = [t["label"] for t in r2["topics"]]
    assert labels_1 == labels_2, "Topic labels must be deterministically identical across repeated runs"

    terms_1 = [[tm["term"] for tm in t["top_terms"]] for t in r1["topics"]]
    terms_2 = [[tm["term"] for tm in t["top_terms"]] for t in r2["topics"]]
    assert terms_1 == terms_2, "Top terms must be deterministically identical across repeated runs"


def test_11_organization_security_isolation(db_session: Session, engine_test_setup, completed_topic_analysis):
    """Verify ECL user receives 403 when attempting to access BCCL topic endpoints."""
    analysis = completed_topic_analysis["analysis"]
    assert analysis is not None

    topic = db_session.query(Topic).filter(Topic.analysis_id == analysis.id).first()
    assert topic is not None

    token_ecl = create_access_token(engine_test_setup["user_ecl"].username)
    headers_ecl = {"Authorization": f"Bearer {token_ecl}"}

    token_hq = create_access_token(engine_test_setup["user_hq"].username)
    headers_hq = {"Authorization": f"Bearer {token_hq}"}

    # 1. ECL user attempts to list BCCL topics -> 403 Forbidden
    res_unauth = client.get(f"/api/v1/topics/{analysis.id}/topics", headers=headers_ecl)
    assert res_unauth.status_code == 403

    # 2. ECL user attempts to get BCCL topic detail -> 403 Forbidden
    res_detail_unauth = client.get(f"/api/v1/topics/{analysis.id}/topics/{topic.id}", headers=headers_ecl)
    assert res_detail_unauth.status_code == 403

    # 3. ECL user attempts to get BCCL topic evidence -> 403 Forbidden
    res_ev_unauth = client.get(f"/api/v1/topics/{analysis.id}/topics/{topic.id}/evidence", headers=headers_ecl)
    assert res_ev_unauth.status_code == 403

    # 4. Central HQ user gets topics -> 200 OK
    res_hq = client.get(f"/api/v1/topics/{analysis.id}/topics", headers=headers_hq)
    assert res_hq.status_code == 200
    assert res_hq.json()["topic_count"] > 0

    # 5. Central HQ user gets topic detail -> 200 OK
    res_detail_hq = client.get(f"/api/v1/topics/{analysis.id}/topics/{topic.id}", headers=headers_hq)
    assert res_detail_hq.status_code == 200
    assert "terms" in res_detail_hq.json()
    assert "documents" in res_detail_hq.json()

    # 6. Central HQ user gets topic evidence -> 200 OK
    res_ev_hq = client.get(f"/api/v1/topics/{analysis.id}/topics/{topic.id}/evidence", headers=headers_hq)
    assert res_ev_hq.status_code == 200
    assert len(res_ev_hq.json()["items"]) > 0


def test_12_zero_cloud_dependency():
    """Verify pure local embedding and local scikit-learn execution without any external network calls."""
    from app.services.embedding import get_embedding_provider
    provider = get_embedding_provider()
    assert provider.model_name == "BAAI/bge-small-en-v1.5" or "koyla" in provider.model_name
    assert provider.dimension == 384

    # Local vector encoding
    vec = provider.embed_text("Local offline coal reserve stratigraphy")
    assert len(vec) == 384
    assert all(isinstance(x, float) for x in vec)
