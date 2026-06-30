import re
import PyPDF2
from io import BytesIO
from datetime import datetime

def normalize_pdf_text(text: str | None) -> str:
    text = (text or "").replace("\x00", "")
    return re.sub(r"\s+", " ", text).strip()


def parse_pdf_dates_from_text(text: str | None, default_year: int | str | None = None):
    text = normalize_pdf_text(text)
    if not text:
        return {
            "start_date": None,
            "end_date": None,
        }

    lower_text = text.lower()
    catalogue_index = lower_text.find("auction catalogue")
    if catalogue_index >= 0:
        header_text = text[max(0, catalogue_index - 100):catalogue_index + 600]
    else:
        header_text = text[:700]

    dates = []
    for day, month, year in re.findall(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", header_text):
        try:
            dates.append(datetime(int(year), int(month), int(day)))
        except ValueError:
            continue

    if not dates:
        year = None
        if default_year:
            try:
                year = int(default_year)
            except (TypeError, ValueError):
                year = None

        if year is None:
            year_match = re.search(r"\b(20\d{2}|19\d{2})\b", header_text)
            year = int(year_match.group(1)) if year_match else datetime.now().year

        short_date_matches = re.findall(
            r"\b(\d{1,2})/(\d{1,2})\b\s+(?:at|a|à)\s+\d{1,2}[:h]\d{2}",
            header_text,
            flags=re.IGNORECASE,
        )
        for day, month in short_date_matches:
            try:
                dates.append(datetime(year, int(month), int(day)))
            except ValueError:
                continue

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


def parse_pdf(file, default_year: int | str | None = None):
    pdf_reader = PyPDF2.PdfReader(BytesIO(file))
    page = pdf_reader.pages[0]
    text = page.extract_text()

    return parse_pdf_dates_from_text(text, default_year=default_year)
