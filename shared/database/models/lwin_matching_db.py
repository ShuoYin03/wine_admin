from sqlalchemy import Column, Integer, Text, ARRAY, BigInteger, JSON, Float
from shared.database.models.base_db import Base

class LwinMatchingModel(Base):
    __tablename__ = 'lwin_matching'
    id = Column(Integer, primary_key=True)
    lot_id = Column(Integer)
    matched = Column(Text)
    lwin = Column(ARRAY(Integer))
    lwin_11 = Column(ARRAY(BigInteger))
    match_item = Column(JSON)
    match_score = Column(ARRAY(Float))