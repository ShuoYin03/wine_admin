import os, sys
from browserforge.fingerprints import Screen
PROJECT_ROOT = os.path.abspath(os.path.join(__file__, "../../../.."))
sys.path.insert(0, PROJECT_ROOT)
import time
from camoufox.sync_api import Camoufox
from dotenv import load_dotenv

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
STATE_PATH = os.path.join(PROJECT_ROOT, "wine_spider", "login_state", "sothebys_cookies.json")

def click_cloudflare_checkbox_by_position(page, sleep_time=5) -> bool:
    for frame in page.frames:
        if frame.url.startswith("https://challenges.cloudflare.com"):
            try:
                frame_element = frame.frame_element()
                bounding_box = frame_element.bounding_box()
                if not bounding_box:
                    continue

                checkbox_x = bounding_box["x"] + bounding_box["width"] / 9
                checkbox_y = bounding_box["y"] + bounding_box["height"] / 2

                time.sleep(sleep_time)
                page.mouse.click(checkbox_x, checkbox_y)
                return True
            except Exception:
                continue
    return False

def do_login():
    with Camoufox(
        headless=False,
        os="windows",
        humanize=True,
        disable_coop=True,
        screen=Screen(max_width=1920, max_height=1080)
    ) as browser:
        page = browser.new_page()
        page.goto("https://www.sothebys.com/en", wait_until="networkidle")
        try:
            page.click("#onetrust-reject-all-handler")
        except Exception:
            pass
        page.click('div.LinkedText a[href*="auth0login"]')

        page.fill("#email", EMAIL)
        page.fill("#password", PASSWORD)

        page.wait_for_timeout(3000)

        has_turnstile = any(
            "challenges.cloudflare.com" in f.url
            for f in page.frames
        )

        if has_turnstile:
            clicked = click_cloudflare_checkbox_by_position(page, sleep_time=5)
            page.wait_for_selector(
                "iframe[src*='challenges.cloudflare.com']",
                state="detached",
                timeout=20000
            )
        else:
            print("No Turnstile")

        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=20000)
        page.context.storage_state(path=STATE_PATH)

if __name__ == "__main__":
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    do_login()
    print("Logged in and saved state to", STATE_PATH)
