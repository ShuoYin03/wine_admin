import os
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

class SothebysLoginMiddleware:
    def __init__(self, state_path, expire_days, login_script):
        self.state_path = state_path
        self.expire_seconds = expire_days * 86400
        self.login_script = login_script
        self.cookie = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            state_path=crawler.settings.get("SOTHEBYS_STATE_PATH"),
            expire_days=crawler.settings.getint("SOTHEBYS_STATE_EXPIRE_DAYS", 10),
            login_script=crawler.settings.get("SOTHEBYS_LOGIN_SCRIPT", "login.py")
        )
    
    def process_request(self, request, spider):
        if spider.name == "sothebys_spider":
            self._ensure_fresh_state()
            request.meta["playwright_context"] = "sothebys"

        return None
    
    def _ensure_fresh_state(self):
        if not os.path.exists(self.state_path) or \
           (time.time() - os.path.getmtime(self.state_path)) > self.expire_seconds:
            print("Login state missing or expired, re-running login script…")
            subprocess.run(
                ["python", self.login_script],
                check=True
            )