from datetime import datetime

def extract_month_year_and_format(date_str: str) -> tuple[int, int, str]:
    dt = datetime.strptime(date_str, "%A, %B %d, %Y")
    month = dt.month
    year = dt.year
    formatted = dt.strftime("%Y-%m-%d")
    return month, year, formatted