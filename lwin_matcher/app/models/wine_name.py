import re
import unicodedata

class WineName:
    def __init__(self, raw: str):
        self.raw = raw or ""
        self.text = self.raw

    def __str__(self):
        return self.text

    def value(self):
        return self.text

    def reset(self):
        self.text = self.raw
        return self

    def lower(self):
        self.text = self.text.lower()
        return self

    def normalize_unicode(self):
        self.text = (
            unicodedata.normalize("NFKD", self.text)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        return self

    def remove_year(self):
        self.text = re.sub(r"\b(19|20)\d{2}\b", "", self.text)
        self.text = re.sub(
            r"\b(19|20)\d{2}\s*[-/]\s*(19|20)\d{2}\b", "", self.text
        )
        return self

    def remove_brackets(self):
        self.text = re.sub(r"\([^)]*\)", "", self.text)
        self.text = re.sub(r"\[[^\]]*\]", "", self.text)
        self.text = re.sub(r"\{[^}]*\}", "", self.text)
        return self

    def normalize_space(self):
        self.text = re.sub(r"\s+", " ", self.text).strip()
        return self
