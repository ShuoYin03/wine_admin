import os
from dotenv import load_dotenv
from contextlib import contextmanager
from sqlalchemy import Table, MetaData, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.dialects.postgresql import insert

load_dotenv()

class DatabaseClient:
    def __init__(self):
        self.engine = create_engine(os.getenv('DB_URL'))
        self.Session = sessionmaker(bind=self.engine)
        self.metadata = MetaData()

    @contextmanager
    def session_scope(self):
        session = self.Session()
        try:
            yield session
        finally:
            session.close()

    def get_table(self, name):
        return Table(name, self.metadata, autoload_with=self.engine)
    
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

    def parse_filters(self, filters: list[list], table_map: dict):
        and_conditions = []
        or_conditions = []

        for column, op, value in filters or []:
            col = None
            for table in table_map.values():
                if column in table.c:
                    col = table.c[column]
                    break
            if col is None:
                continue

            condition = None
            if op == "eq":
                condition = col == value
            elif op == "like":
                condition = col.ilike(f"%{value}%")
            elif op == "gt":
                condition = col > value
            elif op == "lt":
                condition = col < value
            elif op == "gte":
                condition = col >= value
            elif op == "lte":
                condition = col <= value
            elif op == "between" and isinstance(value, (tuple, list)) and len(value) == 2:
                condition = col.between(value[0], value[1])
            elif op == "contains":
                condition = col.any(value)

            if condition is not None:
                if op == "contains":
                    or_conditions.append(condition)
                else:
                    and_conditions.append(condition)

        if or_conditions and and_conditions:
            return and_(or_(*or_conditions), *and_conditions)
        elif or_conditions:
            return or_(*or_conditions)
        elif and_conditions:
            return and_(*and_conditions)
        else:
            return None

    def apply_order(self, query, order_by, table_map):
        if not order_by:
            return query
        fields = [order_by] if isinstance(order_by, str) else order_by
        for field in fields:
            desc = field.startswith("-")
            field_name = field.lstrip("-")
            for table in table_map.values():
                if field_name in table.c:
                    col = table.c[field_name]
                    query = query.order_by(col.desc() if desc else col)
                    break
        return query

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
        with self.session_scope() as session:
            table = self.get_table(table_name)

            table_map = {"main": table}
            columns = [getattr(table.c, f) for f in select_fields] if select_fields else [table]

            query = session.query(*columns)

            if distinct_fields:
                query = session.query(getattr(table.c, distinct_fields).distinct())

            conditions = self.parse_filters(filters, table_map)
            if conditions is not None:
                query = query.filter(conditions)

            query = self.apply_order(query, order_by, table_map)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            count = None
            if return_count:
                count_query = session.query(func.count()).select_from(table)
                if conditions is not None:
                    count_query = count_query.filter(conditions)
                count = count_query.scalar()

            results = query.all()
            session.close()

            data = [dict(row._mapping) for row in results]
            return (data, count) if return_count else data

    def query_lots_with_auction(
        self, 
        filters=None, 
        order_by=None, 
        limit=None, 
        offset=None, 
        select_fields=None, 
        distinct_fields=None, 
        return_count=False
    ):
        with self.session_scope() as session:
            lots = self.get_table("lots")
            auctions = self.get_table("auctions")

            table_map = {"lots": lots, "auctions": auctions}

            selected_columns = []
            if select_fields:
                for field in select_fields:
                    for table in table_map.values():
                        if field in table.c:
                            selected_columns.append(table.c[field])
                            break
            else:
                selected_columns = [lots, auctions]

            if distinct_fields:
                for idx, col in enumerate(selected_columns):
                    if col.name == distinct_fields:
                        selected_columns[idx] = col.distinct()
                        break
            
            query = session.query(*selected_columns)

            query = query.join(auctions, lots.c.auction_id == auctions.c.id)

            conditions = self.parse_filters(filters, table_map)
            if conditions is not None:
                query = query.filter(conditions)

            query = self.apply_order(query, order_by, table_map)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            count = None
            if return_count:
                count_query = session.query(func.count()).select_from(lots.join(auctions, lots.c.auction_id == auctions.c.id))
                if conditions is not None:
                    count_query = count_query.filter(conditions)
                count = count_query.scalar()

            results = query.all()
            session.close()

            data = [dict(row._mapping) for row in results]
            if distinct_fields:
                data = [row[0] for row in results]

            return (data, count) if return_count else data
        
    def query_lwin_with_lots(
        self, 
        filters=None, 
        order_by=None, 
        limit=50, 
        offset=0, 
        select_fields=None, 
        distinct_fields=None, 
        return_count=False
    ):
        with self.session_scope() as session:
            lwin_matching = self.get_table("lwin_matching")
            lots = self.get_table("lots")

            table_map = {"lwin_matching": lwin_matching, "lots": lots}

            selected_columns = []
            if select_fields:
                for field in select_fields:
                    for table in table_map.values():
                        if field in table.c:
                            selected_columns.append(table.c[field])
                            break
            else:
                selected_columns = [lwin_matching, lots]

            if distinct_fields:
                for idx, col in enumerate(selected_columns):
                    if col.name == distinct_fields:
                        selected_columns[idx] = col.distinct()
                        break
            
            query = session.query(*selected_columns)

            query = query.join(lots, lwin_matching.c.id == lots.c.id)

            conditions = self.parse_filters(filters, table_map)
            if conditions is not None:
                query = query.filter(conditions)

            query = self.apply_order(query, order_by, table_map)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            count = None
            if return_count:
                count_query = session.query(func.count()).select_from(lwin_matching.join(lots, lwin_matching.c.id == lots.c.id))
                if conditions is not None:
                    count_query = count_query.filter(conditions)
                count = count_query.scalar()

            results = query.all()
            session.close()

            data = [dict(row._mapping) for row in results]
            if distinct_fields:
                data = [row[0] for row in results]

            return (data, count) if return_count else data
    
    def bm25_search(self, table_name, search_text, limit=50):
        with self.session_scope() as session:
            query = text(f"""
                SELECT *, 
                    ts_rank_cd(
                        to_tsvector('simple', display_name), 
                        websearch_to_tsquery('simple', :search_text)
                    ) AS rank
                FROM {table_name}
                WHERE to_tsvector('simple', display_name)
                    @@ websearch_to_tsquery('simple', :search_text)
                ORDER BY rank DESC
                LIMIT :limit
            """)
            results = session.execute(query, {'search_text': search_text, 'limit': limit}).fetchall()
            return [dict(row._mapping) for row in results]
        
    def close(self):
        self.engine.dispose()