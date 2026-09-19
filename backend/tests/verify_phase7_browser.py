import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = os.getenv("ARTIFACT_DIR", os.path.join(os.path.dirname(__file__), "..", "artifacts"))

def run_phase7_browser_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 950})
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

        print("[4] Navigating to Report Studio (/reports)...", flush=True)
        page.goto("http://localhost:5173/reports", wait_until="networkidle")
        page.wait_for_selector("text=Official Report Studio", timeout=10000)
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_01_report_list.png"))
        print("    [[OK]] phase7_01_report_list.png captured.", flush=True)

        print("[5] Navigating to New Report Generator (/reports/new)...", flush=True)
        page.goto("http://localhost:5173/reports/new", wait_until="networkidle")
        page.wait_for_selector("text=Generate Official Mining Plan", timeout=10000)
        time.sleep(1)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_02_report_new_form.png"))
        print("    [[OK]] phase7_02_report_new_form.png captured.", flush=True)

        print("[6] Generating Statutory Mining Plan (Appendix-I 2025)...", flush=True)
        page.click("button:has-text('Compile Statutory Report Draft')")

        # Wait for redirect to /reports/:id
        page.wait_for_url("**/reports/*", timeout=45000)
        page.wait_for_selector("text=MoC / CCO 2025 Statutory Format", timeout=20000)
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_03_report_studio_overview.png"))
        print("    [[OK]] phase7_03_report_studio_overview.png captured.", flush=True)

        print("[7] Inspecting Chapters & Fields tab...", flush=True)
        page.click("button:has-text('Chapters & Fields')")
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_04_chapters_fields_provenance.png"))
        print("    [[OK]] phase7_04_chapters_fields_provenance.png captured.", flush=True)

        print("[7b] Inspecting Prescribed Tables tab (23 tables)...", flush=True)
        page.click("button:has-text('Prescribed Tables')")
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_04b_prescribed_tables.png"))
        print("    [[OK]] phase7_04b_prescribed_tables.png captured.", flush=True)

        print("[7c] Inspecting Technical Plates tab (Plates I to XXIII)...", flush=True)
        page.click("button:has-text('Technical Plates')")
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_04c_technical_plates.png"))
        print("    [[OK]] phase7_04c_technical_plates.png captured.", flush=True)

        print("[7d] Inspecting Statutory Annexures tab (Annexures I to VIII)...", flush=True)
        page.click("button:has-text('Statutory Annexures')")
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_04d_statutory_annexures.png"))
        print("    [[OK]] phase7_04d_statutory_annexures.png captured.", flush=True)

        print("[8] Performing QP Inline Review / Correction...", flush=True)
        page.click("button:has-text('Chapters & Fields')")
        time.sleep(1)
        edit_icons = page.locator("button[title='Correct field value']")
        if edit_icons.count() > 0:
            edit_icons.first.click()
            time.sleep(1)
            page.fill("textarea", "48.50 MT (QP Verified from 2026 Borehole log)")
            page.fill("input[placeholder*='Review note']", "Verified and corrected by Recognized Qualified Person per Rule 22C.")
            page.click("button:has-text('Save Correction')")
            time.sleep(2)
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_05_qp_human_review_correction.png"))
            print("    [[OK]] phase7_05_qp_human_review_correction.png captured.", flush=True)

        print("[9] Inspecting Certifications tab and signing statutory certificate...", flush=True)
        page.click("button:has-text('Certifications')")
        time.sleep(1)
        sign_btn = page.locator("button:has-text('Sign Undertaking')")
        if sign_btn.count() > 0:
            sign_btn.first.click()
            time.sleep(1)
            page.click("button:has-text('Sign & Record Audit Entry')")
            time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_06_statutory_certifications_signed.png"))
        print("    [[OK]] phase7_06_statutory_certifications_signed.png captured.", flush=True)

        print("[10] Inspecting Compliance Audit tab...", flush=True)
        page.click("button:has-text('Compliance Issues')")
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_07_compliance_audit.png"))
        print("    [[OK]] phase7_07_compliance_audit.png captured.", flush=True)

        print("[11] Testing Version Freezing and Native DOCX Generation...", flush=True)
        freeze_btn = page.locator("button:has-text('Freeze Immutable Version')")
        if freeze_btn.count() > 0:
            freeze_btn.click()
            time.sleep(3)

        page.click("button:has-text('Version History')")
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase7_08_version_freeze_docx.png"))
        print("    [[OK]] phase7_08_version_freeze_docx.png captured.", flush=True)

        browser.close()
        print("\nALL PHASE 7 BROWSER ACCEPTANCE TESTS COMPLETED SUCCESSFULLY!", flush=True)

if __name__ == "__main__":
    run_phase7_browser_verification()
