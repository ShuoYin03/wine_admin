import re
import unicodedata

def generate_external_id(title: str) -> str:
    title = title.lower()
    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
    title = re.sub(r'\s*[\-&xX]+\s*', ' ', title)
    title = re.sub(r'[^a-z0-9\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    slug = title.replace(' ', '-')
    return slug