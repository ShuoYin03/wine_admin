from .base_database_client import BaseDatabaseClient
from shared.database.models.lwin_database_db import LwinDatabaseModel
import pandas as pd
from sqlalchemy import func

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

            df = pd.DataFrame(data, dtype=object)
            # Keep missing values as None instead of NaN
            df = df.where(pd.notnull(df), None)
            return df

    def get_by_display_name(self, display_name):
        normalized = (display_name or '').strip().lower()

        with self.session_scope() as session:
            orm_objects = session.query(self.model).filter(
                func.lower(func.trim(self.model.display_name)) == normalized
            ).all()

            return [
                {
                    column.name: getattr(obj, column.name)
                    for column in self.model.__table__.columns
                }
                for obj in orm_objects
            ]