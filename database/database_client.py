import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Table, MetaData, func, and_
from sqlalchemy.dialects.postgresql import insert

load_dotenv()

class DatabaseClient:
    def __init__(self):
        self.engine = create_engine(os.getenv('DB_URL'))
        self.Session = sessionmaker(bind=self.engine)
        self.metadata = MetaData()

    def get_table(self, table_name):
        return Table(table_name, self.metadata, autoload_with=self.engine)

    def get_random_item(self, model_class):
        session = self.Session()
        try:
            result = session.query(model_class).order_by(func.random()).limit(1).first()
            return result
        except Exception as e:
            print(f"Error: {e}")
            return None
        finally:
            session.close()

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
    
    def build_query(self, table, session, select_fields=None):
        if select_fields:
            columns = [getattr(table.c, field) for field in select_fields]
            return session.query(*columns)
        return session.query(table)

    def query_items(self, table_name, filters=None, order_by=None, limit=None, offset=None, select_fields=None, distinct_fields=None):
        table = self.get_table(table_name)
        session = self.Session()

        # try:
        if distinct_fields:
            column = getattr(table.c, distinct_fields)
            query = session.query(column.distinct())
        else:
            query = self.build_query(table, session, select_fields)

        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, tuple) and len(value) == 2:
                    conditions.append(getattr(table.c, key).between(value[0], value[1]))
                elif key.endswith('__like'):
                    key = key.replace('__like', '')
                    conditions.append(getattr(table.c, key).ilike(f"%{value}%"))
                elif key.endswith('__gt'):
                    key = key.replace('__gt', '')
                    conditions.append(getattr(table.c, key) > value)
                elif key.endswith('__lt'):
                    key = key.replace('__lt', '')
                    conditions.append(getattr(table.c, key) < value)
                elif key.endswith('__gte'):
                    key = key.replace('__gte', '')
                    conditions.append(getattr(table.c, key) >= value)
                elif key.endswith('__lte'):
                    key = key.replace('__lte', '')
                    conditions.append(getattr(table.c, key) <= value)
                else:
                    conditions.append(getattr(table.c, key) == value)

            query = query.filter(and_(*conditions))

        if order_by:
            if isinstance(order_by, str):
                query = query.order_by(getattr(table.c, order_by[1:]).desc()) if order_by.startswith('-') else query.order_by(getattr(table.c, order_by))
            elif isinstance(order_by, list):
                order_clauses = [getattr(table.c, field[1:]).desc() if field.startswith('-') else getattr(table.c, field) for field in order_by]
                query = query.order_by(*order_clauses)

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        results = query.all()

        if distinct_fields:
            return [row[0] for row in results]

        return [dict(row._mapping) for row in results]

        # except Exception as e:
        #     print(f"Error: {e}")
        #     return []
        # finally:
        #     session.close()

    # def query_items(self, table_name, filters=None, order_by=None, limit=None, offset=None, select_fields=None):
    #     table = self.get_table(table_name)
    #     session = self.Session()
        
    #     try:
    #         query = self.build_query(table, session, select_fields)

    #         if filters:
    #             conditions = []
    #             for key, value in filters.items():
    #                 if isinstance(value, tuple) and len(value) == 2:
    #                     conditions.append(getattr(table.c, key).between(value[0], value[1]))

    #                 elif key.endswith('__like'):
    #                     key = key.replace('__like', '')
    #                     conditions.append(getattr(table.c, key).ilike(f"%{value}%"))
                    
    #                 elif key.endswith('__gt'):
    #                     key = key.replace('__gt', '')
    #                     conditions.append(getattr(table.c, key) > value)
                    
    #                 elif key.endswith('__lt'):
    #                     key = key.replace('__lt', '')
    #                     conditions.append(getattr(table.c, key) < value)
                    
    #                 elif key.endswith('__gte'):
    #                     key = key.replace('__gte', '')
    #                     conditions.append(getattr(table.c, key) >= value)
                    
    #                 elif key.endswith('__lte'):
    #                     key = key.replace('__lte', '')
    #                     conditions.append(getattr(table.c, key) <= value)
    #                 else:
    #                     conditions.append(getattr(table.c, key) == value)

    #             query = query.filter(and_(*conditions))
            
    #         if order_by:
    #             if isinstance(order_by, str):
    #                 query = query.order_by(getattr(table.c, order_by[1:]).desc()) if order_by.startswith('-') else query.order_by(getattr(table.c, order_by))
    #             elif isinstance(order_by, list):
    #                 order_clauses = [getattr(table.c, field[1:]).desc() if field.startswith('-') else getattr(table.c, field) for field in order_by]
    #                 query = query.order_by(*order_clauses)

    #         if offset:
    #             query = query.offset(offset)

    #         if limit:
    #             query = query.limit(limit)

    #         results = query.all()

    #         return [dict(row._mapping) for row in results]

    #     except Exception as e:
    #         print(f"Error: {e}")
    #         return []
    #     finally:
    #         session.close()

    def close(self):
        self.engine.dispose()