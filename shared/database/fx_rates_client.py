from .base_database_client import BaseDatabaseClient
from shared.database.models.fx_rate_db import FxRatesModel

class FxRatesClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(FxRatesModel, db_instance=db_instance)
    
    def get_by_date_and_currencies(self, rates_from, rates_to, date):
        with self.session_scope() as session:
            return session.query(self.model).filter_by(
                rates_from=rates_from,
                rates_to=rates_to,
                date=date
            ).first()
