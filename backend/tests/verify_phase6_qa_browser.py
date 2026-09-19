import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = os.getenv("ARTIFACT_DIR", os.path.join(os.path.dirname(__file__), "..", "artifacts"))

def verify_arithmetic_and_conflict():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("[1] Navigating to login page...", flush=True)
        page.goto("http://localhost:5173/login", wait_until="networkidle")

        print("[2] Logging in as hq_officer...", flush=True)
        page.fill("#username", "hq_officer")
        page.fill("#password", "Admin123!")
        page.click("button[type='submit']")

        page.wait_for_url("**/dashboard", timeout=5000)
        print("[3] Logged in successfully.", flush=True)
        time.sleep(1)

        print("[4] Navigating to Grounded AI Q&A (/ask)...", flush=True)
        page.goto("http://localhost:5173/ask", wait_until="networkidle")
        page.wait_for_selector("text=Grounded AI Q&A Console", timeout=5000)
        time.sleep(1)

        print("[5] Triggering Preset [2] Deterministic YoY Calculation...", flush=True)
        page.click("button:has-text('[2]')")

        # Wait for calculation response
        page.wait_for_selector("text=Deterministic Calculations", timeout=25000)
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase6_04_arithmetic_calculation.png"))
        print("    Arithmetic calculation screenshot captured.", flush=True)

        print("[6] Triggering Preset [4] Cross-Document Conflict Test...", flush=True)
        page.click("button:has-text('[4]')")

        # Wait for conflict alert
        page.wait_for_selector("text=Cross-Document Discrepancy Flagged", timeout=25000)
        time.sleep(2)
        page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase6_05_cross_document_conflict.png"))
        print("    Conflict alert screenshot captured.", flush=True)

        browser.close()
        print("BROWSER SCREENSHOTS COMPLETE!", flush=True)

if __name__ == "__main__":
    verify_arithmetic_and_conflict()
