import httpx
import uuid

BASE_URL = "http://localhost:8000"

def run_verification():
    print("=== KOYLA DOCKERIZED TABLE INTELLIGENCE VERIFICATION ===")
    
    # 1. Health check
    r = httpx.get(f"{BASE_URL}/api/v1/system/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    health = r.json()
    print(f"1. System Health: status={health['status']}, database={health['database_type']}, pgvector={health['pgvector_enabled']}")
    assert health["status"] == "UP"
    assert health["pgvector_enabled"] is True

    # 2. Login
    r = httpx.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": "hq_officer", "password": "Admin123!"}
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("2. Auth Login successful as CMPDI HQ Officer.")

    # 3. Get an organization
    r = httpx.get(f"{BASE_URL}/api/v1/organizations/", headers=headers)
    assert r.status_code == 200
    orgs = r.json()
    bccl_org = next(o for o in orgs if o["code"] == "BCCL")
    print(f"3. Organization verified: {bccl_org['name']} ({bccl_org['code']})")

    # 4. Upload document
    with open("demo_data/geological_summary_bccl.pdf", "rb") as f:
        r = httpx.post(
            f"{BASE_URL}/api/v1/documents/upload?sync=true",
            headers=headers,
            data={
                "organization_id": bccl_org["id"],
                "title": f"Docker Verification Tables {uuid.uuid4().hex[:6]}",
                "document_type": "GEOLOGICAL_REPORT",
                "source_tier": "TIER_A"
            },
            files={"file": ("geological_summary_bccl.pdf", f, "application/pdf")}
        )
    assert r.status_code == 201, f"Upload failed: {r.text}"
    doc_id = r.json()["id"]
    print(f"4. Uploaded & processed document: {doc_id}")

    # 5. Verify Physical View
    r = httpx.get(f"{BASE_URL}/api/v1/documents/{doc_id}/tables?view=physical", headers=headers)
    assert r.status_code == 200, f"Failed to get physical tables: {r.text}"
    phys_tables = r.json()
    print(f"5. Physical View returned {len(phys_tables)} table(s)")
    for pt in phys_tables:
        print(f"   - Physical Slice on Page {pt['page_number']}: {pt['row_count']} rows, Part {pt['part_number']}/{pt['total_parts']}, Status: {pt['continuation_status']}")
        assert "row_details" in pt
        for rd in pt["row_details"]:
            assert "source_page" in rd
            assert "logical_row_index" in rd

    # 6. Verify Logical View
    r = httpx.get(f"{BASE_URL}/api/v1/documents/{doc_id}/tables?view=logical", headers=headers)
    assert r.status_code == 200, f"Failed to get logical tables: {r.text}"
    log_tables = r.json()
    print(f"6. Logical View returned {len(log_tables)} table(s)")
    for lt in log_tables:
        print(f"   - Logical Table: {lt['caption']}, Total Rows: {lt['row_count']}, Spanned: {lt['spanned_pages']}, Slices: {len(lt['physical_slices'])}")
        assert "physical_slices" in lt
        assert "row_details" in lt
        for rd in lt["row_details"]:
            assert rd["source_page"] in lt["spanned_pages"]

    # 7. Frontend check
    rf = httpx.get("http://localhost:5173")
    assert rf.status_code == 200
    print("7. Frontend container is serving HTTP 200 on port 5173.")

    print("\nALL DOCKERIZED TABLE INTELLIGENCE ACCEPTANCE CHECKS PASSED!")

if __name__ == "__main__":
    run_verification()
