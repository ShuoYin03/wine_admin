from sqlalchemy import Column, Integer, Text, DateTime
from shared.database.models.base_db import Base

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
