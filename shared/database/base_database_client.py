from __future__ import annotations
from typing import Any
from flask import current_app
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import and_, or_, func, text
from sqlalchemy.dialects.postgresql import insert, ARRAY as PG_ARRAY
from sqlalchemy.sql import quoted_name
from shared.database.session_factory import get_shared_session_factory, dispose_shared_engine

class BaseDatabaseClient:
    def __init__(self, orm_model: type, db_instance: Any | None = None) -> None:
        self.model = orm_model
        if db_instance:
            self.db = db_instance
            self.SessionFactory = None
        else:
            self.db = None
            self.SessionFactory = get_shared_session_factory()

    @contextmanager
    def session_scope(self):
        if self.db:
            session = self.db.session
        else:
            session = self.SessionFactory()
        
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

    def get_all(self) -> list:
        with self.session_scope() as session:
            return session.query(self.model).all()

    def get_by_id(self, item_id: int) -> Any | None:
        with self.session_scope() as session:
            return session.get(self.model, item_id)
    
    def get_by_external_id(self, external_id: str) -> Any | None:
        with self.session_scope() as session:
            return session.query(self.model).filter_by(external_id=external_id).first()
    
    def bulk_insert(self, data_list: list[dict], chunk_size: int = 1000) -> None:
        if not data_list:
            return
        
        with self.session_scope() as session:
            for start in range(0, len(data_list), chunk_size):
                chunk = data_list[start:start + chunk_size]
                session.execute(insert(self.model), chunk)
                
    def upsert(self, data_dict: dict, index_elements: list) -> None:
        with self.session_scope() as session:
            stmt = insert(self.model).values(**data_dict)

            update_dict = {
                c.name: getattr(stmt.excluded, c.name)
                for c in self.model.__table__.columns
                if c.name != "id"
            }

            stmt = stmt.on_conflict_do_update(
                index_elements=index_elements,
                set_=update_dict
            )

            session.execute(stmt)
    
    def bulk_upsert(self, data_list: list[dict], index_elements: list, chunk_size: int = 1000) -> None:
        if not data_list:
            return

        with self.session_scope() as session:
            for start in range(0, len(data_list), chunk_size):
                chunk = data_list[start:start + chunk_size]

                stmt = insert(self.model).values(chunk)

                update_dict = {
                    c.name: getattr(stmt.excluded, c.name)
                    for c in self.model.__table__.columns
                    if c.name != "id"
                }

                stmt = stmt.on_conflict_do_update(
                    index_elements=index_elements,
                    set_=update_dict
                )

                session.execute(stmt)

    def upsert_by_external_id(self, data_dict: dict) -> None:
        with self.session_scope() as session:
            existing = session.query(self.model).filter_by(
                external_id=data_dict["external_id"]
            ).first()
            if existing:
                for key, value in data_dict.items():
                    if key != "id":
                        setattr(existing, key, value)
            else:
                session.add(self.model(**data_dict))

    def update_item(self, item_id: int, update_data: dict) -> None:
        with self.session_scope() as session:
            session.query(self.model).filter_by(id=item_id).update(update_data)

    def delete_item(self, item_id: int) -> None:
        with self.session_scope() as session:
            session.query(self.model).filter_by(id=item_id).delete()
    
    def delete_by_external_id(self, external_id: str) -> None:
        with self.session_scope() as session:
            session.query(self.model).filter_by(external_id=external_id).delete()

    def parse_filters(self, filters: list | None, table_map: dict) -> Any | None:
        and_conditions = []
        or_conditions = []

        for f in filters or []:
            column, op, value = f["field"], f["op"], f["value"]
            
            col = None
            for table in table_map.values():
                if hasattr(table, column):
                    col = getattr(table, column)
                    break
            if col is None:
                continue

            condition = None
            if op == "=":
                condition = col == value
            elif op == "~":
                condition = col.ilike(f"%{value}%")
            elif op == ">":
                condition = col > value
            elif op == "<":
                condition = col < value
            elif op == ">=":
                condition = col >= value
            elif op == "<=":
                condition = col <= value
            elif op == "><" and isinstance(value, (tuple, list)) and len(value) == 2:
                condition = col.between(value[0], value[1])
            elif op == "@>":
                col_type = getattr(col, 'type', None)
                if isinstance(col_type, PG_ARRAY):
                    condition = col.any(value)
                else:
                    condition = col == value
            # elif op == "isnull":
            #     if value:
            #         condition = col == None  # 或 col.is_(None)
            #     else:
            #         condition = col != None

            if condition is not None:
                if op == "@>":
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
        
    def apply_filters(self, query: Any, filters: list | None, table_map: dict) -> Any:
        conditions = self.parse_filters(filters, table_map)
        return query.filter(conditions) if conditions is not None else query

    def apply_sort(self, query: Any, order_by: str | list[str] | None, table_map: dict) -> Any:
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

    def apply_select(self, query: Any, select_fields: list[str] | None, table_map: dict) -> Any:
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

    def apply_distinct(self, query: Any, distinct_fields: str | None) -> Any:
        if not distinct_fields:
            return query
        col = getattr(self.model, distinct_fields, None)
        if isinstance(col, InstrumentedAttribute):
            return query.with_entities(col.distinct())
        return query

    def apply_pagination(self, query: Any, limit: int | None = None, offset: int | None = None) -> Any:
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query
    
    def get_table_count(self, session: Any, filters: list | None = None, table_map: dict | None = None) -> int:
        count_query = session.query(func.count(self.model.id))

        if filters and table_map:
            count_query = self.apply_filters(count_query, filters, table_map)

        return count_query.scalar()
        
    def bm25_search(self, table_name: str, search_text: str, limit: int = 50) -> list[dict]:
        with self.session_scope() as session:
            safe_table = quoted_name(table_name, quote=True)
            query = text(f"""
                SELECT *, 
                    ts_rank_cd(
                        to_tsvector('simple', display_name), 
                        websearch_to_tsquery('simple', :search_text)
                    ) AS rank
                FROM {safe_table}
                WHERE to_tsvector('simple', display_name)
                    @@ websearch_to_tsquery('simple', :search_text)
                ORDER BY rank DESC
                LIMIT :limit
            """)
            results = session.execute(query, {'search_text': search_text, 'limit': limit}).fetchall()
            return [dict(row._mapping) for row in results]
        
    def close(self) -> None:
        if not self.db:
            dispose_shared_engine()