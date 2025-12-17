from shared.database import LwinDatabaseClient
from lwin_matcher.app.model import LwinMatchingParams
from lwin_matcher.app.service.lwin_matching_engine import LwinMatcherEngine

class LwinMatchingService:
    def __init__(self, lwin_data):
        self.lwin_database_client = LwinDatabaseClient()
        self.lwin_matching_engine = LwinMatcherEngine(self.lwin_database_client.get_all())

    def match(self, lwin_matching_params, topk=5):
        pass