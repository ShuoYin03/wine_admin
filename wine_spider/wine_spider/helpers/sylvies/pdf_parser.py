import re
import PyPDF2
from io import BytesIO
from datetime import datetime

def parse_pdf(file):
    pdf_reader = PyPDF2.PdfReader(BytesIO(file))
    page = pdf_reader.pages[0]
    text = page.extract_text()
    
    text = text.replace("\n", " ")

    match = re.search(r"Auction catalogue: (.+?)(?=\d{1,2} \d{4}|\Z)", text)
    if not match:
        return {
            "start_date": None,
            "end_date": None,
        }

    catalogue_text = match.group(1)

    pattern = r"(\d{1,2}/\d{1,2}) at (\d{1,2}:\d{2}) CET(?: from lot (\d+))?"
    matches = re.findall(pattern, catalogue_text)
    if not matches:
        return {
            "start_date": None,
            "end_date": None,
        }

    current_year = datetime.now().year
    dates = []
    for date_str, _, _ in matches:
        try:
            day, month = map(int, date_str.split('/'))
            dt = datetime(current_year, month, day)
            dates.append(dt)
        except Exception:
            return {
                "start_date": None,
                "end_date": None,
            }

    if not dates:
        return {
            "start_date": None,
            "end_date": None,
        }

    start_date = min(dates).strftime('%Y-%m-%d')
    end_date = max(dates).strftime('%Y-%m-%d')

    return {
        "start_date": start_date,
        "end_date": end_date,
    }