from datetime import datetime

def parse_date(date_str):
    try:
        parsed_date = datetime.strptime(date_str, "%d %b %Y")
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Date parsing error: {e}")