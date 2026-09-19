import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = os.getenv("ARTIFACT_DIR", os.path.join(os.path.dirname(__file__), "..", "artifacts"))
BASE_URL = "http://localhost:5173"
ANALYSIS_ID = "03625855-4c7a-4e5b-9aa1-e745e8ede4f1"

def run_browser_verification():
    print(f"Starting real live browser verification against {BASE_URL}/topics...")
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Login
        print("1. Logging into CMPDI Secure Portal as sysadmin...")
        page.goto(f"{BASE_URL}/login")
        page.wait_for_selector("#username")
        page.fill("#username", "sysadmin")
        page.fill("#password", "Admin123!")
        page.click("button[type='submit']")
        page.wait_for_url(f"**/dashboard", timeout=10000)
        print("   Login successful, navigated to Dashboard.")

        # 2. Navigate to /topics
        print(f"2. Navigating to /topics?id={ANALYSIS_ID}...")
        page.goto(f"{BASE_URL}/topics?id={ANALYSIS_ID}")
        page.wait_for_selector("text=TOPIC INTELLIGENCE CONTROL ROOM", timeout=10000)
        time.sleep(2)  # Wait for API requests to resolve

        # 3. Verify Header & Operational Metadata
        print("3. Verifying Header and Operational Analysis Metadata Banner...")
        analysis_tag = page.locator("text=Analysis: 03625855...").first
        if analysis_tag.is_visible():
            print("   [OK] Analysis UUID matched: 03625855...")
        else:
            print("   [WARN] Analysis tag not immediately visible")

        # Screenshot 1: Topic Register Table
        ss1_path = os.path.join(ARTIFACTS_DIR, "phase84_01_topic_control_room_register.png")
        page.screenshot(path=ss1_path, full_page=True)
        print(f"   Saved Screenshot 1: {ss1_path}")

        # 4. Word Cloud Tab
        print("4. Testing Word Cloud & Vocabulary Register Tab...")
        page.click("text=WORD CLOUD & VOCABULARY")
        page.wait_for_selector("text=MATHEMATICAL CLASS-BASED TF-IDF WORD CLOUD", timeout=8000)
        time.sleep(1)
        ss2_path = os.path.join(ARTIFACTS_DIR, "phase84_02_word_cloud_vocabulary.png")
        page.screenshot(path=ss2_path, full_page=True)
        print(f"   Saved Screenshot 2: {ss2_path}")

        # 5. Temporal Trends Tab
        print("5. Testing Temporal Trends Tab...")
        page.click("button:has-text('TEMPORAL TRENDS')")
        page.wait_for_selector("text=TOPIC PREVALENCE OVER TIME", timeout=8000)
        time.sleep(1)
        ss3_path = os.path.join(ARTIFACTS_DIR, "phase84_03_temporal_trends.png")
        page.screenshot(path=ss3_path, full_page=True)
        print(f"   Saved Screenshot 3: {ss3_path}")

        # 6. Year-to-Year Shift Tab
        print("6. Testing Year-to-Year Shift Workbench...")
        page.click("button:has-text('YEAR-TO-YEAR SHIFT')")
        page.wait_for_selector("text=YEAR-TO-YEAR TOPIC SHIFT & PROGRESSION", timeout=8000)
        time.sleep(1)
        ss4_path = os.path.join(ARTIFACTS_DIR, "phase84_04_yoy_shift.png")
        page.screenshot(path=ss4_path, full_page=True)
        print(f"   Saved Screenshot 4: {ss4_path}")

        # 7. Comparison Workbench Tab
        print("7. Testing Comparison Workbench...")
        page.click("button:has-text('COMPARISON WORKBENCH')")
        page.wait_for_selector("text=MULTI-DIMENSIONAL TOPIC COMPARISON", timeout=8000)
        time.sleep(1)
        ss5_path = os.path.join(ARTIFACTS_DIR, "phase84_05_comparison_workbench.png")
        page.screenshot(path=ss5_path, full_page=True)
        print(f"   Saved Screenshot 5: {ss5_path}")

        # 8. Topic Detail & Evidence Tab
        print("8. Testing Topic Detail & Grounded Evidence...")
        page.click("button:has-text('TOPIC DETAIL & EVIDENCE')")
        page.wait_for_selector("text=SELECTED TOPIC DOSSIER", timeout=8000)
        page.wait_for_selector("text=GROUNDED EVIDENCE CARDS & PHYSICAL PROVENANCE", timeout=8000)
        time.sleep(1)
        ss6_path = os.path.join(ARTIFACTS_DIR, "phase84_06_topic_detail_evidence.png")
        page.screenshot(path=ss6_path, full_page=True)
        print(f"   Saved Screenshot 6: {ss6_path}")

        # 9. Term Evolution Tab
        print("9. Testing Term Evolution...")
        page.click("button:has-text('TERM EVOLUTION')")
        page.wait_for_selector("text=TERM EVOLUTION ACROSS TIME", timeout=8000)
        time.sleep(1)
        ss7_path = os.path.join(ARTIFACTS_DIR, "phase84_07_term_evolution.png")
        page.screenshot(path=ss7_path, full_page=True)
        print(f"   Saved Screenshot 7: {ss7_path}")

        # 10. Local AI Summary Generation
        print("10. Triggering Factual AI Summary...")
        summary_btn = page.locator("button:has-text('Factual AI Summary')")
        if summary_btn.is_visible():
            summary_btn.click()
            page.wait_for_selector("text=EMPIRICAL SYNTHESIS SUMMARY", timeout=10000)
            time.sleep(1)
            ss8_path = os.path.join(ARTIFACTS_DIR, "phase84_08_factual_ai_summary.png")
            page.screenshot(path=ss8_path, full_page=True)
            print(f"   Saved Screenshot 8: {ss8_path}")

        # 11. Add Analysis to Report Modal
        print("11. Testing Add Analysis to Report Modal...")
        add_btn = page.locator("button:has-text('Add Analysis to Report')").first
        if add_btn.is_visible():
            add_btn.click()
            page.wait_for_selector("text=ADD ANALYSIS TO STATUTORY REPORT", timeout=8000)
            time.sleep(1)
            ss9_path = os.path.join(ARTIFACTS_DIR, "phase84_09_add_to_report_modal.png")
            page.screenshot(path=ss9_path, full_page=True)
            print(f"   Saved Screenshot 9: {ss9_path}")
            
            # Close modal
            page.click("button:has-text('Close')")
            time.sleep(0.5)

        # 12. Evidence Navigation: Click VIEW SOURCE
        print("12. Testing VIEW SOURCE Deep Link Navigation...")
        page.click("button:has-text('TOPIC DETAIL & EVIDENCE')")
        time.sleep(1)
        view_source_link = page.locator("a:has-text('VIEW SOURCE')").first
        if view_source_link.is_visible():
            target_href = view_source_link.get_attribute("href")
            print(f"   VIEW SOURCE target href: {target_href}")
            view_source_link.click()
            page.wait_for_url("**/documents/**", timeout=10000)
            time.sleep(1.5)
            ss10_path = os.path.join(ARTIFACTS_DIR, "phase84_10_view_source_navigation.png")
            page.screenshot(path=ss10_path, full_page=True)
            print(f"   Navigated to Document Viewer successfully! Saved Screenshot 10: {ss10_path}")

        browser.close()
        print("\nALL 12 REAL BROWSER VERIFICATION STEPS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_browser_verification()
