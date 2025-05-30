import os
from flask import current_app
from contextlib import contextmanager
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import create_engine, and_, or_, func, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.dialects.postgresql import ARRAY

class BaseDatabaseClient:
    def __init__(self, orm_model, db_instance):
        self.model = orm_model
        if db_instance:
            self.db = db_instance
        else:
            db_url = os.getenv("DB_URL")
            engine = create_engine(db_url)
            self.db = None
            self.Session = scoped_session(sessionmaker(bind=engine))


    @contextmanager
    def session_scope(self):
        if self.db:
            session = self.db.session()
        else:
            session = self.Session()
        
        try:
            yield session
            session.commit()
        except Exception as e:
            if self.db:
                current_app.logger.error(f"[DB ERROR] {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def get_all(self):
        with self.session_scope() as session:
            return session.query(self.model).all()

    def get_by_id(self, item_id):
        with self.session_scope() as session:
            return session.get(self.model, item_id)
    
    def get_by_external_id(self, external_id):
        with self.session_scope() as session:
            return session.query(self.model).filter_by(external_id=external_id).first()
    
    def upsert(self, data_dict):
        with self.session_scope() as session:
            instance = session.get(self.model, data_dict.get("id"))
            if instance:
                for key, value in data_dict.items():
                    setattr(instance, key, value)
            else:
                instance = self.model(**data_dict)
                session.add(instance)

    def upsert_by_external_id(self, data_dict):
        with self.session_scope() as session:
            instance = session.query(self.model).filter_by(external_id=data_dict.get("external_id")).first()
            if instance:
                for key, value in data_dict.items():
                    setattr(instance, key, value)
            else:
                instance = self.model(**data_dict)
                session.add(instance)

    def update_item(self, item_id, update_data):
        with self.session_scope() as session:
            session.query(self.model).filter_by(id=item_id).update(update_data)

    def delete_item(self, item_id):
        with self.session_scope() as session:
            session.query(self.model).filter_by(id=item_id).delete()
    
    def delete_by_external_id(self, external_id):
        with self.session_scope() as session:
            session.query(self.model).filter_by(external_id=external_id).delete()

    def parse_filters(self, filters, table_map):
        and_conditions = []
        or_conditions = []

        for column, op, value in filters or []:
            col = None
            for table in table_map.values():
                if hasattr(table, column):
                    col = getattr(table, column)
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
                if isinstance(col.type, ARRAY):
                    condition = func.any(col) == value
                else:
                    condition = col.ilike(f'%{value}%')

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
        
    def apply_filters(self, query, filters, table_map):
        conditions = self.parse_filters(filters, table_map)
        return query.filter(conditions) if conditions is not None else query

    def apply_sort(self, query, order_by, table_map):
        if not order_by:
            return query
        fields = [order_by] if isinstance(order_by, str) else order_by
        for field in fields:
            desc = field.startswith("-")
            field_name = field.lstrip("-")
            for table in table_map.values():
                col = getattr(table, field_name, None)
                if isinstance(col, InstrumentedAttribute):
                    query = query.order_by(col.desc() if desc else col)
                    break
        return query

    def apply_select(self, query, select_fields, table_map):
        if not select_fields:
            return query
        selected_columns = []
        for field in select_fields:
            for table in table_map.values():
                col = getattr(table, field, None)
                if isinstance(col, InstrumentedAttribute):
                    selected_columns.append(col)
                    break
        return query.with_entities(*selected_columns)

    def apply_distinct(self, query, distinct_fields):
        if not distinct_fields:
            return query
        col = getattr(self.model, distinct_fields, None)
        if isinstance(col, InstrumentedAttribute):
            return query.with_entities(col.distinct())
        return query

    def apply_pagination(self, query, limit=None, offset=None):
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query
    
    def get_table_count(self, session, filters=None, table_map=None):
        count_query = session.query(func.count(self.model.id))

        if filters and table_map:
            count_query = self.apply_filters(count_query, filters, table_map)

        return count_query.scalar()
        
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