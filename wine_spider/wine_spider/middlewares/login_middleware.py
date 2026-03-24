import os
import time
import json
import subprocess
from dotenv import load_dotenv

load_dotenv()


class BaseLoginMiddleware:
    spider_name: str = None

    def __init__(self, state_path, expire_days, login_script):
        self.state_path = state_path
        self.expire_seconds = expire_days * 86400
        self.login_script = login_script

    def process_request(self, request, spider):
        if spider.name == self.spider_name:
            self._ensure_fresh_state()
            self._apply_auth(request)
        return None

    def _ensure_fresh_state(self):
        if not os.path.exists(self.state_path) or \
           (time.time() - os.path.getmtime(self.state_path)) > self.expire_seconds:
            print("Login state missing or expired, re-running login script…")
            subprocess.run(["python", self.login_script], check=True)

    def _apply_auth(self, request):
        raise NotImplementedError


class SothebysLoginMiddleware(BaseLoginMiddleware):
    spider_name = "sothebys_spider"

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            state_path=crawler.settings.get("SOTHEBYS_STATE_PATH"),
            expire_days=crawler.settings.getint("SOTHEBYS_STATE_EXPIRE_DAYS", 10),
            login_script=crawler.settings.get("SOTHEBYS_LOGIN_SCRIPT", "login.py"),
        )

    def _apply_auth(self, request):
        request.meta["playwright_context"] = "sothebys"


class WineauctioneerLoginMiddleware(BaseLoginMiddleware):
    spider_name = "wineauctioneer_spider"

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            state_path=crawler.settings.get("WINEAUCTIONEER_STATE_PATH"),
            expire_days=crawler.settings.getint("WINEAUCTIONEER_STATE_EXPIRE_DAYS", 10),
            login_script=crawler.settings.get("WINEAUCTIONEER_LOGIN_SCRIPT", "login.py"),
        )

    def _apply_auth(self, request):
        with open(self.state_path, "r") as f:
            cookies = json.load(f)
        cookies = {c["name"]: c["value"] for c in cookies.get("cookies", [])}
        request.cookies = cookies
