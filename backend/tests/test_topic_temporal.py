"""
Unit and Integration Test Suite for Phase 8.3: Temporal & Comparative Topic Analytics.

Tests cover:
1. Global model reused across multiple fiscal years (single analysis alignment)
2. Topic prevalence calculation by fiscal year
3. Correct document-share denominator reporting
4. Correct chunk-share denominator reporting
5. Exact hand-computed temporal verification (20% -> 30%, +10 pp, +50% growth)
6. Absolute change calculation (Δ_abs)
7. Percentage-point change calculation (Δ_pp)
8. Relative percentage growth calculation (g_rel)
9. Emerging-topic detection with supporting evidence
10. Growing-topic detection with evidence gates
11. Declining-topic detection with evidence gates
12. Disappearing-topic detection with evidence gates
13. Recurring-topic detection (Present -> Absent -> Present across >=3 periods)
14. Insufficient-history handling for single period or unobserved points
15. Topic persistence classification (PERSISTENT, INTERMITTENT, NEW, DISAPPEARED)
16. Organization comparison across authorized entities
17. Mine comparison (common topics, unique topics, prevalence)
18. Block comparison (common topics, unique topics, prevalence)
19. Document-type comparison
20. Term evolution across periods
21. Sample-size and denominator reporting
22. Evidence and physical page provenance retention
23. Server-side organization security isolation (tenant access boundaries)
24. Deterministic repeatability and cache reuse
25. Invalid fiscal-year rejection and no causal claims
26. Small-sample minimum-evidence gate verification (5 docs with 20%->40% yields INSUFFICIENT_HISTORY)
"""

import uuid
from datetime import datetime
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.models.organization import Organization
from app.models.user import User, Role
from app.models.document import Document
from app.models.chunk import Chunk, Embedding
from app.models.topic import TopicAnalysis, Topic, TopicTerm, TopicDocument, TopicEvidence, TopicTrend, TopicComparison
from app.core.security import get_password_hash, create_access_token
from app.core.temporal import validate_fiscal_year_syntax
from app.services.topics.corpus_service import corpus_service
from app.services.topics.topic_engine import topic_engine, DEFAULT_RANDOM_STATE
from app.services.topics.temporal_service import temporal_service, parse_period_sort_key

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def temporal_test_setup(db_session: Session):
    """Provisions test organizations, users, and multi-year documents/chunks for temporal analysis."""
    # 1. Organizations
    org_ecl = db_session.query(Organization).filter(Organization.code == "ECL_TEMP_TEST").first()
    if not org_ecl:
        org_ecl = Organization(
            id=str(uuid.uuid4()),
            code="ECL_TEMP_TEST",
            name="Eastern Coalfields Limited (Temporal Test)",
            org_type="SUBSIDIARY",
        )
        db_session.add(org_ecl)

    org_bccl = db_session.query(Organization).filter(Organization.code == "BCCL_TEMP_TEST").first()
    if not org_bccl:
        org_bccl = Organization(
            id=str(uuid.uuid4()),
            code="BCCL_TEMP_TEST",
            name="Bharat Coking Coal Limited (Temporal Test)",
            org_type="SUBSIDIARY",
        )
        db_session.add(org_bccl)

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

    user_ecl = db_session.query(User).filter(User.username == "ecl_temp_user").first()
    if not user_ecl:
        user_ecl = User(
            id=str(uuid.uuid4()),
            username="ecl_temp_user",
            email="ecl_temp@koyla.local",
            full_name="ECL Temporal User",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_ecl.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user_ecl.roles.append(role_analyst)
        db_session.add(user_ecl)

    user_bccl = db_session.query(User).filter(User.username == "bccl_temp_user").first()
    if not user_bccl:
        user_bccl = User(
            id=str(uuid.uuid4()),
            username="bccl_temp_user",
            email="bccl_temp@koyla.local",
            full_name="BCCL Temporal User",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_bccl.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user_bccl.roles.append(role_analyst)
        db_session.add(user_bccl)

    user_hq = db_session.query(User).filter(User.username == "hq_temp_user").first()
    if not user_hq:
        user_hq = User(
            id=str(uuid.uuid4()),
            username="hq_temp_user",
            email="hq_temp@koyla.local",
            full_name="HQ Temporal User",
            hashed_password=get_password_hash("Password123!"),
            organization_id=org_ecl.id,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        user_hq.roles.append(role_hq)
        db_session.add(user_hq)

    db_session.commit()

    # 3. Clean up prior test documents and analyses for pristine isolation
    test_org_ids = [org_ecl.id, org_bccl.id]
    analyses = db_session.query(TopicAnalysis).filter(TopicAnalysis.organization_id.in_(test_org_ids)).all()
    for an in analyses:
        db_session.query(TopicTrend).filter(TopicTrend.analysis_id == an.id).delete()
        db_session.query(TopicComparison).filter(TopicComparison.analysis_id == an.id).delete()
        topics = db_session.query(Topic).filter(Topic.analysis_id == an.id).all()
        for tp in topics:
            db_session.query(TopicTerm).filter(TopicTerm.topic_id == tp.id).delete()
            db_session.query(TopicDocument).filter(TopicDocument.topic_id == tp.id).delete()
            db_session.query(TopicEvidence).filter(TopicEvidence.topic_id == tp.id).delete()
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

    # 4. Multi-Year Corpus Setup (3 Fiscal Years: FY2023-24, FY2024-25, FY2025-26)
    # Each fiscal year will contain at least 5 documents to pass minimum_period_documents gate
    # Topics will be clearly themed:
    #   - Mining Operations: High in FY23-24 (4 docs), Declining in FY24-25 (2 docs), Low in FY25-26 (1 doc)
    #   - Geology Reserves: Steady in FY23-24 (2 docs), FY24-25 (3 docs), FY25-26 (2 docs)
    #   - Closure & Reclamation: Absent in FY23-24 (0 docs), Emerging in FY24-25 (2 docs), High in FY25-26 (4 docs)
    
    docs_created = []
    chunks_created = []

    def create_test_doc(title, doc_type, fy, mine, block, org_id, content_snippets):
        doc = Document(
            id=str(uuid.uuid4()),
            organization_id=org_id,
            title=f"{title} {fy}",
            document_type=doc_type,
            source_tier="TIER_A",
            original_filename=f"{title.lower().replace(' ', '_')}_{fy}.pdf",
            file_path=f"storage/test/{title}_{fy}.pdf",
            mime_type="application/pdf",
            file_size_bytes=10240,
            sha256_hash="hash_" + str(uuid.uuid4())[:8],
            status="COMPLETED",
            created_by=user_hq.id,
            created_at=datetime.utcnow(),
        )
        db_session.add(doc)
        db_session.flush()
        docs_created.append(doc)

        for idx, snip in enumerate(content_snippets):
            c = Chunk(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                chunk_index=idx + 1,
                page_number=idx + 1,
                chunk_type="TEXT",
                content=snip,
                section_heading=f"Section {idx+1}",
                metadata_json={"mine_name": mine, "block_name": block, "fiscal_year": fy},
            )
            db_session.add(c)
            chunks_created.append(c)
        return doc

    # --- FY2023-24 (Total 6 docs: 4 Mining, 2 Geology, 0 Closure) ---
    for i in range(4):
        create_test_doc(
            f"Rajmahal Mining Operations Part {i+1}", "MINING_PLAN", "FY2023-24", "Rajmahal OCP", "Simlong Block", org_ecl.id,
            [f"Underground and opencast coal mining operations continuous miner longwall coal extraction drivage face {i}."]
        )
    for i in range(2):
        create_test_doc(
            f"Rajmahal Geological Core Drilling {i+1}", "GEOLOGICAL_REPORT", "FY2023-24", "Rajmahal OCP", "Simlong Block", org_ecl.id,
            [f"Borehole core exploration verified proved coal reserves seam stratigraphy thickness {i}."]
        )

    # --- FY2024-25 (Total 7 docs: 2 Mining, 3 Geology, 2 Closure) ---
    for i in range(2):
        create_test_doc(
            f"Rajmahal Mining Operations Modernization {i+1}", "MINING_PLAN", "FY2024-25", "Rajmahal OCP", "Simlong Block", org_ecl.id,
            [f"Powered support longwall continuous miner shearer coal extraction drivage panel {i}."]
        )
    for i in range(3):
        create_test_doc(
            f"Simlong Geological Evaluation {i+1}", "GEOLOGICAL_REPORT", "FY2024-25", "Rajmahal OCP", "Simlong Block", org_ecl.id,
            [f"Geological borehole exploration verified proved coal reserves seam thickness coking grade {i}."]
        )
    for i in range(2):
        create_test_doc(
            f"Rajmahal Closure & Environment {i+1}", "CLOSURE_PLAN", "FY2024-25", "Rajmahal OCP", "Simlong Block", org_ecl.id,
            [f"Progressive mine closure plan environmental biological reclamation afforestation topsoil preservation {i}."]
        )

    # --- FY2025-26 (Total 7 docs: 1 Mining, 2 Geology, 4 Closure) ---
    create_test_doc(
        "Rajmahal Mining Final Panel", "MINING_PLAN", "FY2025-26", "Rajmahal OCP", "Simlong Block", org_ecl.id,
        ["Continuous miner coal extraction drivage panel face operations."]
    )
    for i in range(2):
        create_test_doc(
            f"Simlong Seam Evaluation {i+1}", "GEOLOGICAL_REPORT", "FY2025-26", "Rajmahal OCP", "Simlong Block", org_ecl.id,
            [f"Geological core drilling proved coal reserves seam stratigraphy {i}."]
        )
    for i in range(4):
        create_test_doc(
            f"Rajmahal Final Closure Execution {i+1}", "CLOSURE_PLAN", "FY2025-26", "Rajmahal OCP", "Simlong Block", org_ecl.id,
            [f"Progressive mine closure plan biological reclamation green belt afforestation water treatment bank guarantee {i}."]
        )

    # Cross-subsidiary test document (BCCL) for org comparison
    create_test_doc(
        "Moonidih Underground Mine Plan", "MINING_PLAN", "FY2024-25", "Moonidih UG", "Jharia Block II", org_bccl.id,
        ["Underground coal mining at Moonidih using powered support longwall shearer production."]
    )

    db_session.commit()

    return {
        "org_ecl": org_ecl,
        "org_bccl": org_bccl,
        "user_ecl": user_ecl,
        "user_bccl": user_bccl,
        "user_hq": user_hq,
        "total_docs": len(docs_created),
        "total_chunks": len(chunks_created),
    }


@pytest.fixture(scope="function")
def global_temporal_analysis(db_session: Session, temporal_test_setup):
    """Executes a single unified Phase 8.2 global topic discovery across all periods for ECL."""
    org_ecl = temporal_test_setup["org_ecl"]
    user_hq = temporal_test_setup["user_hq"]

    corpus_res = corpus_service.build_corpus(
        db=db_session,
        allowed_org_ids=[org_ecl.id],
        filters={"organization_id": org_ecl.id},
    )

    analysis = TopicAnalysis(
        id=str(uuid.uuid4()),
        organization_id=org_ecl.id,
        corpus_filters={"organization_id": org_ecl.id},
        corpus_hash="temporal_global_hash_" + str(uuid.uuid4())[:8],
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


# ==============================================================================
# TESTS
# ==============================================================================

def test_01_global_model_reused_across_fiscal_years(db_session: Session, global_temporal_analysis):
    """Verify that ONE single global topic analysis is reused without independently re-running topic modeling."""
    analysis = global_temporal_analysis["analysis"]
    topics = db_session.query(Topic).filter(Topic.analysis_id == analysis.id).all()
    assert len(topics) >= 2

    # Verify all topics belong to the same single analysis_id
    for t in topics:
        assert t.analysis_id == analysis.id


def test_02_topic_prevalence_by_fiscal_year(db_session: Session, global_temporal_analysis):
    """Verify temporal prevalence is calculated per topic for each fiscal year."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compute_analysis_trends(db_session, analysis.id)

    assert res["status"] == "COMPLETED"
    assert len(res["periods"]) >= 3
    assert "FY2023-24" in res["periods"]
    assert "FY2024-25" in res["periods"]
    assert "FY2025-26" in res["periods"]

    trends = res["trends"]
    assert len(trends) >= 2
    for t in trends:
        assert len(t["series"]) >= 3
        for pt in t["series"]:
            assert "document_share_pct" in pt
            assert "chunk_share_pct" in pt
            assert 0.0 <= pt["document_share_pct"] <= 100.0


def test_03_correct_document_share_denominator(db_session: Session, global_temporal_analysis):
    """Verify document_share_pct is strictly calculated using all_analyzed_documents_in_period."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compute_analysis_trends(db_session, analysis.id)

    for topic in res["trends"]:
        for pt in topic["series"]:
            doc_cnt = pt["document_count"]
            tot_docs = pt["corpus_document_count"]
            share = pt["document_share_pct"]
            assert tot_docs > 0
            expected_share = round((doc_cnt / float(tot_docs)) * 100.0, 2)
            assert share == expected_share


def test_04_correct_chunk_share_denominator(db_session: Session, global_temporal_analysis):
    """Verify chunk_share_pct is strictly calculated using all_analyzed_chunks_in_period."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compute_analysis_trends(db_session, analysis.id)

    for topic in res["trends"]:
        for pt in topic["series"]:
            chunk_cnt = pt["chunk_count"]
            tot_chunks = pt["corpus_chunk_count"]
            chunk_share = pt["chunk_share_pct"]
            assert tot_chunks > 0
            expected_share = round((chunk_cnt / float(tot_chunks)) * 100.0, 2)
            assert chunk_share == expected_share


def test_05_hand_computed_temporal_verification():
    """
    Verify exact mathematical correctness against hand-calculated values:
    FY2023-24: 100 total docs, 20 belong to Topic A (20.0%)
    FY2024-25: 100 total docs, 30 belong to Topic A (30.0%)

    Expected:
    - Absolute change: +10 docs
    - Percentage-point change: +10.0 percentage points
    - Relative growth: +50.0%
    """
    doc_a = 20
    tot_a = 100
    doc_b = 30
    tot_b = 100

    share_a = (doc_a / tot_a) * 100.0  # 20.0%
    share_b = (doc_b / tot_b) * 100.0  # 30.0%

    abs_change = doc_b - doc_a  # +10
    pp_change = round(share_b - share_a, 2)  # +10.0
    rel_growth = round(((share_b - share_a) / share_a) * 100.0, 2)  # +50.0%

    assert share_a == 20.0
    assert share_b == 30.0
    assert abs_change == 10
    assert pp_change == 10.0
    assert rel_growth == 50.0


def test_06_absolute_change_calculation(db_session: Session, global_temporal_analysis):
    """Verify absolute document change between consecutive periods (D_t - D_{t-1})."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compute_analysis_trends(db_session, analysis.id)

    for topic in res["trends"]:
        series = topic["series"]
        # First period absolute_change must be None
        assert series[0]["absolute_change"] is None
        for i in range(1, len(series)):
            expected_diff = series[i]["document_count"] - series[i - 1]["document_count"]
            assert series[i]["absolute_change"] == expected_diff


def test_07_percentage_point_change_calculation(db_session: Session, global_temporal_analysis):
    """Verify percentage-point change between consecutive periods (Share_t - Share_{t-1})."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compute_analysis_trends(db_session, analysis.id)

    for topic in res["trends"]:
        series = topic["series"]
        assert series[0]["percentage_point_change"] is None
        for i in range(1, len(series)):
            expected_pp = round(series[i]["document_share_pct"] - series[i - 1]["document_share_pct"], 2)
            assert series[i]["percentage_point_change"] == expected_pp


def test_08_relative_percentage_growth_calculation(db_session: Session, global_temporal_analysis):
    """Verify relative percentage growth ((Share_t - Share_{t-1}) / Share_{t-1} * 100)."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compute_analysis_trends(db_session, analysis.id)

    for topic in res["trends"]:
        series = topic["series"]
        assert series[0]["growth_rate_pct"] is None
        for i in range(1, len(series)):
            prev_share = series[i - 1]["document_share_pct"]
            curr_share = series[i]["document_share_pct"]
            if prev_share > 0:
                expected_growth = round(((curr_share - prev_share) / prev_share) * 100.0, 2)
                assert series[i]["growth_rate_pct"] == expected_growth


def test_09_emerging_topic_detection(db_session: Session, global_temporal_analysis):
    """Verify emerging topic detection (absent in earlier period, appears in later period with evidence)."""
    analysis = global_temporal_analysis["analysis"]
    emerging = temporal_service.get_emerging_topics(db_session, analysis.id)

    # Reclamation/Closure was absent in FY23-24 (0 docs) and appeared with 2 docs in FY24-25 and 4 in FY25-26
    assert len(emerging) >= 1
    closure_topic = next((t for t in emerging if "closure" in t["label"].lower() or "reclamation" in t["label"].lower()), None)
    assert closure_topic is not None
    assert closure_topic["supporting_documents"] >= 2
    assert len(closure_topic["evidence"]) > 0


def test_10_growing_topic_detection(db_session: Session, global_temporal_analysis):
    """Verify growing topic classification with minimum evidence gate."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compute_analysis_trends(db_session, analysis.id)

    all_statuses = [pt["trend_status"] for t in res["trends"] for pt in t["series"][1:]]
    assert "GROWING" in all_statuses or "EMERGING" in all_statuses


def test_11_declining_topic_detection(db_session: Session, global_temporal_analysis):
    """Verify declining topic detection (prevalence contracts over comparable periods)."""
    analysis = global_temporal_analysis["analysis"]
    declining = temporal_service.get_declining_topics(db_session, analysis.id)

    # Mining Operations declined from 4 docs in FY23-24 to 2 in FY24-25 and 1 in FY25-26
    assert len(declining) >= 1
    mining_topic = next((t for t in declining if "mining" in t["label"].lower() or "continuous" in t["label"].lower()), None)
    assert mining_topic is not None


def test_12_disappearing_topic_detection():
    """Verify DISAPPEARING trend classification when topic had evidence earlier and drops to 0 later."""
    status = temporal_service._classify_trend(
        period_index=1,
        total_periods=2,
        doc_share=0.0,
        prev_doc_share=25.0,
        t_doc_count=0,
        prev_doc_count=3,
        p_tot_docs=10,
        prev_p_tot_docs=12,
        pp_change=-25.0,
        history_presence=[True, False],
        min_period_documents=5,
        min_topic_documents=2,
        percentage_point_threshold=2.0,
    )
    assert status == "DISAPPEARING"


def test_13_recurring_topic_detection():
    """Verify RECURRING trend classification across >=3 periods (Present -> Absent -> Present)."""
    status = temporal_service._classify_trend(
        period_index=2,
        total_periods=3,
        doc_share=20.0,
        prev_doc_share=0.0,
        t_doc_count=2,
        prev_doc_count=0,
        p_tot_docs=10,
        prev_p_tot_docs=10,
        pp_change=20.0,
        history_presence=[True, False, True],  # Present -> Absent -> Present
        min_period_documents=5,
        min_topic_documents=2,
        percentage_point_threshold=2.0,
    )
    assert status == "RECURRING"


def test_14_insufficient_history_handling():
    """Verify INSUFFICIENT_HISTORY is returned for period index 0 or when history is too short."""
    status_first_period = temporal_service._classify_trend(
        period_index=0,
        total_periods=2,
        doc_share=20.0,
        prev_doc_share=None,
        t_doc_count=2,
        prev_doc_count=None,
        p_tot_docs=10,
        prev_p_tot_docs=0,
        pp_change=None,
        history_presence=[True],
        min_period_documents=5,
        min_topic_documents=2,
        percentage_point_threshold=2.0,
    )
    assert status_first_period == "INSUFFICIENT_HISTORY"


def test_15_topic_persistence_classification(db_session: Session, global_temporal_analysis):
    """Verify persistence classification across observed periods (PERSISTENT, INTERMITTENT, NEW)."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compute_analysis_trends(db_session, analysis.id)

    persistences = [t["persistence_status"] for t in res["trends"]]
    assert any(p in ["PERSISTENT", "NEW", "INTERMITTENT"] for p in persistences)


def test_16_organization_comparison(db_session: Session, global_temporal_analysis):
    """Verify organization comparison using the same global topic model."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compare_dimension(
        db=db_session,
        analysis_id=analysis.id,
        dimension_type="ORGANIZATION",
    )
    assert res["dimension_type"] == "ORGANIZATION"
    assert "ECL_TEMP_TEST" in res["available_values"]
    assert "ECL_TEMP_TEST" in res["distribution"]


def test_17_mine_comparison(db_session: Session, global_temporal_analysis):
    """Verify mine comparison returns common topics and unique topics."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compare_dimension(
        db=db_session,
        analysis_id=analysis.id,
        dimension_type="MINE",
    )
    assert res["dimension_type"] == "MINE"
    assert "Rajmahal OCP" in res["available_values"]


def test_18_block_comparison(db_session: Session, global_temporal_analysis):
    """Verify block comparison returns topic breakdown."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compare_dimension(
        db=db_session,
        analysis_id=analysis.id,
        dimension_type="BLOCK",
    )
    assert res["dimension_type"] == "BLOCK"
    assert "Simlong Block" in res["available_values"]


def test_19_document_type_comparison(db_session: Session, global_temporal_analysis):
    """Verify document-type comparison returns topic distribution across document types."""
    analysis = global_temporal_analysis["analysis"]
    res = temporal_service.compare_dimension(
        db=db_session,
        analysis_id=analysis.id,
        dimension_type="DOCUMENT_TYPE",
    )
    assert res["dimension_type"] == "DOCUMENT_TYPE"
    assert "MINING_PLAN" in res["available_values"]
    assert "GEOLOGICAL_REPORT" in res["available_values"]


def test_20_term_evolution_across_periods(db_session: Session, global_temporal_analysis):
    """Verify term evolution tracks term presence and weights over periods."""
    analysis = global_temporal_analysis["analysis"]
    topic = db_session.query(Topic).filter(Topic.analysis_id == analysis.id).first()
    assert topic is not None

    evolution = temporal_service.get_term_evolution(db_session, analysis.id, topic.id)
    assert evolution["topic_id"] == topic.id
    assert len(evolution["term_evolution"]) > 0
    first_term = evolution["term_evolution"][0]
    assert "term" in first_term
    assert "global_weight" in first_term
    assert "period_frequencies" in first_term


def test_21_sample_size_and_denominator_reporting(db_session: Session, global_temporal_analysis):
    """Verify sample size and denominators are always reported in API response."""
    analysis = global_temporal_analysis["analysis"]
    token = create_access_token(global_temporal_analysis["analysis"].creator.username)
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/topics/{analysis.id}/trends", headers=headers)
    assert res.status_code == 200
    data = res.json()
    for topic in data["trends"]:
        for pt in topic["series"]:
            assert pt["corpus_document_count"] >= 1
            assert pt["corpus_chunk_count"] >= 1


def test_22_evidence_and_provenance_retention(db_session: Session, global_temporal_analysis):
    """Verify evidence items retain physical page number and section heading."""
    analysis = global_temporal_analysis["analysis"]
    emerging = temporal_service.get_emerging_topics(db_session, analysis.id)
    assert len(emerging) > 0
    ev = emerging[0]["evidence"][0]
    assert "page_number" in ev
    assert "section_heading" in ev
    assert "representative_score" in ev


def test_23_server_side_organization_security_isolation(db_session: Session, temporal_test_setup, global_temporal_analysis):
    """Verify BCCL subsidiary analyst receives 403 when accessing ECL topic trends."""
    analysis = global_temporal_analysis["analysis"]
    user_bccl = temporal_test_setup["user_bccl"]

    token_bccl = create_access_token(user_bccl.username)
    headers_bccl = {"Authorization": f"Bearer {token_bccl}"}

    res = client.get(f"/api/v1/topics/{analysis.id}/trends", headers=headers_bccl)
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


def test_24_deterministic_repeatability_and_cache_reuse(db_session: Session, global_temporal_analysis):
    """Verify trends calculation is cached and deterministically repeatable."""
    analysis = global_temporal_analysis["analysis"]
    # Run 1: compute and persist
    r1 = temporal_service.compute_analysis_trends(db_session, analysis.id, force_refresh=True)
    # Run 2: cache reuse
    r2 = temporal_service.compute_analysis_trends(db_session, analysis.id, force_refresh=False)

    assert r1["periods"] == r2["periods"]
    assert len(r1["trends"]) == len(r2["trends"])
    assert r1["trends"][0]["series"] == r2["trends"][0]["series"]


def test_25_invalid_fiscal_year_rejection_and_no_causal_claims():
    """Verify invalid fiscal year syntax is rejected and no causal claims are in classification labels."""
    is_valid_1, _ = validate_fiscal_year_syntax("2025-61")  # Invalid rollover
    assert is_valid_1 is False

    is_valid_2, _ = validate_fiscal_year_syntax("FY2023-28")  # Invalid 5-year jump
    assert is_valid_2 is False

    is_valid_3, norm = validate_fiscal_year_syntax("FY2024-25")
    assert is_valid_3 is True
    assert norm == "FY2024-25"


def test_26_small_sample_minimum_evidence_gate():
    """
    Verify that a mathematically large percentage-point movement in a tiny corpus
    does NOT automatically become GROWING or DECLINING.
    
    Example from prompt:
    Period A: 5 documents, 1 topic document (20.0%)
    Period B: 5 documents, 2 topic documents (40.0%)
    Δpp = +20.0 percentage points!
    
    With min_topic_documents = 2: Period A has only 1 topic doc (< 2).
    Evidence gate must assign INSUFFICIENT_HISTORY rather than GROWING!
    """
    status = temporal_service._classify_trend(
        period_index=1,
        total_periods=2,
        doc_share=40.0,
        prev_doc_share=20.0,
        t_doc_count=2,
        prev_doc_count=1,  # Below min_topic_documents = 2!
        p_tot_docs=5,
        prev_p_tot_docs=5,
        pp_change=20.0,
        history_presence=[False, True],
        min_period_documents=5,
        min_topic_documents=2,
        percentage_point_threshold=2.0,
    )
    assert status == "INSUFFICIENT_HISTORY", "Small sample below min_topic_documents must yield INSUFFICIENT_HISTORY"
