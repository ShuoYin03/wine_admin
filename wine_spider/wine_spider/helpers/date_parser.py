from wine_spider.exceptions import InvalidDateInputException
from datetime import datetime
import re

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
    
def month_to_quarter(month):
    month_dict = {
        "january": 1,
        "february": 1,
        "march": 1,
        "april": 2,
        "may": 2,
        "june": 2,
        "july": 3,
        "august": 3,
        "september": 3,
        "october": 4,
        "november": 4,
        "december": 4
    }

    if month.lower() in month_dict:
        return month_dict[month.lower()]
    
def extract_date(date_string):
    try:
        return datetime.strptime(date_string.split("T")[0], "%Y-%m-%d").date()
    except (AttributeError, ValueError):
        raise InvalidDateInputException(date_string)
    
def extract_year(date_string):
    if not date_string:
        return None

    pattern = r'(\d{4})(?:-(\d{4}))?'
    match = re.search(pattern, date_string)
    if match:
        return match.group(0)
    return None


