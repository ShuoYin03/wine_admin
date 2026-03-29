from sqlalchemy import Column, Integer, Text, ARRAY, BigInteger, JSON, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from shared.database.models.base_db import Base

class LwinMatchingModel(Base):
    __tablename__ = 'lwin_matching'
    __table_args__ = (UniqueConstraint('lot_item_id'),)

    id = Column(Integer, primary_key=True)
    lot_item_id = Column(Integer, ForeignKey('lot_items.id', ondelete='CASCADE'))
    matched = Column(Text)
    lwin = Column(ARRAY(Integer))
    lwin_11 = Column(ARRAY(BigInteger))
    match_item = Column(JSON)
    match_score = Column(ARRAY(Float))

    lot_item = relationship("LotItemModel", back_populates="lwin_matching")