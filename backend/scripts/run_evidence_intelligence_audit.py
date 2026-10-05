import json
import sys
import time
from sqlalchemy import or_, func
from app.db.database import SessionLocal
from app.models import (
    Document, DocumentVersion, ProcessingJob, DocumentPage, Table, TableRow,
    Chunk, Embedding, AuditEvent, VisualAsset,
    ExtractionRun, ExtractedField, ValidationResult,
    ReconciliationGroup, ReconciliationCandidate,
    VerificationTask, StatutoryReserveVerification,
    QueryRecord, AnswerRecord, AnswerCitation,
    Organization, User, BoreholeStratum
)
from app.services.qa.qa_service import qa_service
from app.services.retrieval.service import retrieval_service
from app.services.qa.structured_lookup import structured_lookup_service
from app.services.qa.grounding_checker import grounding_checker

def run_audit():
    db = SessionLocal()
    print("=" * 80)
    print("KOYLA EVIDENCE INTELLIGENCE CAPABILITY AUDIT")
    print("=" * 80)

    # Find a central admin/reviewer user or first user
    user = db.query(User).filter(User.username == "central_admin").first()
    if not user:
        user = db.query(User).first()
    print(f"Executing audit as User: {user.username} (ID: {user.id})")

    # Fetch all organizations to allow cross-org queries if user has access
    orgs = db.query(Organization).all()
    allowed_org_ids = [o.id for o in orgs]
    print(f"Allowed Organization Scopes: {len(allowed_org_ids)} organizations")

    # Questions to audit
    questions = [
        ("Q1", "Find all references to Seam IV. Group them by mine, report, year, and document type."),
        ("Q2", "What are the thickness, depth, roof, floor and ash percentage associated with Seam IV? Give the source document and page for each attribute."),
        ("Q3", "Different documents contain different values for the reserve of Seam IV. Identify all conflicting values and explain why they may differ."),
        ("Q4", "For the conflicting reserve values of Seam IV, identify the date, document type, revision/status and source location associated with each value."),
        ("Q5", "Which source should be considered authoritative for the current reserve of Seam IV? Explain the evidence you used to determine this, rather than simply choosing the most recent number."),
        ("Q6", "Calculate the current recoverable reserve of Seam IV using the relevant source data. Show every input, operation, unit, source document and page used in the calculation."),
        ("Q7", "Verify the calculation you just performed. Check whether the units are consistent, whether any input was duplicated, and whether every input has a source."),
        ("Q8", "For Seam IV, explain the relationship between its thickness, depth, roof lithology, floor lithology and ash percentage. Do not simply list the values."),
        ("Q9", "Are 'Seam IV', 'Seam-IV', 'IV Seam' and 'Seam 4' referring to the same geological entity in these documents? Provide the evidence supporting your conclusion."),
        ("Q10", "The documents contain inconsistent information about Seam IV. Do not guess. Identify the inconsistency, explain what additional evidence is required to resolve it, and state what cannot currently be concluded."),
        ("Q11", "For every factual claim in your answer, provide the exact source document and page/table/section from which it was obtained."),
        ("Q12", "Separate your answer into three categories: (1) directly stated facts, (2) values calculated from source data, and (3) conclusions inferred from the documents."),
        ("Q13", "How did the reported reserve/production value for Seam IV change over time? Construct a chronological timeline and cite the source for every value."),
        # Killer domain question targeting well-evidenced corpus:
        ("Q14_KILLER", "What was the raw coal production for Rajmahal Opencast Mine in FY 2023-24, and what was the growth compared to previous year? State the exact values, sources, and any conflicting records.")
    ]

    results = {}

    for q_code, q_text in questions:
        print("\n" + "=" * 80)
        print(f"RUNNING {q_code}: \"{q_text}\"")
        print("=" * 80)
        t_start = time.perf_counter()
        
        try:
            res = qa_service.answer_query(
                db=db,
                current_user=user,
                query=q_text,
                allowed_org_ids=allowed_org_ids
            )
            elapsed_sec = time.perf_counter() - t_start

            ans = res.get("answer", "")
            status = res.get("verification_status", "UNKNOWN")
            facts = res.get("structured_facts", [])
            citations = res.get("citations", [])
            calcs = res.get("calculations", [])
            agg = res.get("aggregation_result")
            claims = res.get("claim_audit", [])
            refusal_reason = res.get("refusal_reason")

            print(f"Elapsed Time: {elapsed_sec:.2f}s")
            print(f"Verification Status: {status}")
            print(f"Facts Found: {len(facts)}")
            print(f"Citations Returned: {len(citations)}")
            print(f"Calculations Performed: {len(calcs)}")
            print(f"Aggregation Present: {agg is not None}")
            if refusal_reason:
                print(f"Refusal Reason: {refusal_reason}")
            print(f"\n--- Answer ---:\n{ans}\n")

            print("--- Citations Details ---")
            for c in citations[:5]:
                print(f"  * [{c.get('citation_index', 0)}] {c.get('document_title')} (DocID: {c.get('document_id')}, P.{c.get('page_number')}, Tier: {c.get('source_tier')})")
                print(f"    Excerpt: {str(c.get('excerpt'))[:150]}...")

            results[q_code] = {
                "question": q_text,
                "answer": ans,
                "verification_status": status,
                "refusal_reason": refusal_reason,
                "facts": facts,
                "citations": citations,
                "calculations": calcs,
                "aggregation_result": agg,
                "claim_audit": claims,
                "elapsed_sec": elapsed_sec
            }

        except Exception as e:
            print(f"ERROR executing {q_code}: {e}")
            import traceback
            traceback.print_exc()
            results[q_code] = {
                "question": q_text,
                "error": str(e)
            }

    # Save raw audit results to json
    with open("/app/audit_raw_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, default=str, indent=2)
    print("\nSaved raw audit results to /app/audit_raw_results.json")

    db.close()

if __name__ == "__main__":
    run_audit()
