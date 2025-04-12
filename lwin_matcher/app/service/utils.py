import re
import numpy as np
from rapidfuzz import fuzz
from rank_bm25 import BM25Okapi
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

class LwinMatchingUtils:
    def __init__(self, table_items):
        self.table_items = table_items
        cleaned_titles = table_items.apply(self.merge_text_fields, axis=1).apply(self.clean_title).tolist()
        self.tokenized_corpus = [self.generate_mixed_ngrams(doc.split()) for doc in cleaned_titles]

        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def generate_ngrams(self, tokens, n=3):
        return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]
    
    def generate_mixed_ngrams(self, tokens):
        ngrams = []
        ngrams += self.generate_ngrams(tokens, n=1)
        if len(tokens) >= 2:
            ngrams += self.generate_ngrams(tokens, n=2)
        if len(tokens) >= 3:
            ngrams += self.generate_ngrams(tokens, n=3)
        return ngrams

    def search_by_bm25(self, title, limit=20):
        if not title:
            return []
        title = self.clean_title(title)
        tokenized_query = self.generate_mixed_ngrams(title.split())

        scores = self.bm25.get_scores(tokenized_query)
        
        top_indices = np.argsort(scores)[::-1][:limit]

        matches = []
        for idx in top_indices:
            row = self.table_items.iloc[idx]
            score = scores[idx]
            matches.append((row, score))
        
        return matches

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
    
    def convert_to_serializable(self, obj):
        for i in range(len(obj)):
            if isinstance(obj[i], np.float64):
                obj[i] = float(obj[i])

        return obj