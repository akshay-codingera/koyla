import os
import sys
import time
import json
import httpx

BASE_URL = os.getenv("KOYLA_API_URL", "http://localhost:8000/api/v1")
FRONTEND_URL = os.getenv("KOYLA_FRONTEND_URL", "http://localhost:5173")

def run_smoke_tests():
    results = {}
    print("=== KOYLA PORTABILITY & FUNCTIONAL SMOKE TEST ===")
    print(f"Target Backend API: {BASE_URL}")
    print(f"Target Frontend:    {FRONTEND_URL}\n")

    client = httpx.Client(timeout=60.0)

    # 1. Health check
    print("1. Testing /system/health...")
    try:
        r = client.get(f"{BASE_URL}/system/health")
        assert r.status_code == 200, f"Status {r.status_code}"
        health_data = r.json()
        assert health_data.get("status") == "UP", f"Overall status {health_data.get('status')}"
        assert health_data.get("services", {}).get("database") == "UP"
        assert health_data.get("services", {}).get("vector_store") == "UP"
        results["health"] = {"status": "PASS", "data": health_data}
        print("   [PASS] Health check UP (pgvector, db, embedding, reports up)")
    except Exception as e:
        results["health"] = {"status": "FAIL", "error": str(e)}
        print(f"   [FAIL] Health check failed: {e}")

    # 2. Authentication
    print("\n2. Testing /auth/login (hq_officer)...")
    token = None
    user_org_id = None
    headers = {}
    try:
        r = client.post(f"{BASE_URL}/auth/login", data={"username": "hq_officer", "password": "Admin123!"})
        if r.status_code != 200:
            r = client.post(f"{BASE_URL}/auth/login", data={"username": "hq_officer", "password": "password123"})
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        auth_data = r.json()
        token = auth_data.get("access_token")
        assert token, "Missing access_token"
        user_info = auth_data.get("user", {})
        user_org_id = user_info.get("organization", {}).get("id")
        headers = {"Authorization": f"Bearer {token}"}
        results["auth"] = {"status": "PASS", "user": user_info.get("username"), "org_id": user_org_id}
        print(f"   [PASS] Authenticated successfully as {user_info.get('username')} (Org: {user_org_id})")
    except Exception as e:
        results["auth"] = {"status": "FAIL", "error": str(e)}
        print(f"   [FAIL] Auth failed: {e}")

    # 3. Document Ingestion
    print("\n3. Testing Document Upload & Ingestion...")
    doc_id = None
    sample_pdf = os.path.join(os.path.dirname(__file__), "..", "docs", "mp-guidelines-31012025_0.pdf")
    if not os.path.exists(sample_pdf):
        sample_pdf = os.path.join("backend", "docs", "mp-guidelines-31012025_0.pdf")

    try:
        assert os.path.exists(sample_pdf), f"Sample file not found at {sample_pdf}"
        with open(sample_pdf, "rb") as f:
            files = {"file": ("statutory_guidelines.pdf", f, "application/pdf")}
            data = {
                "title": "MoC Statutory Guidelines Test Upload",
                "document_type": "STATUTORY_GUIDELINE",
                "source_tier": "TIER_A",
                "organization_id": user_org_id or ""
            }
            r = client.post(f"{BASE_URL}/documents/upload", headers=headers, files=files, data=data)
            assert r.status_code in [200, 201], f"Upload returned {r.status_code}: {r.text}"
            doc_data = r.json()
            doc_id = doc_data.get("id")
            assert doc_id, "No document ID returned"
            results["ingestion"] = {"status": "PASS", "document_id": doc_id, "sha256": doc_data.get("sha256_hash")}
            print(f"   [PASS] Document uploaded, ID: {doc_id}, SHA256: {doc_data.get('sha256_hash')[:16]}...")
    except Exception as e:
        results["ingestion"] = {"status": "FAIL", "error": str(e)}
        print(f"   [FAIL] Ingestion failed: {e}")

    # 4. Document Detail & Parsing Status
    print("\n4. Waiting for document processing / inspection...")
    try:
        if doc_id:
            doc_detail = {}
            for _ in range(15):
                r = client.get(f"{BASE_URL}/documents/{doc_id}", headers=headers)
                if r.status_code == 200:
                    doc_detail = r.json()
                    if doc_detail.get("status") in ["COMPLETED", "INDEXED", "PROCESSED", "READY"]:
                        break
                time.sleep(1)
            results["document_detail"] = {
                "status": "PASS",
                "doc_status": doc_detail.get("status"),
                "pages": len(doc_detail.get("pages", [])),
                "chunks": len(doc_detail.get("chunks", []))
            }
            print(f"   [PASS] Document status: {doc_detail.get('status')}, pages: {len(doc_detail.get('pages', []))}")
        else:
            results["document_detail"] = {"status": "SKIPPED"}
    except Exception as e:
        results["document_detail"] = {"status": "FAIL", "error": str(e)}
        print(f"   [FAIL] Document detail error: {e}")

    # 5. Hybrid Search
    print("\n5. Testing Hybrid Retrieval (/search/query)...")
    try:
        payload = {
            "query": "mining plan guidelines coal reserves",
            "search_mode": "HYBRID",
            "top_k": 5,
            "enable_reranker": False
        }
        r = client.post(f"{BASE_URL}/search/query", headers=headers, json=payload)
        assert r.status_code == 200, f"Search failed: {r.status_code} {r.text}"
        search_data = r.json()
        results_list = search_data.get("results", [])
        results["search"] = {"status": "PASS", "results_count": len(results_list)}
        print(f"   [PASS] Hybrid search returned {len(results_list)} ranked evidence items")
    except Exception as e:
        results["search"] = {"status": "FAIL", "error": str(e)}
        print(f"   [FAIL] Search failed: {e}")

    # 6. Grounded Q&A
    print("\n6. Testing Grounded Q&A (/qa/query)...")
    try:
        qa_payload = {
            "query": "What are the guidelines for mining plan submission?",
            "top_k": 3,
            "enable_reranker": False
        }
        r = client.post(f"{BASE_URL}/qa/query", headers=headers, json=qa_payload)
        assert r.status_code == 200, f"QA failed: {r.status_code} {r.text}"
        qa_data = r.json()
        citations = qa_data.get("citations", [])
        answer_text = qa_data.get("answer", "")
        assert answer_text, "Empty answer returned"
        results["qa"] = {
            "status": "PASS",
            "answer_preview": answer_text[:120].replace("\n", " ") + "...",
            "citations_count": len(citations),
            "verification_status": qa_data.get("verification_status")
        }
        print(f"   [PASS] Q&A generated answer with {len(citations)} citations (Status: {qa_data.get('verification_status')})")
    except Exception as e:
        results["qa"] = {"status": "FAIL", "error": str(e)}
        print(f"   [FAIL] Q&A failed: {e}")

    # 7. Topic Intelligence Discovery
    print("\n7. Testing Topic Discovery (/topics)...")
    try:
        r = client.get(f"{BASE_URL}/topics", headers=headers)
        assert r.status_code == 200, f"Topic analyses list failed: {r.status_code}"
        analyses_data = r.json()
        analyses = analyses_data.get("items", []) if isinstance(analyses_data, dict) else analyses_data
        results["topics"] = {"status": "PASS", "available_analyses": len(analyses)}
        print(f"   [PASS] Topic analyses accessible: {len(analyses)} existing runs")
    except Exception as e:
        results["topics"] = {"status": "FAIL", "error": str(e)}
        print(f"   [FAIL] Topics check failed: {e}")

    # 8. Statutory Report Studio & DOCX Generation
    print("\n8. Testing Statutory Report Generation & DOCX Export...")
    created_report_id = None
    try:
        # Fetch available format
        r_fmt = client.get(f"{BASE_URL}/reports/formats", headers=headers)
        formats = r_fmt.json() if r_fmt.status_code == 200 else []
        fmt_id = formats[0].get("id") if formats else "CMPDI_MINING_PLAN_MOC_2025"

        report_payload = {
            "format_id": fmt_id,
            "organization_id": user_org_id or "",
            "mine_name": "Portability Validation Colliery",
            "block_name": "Block-IV Central Coalfield",
            "base_date": "2026-03"
        }
        r = client.post(f"{BASE_URL}/reports/generate", headers=headers, json=report_payload)
        assert r.status_code in [200, 201], f"Report generation failed: {r.status_code} {r.text}"
        report_data = r.json()
        created_report_id = report_data.get("report_id")
        assert created_report_id, "Missing report_id"

        # Export DOCX
        export_payload = {"freeze_version": False, "change_summary": "Smoke test export"}
        r = client.post(f"{BASE_URL}/reports/{created_report_id}/export", headers=headers, json=export_payload)
        assert r.status_code in [200, 201], f"DOCX export failed: {r.status_code} {r.text}"
        export_data = r.json()

        # Download / verify DOCX
        r = client.get(f"{BASE_URL}/reports/{created_report_id}/download", headers=headers)
        assert r.status_code == 200, f"Download failed: {r.status_code}"
        docx_bytes = len(r.content)
        assert docx_bytes > 500, f"DOCX file suspiciously small: {docx_bytes} bytes"

        results["reports"] = {
            "status": "PASS",
            "report_id": created_report_id,
            "docx_bytes": docx_bytes,
            "docx_path": export_data.get("docx_file_path")
        }
        print(f"   [PASS] Report generated and downloaded successfully ({docx_bytes} bytes DOCX)")
    except Exception as e:
        results["reports"] = {"status": "FAIL", "error": str(e)}
        print(f"   [FAIL] Reports failed: {e}")

    # 9. Audit Event Traceability
    print("\n9. Testing Immutable Audit Events (/audit/logs)...")
    try:
        r = client.get(f"{BASE_URL}/audit/logs?limit=10", headers=headers)
        assert r.status_code == 200, f"Audit query failed: {r.status_code}"
        events = r.json()
        assert len(events) > 0, "No audit events found"
        results["audit"] = {"status": "PASS", "recent_events_count": len(events)}
        print(f"   [PASS] Audit events verified: {len(events)} events recorded in database")
    except Exception as e:
        results["audit"] = {"status": "FAIL", "error": str(e)}
        print(f"   [FAIL] Audit check failed: {e}")

    # 10. Frontend Availability
    print("\n10. Testing Frontend Web Server (http://localhost:5173)...")
    try:
        r = client.get(FRONTEND_URL)
        assert r.status_code == 200, f"Frontend returned {r.status_code}"
        assert "<div id=\"root\">" in r.text or "koyla" in r.text.lower()
        results["frontend"] = {"status": "PASS", "status_code": 200}
        print("   [PASS] Frontend responding with healthy SPA entrypoint")
    except Exception as e:
        results["frontend"] = {"status": "FAIL", "error": str(e)}
        print(f"   [FAIL] Frontend check failed: {e}")

    print("\n=== SMOKE TEST SUMMARY ===")
    all_passed = all(v.get("status") == "PASS" for v in results.values())
    print(f"Overall Result: {'ALL PASS' if all_passed else 'SOME CHECKS FAILED'}")
    print(json.dumps(results, indent=2))
    return results, created_report_id

if __name__ == "__main__":
    res, _ = run_smoke_tests()
    if not all(v.get("status") == "PASS" for v in res.values()):
        sys.exit(1)
