from sqlalchemy.orm import relationship
from sqlalchemy import ARRAY, Column, Float, Integer, String, ForeignKey, Text, Date, Boolean
from shared.database.models.base_db import Base

class LotModel(Base):
    __tablename__ = 'lots'
    id = Column(Integer, primary_key=True)
    external_id = Column(Text, unique=True)
    auction_id = Column(Text, ForeignKey('auctions.external_id', ondelete="CASCADE"))
    lot_name = Column(Text)
    lot_type = Column(ARRAY(String(100)))
    volume = Column(Float)
    unit = Column(Integer)
    original_currency = Column(String(10))
    start_price = Column(Integer)
    end_price = Column(Float)
    low_estimate = Column(Integer)
    high_estimate = Column(Integer)
    sold = Column(Boolean)
    sold_date = Column(Date)
    region = Column(String(100))
    sub_region = Column(String(100))
    country = Column(String(50))
    success = Column(Boolean)
    url = Column(Text)

    auction = relationship("AuctionModel", back_populates="lots")
    items = relationship("LotItemModel", back_populates="lot")
    # lwin = relationship("LwinMatchingModel", back_populates="lot", uselist=False)