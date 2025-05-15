import os, sys
PROJECT_ROOT = os.path.abspath(os.path.join(__file__, "../../../.."))
sys.path.insert(0, PROJECT_ROOT)
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from wine_spider.helpers import CaptchaParser

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
STATE_PATH = os.path.join(PROJECT_ROOT, "wine_spider", "login_state", "sothebys_cookies.json")

def do_login():
    parser = CaptchaParser()
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    page = ctx.new_page()
    page.goto("https://www.sothebys.com/en", wait_until="networkidle")
    page.click("#onetrust-reject-all-handler")
    page.click('div.LinkedText a[href*="auth0login"]')

    page.fill("#email", EMAIL)
    page.fill("#password", PASSWORD)
    captcha_url = page.locator(".captcha-challenge img").get_attribute("src")
    captcha_text = parser.parse_captcha(captcha_url)
    page.fill('input[name="captcha"]', captcha_text)
    time.sleep(15)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle", timeout=20000)
    ctx.storage_state(path=STATE_PATH)
    browser.close()
    pw.stop()

if __name__ == "__main__":
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    do_login()
    print("Logged in and saved state to", STATE_PATH)
