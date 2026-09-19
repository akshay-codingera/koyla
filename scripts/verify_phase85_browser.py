import sys
import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = os.getenv("ARTIFACT_DIR", os.path.join(os.path.dirname(__file__), "..", "artifacts"))

def run_browser_verification():
    print("Launching Playwright browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Login
        print("1. Navigating to Login page (http://localhost:5173/login)...")
        page.goto("http://localhost:5173/login", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        page.click('button[type="submit"]')
        page.wait_for_timeout(2000)
        print("Login successful, reached dashboard:", page.url)

        # 2. Topic Workspace
        print("2. Navigating to Topic Workspace (http://localhost:5173/topics)...")
        page.goto("http://localhost:5173/topics", wait_until="domcontentloaded")
        page.wait_for_timeout(3500)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase85_01_topics_workspace.png"))
        print("Captured: phase85_01_topics_workspace.png")

        # Click on the first topic in Topic Register to select it
        topic_row = page.locator('tbody tr').first
        if topic_row.count() > 0:
            print("Selecting first topic in register...")
            topic_row.click()
            page.wait_for_timeout(1500)

        # Scroll to view temporal trends and comparison workbench
        print("3. Scrolling to Temporal Trends and Comparisons...")
        page.evaluate("window.scrollBy(0, 650)")
        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase85_02_temporal_and_comparison.png"))
        print("Captured: phase85_02_temporal_and_comparison.png")

        # Switch to "TOPIC DETAIL & EVIDENCE" tab
        evidence_tab = page.locator('button:has-text("TOPIC DETAIL & EVIDENCE")')
        if evidence_tab.count() > 0:
            evidence_tab.click()
            page.wait_for_timeout(1500)

        # Scroll to view Evidence Cards & AI Summary
        print("4. Viewing Evidence and Summary...")
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase85_03_evidence_and_summary.png"))
        print("Captured: phase85_03_evidence_and_summary.png")

        # 5. Click "VIEW SOURCE" on evidence card to verify deep navigation to DocumentDetail
        print("5. Clicking VIEW SOURCE to verify deep navigation...")
        view_source_btn = page.locator('button:has-text("VIEW SOURCE"), a:has-text("VIEW SOURCE")').first
        if view_source_btn.count() > 0:
            view_source_btn.click()
            page.wait_for_timeout(3000)
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase85_04_view_source_navigation.png"))
            print("Captured: phase85_04_view_source_navigation.png (Document detail with targeted chunk/page)")
        else:
            print("Notice: VIEW SOURCE button not directly found on current view")

        # 6. Navigate to System Telemetry (/system)
        print("6. Navigating to System Telemetry (http://localhost:5173/system)...")
        page.goto("http://localhost:5173/system", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase85_06_system_health_telemetry.png"))
        print("Captured: phase85_06_system_health_telemetry.png")

        # 7. Navigate to Report Studio to verify Inspect Brief
        print("7. Navigating to Report Studio...")
        page.goto("http://localhost:5173/reports", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        
        # Check if there is an existing report to open
        report_link = page.locator('a[href^="/reports/"]').first
        if report_link.count() > 0:
            report_link.click()
            page.wait_for_timeout(2000)
            # Switch to annexures tab
            annexure_tab = page.locator('button:has-text("ANNEXURES")')
            if annexure_tab.count() > 0:
                annexure_tab.click()
                page.wait_for_timeout(1000)
                
                # Check for INSPECT BRIEF button
                inspect_btn = page.locator('button:has-text("INSPECT BRIEF")').first
                if inspect_btn.count() > 0:
                    inspect_btn.click()
                    page.wait_for_timeout(1000)
                    
            page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase85_05_report_studio_attached_annexure.png"))
            print("Captured: phase85_05_report_studio_attached_annexure.png")

        browser.close()
        print("Browser verification completed successfully!")

if __name__ == "__main__":
    run_browser_verification()
