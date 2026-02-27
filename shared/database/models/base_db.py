from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

class Base(AsyncAttrs, DeclarativeBase):
    def model_to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}