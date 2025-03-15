import os
import re
import time
import json
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from wine_spider.helpers.sothebys.captcha_parser import CaptchaParser

load_dotenv()

EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')
captchaParser = CaptchaParser()

class SothebysClient:
    def __init__(self, headless=True):  
        self.api_url = "https://clientapi.prod.sothelabs.com/graphql"

        self.playwright = sync_playwright().start() 
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--start-maximized"
            ]
        )

        self.cookies_path = "wine_spider/login_state/sothebys_cookies.json"
        if os.path.exists(self.cookies_path):
            self.context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                storage_state=self.cookies_path
            )

            self.page = self.context.new_page()
        else:
            self.context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            )

            self.page = self.context.new_page()
            self.login()
            time.sleep(5)
            self.context.storage_state(path=self.cookies_path)

        self.context.route("**/*", lambda route, request: route.abort() if request.resource_type in ["image", "stylesheet"] else route.continue_())

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
        self.page.goto(url, wait_until="networkidle", timeout=30000)
        return self.page.content()

    def get_authorisation_token_and_response(self, url):
        target_url_base = "https://accounts.sothebys.com/authorize"
        target_text = None

        def log_response(response):
            nonlocal target_text
            if response.url.startswith(target_url_base):
                target_text = response.text()

        self.page.on("response", log_response)
        self.page.goto(url, wait_until="networkidle")

        target_text = re.search(r'"access_token"\s*:\s*"([^"]+)"', target_text)
        target_text = target_text.group(1)
        return self.page.content(), target_text

    def auction_query(self, viking_id):
        payload = {
            "operationName": "AuctionQuery",
            "variables": {
                "id": viking_id,
                "language": "ENGLISH"
            },
            "query": """
                query AuctionQuery($id: String!, $language: TranslationLanguage!) {
                    auction(id: $id, language: $language) {
                        id
                        auctionId
                        title
                        currency
                        location: locationV2 {
                            name
                        }
                        dates {
                            acceptsBids
                            closed    
                        }
                        sessions {
                            lotRange {
                                fromLotNr
                                toLotNr
                            }
                        }
                        state
                    }
                }
            """
        }
        
        return payload
    
    def lot_card_query(self, viking_id, lot_ids):
        payload = {
            "operationName": "LotCardsQuery",
            "variables": {
                "id": viking_id,
                "lotIds": lot_ids,
                "language": "ENGLISH"
            },
            "query": """
                query LotCardsQuery($id: String!, $lotIds: [String!]!, $language: TranslationLanguage!) {
                    auction(id: $id, language: $language) {
                        lot_ids: lotCardsFromIds(ids: $lotIds) {
                            ...LotItemFragment
                        }
                    }
                }

                fragment LotItemFragment on LotCard {
                    lotId
                    bidState {
                        ...BidStateFragment
                    }
                }

                fragment BidStateFragment on BidState {
                    bidType: bidTypeV2 {
                        __typename
                    }
                    startingBid: startingBidV2 {
                        ...AmountFragment
                    }
                    sold {
                        ... on ResultVisible {
                            isSold
                            premiums {
                                finalPrice: finalPriceV2 {
                                    ...AmountFragment
                                }
                            }
                        }
                        }
                }

                fragment AmountFragment on Amount {
                    currency
                    amount
                }
            """
        }

        return payload

    def extract_algolia_api_key(self, html):
        soup = BeautifulSoup(html, "html.parser")
        script_tag = soup.find("script", {"id": "__NEXT_DATA__", "type": "application/json"})
        algolia_api_key = json.loads(script_tag.string)['props']['pageProps']['algoliaSearchKey']

        return algolia_api_key

    def algolia_api(self, auction_id, api_key, page):
        url = "https://kar1ueupjd-dsn.algolia.net/1/indexes/prod_lots/query?x-algolia-agent=Algolia%20for%20JavaScript%20(4.14.3)%3B%20Browser"

        headers = {
            "accept-encoding": "gzip, deflate",
            "accept": "*/*",
            "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,it;q=0.7",
            "connection": "keep-alive",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.sothebys.com",
            "referer": "https://www.sothebys.com/",
            "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "x-algolia-api-key": api_key,
            "x-algolia-application-id": "KAR1UEUPJD",
        }

        payload = {
            "query": "",
            "filters": f"auctionId:'{auction_id}' AND objectTypes:'All' AND NOT isHidden:true AND NOT restrictedInCountries:'GB'",
            "facetFilters": [["withdrawn:false"], []],
            "hitsPerPage": 48,
            "page": page,
            "facets": ["*"],
            "numericFilters": [],
        }

        return url, headers, payload

    def close(self):
        self.browser.close()
        self.playwright.stop()

    def __del__(self):
        self.close()
    
