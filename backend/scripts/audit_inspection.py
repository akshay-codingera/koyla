import sys
from sqlalchemy import or_, func
from app.db.database import SessionLocal
from app.models import (
    Document, DocumentVersion, ProcessingJob, DocumentPage, Table, TableRow,
    Chunk, Embedding, AuditEvent, VisualAsset,
    ExtractionRun, ExtractedField, ValidationResult,
    ReconciliationGroup, ReconciliationCandidate,
    VerificationTask, StatutoryReserveVerification,
    QueryRecord, AnswerRecord, AnswerCitation,
    Organization, BoreholeStratum
)

def inspect():
    db = SessionLocal()
    print("=" * 70)
    print("KOYLA SYSTEM AUDIT: CURRENT DATABASE INVENTORY")
    print("=" * 70)

    # 1. Baseline Counts
    counts = {
        "Organizations": db.query(Organization).count(),
        "Documents Total": db.query(Document).count(),
        "Document Pages": db.query(DocumentPage).count(),
        "Chunks (Text & Table)": db.query(Chunk).count(),
        "Visual Assets": db.query(VisualAsset).count(),
        "Tables": db.query(Table).count(),
        "Table Rows": db.query(TableRow).count(),
        "Extracted Fields": db.query(ExtractedField).count(),
        "Borehole Strata Records": db.query(BoreholeStratum).count(),
        "Reconciliation Groups": db.query(ReconciliationGroup).count(),
        "Reconciliation Candidates": db.query(ReconciliationCandidate).count(),
        "Verification Tasks": db.query(VerificationTask).count(),
        "Statutory Reserve Verifications": db.query(StatutoryReserveVerification).count(),
        "Historical Queries Logged": db.query(QueryRecord).count(),
        "Historical Answers Logged": db.query(AnswerRecord).count(),
        "Audit Events Logged": db.query(AuditEvent).count(),
    }
    for k, v in counts.items():
        print(f"{k:<35}: {v}")

    # 2. Documents Breakdown
    print("\n--- Document Status Breakdown ---")
    doc_statuses = db.query(Document.status, func.count(Document.id)).group_by(Document.status).all()
    for status, count in doc_statuses:
        print(f"  {status:<25}: {count}")

    print("\n--- Document Types Breakdown ---")
    doc_types = db.query(Document.document_type, func.count(Document.id)).group_by(Document.document_type).all()
    for dt, count in doc_types:
        print(f"  {dt:<25}: {count}")

    # 3. Search for "Seam IV" across documents, chunks, and fields
    print("\n--- Search for 'Seam IV' / 'Seam-IV' / 'Seam 4' ---")
    seam_chunks = db.query(Chunk).filter(
        or_(
            Chunk.content.ilike("%seam iv%"),
            Chunk.content.ilike("%seam-iv%"),
            Chunk.content.ilike("%seam 4%"),
            Chunk.content.ilike("%iv seam%")
        )
    ).all()
    print(f"Total Chunks mentioning Seam IV variants: {len(seam_chunks)}")
    for idx, c in enumerate(seam_chunks[:15], 1):
        doc = db.query(Document).filter(Document.id == c.document_id).first()
        doc_title = doc.title if doc else "Unknown"
        doc_type = doc.document_type if doc else "Unknown"
        org = db.query(Organization).filter(Organization.id == doc.organization_id).first() if doc else None
        org_name = org.name if org else "Unknown"
        print(f"\n[{idx}] Doc: '{doc_title}' ({doc_type}) | Org: {org_name} | Page: {c.page_number} | Chunk ID: {c.id}")
        clean_content = c.content.strip().replace("\n", " ")
        print(f"    Content: {clean_content[:250]}...")

    # 4. Search for Extracted Fields mentioning Seam IV
    print("\n--- Search Extracted Fields for 'Seam' ---")
    seam_fields = db.query(ExtractedField).filter(
        or_(
            ExtractedField.field_name.ilike("%seam%"),
            ExtractedField.raw_value.ilike("%seam%"),
            ExtractedField.source_text.ilike("%seam%")
        )
    ).all()
    print(f"Total Extracted Fields referencing Seam: {len(seam_fields)}")
    for idx, f in enumerate(seam_fields[:25], 1):
        doc = db.query(Document).filter(Document.id == f.document_id).first()
        doc_title = doc.title if doc else "Unknown"
        ent = (f.metadata_json or {}).get("entity_name") or "N/A"
        print(f"[{idx}] Entity: '{ent}' | Metric: '{f.field_name}' | Value: '{f.raw_value}' {f.unit or ''} | Doc: '{doc_title}' P.{f.page_number} | Status: {f.verification_status}")

    # 5. Search for Borehole Strata
    print("\n--- Search Borehole Strata ---")
    strata = db.query(BoreholeStratum).all()
    print(f"Total Borehole Strata in DB: {len(strata)}")
    for idx, s in enumerate(strata[:10], 1):
        print(f"[{idx}] Borehole: {s.borehole_id} | Stratum: {s.stratum_name} | Order: {s.stratum_order} | Lithology: {s.lithology_standardized} | From: {s.depth_from_m}m To: {s.depth_to_m}m (Thickness: {s.thickness_m}m)")

    # 6. Check demo dataset files in data/ or corpus/
    print("\n--- Documents by Distinct Title (Corpus summary) ---")
    distinct_titles = db.query(Document.title, Document.document_type, Document.source_tier, func.count(Document.id)).group_by(Document.title, Document.document_type, Document.source_tier).all()
    for dt in distinct_titles:
        print(f"  - {dt[0]} (Type: {dt[1]}, Tier: {dt[2]}, Copies/Instances: {dt[3]})")

    db.close()

if __name__ == "__main__":
    inspect()
