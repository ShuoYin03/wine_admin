import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(__file__, "../../../.."))
sys.path.insert(0, PROJECT_ROOT)
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
STATE_PATH = os.path.join(PROJECT_ROOT, "wine_spider", "login_state", "wineauctioneer_cookies.json")

def do_login():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False, 
            args=[
                "--disable-blink-features=AutomationControlled",    
                ]
            )
        
        ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = ctx.new_page()

        # Go to the page and accept cookies
        page.goto("https://wineauctioneer.com/")
        page.click("text=Accept all")

        # Click svg to open login menu
        page.click('svg[id="icon-circle-user-light"]')
        page.wait_for_selector("#collapseUserMenu .user-login-form h4", state="visible")

        # Fill in the login form
        login_container = page.locator("#collapseUserMenu")
        email_input = login_container.locator('input[data-drupal-selector="edit-name"]')
        email_input.wait_for(state="visible")
        email_input.fill(EMAIL)

        password_input = login_container.locator('input[data-drupal-selector="edit-pass"]')
        password_input.fill(PASSWORD)

        # Click the login button
        login_container.locator('input[data-drupal-selector="edit-submit"]').click()
        
        page.wait_for_load_state("networkidle", timeout=20000)
        ctx.storage_state(path=STATE_PATH)
        browser.close()

if __name__ == "__main__":
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    do_login()