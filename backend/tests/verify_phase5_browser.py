import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = os.getenv("ARTIFACT_DIR", os.path.join(os.path.dirname(__file__), "..", "artifacts"))

def verify_knowledge_explorer():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("[1] Navigating to login page...", flush=True)
        page.goto("http://localhost:5173/login", wait_until="networkidle")
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase5_01_login.png"))

        print("[2] Logging in as hq_officer...", flush=True)
        page.fill("#username", "hq_officer")
        page.fill("#password", "Admin123!")
        page.click("button[type='submit']")

        # Wait for navigation to dashboard
        page.wait_for_url("**/dashboard", timeout=5000)
        print("[3] Logged in successfully. Current URL:", page.url, flush=True)
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase5_02_dashboard.png"))

        print("[4] Navigating to Knowledge Explorer (/knowledge)...", flush=True)
        page.goto("http://localhost:5173/knowledge", wait_until="networkidle")
        page.wait_for_selector("text=Knowledge Explorer", timeout=5000)
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase5_03_knowledge_init.png"))

        print("[5] Executing Hybrid Search for 'geological exploration drilling'...", flush=True)
        search_input = page.locator("input[placeholder*='Search reports']")
        search_input.fill("geological exploration drilling")
        page.click("button:has-text('Retrieve Evidence')")

        # Wait for results
        page.wait_for_selector("text=Evidence Candidate", timeout=8000)
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase5_04_hybrid_results.png"))

        candidates_header = page.locator("text=Evidence Candidate").first.text_content()
        print(f"    Results loaded: {candidates_header}", flush=True)

        print("[6] Opening Provenance Modal for first candidate...", flush=True)
        provenance_btn = page.locator("button:has-text('Inspect Provenance')").first
        provenance_btn.click()
        page.wait_for_selector("text=Evidence Provenance Lineage", timeout=3000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase5_05_provenance_modal.png"))

        # Close provenance modal using the X button
        page.locator("button:has(svg.lucide-x)").first.click()
        time.sleep(0.5)

        print("[7] Opening Retrieval Latency & Trace Modal...", flush=True)
        trace_btn = page.locator("button:has-text('Inspect Retrieval Trace')").first
        trace_btn.click()
        page.wait_for_selector("text=Retrieval Trace & Performance Telemetry", timeout=3000)
        time.sleep(0.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase5_06_trace_modal.png"))

        # Close trace modal using the X button
        page.locator("button:has(svg.lucide-x)").first.click()
        time.sleep(0.5)

        print("[8] Testing Keyword Mode Search...", flush=True)
        page.click("button:has-text('Keyword (PostgreSQL FTS)')")
        page.click("button:has-text('Retrieve Evidence')")
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase5_07_keyword_search.png"))

        print("[9] Testing Dense Semantic Mode Search...", flush=True)
        page.click("button:has-text('Semantic (Dense pgvector)')")
        page.click("button:has-text('Retrieve Evidence')")
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase5_08_semantic_search.png"))

        print("[10] Testing Document Viewer link navigation...", flush=True)
        open_doc_btn = page.locator("button:has-text('Open in Document Viewer')").first
        if open_doc_btn.count() > 0:
            open_doc_btn.click()
            page.wait_for_url("**/documents/*", timeout=5000)
            print("     Navigated to Document Viewer URL:", page.url, flush=True)
            time.sleep(1.5)
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase5_09_document_viewer.png"))

        print("[11] Testing Organization Isolation as ri1_analyst...", flush=True)
        # Logout
        page.click("button:has-text('Logout')")
        page.wait_for_url("**/login", timeout=5000)

        # Login as ri1_analyst
        page.fill("#username", "ri1_analyst")
        page.fill("#password", "Password123!")
        page.click("button[type='submit']")
        page.wait_for_url("**/dashboard", timeout=5000)

        # Navigate to knowledge explorer
        page.goto("http://localhost:5173/knowledge", wait_until="networkidle")
        search_input = page.locator("input[placeholder*='Search reports']")
        search_input.fill("geological exploration drilling")
        page.click("button:has-text('Retrieve Evidence')")
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase5_10_ri1_isolated_search.png"))

        no_results = page.locator("text=No Evidence Found").count()
        print(f"     ri1_analyst query completed. Empty state detected: {no_results > 0 or page.locator('text=0 Evidence Candidates Retrieved').count() > 0}", flush=True)

        print("=== BROWSER VERIFICATION COMPLETED SUCCESSFULLY ===", flush=True)
        browser.close()

if __name__ == "__main__":
    verify_knowledge_explorer()
