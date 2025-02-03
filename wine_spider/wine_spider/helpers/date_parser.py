import re
from datetime import datetime
from exceptions import InvalidDateInputException

def parse_date(date_str):
    single_date_pattern = r'(\d{1,2}) (\w+) (\d{4})'
    range_date_pattern = r'(\d{1,2})-(\d{1,2}) (\w+) (\d{4})'
    multi_month_range_pattern = r'(\d{1,2}) (\w+)-(\d{1,2}) (\w+) (\d{4})'

    match = re.match(single_date_pattern, date_str)
    if match:
        day, month, year = match.groups()
        start_date = datetime.strptime(f'{day} {month} {year}', '%d %B %Y')
        return start_date, None

    match = re.match(range_date_pattern, date_str)
    if match:
        start_day, end_day, month, year = match.groups()
        start_date = datetime.strptime(f'{start_day} {month} {year}', '%d %B %Y')
        end_date = datetime.strptime(f'{end_day} {month} {year}', '%d %B %Y')
        return start_date, end_date

    match = re.match(multi_month_range_pattern, date_str)
    if match:
        start_day, start_month, end_day, end_month, year = match.groups()
        start_date = datetime.strptime(f'{start_day} {start_month} {year}', '%d %B %Y')
        end_date = datetime.strptime(f'{end_day} {end_month} {year}', '%d %B %Y')
        return start_date, end_date

    raise InvalidDateInputException(date_str)

def parse_quarter(month):
    if month in [1, 2, 3]:
        return 1
    elif month in [4, 5, 6]:
        return 2
    elif month in [7, 8, 9]:
        return 3
    else:
        return 4