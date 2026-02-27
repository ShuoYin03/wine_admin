from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Text
from shared.database.models.base_db import Base

class LotItemModel(Base):
    __tablename__ = 'lot_items'
    id = Column(Integer, primary_key=True)
    lot_id = Column(Text, ForeignKey('lots.external_id', ondelete="CASCADE"))
    lot_producer = Column(String(100))
    vintage = Column(String(20))
    unit_format = Column(String(100))
    wine_colour = Column(String(50))

    lot = relationship("LotModel", back_populates="items")