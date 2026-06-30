import os
import sys
from browserforge.fingerprints import Screen
PROJECT_ROOT = os.path.abspath(os.path.join(__file__, "../../../.."))
sys.path.insert(0, PROJECT_ROOT)
import time
from camoufox.sync_api import Camoufox
from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

load_dotenv()
STATE_PATH = os.path.join(PROJECT_ROOT, "wine_spider", "login_state", "sothebys_cookies.json")
LOGIN_URL = "https://www.sothebys.com/api/auth0login?lang=en&fromHeader=Y"
USERNAME_SELECTOR = '#username, input[name="username"], #email, input[name="email"], input[type="email"]'
PASSWORD_SELECTOR = '#password, input[name="password"], input[type="password"]'
SUBMIT_SELECTOR = 'button[type="submit"], button[name="action"]'

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

def get_credentials() -> tuple[str, str]:
    email = os.getenv("SOTHEBYS_EMAIL") or os.getenv("EMAIL")
    password = os.getenv("SOTHEBYS_PASSWORD") or os.getenv("PASSWORD")
    if not email or not password:
        raise RuntimeError(
            "Sotheby's login requires SOTHEBYS_EMAIL/SOTHEBYS_PASSWORD "
            "or EMAIL/PASSWORD environment variables."
        )
    return email, password

def wait_for_turnstile_if_present(page, timeout=20000) -> None:
    has_turnstile = any(
        "challenges.cloudflare.com" in frame.url
        for frame in page.frames
    )
    if not has_turnstile:
        return

    clicked = click_cloudflare_checkbox_by_position(page, sleep_time=5)
    if clicked:
        page.wait_for_selector(
            "iframe[src*='challenges.cloudflare.com']",
            state="detached",
            timeout=timeout,
        )

def password_visible(page, timeout=1500) -> bool:
    try:
        page.wait_for_selector(PASSWORD_SELECTOR, state="visible", timeout=timeout)
        return True
    except PlaywrightTimeoutError:
        return False
    except Exception:
        return False

def submit_auth0_login(page, email: str, password: str) -> None:
    page.wait_for_selector(USERNAME_SELECTOR, state="visible", timeout=30000)
    page.fill(USERNAME_SELECTOR, email)

    if not password_visible(page):
        wait_for_turnstile_if_present(page)
        page.click(SUBMIT_SELECTOR)
        page.wait_for_selector(PASSWORD_SELECTOR, state="visible", timeout=45000)

    page.fill(PASSWORD_SELECTOR, password)
    wait_for_turnstile_if_present(page)
    page.click(SUBMIT_SELECTOR)
    page.wait_for_load_state("networkidle", timeout=30000)

def do_login():
    email, password = get_credentials()
    with Camoufox(
        headless=False,
        os="windows",
        humanize=True,
        disable_coop=True,
        screen=Screen(max_width=1920, max_height=1080)
    ) as browser:
        page = browser.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
        submit_auth0_login(page, email, password)
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        page.context.storage_state(path=STATE_PATH)

if __name__ == "__main__":
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    do_login()
    print("Logged in and saved state to", STATE_PATH)
