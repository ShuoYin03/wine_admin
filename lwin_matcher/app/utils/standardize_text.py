import re

def standardize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[-‐-‒–—―]', ' ', text)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text