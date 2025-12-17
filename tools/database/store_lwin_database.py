import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. 数据库连接配置
db_url = os.getenv('DB_URL')
engine = create_engine(db_url, echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# 2. SQLAlchemy ORM模型
class LwinDatabaseModel(Base):
    __tablename__ = 'lwin_database'
    id = Column(Integer, primary_key=True)
    lwin = Column(BigInteger)
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

csv_path = '../../files/LWINdatabase.xlsx'
df = pd.read_excel(csv_path, header=0)

def clean_numeric_value(val):
    """彻底清理数值，确保nan转换为None"""
    if val is None:
        return None
    if pd.isna(val) or pd.isnull(val):
        return None
    if isinstance(val, str):
        val = val.strip()
        if val == '' or val.lower() == 'nan':
            return None
    try:
        # 先转换为float检查是否为有效数字
        float_val = float(val)
        if np.isnan(float_val) or np.isinf(float_val):
            return None
        return int(float_val)
    except (ValueError, TypeError, OverflowError):
        return None

def clean_string_value(val):
    """清理字符串值"""
    if val is None or pd.isna(val) or pd.isnull(val):
        return None
    if isinstance(val, str):
        val = val.strip()
        if val == '' or val.lower() == 'nan':
            return None
        return val
    return str(val).strip() if str(val).strip() else None

def clean_date_value(val):
    """清理日期值"""
    if val is None or pd.isna(val) or pd.isnull(val):
        return None
    try:
        if isinstance(val, str) and val.strip() == '':
            return None
        return pd.to_datetime(val, errors='coerce')
    except:
        return None

print("Starting data cleaning...")

# 彻底清理数值列
numeric_columns = ['LWIN', 'FIRST_VINTAGE', 'FINAL_VINTAGE']
for col in numeric_columns:
    if col in df.columns:
        print(f"Cleaning numeric column: {col}")
        df[col] = df[col].apply(clean_numeric_value)

# 清理字符串列
string_columns = ['STATUS', 'DISPLAY_NAME', 'PRODUCER_TITLE', 'PRODUCER_NAME', 
                 'WINE', 'COUNTRY', 'REGION', 'SUB_REGION', 'SITE', 'PARCEL', 
                 'COLOUR', 'TYPE', 'SUB_TYPE', 'DESIGNATION', 'CLASSIFICATION', 
                 'VINTAGE_CONFIG', 'REFERENCE']

for col in string_columns:
    if col in df.columns:
        print(f"Cleaning string column: {col}")
        df[col] = df[col].apply(clean_string_value)

# 清理日期列
date_columns = ['DATE_ADDED', 'DATE_UPDATED']
for col in date_columns:
    if col in df.columns:
        print(f"Cleaning date column: {col}")
        df[col] = df[col].apply(clean_date_value)

# 最后一步：将剩余的nan值替换为None
df = df.replace([np.nan, pd.NaT], None)

print("Data cleaning completed. Creating objects...")

# 验证数据完整性并创建对象
objects = []
error_count = 0

for index, row in df.iterrows():
    try:
        # 额外验证关键字段
        lwin_val = row.get('LWIN')
        print(f"Processing row {index} with LWIN: {lwin_val}")
        first_vintage_val = row.get('FIRST_VINTAGE')
        final_vintage_val = row.get('FINAL_VINTAGE')
        
        # 确保没有nan值传递给数据库
        if pd.isna(lwin_val):
            lwin_val = None
        if pd.isna(first_vintage_val):
            first_vintage_val = None
        if pd.isna(final_vintage_val):
            final_vintage_val = None
            
        # 验证并转换数据类型
        if lwin_val is not None:
            print("I am here")
            try:
                if isinstance(lwin_val, float) and lwin_val.is_integer():
                    print("LWIN:", lwin_val, type(lwin_val))
                    lwin_val = int(lwin_val)
                    print("Converted LWIN:", lwin_val, type(lwin_val))
                elif not isinstance(lwin_val, int):
                    print(f"Warning: LWIN value {lwin_val} cannot be converted to int, skipping row {index}")
                    error_count += 1
                    continue
            except:
                print(f"Warning: LWIN value {lwin_val} is invalid, skipping row {index}")
                error_count += 1
                continue
            
        if first_vintage_val is not None:
            try:
                if isinstance(first_vintage_val, float) and first_vintage_val.is_integer():
                    first_vintage_val = int(first_vintage_val)
                elif not isinstance(first_vintage_val, int):
                    print(f"Warning: FIRST_VINTAGE value {first_vintage_val} cannot be converted to int, skipping row {index}")
                    error_count += 1
                    continue
            except:
                print(f"Warning: FIRST_VINTAGE value {first_vintage_val} is invalid, skipping row {index}")
                error_count += 1
                continue
            
        if final_vintage_val is not None:
            try:
                if isinstance(final_vintage_val, float) and final_vintage_val.is_integer():
                    final_vintage_val = int(final_vintage_val)
                elif not isinstance(final_vintage_val, int):
                    print(f"Warning: FINAL_VINTAGE value {final_vintage_val} cannot be converted to int, skipping row {index}")
                    error_count += 1
                    continue
            except:
                print(f"Warning: FINAL_VINTAGE value {final_vintage_val} is invalid, skipping row {index}")
                error_count += 1
                continue
        
        obj = LwinDatabaseModel(
            id=index,
            lwin=lwin_val,
            status=row.get('STATUS'),
            display_name=row.get('DISPLAY_NAME'),
            producer_title=row.get('PRODUCER_TITLE'),
            producer_name=row.get('PRODUCER_NAME'),
            wine=row.get('WINE'),
            country=row.get('COUNTRY'),
            region=row.get('REGION'),
            sub_region=row.get('SUB_REGION'),
            site=row.get('SITE'),
            parcel=row.get('PARCEL'),
            colour=row.get('COLOUR'),
            type=row.get('TYPE'),
            sub_type=row.get('SUB_TYPE'),
            designation=row.get('DESIGNATION'),
            classification=row.get('CLASSIFICATION'),
            vintage_config=row.get('VINTAGE_CONFIG'),
            first_vintage=first_vintage_val,
            final_vintage=final_vintage_val,
            date_added=row.get('DATE_ADDED'),
            date_updated=row.get('DATE_UPDATED'),
            reference=row.get('REFERENCE')
        )
        objects.append(obj)
        
    except Exception as e:
        error_count += 1
        print(f"Error processing row {index} (LWIN: {row.get('LWIN', 'unknown')}): {e}")
        continue

print(f"Processed {len(objects)} records for insertion")
print(f"Encountered {error_count} errors during processing")

# 批量插入数据
session = Session()
try:
    # 先测试插入一条记录
    if objects:
        print("Testing with first record...")
        test_obj = objects[0]
        session.add(test_obj)
        session.commit()
        print("Test record inserted successfully")
        
        # 移除已插入的测试记录
        objects = objects[1:]
    
    # 分批处理剩余记录
    batch_size = 500  # 减小批次大小
    total_inserted = 1  # 包含测试记录
    
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i+batch_size]
        
        # 额外验证批次中的每个对象
        clean_batch = []
        for obj in batch:
            # 最后一次检查nan值
            if (hasattr(obj, 'first_vintage') and pd.isna(obj.first_vintage)):
                obj.first_vintage = None
            if (hasattr(obj, 'final_vintage') and pd.isna(obj.final_vintage)):
                obj.final_vintage = None
            if (hasattr(obj, 'lwin') and pd.isna(obj.lwin)):
                obj.lwin = None
            clean_batch.append(obj)
        
        session.bulk_save_objects(clean_batch)
        session.commit()
        total_inserted += len(clean_batch)
        print(f"Inserted batch {i//batch_size + 1} ({len(clean_batch)} records). Total: {total_inserted}")
    
    print(f"All data inserted successfully! Total records: {total_inserted}")
    
except Exception as e:
    session.rollback()
    print("Error occurred:", e)
    print("Detailed error:")
    import traceback
    traceback.print_exc()
    
    # 尝试单条插入来定位问题
    print("\nTrying to identify problematic record...")
    if objects:
        for i, obj in enumerate(objects[:10]):  # 检查前10条记录
            try:
                session.add(obj)
                session.commit()
                print(f"Record {i} inserted successfully")
            except Exception as single_error:
                session.rollback()
                print(f"Record {i} failed: {single_error}")
                print(f"Object data: lwin={obj.lwin}, first_vintage={obj.first_vintage}, final_vintage={obj.final_vintage}")
finally:
    session.close()