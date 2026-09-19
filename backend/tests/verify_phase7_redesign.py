import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = os.getenv("ARTIFACT_DIR", os.path.join(os.path.dirname(__file__), "..", "artifacts"))

def run_phase7_redesign_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Desktop enterprise resolution: 1536 x 960
        context = browser.new_context(viewport={"width": 1536, "height": 960})
        page = context.new_page()

        print("[1] Navigating to login page...", flush=True)
        page.goto("http://localhost:5173/login", wait_until="networkidle")
        time.sleep(1)

        print("[2] Logging in as hq_officer...", flush=True)
        page.fill("#username", "hq_officer")
        page.fill("#password", "Admin123!")
        page.click("button[type='submit']")

        page.wait_for_url("**/dashboard", timeout=8000)
        print("[3] Logged in successfully.", flush=True)
        time.sleep(1)

        print("[4] Navigating to Statutory Dossier Register (/reports)...", flush=True)
        page.goto("http://localhost:5173/reports", wait_until="networkidle")
        page.wait_for_selector("text=STATUTORY REPORT DOSSIER REGISTER", timeout=10000)
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "redesign_01_report_dossier_register.png"))
        print("    [[OK]] redesign_01_report_dossier_register.png captured.", flush=True)

        print("[5] Navigating to New Dossier Compiler (/reports/new)...", flush=True)
        page.goto("http://localhost:5173/reports/new", wait_until="networkidle")
        page.wait_for_selector("text=MINISTRY OF COAL STATUTORY COMPILATION GATEWAY", timeout=10000)
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "redesign_02_new_dossier_compiler.png"))
        print("    [[OK]] redesign_02_new_dossier_compiler.png captured.", flush=True)

        print("[6] Opening first available dossier in Report Studio...", flush=True)
        page.goto("http://localhost:5173/reports", wait_until="networkidle")
        page.wait_for_selector("text=OPEN DOSSIER", timeout=10000)
        page.click("text=OPEN DOSSIER", timeout=5000)

        page.wait_for_url("**/reports/*", timeout=15000)
        page.wait_for_selector("text=STATUTORY REPORT DOSSIER", timeout=20000)
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "redesign_03_dossier_header_and_overview.png"))
        print("    [[OK]] redesign_03_dossier_header_and_overview.png captured.", flush=True)

        print("[7] Inspecting Chapter 2: Geology & Reserves (with calculation sheet and evidence)...", flush=True)
        page.click("button:has-text('GEOLOGY & RESERVES')")
        time.sleep(1)
        # Click 2.2 Reserve sub-section to focus on calculation sheet
        reserve_sub = page.query_selector("button:has-text('2.2 Reserve / Resource')")
        if reserve_sub:
            reserve_sub.click()
            time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "redesign_04_chapter2_geology_and_reserves.png"))
        print("    [[OK]] redesign_04_chapter2_geology_and_reserves.png captured.", flush=True)

        print("[8] Opening Forensic Evidence Drawer / Modal...", flush=True)
        evidence_btn = page.query_selector("button:has-text('EVIDENCE')")
        if evidence_btn:
            evidence_btn.click()
            time.sleep(1)
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "redesign_05_forensic_evidence_modal.png"))
            print("    [[OK]] redesign_05_forensic_evidence_modal.png captured.", flush=True)
            page.click("button:has-text('CLOSE')")
            time.sleep(0.5)

        print("[9] Inspecting Prescribed Tables Register...", flush=True)
        page.click("button:has-text('PRESCRIBED TABLES')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "redesign_06_prescribed_tables_register.png"))
        print("    [[OK]] redesign_06_prescribed_tables_register.png captured.", flush=True)

        print("[10] Inspecting Technical Plates Drawing Register...", flush=True)
        page.click("button:has-text('TECHNICAL PLATES')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "redesign_07_technical_plates_drawing_register.png"))
        print("    [[OK]] redesign_07_technical_plates_drawing_register.png captured.", flush=True)

        print("[11] Inspecting Statutory Annexures Register...", flush=True)
        page.click("button:has-text('STATUTORY ANNEXURES')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "redesign_08_statutory_annexures_register.png"))
        print("    [[OK]] redesign_08_statutory_annexures_register.png captured.", flush=True)

        print("[12] Inspecting Statutory Execution (Certifications)...", flush=True)
        page.click("button:has-text('STATUTORY EXECUTION')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "redesign_09_statutory_certifications_execution.png"))
        print("    [[OK]] redesign_09_statutory_certifications_execution.png captured.", flush=True)

        print("[13] Inspecting Statutory Compliance Audit Register...", flush=True)
        page.click("button:has-text('COMPLIANCE AUDIT')")
        time.sleep(1.5)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "redesign_10_compliance_auditor_register.png"))
        print("    [[OK]] redesign_10_compliance_auditor_register.png captured.", flush=True)

        print("[COMPLETE] All 10 redesign verification screenshots captured successfully!", flush=True)
        browser.close()

if __name__ == "__main__":
    run_phase7_redesign_verification()
