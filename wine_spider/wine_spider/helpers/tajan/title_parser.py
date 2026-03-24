from wine_spider.helpers.date_parser import extract_years_from_text


def extract_years(text: str) -> list[int]:
    return extract_years_from_text(text, min_year=1500)
