import pandas as pd
from typing import List, Tuple, Dict
from src.normalization.lexical import LexicalNormalizer
from src.normalization.embeddings import SemanticNormalizer

class HybridRetriever:
    def __init__(self, lexical: LexicalNormalizer, semantic: SemanticNormalizer, use_fuzzywuzzy: bool = False):
        self.lexical = lexical
        self.semantic = semantic
        self.use_fuzzywuzzy = use_fuzzywuzzy
        
    def retrieve(self, query: str, top_k: int = 5) -> List[Tuple[str, str, float]]:
        """
        Retrieves the best MedDRA matches using a hybrid of lexical and semantic search.
        It uses a simple fusion approach: it tracks the max score across both 
        retrievers for each concept.
        Returns a list of tuples: (meddra_pt, meddra_pt_id, score)
        """
        if not query:
            return []
            
        exact = self.lexical.match_exact(query)
        if exact:
            return exact
            
        if self.use_fuzzywuzzy:
            lex_results = self.lexical.match_fuzzywuzzy(query, top_k=top_k)
        else:
            lex_results = self.lexical.match_tfidf(query, top_k=top_k)
            
        sem_results = self.semantic.match(query, top_k=top_k)
        
        combined_scores: Dict[str, Tuple[str, float]] = {} # id -> (pt, max_score)
        
        for pt, pt_id, score in lex_results:
            combined_scores[pt_id] = (pt, score)
            
        for pt, pt_id, score in sem_results:
            if pt_id in combined_scores:
                combined_scores[pt_id] = (pt, max(combined_scores[pt_id][1], score))
            else:
                combined_scores[pt_id] = (pt, score)
                
        sorted_results = sorted(
            [(pt, pt_id, score) for pt_id, (pt, score) in combined_scores.items()],
            key=lambda x: x[2],
            reverse=True
        )
        
        return sorted_results[:top_k]
