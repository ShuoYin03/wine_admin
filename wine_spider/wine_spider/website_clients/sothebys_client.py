import os
import time
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from wine_spider.helpers.captcha_parser import CaptchaParser

load_dotenv()

EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')
captchaParser = CaptchaParser()

class SothebysClient:
    def __init__(self):            
        self.playwright = sync_playwright().start() 

        self.browser = self.playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--start-maximized"
            ]
        )
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        )
        self.page = self.context.new_page()

        self.api_url = "https://clientapi.prod.sothelabs.com/graphql"
        self.login()
    
    def get_csrf(self):
        params = {
            "client": "M0egh8p8NswdGM6X53jp128a2bTOHN2E",
            "protocol": "oauth2",
            "audience": "https://customer.api.sothebys.com",
            "language": "en",
            "redirect_uri": "https://www.sothebys.com/api/auth0callback?language=en&resource=fromHeader&src=",
            "response_type": "code",
            "scope": "openid email offline_access",
            "ui_locales": "en"
        }

        response = requests.get("https://accounts.sothebys.com/login", params=params)
        print(response.cookies.get_dict())
        csrf = response.cookies.get_dict()['_csrf']
        return csrf
        
    def login(self):
        self.page.goto("https://www.sothebys.com/en", wait_until="networkidle", timeout=10000)

        reject_btn = self.page.query_selector("#onetrust-reject-all-handler")
        reject_btn.click()
        time.sleep(1)

        login_btn = self.page.query_selector('div.LinkedText a[href*="auth0login"]')
        login_btn.click()

        self.page.wait_for_selector(".captcha-challenge img", state="visible", timeout=10000)
        html = self.page.content()
        soup = BeautifulSoup(html, "html.parser")
        captcha_img = soup.select_one(".captcha-challenge img")
        captcha_string = captcha_img.get("src")
        captcha = captchaParser.parse_captcha(captcha_string)

        email_input = self.page.query_selector('#email')
        email_input.fill(EMAIL)

        password_input = self.page.query_selector('#password')
        password_input.fill(PASSWORD)

        captcha_input = self.page.query_selector('input[name="captcha"]')
        captcha_input.fill(captcha)

        time.sleep(20)
        login_btn = self.page.query_selector('button[type="submit"]')
        login_btn.click()

    def go_to(self, url):
        self.page.goto(url, wait_until="networkidle", timeout=10000)
        return self.page.content()
    
    def auction_query(self, cookies):
        pass

    def lot_query(self, cookies):
        pass
    
    def lot_card_query(self, cookies):
        pass

    def close(self):
        self.browser.close()
        self.playwright.stop()

    def __del__(self):
        self.close()
    
