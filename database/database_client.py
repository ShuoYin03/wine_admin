import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect, Table, MetaData
from sqlalchemy.dialects.postgresql import insert

load_dotenv()

class DatabaseClient:
    def __init__(self):
        self.engine = create_engine(os.getenv('DB_URL'))
        self.Session = sessionmaker(bind=self.engine)
        self.metadata = MetaData()

    def get_table(self, table_name):
        return Table(table_name, self.metadata, autoload_with=self.engine)

    def insert_item(self, table_name, item_data):
        table = self.get_table(table_name)
        
        session = self.Session()
        try:
            insert_stmt = insert(table).values(**item_data)
            update_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['id'],
                set_={k: v for k, v in item_data.items()}
            )
            
            with session.begin():
                session.execute(update_stmt)
            
        except Exception as e:
            session.rollback()
            print(f"Error: {e}")
        finally:
            session.close()

    def close(self):
        self.sess.close()
