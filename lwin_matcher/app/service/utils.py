import re
import bm25s
import Stemmer
import numpy as np

class LwinMatchingUtils:
    def __init__(self, table_items):
        self.table_items = table_items
        self.corpus = table_items.apply(self.merge_text_fields, axis=1).apply(self.clean_title).tolist()
        self.stemmer = Stemmer.Stemmer("english")
        self.tokenized_corpus = bm25s.tokenize(self.corpus, stopwords="en", stemmer=self.stemmer)

        self.retriever = bm25s.BM25()
        self.retriever.index(self.tokenized_corpus)

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

        query_tokens = bm25s.tokenize([title], stopwords="en", stemmer=self.stemmer)

        results, scores = self.retriever.retrieve(query_tokens, k=limit)

        matches = []
        for idx, score in zip(results[0], scores[0]):
            row = self.table_items.iloc[idx]
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
            elif isinstance(obj[i], np.float32):
                obj[i] = float(obj[i])
            elif isinstance(obj[i], np.int64):
                obj[i] = int(obj[i])
            elif isinstance(obj[i], np.int32):
                obj[i] = int(obj[i])
        return obj