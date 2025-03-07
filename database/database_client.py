import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect, Table, MetaData

class DatabaseClient:
    def __init__(self):
        self.engine = create_engine(os.getenv('DB_URL'))
        self.Session = sessionmaker(bind=self.engine)
        self.sess = self.Session()
        self.metadata = MetaData()

    def get_table(self, table_name):
        return Table(table_name, self.metadata, autoload_with=self.engine)

    def get_one_records(self, table_name):
        table = self.get_table(table_name)
        query = self.sess.query(table).limit(1)
        results = query.all()
        return list(results[0])

    def get_record_by_id(self, table_name, record_id):
        table = self.get_table(table_name)
        query = self.sess.query(table)
        result = query.first()
        return dict(result) if result else None

    def close(self):
        self.sess.close()