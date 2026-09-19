import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

def run_checks():
    client = httpx.Client(timeout=30.0)
    print("1. Checking Docker Health Endpoint...")
    res = client.get(f"{BASE_URL}/system/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health = res.json()
    print("   Health:", json.dumps(health, indent=2))
    assert health["status"] == "UP"
    assert health["pgvector_enabled"] is True

    print("\n2. Logging in as hq_officer...")
    login_res = client.post(f"{BASE_URL}/auth/login", data={"username": "hq_officer", "password": "Admin123!"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    hq_token = login_res.json()["access_token"]
    hq_headers = {"Authorization": f"Bearer {hq_token}"}
    print("   Login successful. Role:", login_res.json()["user"]["role"])

    print("\n3. Listing Organizations from API...")
    orgs_res = client.get(f"{BASE_URL}/organizations/", headers=hq_headers)
    assert orgs_res.status_code == 200
    orgs = orgs_res.json()
    print(f"   Organizations available: {len(orgs)}")
    bccl = next((o for o in orgs if o["code"] == "BCCL"), None)
    ccl = next((o for o in orgs if o["code"] == "CCL"), None)
    ecl = next((o for o in orgs if o["code"] == "ECL"), None)
    cmpdi = next((o for o in orgs if o["code"] == "CMPDI_HQ"), None)
    assert bccl and ccl and ecl and cmpdi

    print("\n4. Ingesting Digital PDF (BCCL Geological Summary)...")
    with open("demo_data/geological_summary_bccl.pdf", "rb") as f:
        pdf_res = client.post(
            f"{BASE_URL}/documents/upload?sync=true",
            headers=hq_headers,
            data={
                "organization_id": bccl["id"],
                "title": "BCCL Geological Exploration Report 2024",
                "document_type": "GEOLOGICAL_REPORT",
                "source_tier": "TIER_A"
            },
            files={"file": ("geological_summary_bccl.pdf", f, "application/pdf")}
        )
    assert pdf_res.status_code == 201, f"Upload failed: {pdf_res.text}"
    pdf_doc = pdf_res.json()
    print(f"   PDF Ingested: ID={pdf_doc['id']}, SHA-256={pdf_doc['sha256_hash'][:16]}..., Tier={pdf_doc['source_tier']}")

    print("\n5. Verifying Extracted Structure for PDF...")
    doc_detail = client.get(f"{BASE_URL}/documents/{pdf_doc['id']}", headers=hq_headers).json()
    print(f"   Pages: {doc_detail['page_count']}, Tables: {doc_detail['table_count']}, Chunks: {doc_detail['chunk_count']}")
    assert doc_detail["status"] == "COMPLETED"
    assert doc_detail["page_count"] >= 1
    assert doc_detail["table_count"] >= 1

    tables = client.get(f"{BASE_URL}/documents/{pdf_doc['id']}/tables", headers=hq_headers).json()
    print(f"   Table 1 Headers: {tables[0]['headers']}")
    print(f"   Table 1 Rows Count: {len(tables[0]['rows'])}")
    assert len(tables[0]["rows"]) >= 4

    print("\n6. Ingesting Excel Spreadsheet (CCL Coal Production)...")
    with open("demo_data/monthly_coal_production_ccl.xlsx", "rb") as f:
        xlsx_res = client.post(
            f"{BASE_URL}/documents/upload?sync=true",
            headers=hq_headers,
            data={
                "organization_id": ccl["id"],
                "title": "CCL FY24 Production Schedule",
                "document_type": "MINE_PRODUCTION",
                "source_tier": "TIER_B"
            },
            files={"file": ("monthly_coal_production_ccl.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
    assert xlsx_res.status_code == 201
    xlsx_doc = xlsx_res.json()
    xlsx_tables = client.get(f"{BASE_URL}/documents/{xlsx_doc['id']}/tables", headers=hq_headers).json()
    print(f"   XLSX Table Headers: {xlsx_tables[0]['headers']}")
    print(f"   XLSX First Row: {xlsx_tables[0]['rows'][0]}")
    assert "Month" in xlsx_tables[0]["headers"]
    assert "Actual_MT" in xlsx_tables[0]["headers"]

    print("\n7. Ingesting DOCX (ECL Safety Audit)...")
    with open("demo_data/mine_safety_inspection_ecl.docx", "rb") as f:
        docx_res = client.post(
            f"{BASE_URL}/documents/upload?sync=true",
            headers=hq_headers,
            data={
                "organization_id": ecl["id"],
                "title": "ECL Annual Safety Audit 2023-24",
                "document_type": "SAFETY_AUDIT",
                "source_tier": "TIER_A"
            },
            files={"file": ("mine_safety_inspection_ecl.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )
    assert docx_res.status_code == 201
    docx_doc = docx_res.json()
    docx_tables = client.get(f"{BASE_URL}/documents/{docx_doc['id']}/tables", headers=hq_headers).json()
    print(f"   DOCX Table Rows Count: {len(docx_tables[0]['rows'])}")
    assert len(docx_tables[0]["rows"]) >= 4

    print("\n8. Ingesting Image (Scanned Borehole Log)...")
    with open("demo_data/scanned_borehole_log.png", "rb") as f:
        png_res = client.post(
            f"{BASE_URL}/documents/upload?sync=true",
            headers=hq_headers,
            data={
                "organization_id": cmpdi["id"],
                "title": "CMPDI Borehole Recovery Log BH-DHN-24",
                "document_type": "BOREHOLE_LOG",
                "source_tier": "TIER_B"
            },
            files={"file": ("scanned_borehole_log.png", f, "image/png")}
        )
    assert png_res.status_code == 201
    png_doc = png_res.json()
    png_pages = client.get(f"{BASE_URL}/documents/{png_doc['id']}/pages", headers=hq_headers).json()
    print(f"   Image OCR Applied: {png_pages[0]['ocr_applied']}, Dim: {png_pages[0]['width']}x{png_pages[0]['height']}")
    assert png_pages[0]["ocr_applied"] is True

    print("\n9. Testing Unsupported Format Rejection (.zip)...")
    with open("demo_data/unsupported_archive.zip", "rb") as f:
        zip_res = client.post(
            f"{BASE_URL}/documents/upload",
            headers=hq_headers,
            data={"organization_id": bccl["id"]},
            files={"file": ("unsupported_archive.zip", f, "application/zip")}
        )
    assert zip_res.status_code == 400
    print(f"   Correctly Rejected: {zip_res.json()['detail']}")

    print("\n10. Testing Organization-Level Access Control...")
    ri_login = client.post(f"{BASE_URL}/auth/login", data={"username": "ri1_analyst", "password": "Password123!"})
    ri_token = ri_login.json()["access_token"]
    ri_headers = {"Authorization": f"Bearer {ri_token}"}
    
    # Try to access BCCL document
    unauthorized_res = client.get(f"{BASE_URL}/documents/{pdf_doc['id']}", headers=ri_headers)
    assert unauthorized_res.status_code == 403, f"Expected 403, got {unauthorized_res.status_code}"
    print("   Correctly Enforced: Access denied to BCCL document for RI-1 user (HTTP 403)")

    print("\nALL DOCKER HTTP VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_checks()
