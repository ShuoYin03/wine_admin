import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime

db_url = os.getenv('DB_URL')
engine = create_engine(db_url, echo=True)
session = sessionmaker(bind=engine)
Base = declarative_base()
session = session()

class LwinDatabaseModel(Base):
    __tablename__ = 'lwin_database'
    id = Column(Integer, primary_key=True)
    lwin = Column(String, unique=True)
    status = Column(String)
    display_name = Column(String)
    producer_title = Column(String)
    producer_name = Column(String)
    wine = Column(String)
    country = Column(String)
    region = Column(String)
    sub_region = Column(String)
    site = Column(String)
    parcel = Column(String)
    colour = Column(String)
    type = Column(String)
    sub_type = Column(String)
    designation = Column(String)
    classification = Column(String)
    vintage_config = Column(String)
    first_vintage = Column(Integer)
    final_vintage = Column(Integer)
    date_added = Column(DateTime)
    date_updated = Column(DateTime)
    reference = Column(String)

csv_path = '../files/LWINdatabase.csv'
df = pd.read_csv(csv_path, header=0)

for index, row in df.iterrows():

    row = row.where(pd.notnull(row), None)
    lwin = LwinDatabaseModel(
        lwin=row['LWIN'],
        status=row['STATUS'],
        display_name=row['DISPLAY_NAME'],
        producer_title=row['PRODUCER_TITLE'],
        producer_name=row['PRODUCER_NAME'],
        wine=row['WINE'],
        country=row['COUNTRY'],
        region=row['REGION'],
        sub_region=row['SUB_REGION'],
        site=row['SITE'],
        parcel=row['PARCEL'],
        colour=row['COLOUR'],
        type=row['TYPE'],
        sub_type=row['SUB_TYPE'],
        designation=row['DESIGNATION'],
        classification=row['CLASSIFICATION'],
        vintage_config=row['VINTAGE_CONFIG'],
        first_vintage=row['FIRST_VINTAGE'],
        final_vintage=row['FINAL_VINTAGE'],
        date_added=row['DATE_ADDED'],
        date_updated=row['DATE_UPDATED'],
        reference=row['REFERENCE']
    )
    session.add(lwin)
    session.commit()

session.close()



    