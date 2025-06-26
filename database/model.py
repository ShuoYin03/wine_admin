from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Float, Boolean, Date, Text, ARRAY, JSON, DateTime, BigInteger

class Base(AsyncAttrs, DeclarativeBase):
    def model_to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class AuctionModel(Base):
    __tablename__ = 'auctions'
    id = Column(Integer, primary_key=True)
    external_id = Column(Text, unique=True)
    auction_title = Column(String(255))
    auction_house = Column(String(255))
    city = Column(String(100))
    continent = Column(String(100))
    start_date = Column(Date)
    end_date = Column(Date)
    year = Column(Integer)
    quarter = Column(Integer)
    auction_type = Column(String(50))
    url = Column(Text)

    lots = relationship("LotModel", back_populates="auction")
    auction_sales = relationship("AuctionSalesModel", back_populates="auction", uselist=False)

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
    lwin = relationship("LwinMatchingModel", back_populates="lot", uselist=False)

class LotItemModel(Base):
    __tablename__ = 'lot_items'
    id = Column(Integer, primary_key=True)
    lot_id = Column(Text, ForeignKey('lots.external_id', ondelete="CASCADE"))
    lot_producer = Column(String(100))
    vintage = Column(String(20))
    unit_format = Column(String(100))
    wine_colour = Column(String(50))

    lot = relationship("LotModel", back_populates="items")

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

class LwinDatabaseModel(Base):
    __tablename__ = 'lwin_database'
    id = Column(Integer, primary_key=True)
    lwin = Column(Integer)
    status = Column(Text)
    display_name = Column(Text)
    producer_title = Column(Text)
    producer_name = Column(Text)
    wine = Column(Text)
    country = Column(Text)
    region = Column(Text)
    sub_region = Column(Text)
    site = Column(Text)
    parcel = Column(Text)
    colour = Column(Text)
    type = Column(Text)
    sub_type = Column(Text)
    designation = Column(Text)
    classification = Column(Text)
    vintage_config = Column(Text)
    first_vintage = Column(Integer)
    final_vintage = Column(Integer)
    date_added = Column(DateTime)
    date_updated = Column(DateTime)
    reference = Column(Text)

class LwinMatchingModel(Base):
    __tablename__ = 'lwin_matching'
    id = Column(Integer, primary_key=True)
    lot_id = Column(Text, ForeignKey('lots.external_id', ondelete="CASCADE"))
    matched = Column(Text)
    lwin = Column(ARRAY(Integer))
    lwin_11 = Column(ARRAY(BigInteger))
    match_item = Column(JSON)
    match_score = Column(ARRAY(Float))

    lot = relationship("LotModel", back_populates="lwin")

class FxRatesModel(Base):
    __tablename__ = 'fx_rates_cache'
    id = Column(Integer, primary_key=True)
    rates_from = Column(String(10))
    rates_to = Column(String(10))
    rates = Column(Float)