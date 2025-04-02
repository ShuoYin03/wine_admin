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

    def query_items(
        self,
        table_name, 
        filters=None, 
        order_by=None, 
        limit=None, 
        offset=None, 
        select_fields=None, 
        distinct_fields=None, 
        return_count=False
    ):
        table = self.get_table(table_name)
        session = self.Session()

        if distinct_fields:
            column = getattr(table.c, distinct_fields)
            query = session.query(column.distinct())
        else:
            query = self.build_query(table, session, select_fields)

        conditions = []
        if filters:
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

        if return_count:
            if conditions:
                count_query = session.query(func.count()).select_from(table).filter(and_(*conditions))
            else:
                count_query = session.query(func.count()).select_from(table)
            count = count_query.scalar()

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
        
        session.close()

        if return_count:
            return [dict(row._mapping) for row in results], count
        
        return [dict(row._mapping) for row in results]
    
    def query_lots_with_auction(
        self,
        filters: dict = None,
        order_by: str = None,
        limit: int = 50,
        offset: int = 0,
        return_count: bool = False,
    ):
        session = self.Session()
        lots = self.get_table("lots")
        auctions = self.get_table("auctions")

        query = session.query(lots, auctions).join(
            auctions, lots.c.auction_id == auctions.c.id
        )

        lots_fields = set(lots.c.keys())
        auction_fields = set(auctions.c.keys())

        conditions = []

        if filters:
            for key, value in filters.items():
                op = "eq"
                if '__' in key:
                    key, op = key.split('__')

                if key in lots_fields:
                    col = lots.c[key]
                elif key in auction_fields:
                    col = auctions.c[key]
                else:
                    continue

                if op == "eq":
                    conditions.append(col == value)
                elif op == "like":
                    conditions.append(col.ilike(f"%{value}%"))
                elif op == "gt":
                    conditions.append(col > value)
                elif op == "lt":
                    conditions.append(col < value)
                elif op == "gte":
                    conditions.append(col >= value)
                elif op == "lte":
                    conditions.append(col <= value)
                elif op == "between" and isinstance(value, (list, tuple)) and len(value) == 2:
                    conditions.append(col.between(value[0], value[1]))

        if conditions:
            query = query.filter(and_(*conditions))

        if order_by:
            field = order_by.lstrip("-")
            desc = order_by.startswith("-")
            if field in lots_fields:
                col = lots.c[field]
            elif field in auction_fields:
                col = auctions.c[field]
            else:
                col = None

            if col is not None:
                query = query.order_by(col.desc() if desc else col)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        if return_count:
            count_query = session.query(func.count()).select_from(
                lots.join(auctions, lots.c.auction_id == auctions.c.id)
            ).filter(and_(*conditions)) if conditions else session.query(func.count()).select_from(
                lots.join(auctions, lots.c.auction_id == auctions.c.id)
            )
            count = count_query.scalar()

        results = query.all()
        session.close()

        if return_count:
            return [dict(row._mapping) for row in results], count

        return  [dict(row._mapping) for row in results]

    def close(self):
        self.engine.dispose()