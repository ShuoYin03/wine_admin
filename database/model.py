from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class AuctionModel(Base):
    __tablename__ = 'auctions'
    id = Column(Integer, primary_key=True)
    auction_id = Column(String)
    auction_name = Column(String)
    auction_date = Column(DateTime)
    auction_type = Column(String)
    auction_lot = Column(Integer)
    auction_currency = Column(String)
    auction_location = Column(String)
    auction_description = Column(Text)
    auction_url = Column(String)
    auction_image = Column(String)
    auction_wine = relationship("WineModel", back_populates="auction")

class AuctionSalesModel(Base):
    __tablename__ = 'auction_sales'
    id = Column(Integer, primary_key=True)
    auction_id = Column(Integer, ForeignKey('auctions.id'))
    auction = relationship("AuctionModel", back_populates="auction_sales")
    total_lots = Column(Integer)
    total_sales = Column(Float)
    total_value = Column(Float)
    total_volume = Column(Float)
    total_low_estimate = Column(Float)
    total_high_estimate = Column(Float)
    total_sold = Column(Float)
    top_lot = Column(String)
    sale_type = Column(String)
    single_cellar = Column(Boolean)
    ex_ch = Column(Boolean)

class LotModel(Base):
    __tablename__ = 'lots'
    id = Column(Integer, primary_key=True)
    auction_id = Column(Integer, ForeignKey('auctions.id'))
    auction = relationship("AuctionModel", back_populates="lots")
    lot_id = Column(String)
    lot_producer = Column(String)
    wine_name = Column(String)
    vintage = Column(Integer)
    unit_format = Column(String)
    unit = Column(Integer)
    volume = Column(Float)
    lot_type = Column(String)
    wine_type = Column(String)
    original_currency = Column(String)
    start_price = Column(Float)
    end_price = Column(Float)
    low_estimate = Column(Float)
    high_estimate = Column(Float)
    sold = Column(Boolean)
    region = Column(String)
    sub_region = Column(String)
    country = Column(String)
    success = Column(Boolean)
    url = Column(String)
    lot_image = Column(String)