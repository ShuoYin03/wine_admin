from sqlalchemy import Column, Integer, String, Float, Date
from shared.database.models.base_db import Base

class FxRatesModel(Base):
    __tablename__ = 'fx_rates_cache'
    id = Column(Integer, primary_key=True)
    rates_from = Column(String(10))
    rates_to = Column(String(10))
    date = Column(Date)
    rates = Column(Float)