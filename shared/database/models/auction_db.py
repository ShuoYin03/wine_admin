from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Text, Date
from shared.database.models.base_db import Base


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