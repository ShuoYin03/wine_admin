from .base_database_client import BaseDatabaseClient
from .model import FxRatesModel

class FxRatesClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(FxRatesModel, db_instance=db_instance)
