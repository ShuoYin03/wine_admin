from wine_spider.exceptions import InvalidDateInputException
from datetime import datetime

def parse_quarter(month):
    if month in [1, 2, 3]:
        return 1
    elif month in [4, 5, 6]:
        return 2
    elif month in [7, 8, 9]:
        return 3
    elif month in [10, 11, 12]:
        return 4
    else:
        raise InvalidDateInputException(month) 
    
def extract_date(date_string):
    try:
        return datetime.strptime(date_string.split("T")[0], "%Y-%m-%d").date()
    except (AttributeError, ValueError):
        raise InvalidDateInputException(date_string)