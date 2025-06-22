from dotenv import load_dotenv
import os

load_dotenv()
BONHAMS_API_KEY = os.getenv("BONHAMS_API_KEY")

class BonhamsHeadersMiddleware:
    def __init__(self):
        self.custom_headers = {
            "x-typesense-api-key": BONHAMS_API_KEY,
        }

    def process_request(self, request, spider):
        for key, value in self.custom_headers.items():
            if key not in request.headers:
                request.headers[key] = value
        return None