import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple
from sklearn.metrics.pairwise import cosine_similarity
import faiss


class SemanticNormalizer:
    def __init__(self, dictionary_df: pd.DataFrame, faiss_index_path: str = None, model_name: str = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext"):
        """
        Initializes the semantic normalizer with a MedDRA dictionary.
        dictionary_df must contain 'meddra_pt_id' and 'meddra_pt'.
        If faiss_index_path is provided, it loads the precomputed index instead of encoding on startup.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence_transformers is required for semantic normalization. "
                "Install with: pip install sentence-transformers"
            ) from exc
            
        self.dict_df = dictionary_df.copy()
        self.dict_texts = self.dict_df['meddra_pt'].str.lower().tolist()
        
        _ROOT = Path(__file__).parent.parent.parent
        onnx_dir = _ROOT / "models" / "sapbert_onnx_quantized"
        if onnx_dir.exists():
            print(f"Loading optimized ONNX SapBERT model from {onnx_dir}...", flush=True)
            
            import onnxruntime as ort
            session_options = ort.SessionOptions()
            session_options.intra_op_num_threads = 1
            session_options.inter_op_num_threads = 1
            
            self.model = SentenceTransformer(
                str(onnx_dir), 
                backend="onnx",
                model_kwargs={
                    "provider": "CPUExecutionProvider",
                    "session_options": session_options
                }
            )
        else:
            print(f"Loading native PyTorch SapBERT model: {model_name}...", flush=True)
            self.model = SentenceTransformer(model_name)
            
        self.faiss_index = None
        
        if faiss_index_path and Path(faiss_index_path).exists():
            print(f"Loading FAISS index from {faiss_index_path}...", flush=True)
            self.faiss_index = faiss.read_index(str(faiss_index_path))
        else:
            print("Encoding dictionary dynamically (slow)...", flush=True)
            self.dict_embeddings = self.model.encode(self.dict_texts, show_progress_bar=False, convert_to_numpy=True)
            faiss.normalize_L2(self.dict_embeddings)
            self.faiss_index = faiss.IndexFlatIP(self.dict_embeddings.shape[1])
            self.faiss_index.add(self.dict_embeddings)
        
    def match(self, query: str, top_k: int = 3, threshold: float = 0.70, margin: float = 0.05) -> Tuple[List[Tuple[str, str, float]], str]:
        """
        Dense semantic retrieval using FAISS. 
        Returns Top-K results and a review status ("Auto-coded" or "Human Review").
        """
        if not query:
            return [], "Human Review"
            
        # Encode the query and normalize
        query_embedding = self.model.encode([query.lower()], show_progress_bar=False, convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        # Search FAISS index
        scores, indices = self.faiss_index.search(query_embedding, top_k)
        scores = scores[0]
        indices = indices[0]
        
        results = []
        for i in range(len(indices)):
            idx = indices[i]
            score = float(scores[i])
            if score > 0.0:  # Minimum safety check
                row = self.dict_df.iloc[idx]
                results.append((row['meddra_pt'], row['meddra_pt_id'], score))
                
        # Margin Logic
        status = "Human Review"
        if len(results) > 0:
            top_1_score = results[0][2]
            if len(results) > 1:
                top_2_score = results[1][2]
                score_margin = top_1_score - top_2_score
                if top_1_score >= threshold and score_margin >= margin:
                    status = "Auto-coded"
            else:
                if top_1_score >= threshold:
                    status = "Auto-coded"
                
        return results, status
