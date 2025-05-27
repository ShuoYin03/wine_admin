# extract the info from excel file
import pandas as pd
import os

def extract_excel_data(file_path):
    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    # Read the Excel file
    df = pd.read_excel(file_path, sheet_name='Sheet1', engine='xlrd', header=2)
    
    row_num = 0
    size = set()
    for index, row in df.iterrows():
        # row_num += 1
        
        # unit = row.get("Qty")
        # volume = row.get("Size")
        # lot_name = row.get("Lot Title")
        # vintage = row.get("Vintage")
        # lot_producer = row.get("Producer")
        # country = row.get("Country")
        # region = row.get("Region")
        # low_estimate = row.get("Low Estimate")
        # high_estimate = row.get("High Estimate")
        # url = row.get("URL")

        # # Print all data
        # print(f"Row {row_num}:")
        # print(f"  Unit: {unit}")
        # print(f"  Volume: {volume}")
        # print(f"  Lot Name: {lot_name}")
        # print(f"  Vintage: {vintage}")
        # print(f"  Lot Producer: {lot_producer}")
        # print(f"  Country: {country}")
        # print(f"  Region: {region}")
        # print(f"  Low Estimate: {low_estimate}")
        # print(f"  High Estimate: {high_estimate}")
        # print(f"  URL: {url}")
        # print("-" * 40)
        # break
        #get all unique sizes
        size.add(row.get("Size", "").strip())
        

    # print(f"Total rows in the sheet: {row_num}")
    print(size)

if __name__ == "__main__":
    # Path to the Excel file
    file_path = "spirits_auction.xls"
    
    # Extract data from the Excel file
    extract_excel_data(file_path)