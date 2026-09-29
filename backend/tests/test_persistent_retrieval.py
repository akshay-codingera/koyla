import os
import sys
import uuid
import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db.database import SessionLocal
from app.models.document import Document
from app.models.chunk import Chunk, Embedding
from app.models.organization import Organization
from app.services.retrieval.keyword_search import keyword_search_engine
from app.services.retrieval.service import retrieval_service
from app.services.retrieval.fusion import reciprocal_rank_fusion

client = TestClient(app)


def test_persistent_lexical_exact_phrase(tmp_path):
    """Verify persistent lexical search matches exact technical phrases via tsquery."""
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        doc = Document(
            organization_id=org.id,
            title="Geological Exploration Report Seam IV",
            document_type="GEOLOGICAL_REPORT",
            original_filename="seam_iv_exploration.pdf",
            file_path="storage/seam_iv.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            sha256_hash="seam_iv_hash_" + str(uuid.uuid4())[:8],
            status="COMPLETED"
        )
        db.add(doc)
        db.commit()

        chunk = Chunk(
            document_id=doc.id,
            chunk_index=1,
            page_number=3,
            chunk_type="TEXT",
            section_heading="Stratigraphic Succession and Coal Seam Details",
            content="Detailed drilling confirmed Seam IV thickness of 6.25 meters with low volatile coking coal and high GCV."
        )
        db.add(chunk)
        db.commit()

        # Query exact phrase
        results = keyword_search_engine.search(
            db=db,
            query='"Seam IV thickness"',
            allowed_org_ids=[org.id],
            top_k=25
        )
        assert len(results) >= 1
        top_match = next(r for r in results if r["chunk_id"] == chunk.id)
        assert "6.25 meters" in top_match["content"]
        assert top_match["document_title"] == "Geological Exploration Report Seam IV"
    finally:
        try:
            db.delete(chunk)
            db.delete(doc)
            db.commit()
        except Exception:
            db.rollback()
        db.close()


def test_domain_terminology_and_fiscal_year():
    """Verify lexical retrieval matches domain terminology and fiscal year patterns."""
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        doc = Document(
            organization_id=org.id,
            title="Annual Mining Review Kusmunda",
            document_type="ANNUAL_REPORT",
            original_filename="kusmunda_annual.pdf",
            file_path="storage/kusmunda_annual.pdf",
            mime_type="application/pdf",
            file_size_bytes=2048,
            sha256_hash="kusmunda_fy24_" + str(uuid.uuid4())[:8],
            status="COMPLETED"
        )
        db.add(doc)
        db.commit()

        chunk = Chunk(
            document_id=doc.id,
            chunk_index=1,
            page_number=12,
            chunk_type="TEXT",
            section_heading="Overburden Removal and Heavy Earth Moving Machinery",
            content="Kusmunda OCP achieved record overburden removal (OBR) of 42.8 M.cum during FY 2023-24 with dragline utilization of 82%."
        )
        db.add(chunk)
        db.commit()

        # Search with domain acronym OBR and fiscal year filter
        results = keyword_search_engine.search(
            db=db,
            query="overburden removal OBR",
            allowed_org_ids=[org.id],
            filters={"fiscal_year": "2023-24"},
            top_k=25
        )
        assert len(results) >= 1
        matched_chunk = next(r for r in results if r["chunk_id"] == chunk.id)
        assert "42.8 M.cum" in matched_chunk["content"]
    finally:
        try:
            db.delete(chunk)
            db.delete(doc)
            db.commit()
        except Exception:
            db.rollback()
        db.close()


def test_metadata_filters_strict_isolation():
    """Verify metadata filters strictly filter by organization, tier, and document type."""
    db = SessionLocal()
    try:
        orgs = db.query(Organization).limit(2).all()
        assert len(orgs) >= 2
        org_a, org_b = orgs[0], orgs[1]

        doc_a = Document(
            organization_id=org_a.id,
            title="SECL Production Dispatch Brief",
            document_type="PRODUCTION_REPORT",
            source_tier="TIER_A",
            original_filename="secl_dispatch.pdf",
            file_path="storage/secl_dispatch.pdf",
            mime_type="application/pdf",
            file_size_bytes=100,
            sha256_hash="sec_a_" + str(uuid.uuid4())[:8],
            status="COMPLETED"
        )
        doc_b = Document(
            organization_id=org_b.id,
            title="BCCL Production Dispatch Brief",
            document_type="INTERNAL_NOTE",
            source_tier="TIER_B",
            original_filename="bccl_dispatch.pdf",
            file_path="storage/bccl_dispatch.pdf",
            mime_type="application/pdf",
            file_size_bytes=100,
            sha256_hash="bcc_b_" + str(uuid.uuid4())[:8],
            status="COMPLETED"
        )
        db.add_all([doc_a, doc_b])
        db.commit()

        chunk_a = Chunk(
            document_id=doc_a.id,
            chunk_index=1,
            page_number=1,
            content="Gevra dispatch quantity exceeded target."
        )
        chunk_b = Chunk(
            document_id=doc_b.id,
            chunk_index=1,
            page_number=1,
            content="Moonidih dispatch quantity exceeded target."
        )
        db.add_all([chunk_a, chunk_b])
        db.commit()

        # Query restricted to org_a
        res_a = keyword_search_engine.search(
            db=db,
            query="Gevra dispatch quantity exceeded",
            allowed_org_ids=[org_a.id],
            filters={"document_type": "PRODUCTION_REPORT", "source_tier": "TIER_A"},
            top_k=50,
        )
        chunk_ids_a = [r["chunk_id"] for r in res_a]
        assert chunk_a.id in chunk_ids_a
        assert chunk_b.id not in chunk_ids_a
    finally:
        db.close()


def test_rrf_hybrid_retrieval_integration():
    """Verify reciprocal rank fusion fuses keyword and dense retrieval without regression."""
    db = SessionLocal()
    try:
        org = db.query(Organization).first()

        # Execute hybrid search via unified retrieval_service
        search_res = retrieval_service.retrieve(
            db=db,
            query="coal production and seam reserve estimates",
            allowed_org_ids=[org.id],
            search_mode="HYBRID",
            top_k=5
        )
        assert "results" in search_res
        assert "trace" in search_res
        assert search_res["trace"]["search_mode"] == "HYBRID"
        assert "timings_ms" in search_res["trace"]
        assert "keyword_search" in search_res["trace"]["timings_ms"]
        assert "dense_search" in search_res["trace"]["timings_ms"]
        assert "rrf_fusion" in search_res["trace"]["timings_ms"]
    finally:
        db.close()
