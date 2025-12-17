from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float, Boolean
from shared.database.models.base_db import Base

class AuctionSalesModel(Base):
    __tablename__ = 'auction_sales'
    id = Column(Integer, primary_key=True)
    auction_id = Column(Text, ForeignKey('auctions.external_id', ondelete="CASCADE"), unique=True)
    lots = Column(Integer)
    sold = Column(Integer)
    currency = Column(String(10))
    total_low_estimate = Column(Integer)
    total_high_estimate = Column(Integer)
    total_sales = Column(Integer)
    volume_sold = Column(Float)
    value_sold = Column(Float)
    top_lot = Column(Text)
    sale_type = Column(String(50))
    single_cellar = Column(Boolean)
    ex_ch = Column(Boolean)

    auction = relationship("AuctionModel", back_populates="auction_sales")