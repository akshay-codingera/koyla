import sys
import os
import uuid
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.organization import Organization
from app.models.user import User, Role
from app.models.document import Document
from app.models.verification import VerificationTask
from app.models.audit import AuditEvent
from app.core.security import get_password_hash

def seed_data():
    db = SessionLocal()
    
    try:
        # Check if already seeded
        if db.query(Organization).count() > 0:
            print("Database already seeded with organizations.")
            return

        print("Seeding CIL/CMPDI Organizational Hierarchy into PostgreSQL...")
        # 1. Apex
        cil = Organization(
            id=str(uuid.uuid4()),
            code="CIL",
            name="Coal India Limited",
            org_type="APEX",
            is_active=True
        )
        db.add(cil)
        db.commit()

        # 2. CMPDI HQ
        cmpdi_hq = Organization(
            id=str(uuid.uuid4()),
            code="CMPDI_HQ",
            name="Central Mine Planning & Design Institute (HQ - Ranchi)",
            org_type="HQ",
            parent_id=cil.id,
            is_active=True
        )
        db.add(cmpdi_hq)
        db.commit()

        # 3. Regional Institutes (RI-1 to RI-7)
        ris = [
            ("RI_1", "Regional Institute - I (Asansol, West Bengal)", cmpdi_hq.id),
            ("RI_2", "Regional Institute - II (Dhanbad, Jharkhand)", cmpdi_hq.id),
            ("RI_3", "Regional Institute - III (Ranchi, Jharkhand)", cmpdi_hq.id),
            ("RI_4", "Regional Institute - IV (Nagpur, Maharashtra)", cmpdi_hq.id),
            ("RI_5", "Regional Institute - V (Bilaspur, Chhattisgarh)", cmpdi_hq.id),
            ("RI_6", "Regional Institute - VI (Singrauli, Madhya Pradesh)", cmpdi_hq.id),
            ("RI_7", "Regional Institute - VII (Bhubaneswar, Odisha)", cmpdi_hq.id),
        ]
        ri_map = {}
        for code, name, parent in ris:
            org = Organization(id=str(uuid.uuid4()), code=code, name=name, org_type="REGIONAL_INSTITUTE", parent_id=parent, is_active=True)
            db.add(org)
            ri_map[code] = org
        db.commit()

        # 4. Coal Producing Subsidiaries
        subs = [
            ("ECL", "Eastern Coalfields Limited", cil.id),
            ("BCCL", "Bharat Coking Coal Limited", cil.id),
            ("CCL", "Central Coalfields Limited", cil.id),
            ("WCL", "Western Coalfields Limited", cil.id),
            ("SECL", "South Eastern Coalfields Limited", cil.id),
            ("MCL", "Mahanadi Coalfields Limited", cil.id),
            ("NCL", "Northern Coalfields Limited", cil.id),
        ]
        sub_map = {}
        for code, name, parent in subs:
            org = Organization(id=str(uuid.uuid4()), code=code, name=name, org_type="SUBSIDIARY", parent_id=parent, is_active=True)
            db.add(org)
            sub_map[code] = org
        db.commit()

        print("Seeding Prototype Roles...")
        roles_data = [
            ("MINISTRY_OFFICER", "Ministry / Central Reviewer", "Central ministry oversight and national briefs"),
            ("CMPDI_HQ_OFFICER", "CMPDI HQ Officer", "National geological coordination and corporate reports"),
            ("RI_OFFICER", "Regional Institute Officer", "Exploration blocks, drilling logs, regional reports"),
            ("SUBSIDIARY_ANALYST", "Subsidiary Analyst", "Mine operational parameters and production statistics"),
            ("VERIFICATION_OFFICER", "Verification Officer", "Data reconciliation, metric validation, anomaly review"),
            ("SYSTEM_ADMIN", "System Administrator", "Platform configuration, user directory, system health"),
        ]
        role_map = {}
        for code, name, desc in roles_data:
            role = Role(id=str(uuid.uuid4()), code=code, name=name, description=desc, permissions=[code])
            db.add(role)
            role_map[code] = role
        db.commit()

        print("Seeding Initial User Accounts...")
        users_data = [
            ("hq_officer", "hq@cmpdi.gov.in", "CMPDI HQ Chief Officer", "Admin123!", cmpdi_hq.id, "CMPDI_HQ_OFFICER"),
            ("ri1_analyst", "ri1@cmpdi.gov.in", "RI-1 Senior Geologist", "Password123!", ri_map["RI_1"].id, "RI_OFFICER"),
            ("ecl_analyst", "analyst@ecl.gov.in", "ECL Production Analyst", "Password123!", sub_map["ECL"].id, "SUBSIDIARY_ANALYST"),
            ("verifier_officer", "verifier@cmpdi.gov.in", "Verification Specialist", "Admin123!", cmpdi_hq.id, "VERIFICATION_OFFICER"),
            ("sysadmin", "admin@cil.gov.in", "System Administrator", "Admin123!", cil.id, "SYSTEM_ADMIN"),
        ]
        user_map = {}
        for uname, email, fname, pwd, org_id, rcode in users_data:
            u = User(
                id=str(uuid.uuid4()),
                username=uname,
                email=email,
                full_name=fname,
                hashed_password=get_password_hash(pwd),
                organization_id=org_id,
                is_active=True,
                created_at=datetime.utcnow()
            )
            u.roles.append(role_map[rcode])
            db.add(u)
            user_map[uname] = u
        db.commit()

        print("Seeding Synthetic Demonstration Documents...")
        doc1 = Document(
            id=str(uuid.uuid4()),
            organization_id=cmpdi_hq.id,
            title="CMPDI Annual Geological Exploration Summary 2025-26 [DEMO DATA]",
            document_type="GEOLOGICAL_REPORT",
            source_tier="TIER_A",
            original_filename="CMPDI_Geological_Summary_2025.pdf",
            file_path="storage/documents/demo_cmpdi_geo_2025.pdf",
            mime_type="application/pdf",
            file_size_bytes=2458900,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            status="PROCESSED",
            is_demo_data=True,
            created_by=user_map["hq_officer"].id,
            created_at=datetime.utcnow()
        )
        doc2 = Document(
            id=str(uuid.uuid4()),
            organization_id=ri_map["RI_1"].id,
            title="Raniganj Coalfield Block Exploration Report [DEMO DATA]",
            document_type="EXPLORATION_REPORT",
            source_tier="TIER_B",
            original_filename="Raniganj_Block_Report.pdf",
            file_path="storage/documents/demo_raniganj_2025.pdf",
            mime_type="application/pdf",
            file_size_bytes=1845200,
            sha256_hash="8729832049823409823094820394820394820394820394820394820394820394",
            status="PROCESSED",
            is_demo_data=True,
            created_by=user_map["ri1_analyst"].id,
            created_at=datetime.utcnow()
        )
        doc3 = Document(
            id=str(uuid.uuid4()),
            organization_id=sub_map["ECL"].id,
            title="ECL Monthly Production & Stripping Ratio Bulletin [DEMO DATA]",
            document_type="PRODUCTION_REPORT",
            source_tier="TIER_B",
            original_filename="ECL_Production_Oct2025.xlsx",
            file_path="storage/documents/demo_ecl_prod_2025.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size_bytes=982100,
            sha256_hash="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            status="AWAITING_VERIFICATION",
            is_demo_data=True,
            created_by=user_map["ecl_analyst"].id,
            created_at=datetime.utcnow()
        )
        db.add_all([doc1, doc2, doc3])
        db.commit()

        print("Seeding Synthetic Verification Tasks...")
        vtask = VerificationTask(
            id=str(uuid.uuid4()),
            task_type="SUSPICIOUS_METRIC",
            document_id=doc3.id,
            assigned_to=user_map["verifier_officer"].id,
            status="PENDING",
            review_notes="Automated rule flag: Stripping ratio discrepancy between Table 4 and Summary paragraph (3.2 vs 4.8)."
        )
        db.add(vtask)
        db.commit()

        print("Seeding Initial Audit Trail Events...")
        a1 = AuditEvent(
            id=str(uuid.uuid4()),
            actor_id=user_map["sysadmin"].id,
            actor_name="sysadmin",
            role_code="SYSTEM_ADMIN",
            organization_id=cil.id,
            action="SYSTEM_INIT_SEED",
            object_type="DATABASE",
            object_id="koyla_postgres",
            details={"description": "Initial PostgreSQL database initialization and demonstration dataset load"}
        )
        db.add(a1)
        db.commit()

        print("PostgreSQL Database Seeding Complete!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
