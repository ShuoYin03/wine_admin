import re
from rapidfuzz import fuzz
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

class LwinMatchingUtils:
    def __init__(self, table_columns):
        self.vectorizer = TfidfVectorizer()
        cleaned_titles = table_columns.apply(self.merge_text_fields, axis=1).apply(self.clean_title).tolist()
        self.tfidf_matrix = self.vectorizer.fit_transform(cleaned_titles)

    def clean_title(self, title):
        if not title:
            return ''
        title = re.sub(r'\s*\(.*?\)\s*$', '', title)
        title = re.sub(r'\b\d{4}\b', '', title)
        title = re.sub(r'[^\w\s]', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        title = title.lower().strip()
        return title
    
    def merge_text_fields(self, row):
        display = row['display_name'] or ''
        producer_title = row['producer_title'] or ''
        producer_name = row['producer_name'] or ''
        wine = row['wine'] or ''
        
        full_text = f"{display} {producer_title} {producer_name} {wine}"
        return full_text

    def calculate_tfidf_similarity(self, title):
        title = self.clean_title(title)
        title_vector = self.vectorizer.transform([title])
        similarities = cosine_similarity(title_vector, self.tfidf_matrix).flatten()
        return similarities

    def fuzzy_score(self, title, target):
        if isinstance(target, str):
            return fuzz.token_set_ratio(self.clean_title(title), self.clean_title(target))
        return 0