from playwright.sync_api import sync_playwright
import os

ARTIFACT_DIR = os.getenv("ARTIFACT_DIR", os.path.join(os.path.dirname(__file__), "..", "artifacts"))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto("http://localhost:5173/login", wait_until="domcontentloaded")
    page.wait_for_timeout(1000)
    page.click('button[type="submit"]')
    page.wait_for_timeout(1500)
    page.goto("http://localhost:5173/reports/95102085-8893-43b5-b2e7-3598a23cf99d", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.click('button:has-text("STATUTORY ANNEXURES")')
    page.wait_for_timeout(1500)
    # Click the last inspect brief button which corresponds to the attached topic brief
    page.locator('button:has-text("INSPECT BRIEF")').last.click()
    page.wait_for_timeout(1500)
    page.screenshot(path=os.path.join(ARTIFACT_DIR, "phase85_05_report_studio_attached_annexure.png"))
    print("Captured phase85_05 with topic brief modal successfully!")
    browser.close()
