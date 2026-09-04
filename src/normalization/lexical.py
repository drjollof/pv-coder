import pandas as pd
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from thefuzz import fuzz

class LexicalNormalizer:
    def __init__(self, dictionary_df: pd.DataFrame):
        """
        Initializes the lexical normalizer with a MedDRA dictionary.
        dictionary_df must contain 'meddra_pt_id' and 'meddra_pt'.

        Precompute exact match dictionary (lowercase)

        Precompute TF-IDF matrix for the dictionary
        We use character n-grams (3-5) to capture spelling variations
        """
        self.dict_df = dictionary_df.copy()
        
        
        self.exact_dict = {
            row['meddra_pt'].lower(): (row['meddra_pt_id'], row['meddra_pt'])
            for _, row in self.dict_df.iterrows()
        }
        
        
        self.vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5))
        self.dict_texts = self.dict_df['meddra_pt'].str.lower().tolist()
        self.tfidf_matrix = self.vectorizer.fit_transform(self.dict_texts)
        
    def match_exact(self, query: str) -> List[Tuple[str, str, float]]:
        """Exact case-insensitive match."""
        if not query:
            return []
        match = self.exact_dict.get(query.lower())
        if match:
            return [(match[1], match[0], 1.0)] # PT, ID, score
        return []
        
    def match_tfidf(self, query: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
        """TF-IDF character n-gram cosine similarity."""
        if not query:
            return []
            
        query_vec = self.vectorizer.transform([query.lower()])
        cos_sim = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get top K indices
        top_indices = cos_sim.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            score = cos_sim[idx]
            
            # Threshold to filter noise
            if score > 0.1: 
                row = self.dict_df.iloc[idx]
                results.append((row['meddra_pt'], row['meddra_pt_id'], score))
        return results
        
    def match_fuzzywuzzy(self, query: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
        """Levenshtein distance based fuzzy matching.
        
        token_sort_ratio handles multi-word variations well
        
        Sort by score descending
        """
        if not query:
            return []
            
        scores = []
        q = query.lower()
        for idx, text in enumerate(self.dict_texts):
            
            score = fuzz.token_sort_ratio(q, text) / 100.0
            if score > 0.5:
                scores.append((idx, score))
                
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for idx, score in scores[:top_k]:
            row = self.dict_df.iloc[idx]
            results.append((row['meddra_pt'], row['meddra_pt_id'], score))
        return results
