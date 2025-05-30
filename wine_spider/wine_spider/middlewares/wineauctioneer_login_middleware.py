import os
import time
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

class WineauctioneerLoginMiddleware:
    def __init__(self, state_path, expire_days, login_script):
        self.state_path = state_path
        self.expire_seconds = expire_days * 86400
        self.login_script = login_script
        self.cookies = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            state_path=crawler.settings.get("WINEAUCTIONEER_STATE_PATH"),
            expire_days=crawler.settings.getint("WINEAUCTIONEER_STATE_EXPIRE_DAYS", 10),
            login_script=crawler.settings.get("WINEAUCTIONEER_LOGIN_SCRIPT", "login.py")
        )
    
    def process_request(self, request, spider):
        if spider.name == "wineauctioneer_spider":
            self._ensure_fresh_state()
            with open(self.state_path, 'r') as f:
                self.cookies = json.load(f)
            self.cookies = {cookie["name"]: cookie["value"] for cookie in self.cookies.get("cookies", [])}
            request.cookies = self.cookies

        return None
    
    def _ensure_fresh_state(self):
        if not os.path.exists(self.state_path) or \
           (time.time() - os.path.getmtime(self.state_path)) > self.expire_seconds:
            subprocess.run(
                ["python", self.login_script],
                check=True
            )