from .base_database_client import BaseDatabaseClient
from .model import LwinDatabaseModel
import pandas as pd

class LwinDatabaseClient(BaseDatabaseClient):
    def __init__(self, db_instance=None):
        super().__init__(LwinDatabaseModel, db_instance=db_instance)

    def get_all(self):
        with self.session_scope() as session:
            orm_objects = session.query(self.model).all()

            data = [
                {
                    column.name: getattr(obj, column.name)
                    for column in self.model.__table__.columns
                }
                for obj in orm_objects
            ]

            return pd.DataFrame(data)