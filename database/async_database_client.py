import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData, func, and_
from sqlalchemy.dialects.postgresql import insert

load_dotenv()

class DatabaseClient:
    def __init__(self):
        self.engine = create_async_engine(
            os.getenv('DB_URL').replace("postgresql://", "postgresql+asyncpg://")
        )
        self.Session = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.metadata = MetaData()

    async def get_table(self, table_name):
        async with self.engine.begin() as conn:
            if table_name not in self.metadata.tables:
                await conn.run_sync(self.metadata.reflect)
            return self.metadata.tables[table_name]

    async def get_random_item(self, model_class):
        async with self.Session() as session:
            try:
                result = await session.execute(
                    model_class.select().order_by(func.random()).limit(1)
                )
                return result.scalar_one_or_none()
            except Exception as e:
                print(f"Error: {e}")
                return None

    async def insert_item(self, table_name, item_data):
        table = await self.get_table(table_name)
        async with self.Session() as session:
            try:
                insert_stmt = insert(table).values(**item_data)
                update_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=['id'],
                    set_={k: v for k, v in item_data.items()}
                )
                
                async with session.begin():
                    await session.execute(update_stmt)
                    await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"Error: {e}")

    async def query_items(self, table_name, filters=None, order_by=None, limit=None, offset=None):
        table = await self.get_table(table_name)
        async with self.Session() as session:
            try:
                query = table.select()

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
                        if order_by.startswith('-'):
                            query = query.order_by(getattr(table.c, order_by[1:]).desc())
                        else:
                            query = query.order_by(getattr(table.c, order_by))
                    elif isinstance(order_by, list):
                        order_clauses = [
                            getattr(table.c, field[1:]).desc() if field.startswith('-') else getattr(table.c, field)
                            for field in order_by
                        ]
                        query = query.order_by(*order_clauses)
                
                if offset:
                    query = query.offset(offset)
                if limit:
                    query = query.limit(limit)

                result = await session.execute(query)
                rows = result.fetchall()

                return [dict(row._mapping) for row in rows]

            except Exception as e:
                print(f"Error: {e}")
                return []

    async def close(self):
        await self.engine.dispose()
