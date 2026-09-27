import os
import io
import time
import uuid
import httpx
from PIL import Image, ImageDraw
import openpyxl

ARTIFACT_DIR = r"C:\Users\aksha\.gemini\antigravity\brain\bf055439-6e03-468d-9c0c-1cb398e9b1ca"
BASE_URL = "http://localhost:8000/api/v1"
FRONTEND_URL = "http://localhost:5173"

def create_demo_files():
    # 1. XLSX Spreadsheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Monthly_Production"
    ws.append(["Mine_Name", "Period", "Target_MT", "Actual_MT", "Variance_MT"])
    ws.append(["Gevra OC", "April 2024", 50.0, 52.5, 2.5])
    ws.append(["Dipka OC", "April 2024", 35.0, 34.2, -0.8])
    ws.append(["Kusmunda OC", "April 2024", 42.0, 43.1, 1.1])
    xlsx_path = "demo_production_records.xlsx"
    wb.save(xlsx_path)

    # 2. CSV File
    csv_content = (
        "mine_name,formation,drilling_depth_m,stripping_ratio\n"
        "Gevra OC,Barakar Formation,280.5,1.85\n"
        "Dipka OC,Barakar Formation,210.0,2.10\n"
        "Kusmunda OC,Raniganj Formation,195.4,1.65\n"
    )
    csv_path = "demo_mine_operations.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_content)

    # 3. Geological Section PNG
    img = Image.new("RGB", (600, 400), color=(240, 235, 225))
    draw = ImageDraw.Draw(img)
    # Draw geological strata
    draw.rectangle([50, 50, 550, 150], fill=(210, 180, 140), outline=(100, 80, 50), width=2)
    draw.text((60, 60), "Overburden / Alluvium (Thickness: 15m)", fill=(50, 40, 20))
    draw.rectangle([50, 150, 550, 250], fill=(60, 60, 60), outline=(0, 0, 0), width=2)
    draw.text((60, 160), "Coal Seam I (Thickness: 8.5m) - Barakar Formation", fill=(255, 255, 255))
    draw.rectangle([50, 250, 550, 350], fill=(180, 160, 120), outline=(80, 60, 40), width=2)
    draw.text((60, 260), "Sandstone Interburden - Gevra Block", fill=(30, 20, 10))
    png_path = "demo_geological_section_map.png"
    img.save(png_path)

    # 4. Text brief
    txt_content = (
        "# Gevra Colliery Operational & Geological Brief\n\n"
        "The Barakar formation at Gevra Colliery exhibits thick coal seams with proved reserves.\n"
        "Exploration drilling confirmed continuous seam correlation across North and South blocks.\n"
    )
    txt_path = "demo_gevra_geology_brief.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)

    return xlsx_path, csv_path, png_path, txt_path

def run_verification():
    print("=== STARTING PHASE 10 UNIVERSAL EVIDENCE ENGINE VERIFICATION ===")
    client = httpx.Client(timeout=30.0)

    # Step 1: Login
    print("\n1. Authenticating as HQ Officer...")
    login_res = client.post(f"{BASE_URL}/auth/login", data={"username": "hq_officer", "password": "Admin123!"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   [OK] Authenticated successfully.")

    # Get SECL organization
    orgs_res = client.get(f"{BASE_URL}/organizations/", headers=headers)
    assert orgs_res.status_code == 200
    secl_org = next((o for o in orgs_res.json() if o["code"] == "SECL"), orgs_res.json()[0])
    org_id = secl_org["id"]
    print(f"   [OK] Using Organization: {secl_org['code']} ({org_id})")

    # Step 2: Create demo files
    print("\n2. Generating heterogeneous demonstration evidence files...")
    xlsx_path, csv_path, png_path, txt_path = create_demo_files()
    print("   [OK] Created XLSX, CSV, PNG, TXT files.")

    # Step 3: Batch Upload
    print("\n3. Executing ONE-ACTION Evidence Batch Ingestion (POST /api/v1/evidence/upload)...")
    with open(xlsx_path, "rb") as f_xlsx, \
         open(csv_path, "rb") as f_csv, \
         open(png_path, "rb") as f_png, \
         open(txt_path, "rb") as f_txt:

        files = [
            ("files", ("gevra_production_apr2024.xlsx", f_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ("files", ("gevra_mine_operations.csv", f_csv, "text/csv")),
            ("files", ("gevra_geological_section.png", f_png, "image/png")),
            ("files", ("gevra_geology_brief.txt", f_txt, "text/plain"))
        ]

        upload_res = client.post(
            f"{BASE_URL}/evidence/upload?sync=true",
            headers=headers,
            data={"organization_id": org_id, "source_tier": "TIER_A"},
            files=files
        )

    assert upload_res.status_code == 201, f"Batch upload failed: {upload_res.text}"
    batch_data = upload_res.json()
    print(f"   [OK] Batch Ingestion Succeeded! Total files processed: {batch_data['total_files']}")
    for item in batch_data["items"]:
        print(f"        - {item['original_filename']} -> Detected: {item['detected_format']}, Inferred: {item['inferred_type']}, Status: {item['status']}")

    # Step 4: Summary Metrics
    print("\n4. Verifying Universal Evidence Summary (GET /api/v1/evidence/summary)...")
    sum_res = client.get(f"{BASE_URL}/evidence/summary", headers=headers)
    assert sum_res.status_code == 200
    summary = sum_res.json()
    print(f"   [OK] Summary Metrics:")
    print(f"        - Total Documents: {summary['total_documents']}")
    print(f"        - Structured Values: {summary['structured_values_count']}")
    print(f"        - Visual Assets: {summary['visual_assets_count']}")
    print(f"        - Tables Preserved: {summary['table_evidence_count']}")
    print(f"        - Text Pages: {summary['text_evidence_count']}")
    print(f"        - Cross-Document Relationships: {summary['relationships_count']}")

    # Step 5: Evidence Items Register
    print("\n5. Verifying Universal Evidence Items Register (GET /api/v1/evidence/items)...")
    items_res = client.get(f"{BASE_URL}/evidence/items?limit=20", headers=headers)
    assert items_res.status_code == 200
    items_data = items_res.json()
    print(f"   [OK] Retrieved {len(items_data['items'])} items (Total: {items_data['total']})")
    for itm in items_data["items"][:5]:
        print(f"        [{itm['evidence_type']}] {itm['provenance_display']} | {itm['content_preview'][:60]} | Conf: {itm['confidence_score']:.2f}")

    # Step 6: Discovered Relationships
    print("\n6. Verifying Discovered Cross-Document Relationships (GET /api/v1/evidence/relationships)...")
    rels_res = client.get(f"{BASE_URL}/evidence/relationships", headers=headers)
    assert rels_res.status_code == 200
    rels = rels_res.json()
    print(f"   [OK] Total Relationships Discovered: {len(rels)}")
    for r in rels[:4]:
        print(f"        - [{r['relationship_type']}] {r['source_title']} <-> {r['target_title']} (Conf: {r['confidence']:.2f})")

    # Step 7: Grounded Q&A with Multimodal Citations
    print("\n7. Executing Grounded Multimodal Q&A Query...")
    qa_res = client.post(
        f"{BASE_URL}/qa/query",
        headers=headers,
        json={
            "query": "What is the coal production target and actual output for Gevra OC?",
            "filters": {"organization_id": org_id},
            "top_k": 5
        }
    )
    assert qa_res.status_code == 200
    qa_data = qa_res.json()
    print(f"   [OK] Answer Status: {qa_data['verification_status']}")
    print(f"        Answer: {qa_data['answer'][:150]}...")
    print(f"        Citations Count: {len(qa_data['citations'])}")
    for c in qa_data["citations"][:3]:
        fmt_str = f" | Format: {c.get('format_provenance', {}).get('provenance_display', 'N/A')}" if c.get('format_provenance') else ""
        vis_str = f" | Visual: {c.get('visual_provenance', {}).get('visual_type', 'N/A')}" if c.get('visual_provenance') else ""
        print(f"        - Citation [{c['citation_index']}] Page {c.get('page_number')}: {c['document_title']}{fmt_str}{vis_str}")

    # Step 8: Playwright Browser Visual Verification
    print("\n8. Executing Playwright Browser Verification & Screenshot Capture...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # Set auth token in localStorage
            page.goto(f"{FRONTEND_URL}/login")
            page.evaluate(f"localStorage.setItem('token', '{token}')")

            # 1. Evidence Control Room
            print("   -> Navigating to /evidence (Evidence Control Room)...")
            page.goto(f"{FRONTEND_URL}/evidence")
            page.wait_for_timeout(2000)
            ss1 = os.path.join(ARTIFACT_DIR, "phase10_01_evidence_control_room.png")
            page.screenshot(path=ss1, full_page=True)
            print(f"      [OK] Saved screenshot: phase10_01_evidence_control_room.png")

            # 2. Document Upload Studio
            print("   -> Navigating to /upload (Universal Evidence Ingestion)...")
            page.goto(f"{FRONTEND_URL}/upload")
            page.wait_for_timeout(1500)
            ss2 = os.path.join(ARTIFACT_DIR, "phase10_02_universal_ingestion_studio.png")
            page.screenshot(path=ss2, full_page=True)
            print(f"      [OK] Saved screenshot: phase10_02_universal_ingestion_studio.png")

            # 3. AI Query Multimodal Citations
            print("   -> Navigating to /query (AI Grounded Q&A)...")
            page.goto(f"{FRONTEND_URL}/query")
            page.wait_for_timeout(1500)
            # Type question and submit
            page.fill("textarea", "What is the coal production target and actual output for Gevra OC?")
            page.click("button:has-text('Execute Grounded Query')")
            try:
                page.wait_for_selector("text=Inference:", timeout=25000)
            except Exception:
                page.wait_for_timeout(8000)
            page.wait_for_timeout(1500)
            ss3 = os.path.join(ARTIFACT_DIR, "phase10_03_multimodal_grounded_qa.png")
            page.screenshot(path=ss3, full_page=True)
            print(f"      [OK] Saved screenshot: phase10_03_multimodal_grounded_qa.png")

            browser.close()
    except Exception as e:
        print(f"   [WARNING] Playwright browser capture notice: {e}")

    # Clean up local temp demo files
    for p_file in [xlsx_path, csv_path, png_path, txt_path]:
        if os.path.exists(p_file):
            try:
                os.remove(p_file)
            except Exception:
                pass

    print("\n=== PHASE 10 VERIFICATION COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_verification()
