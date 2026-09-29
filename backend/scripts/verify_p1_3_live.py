"""
Koyla Phase 11 P1-3: Live Docker Verification Script
Verifies Two-Tier 4-Eyes (Maker-Checker) Verification for Statutory Reserve Edits.

Covers the complete required scenario:
1. Synthetic Statutory Reserve Record Creation (TEST-MINE-001, Geological Reserve, 1000 MT, VERIFIED)
2. Step 1 (Maker): Propose edit 1000 MT -> 1200 MT (Status PENDING, authoritative value remains 1000 MT)
3. Step 2 (Same User): Attempt self-approval -> BLOCKED (HTTP 403, value unchanged, audit event recorded)
4. Step 3 (Independent Checker): Approve edit -> VERIFIED, authoritative value becomes 1200 MT
5. Step 4 (Grounded QA): "What is the geological reserve of TEST-MINE-001?" -> 1200 MT (SUPPORTED)
6. Step 5 (Rejection Path): Propose 1200 -> 1500 MT, checker rejects -> REJECTED, value remains 1200 MT
7. Step 6 (Audit Trail): Verify complete audit sequence recorded in PostgreSQL
"""
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException
from app.db.database import SessionLocal
from app.models.organization import Organization
from app.models.user import User, Role, UserRole
from app.models.document import Document, DocumentPage
from app.models.extraction import ExtractedField, ExtractionRun
from app.models.verification import StatutoryReserveVerification
from app.models.audit import AuditEvent
from app.services.statutory_verification import StatutoryVerificationService
from app.services.qa.qa_service import qa_service


def run_live_verification():
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]
    print("=" * 70)
    print("KOYLA PHASE 11 P1-3: TWO-TIER 4-EYES STATUTORY VERIFICATION")
    print("=" * 70)

    try:
        # 1. Create Organization & Roles & Users
        org = Organization(
            id=str(uuid.uuid4()),
            code=f"WCL_LIVE_{suffix}",
            name=f"Western Coalfields Ltd Live Test {suffix}",
            org_type="SUBSIDIARY",
            is_active=True
        )
        db.add(org)
        db.commit()

        def get_or_create_role(code, name):
            r = db.query(Role).filter(Role.code == code).first()
            if not r:
                r = Role(id=str(uuid.uuid4()), code=code, name=name, permissions=[code])
                db.add(r)
                db.commit()
            return r

        role_maker = get_or_create_role("SUBSIDIARY_ANALYST", "Subsidiary Analyst")
        role_checker = get_or_create_role("VERIFICATION_OFFICER", "Verification Officer")

        user_maker = User(
            id=str(uuid.uuid4()),
            username=f"geologist_maker_{suffix}",
            email=f"maker_{suffix}@wcl.gov.in",
            full_name=f"Senior Geologist Maker {suffix}",
            hashed_password="hash",
            organization_id=org.id,
            is_active=True
        )
        db.add(user_maker)
        db.commit()
        db.add(UserRole(user_id=user_maker.id, role_id=role_maker.id))
        db.commit()

        user_checker = User(
            id=str(uuid.uuid4()),
            username=f"officer_checker_{suffix}",
            email=f"checker_{suffix}@wcl.gov.in",
            full_name=f"Independent Statutory Checker {suffix}",
            hashed_password="hash",
            organization_id=org.id,
            is_active=True
        )
        db.add(user_checker)
        db.commit()
        db.add(UserRole(user_id=user_checker.id, role_id=role_checker.id))
        db.commit()

        print(f"[*] Provisioned synthetic organization '{org.code}'")
        print(f"    - Maker:   '{user_maker.username}' (ID: {user_maker.id})")
        print(f"    - Checker: '{user_checker.username}' (ID: {user_checker.id})")

        # 2. Create Document & Statutory Reserve Field (1000 MT)
        doc = Document(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            title="WCL Statutory Geological Exploration Report 2025-26",
            original_filename="wcl_geology_2025.pdf",
            file_path="/tmp/wcl_geology_2025.pdf",
            sha256_hash=f"hash_live_p13_{suffix}",
            mime_type="application/pdf",
            document_type="GEOLOGICAL_REPORT",
            file_size_bytes=204800
        )
        db.add(doc)
        db.commit()

        page = DocumentPage(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            page_number=1,
            extracted_text="Mine: TEST-MINE-001. Gross Geological Reserve: 1000 MT. Certified as per CMPDI Guidelines."
        )
        db.add(page)
        db.commit()

        run = ExtractionRun(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            status="COMPLETED",
            provider="RULE_BASED"
        )
        db.add(run)
        db.commit()

        reserve_field = ExtractedField(
            id=str(uuid.uuid4()),
            extraction_run_id=run.id,
            organization_id=org.id,
            document_id=doc.id,
            field_name="reserves_total",
            field_category="GEOLOGY",
            data_type="NUMBER",
            raw_value="1000",
            normalized_value="1000",
            numeric_value=1000.0,
            unit="MT",
            page_number=1,
            source_text="Mine: TEST-MINE-001. Gross Geological Reserve: 1000 MT.",
            extraction_method="RULE_BASED",
            confidence_score=0.98,
            confidence_level="HIGH",
            verification_status="VERIFIED",
            metadata_json={"entity_name": "TEST-MINE-001"}
        )
        db.add(reserve_field)
        db.commit()
        db.refresh(reserve_field)

        print(f"[+] Created synthetic statutory reserve record:")
        print(f"    - Record ID:           {reserve_field.id}")
        print(f"    - Mine / Entity:       TEST-MINE-001")
        print(f"    - Metric:              Geological Reserve (reserves_total)")
        print(f"    - Authoritative Value: {reserve_field.numeric_value} {reserve_field.unit}")
        print(f"    - Status:              {reserve_field.verification_status}")

        # ==============================================================================
        # STEP 1 — MAKER PROPOSES EDIT (1000 MT -> 1200 MT)
        # ==============================================================================
        print("\n--- STEP 1: Maker Proposes Edit (1000 MT -> 1200 MT) ---")
        verif1 = StatutoryVerificationService.propose_edit(
            db=db,
            user=user_maker,
            reserve_id=reserve_field.id,
            proposed_value="1200 MT",
            reason="corrected geological reserve measurement",
            comment="Incorporating newly certified borehole drillcore assay logs"
        )

        assert verif1.id is not None
        assert verif1.status == "PENDING_VERIFICATION"
        assert verif1.maker_user_id == user_maker.id
        assert verif1.proposed_numeric_value == 1200.0

        db.refresh(reserve_field)
        assert reserve_field.numeric_value == 1000.0, f"Authoritative value leaked early! Got {reserve_field.numeric_value}"
        print(f"[+] Proposal created successfully (ID: {verif1.id})")
        print(f"    - Status:              {verif1.status}")
        print(f"    - Maker User ID:       {verif1.maker_user_id}")
        print(f"    - Proposed Value:      {verif1.proposed_numeric_value} {verif1.unit}")
        print(f"    - Authoritative Value: {reserve_field.numeric_value} {reserve_field.unit} (Preserved unchanged!)")

        # ==============================================================================
        # STEP 2 — SAME USER ATTEMPTS SELF-APPROVAL (FOUR-EYES VIOLATION)
        # ==============================================================================
        print("\n--- STEP 2: Maker Attempts Self-Approval (Four-Eyes Enforcement) ---")
        self_approval_blocked = False
        try:
            StatutoryVerificationService.approve_edit(
                db=db,
                user=user_maker,  # MAKER ATTEMPTING APPROVAL
                edit_id=verif1.id,
                comment="Self approval attempt"
            )
        except HTTPException as exc:
            if exc.status_code == 403 and "Four-eyes policy violation" in exc.detail:
                self_approval_blocked = True
                print(f"[+] Four-Eyes Violation correctly caught by server: HTTP {exc.status_code}: {exc.detail}")

        assert self_approval_blocked is True, "CRITICAL SECURITY FAILURE: Maker was permitted to self-approve!"

        db.refresh(reserve_field)
        assert reserve_field.numeric_value == 1000.0
        db.refresh(verif1)
        assert verif1.status == "PENDING_VERIFICATION"
        print(f"[+] Authoritative value remains protected: {reserve_field.numeric_value} {reserve_field.unit}")

        # Check self-approval security audit event
        audit_sec = db.query(AuditEvent).filter(
            AuditEvent.action == "STATUTORY_RESERVE_SELF_APPROVAL_BLOCKED",
            AuditEvent.object_id == verif1.id
        ).first()
        assert audit_sec is not None
        print(f"[+] Security audit event logged: '{audit_sec.action}' for Actor: {audit_sec.actor_id}")

        # ==============================================================================
        # STEP 3 — INDEPENDENT CHECKER APPROVES EDIT
        # ==============================================================================
        print("\n--- STEP 3: Independent Checker Approves Edit ---")
        approved_edit = StatutoryVerificationService.approve_edit(
            db=db,
            user=user_checker,  # INDEPENDENT CHECKER
            edit_id=verif1.id,
            comment="Drillcore assays and seam boundary maps independently verified"
        )

        assert approved_edit.status == "VERIFIED"
        assert approved_edit.verifier_user_id == user_checker.id
        assert approved_edit.verified_at is not None

        db.refresh(reserve_field)
        assert reserve_field.numeric_value == 1200.0
        assert reserve_field.verification_status == "VERIFIED"
        assert reserve_field.is_corrected is True
        assert reserve_field.corrected_by == user_checker.id

        print(f"[+] Independent approval completed successfully:")
        print(f"    - Status:              {approved_edit.status}")
        print(f"    - Verifier User ID:    {approved_edit.verifier_user_id}")
        print(f"    - Verified At:         {approved_edit.verified_at.isoformat()}")
        print(f"    - Authoritative Value: {reserve_field.numeric_value} {reserve_field.unit} (Promoted to authoritative!)")

        # ==============================================================================
        # STEP 4 — GROUNDED QA INTEGRATION
        # ==============================================================================
        print("\n--- STEP 4: Grounded QA Evaluation ---")
        query = "What is the total reserve of TEST-MINE-001?"
        print(f"[*] Asking: \"{query}\"")
        qa_res = qa_service.answer_query(
            db=db,
            current_user=user_checker,
            query=query,
            allowed_org_ids=[org.id]
        )

        print(f"[+] Grounded QA Output:")
        print(f"    - Verification Status: {qa_res.get('verification_status')}")
        print(f"    - Grounded Answer:     \"{qa_res.get('answer')}\"")
        print(f"    - Facts:               {len(qa_res.get('structured_facts', []))}")
        print(f"    - Citations:           {len(qa_res.get('citations', []))}")

        assert qa_res["verification_status"] == "SUPPORTED"
        assert "1,200" in qa_res["answer"] or "1200" in qa_res["answer"]

        # ==============================================================================
        # STEP 5 — REJECTION PATH (1200 MT -> 1500 MT)
        # ==============================================================================
        print("\n--- STEP 5: Rejection Path (1200 MT -> 1500 MT) ---")
        verif2 = StatutoryVerificationService.propose_edit(
            db=db,
            user=user_maker,
            reserve_id=reserve_field.id,
            proposed_value="1500 MT",
            reason="Speculative extrapolation into adjacent un-drilled block",
            comment="Requested review by planning division"
        )
        print(f"[*] Second proposal created: {verif2.proposed_numeric_value} MT (Status: {verif2.status})")

        rejected_edit = StatutoryVerificationService.reject_edit(
            db=db,
            user=user_checker,
            edit_id=verif2.id,
            comment="Speculative extrapolation without certified borehole assay is rejected under CIL guidelines"
        )

        assert rejected_edit.status == "REJECTED"
        assert rejected_edit.verifier_user_id == user_checker.id
        assert rejected_edit.rejected_at is not None

        db.refresh(reserve_field)
        assert reserve_field.numeric_value == 1200.0, f"Rejected edit corrupted authoritative value! Got {reserve_field.numeric_value}"

        print(f"[+] Proposal rejected cleanly:")
        print(f"    - Status:              {rejected_edit.status}")
        print(f"    - Verifier Comment:    \"{rejected_edit.verifier_comment}\"")
        print(f"    - Authoritative Value: {reserve_field.numeric_value} {reserve_field.unit} (Preserved at certified 1200 MT!)")

        # ==============================================================================
        # STEP 6 — AUDIT TRAIL VERIFICATION
        # ==============================================================================
        print("\n--- STEP 6: Complete Immutable Audit Trail Verification ---")
        audits = db.query(AuditEvent).filter(
            AuditEvent.organization_id == org.id
        ).order_by(AuditEvent.created_at.asc()).all()

        action_sequence = [a.action for a in audits]
        print(f"[*] Total audit records generated: {len(audits)}")
        for idx, a in enumerate(audits, 1):
            actor_str = str(a.actor_name or a.actor_id or "SYSTEM")
            obj_id_str = str(a.object_id)[:8] if a.object_id else "N/A"
            print(f"    {idx}. Action: {a.action:<42} | Actor: {actor_str:<30} | Object: {a.object_type} ({obj_id_str}...)")

        assert "STATUTORY_RESERVE_EDIT_PROPOSED" in action_sequence
        assert "STATUTORY_RESERVE_SELF_APPROVAL_BLOCKED" in action_sequence
        assert "STATUTORY_RESERVE_EDIT_APPROVED" in action_sequence
        assert "STATUTORY_RESERVE_EDIT_REJECTED" in action_sequence
        print("[+] All statutory audit actions verified present in immutable PostgreSQL audit log!")

        print("\n" + "=" * 70)
        print("ALL P1-3 VERIFICATION CHECKS PASSED SUCCESSFULLY (100% GREEN)")
        print("=" * 70)

    finally:
        # Clean up test entities in strict reverse FK dependency order
        try:
            db.query(StatutoryReserveVerification).filter(
                StatutoryReserveVerification.organization_id == org.id
            ).delete(synchronize_session=False)
            db.query(AuditEvent).filter(
                AuditEvent.organization_id == org.id
            ).delete(synchronize_session=False)
            db.query(ExtractedField).filter(ExtractedField.organization_id == org.id).delete(synchronize_session=False)
            db.query(ExtractionRun).filter(ExtractionRun.document_id == doc.id).delete(synchronize_session=False)
            db.query(DocumentPage).filter(DocumentPage.document_id == doc.id).delete(synchronize_session=False)
            db.query(Document).filter(Document.organization_id == org.id).delete(synchronize_session=False)
            db.query(UserRole).filter(UserRole.user_id.in_([user_maker.id, user_checker.id])).delete(synchronize_session=False)
            db.query(User).filter(User.organization_id == org.id).delete(synchronize_session=False)
            db.query(Organization).filter(Organization.id == org.id).delete(synchronize_session=False)
            db.commit()
            print("[*] Cleanup complete: test entities removed from PostgreSQL.")
        except Exception as e:
            db.rollback()
            print(f"[!] Warning during cleanup: {e}")
        finally:
            db.close()


if __name__ == "__main__":
    run_live_verification()
