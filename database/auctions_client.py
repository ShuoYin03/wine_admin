from .base_database_client import BaseDatabaseClient
from .model import AuctionModel

class AuctionsClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(AuctionModel, db_instance=db_instance)
