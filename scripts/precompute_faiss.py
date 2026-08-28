#!/usr/bin/env python3
"""
Precompute FAISS Index.

Encodes the MedDRA dictionary into 768-dimensional SapBERT embeddings,
applies L2 normalization, and builds a FAISS Inner Product index.
"""

import pandas as pd
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path

def main():
    dict_path = Path("data/processed/tac_meddra_dict.parquet")
    index_path = Path("data/processed/faiss.index")
    model_name = "models/sapbert_onnx_quantized"
    
    if not dict_path.exists():
        print(f"Dictionary not found at {dict_path}. Run preprocessing first.")
        return

    print("Loading MedDRA dictionary...")
    df = pd.read_parquet(dict_path)
    terms = df["reaction_str"].tolist()
    
    print(f"Loading SapBERT from {model_name}...")
    model = SentenceTransformer(model_name)
    
    print(f"Encoding {len(terms)} terms...")
    embeddings = model.encode(terms, batch_size=32, show_progress_bar=True, normalize_embeddings=True)
    
    print("Building FAISS index...")
    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)
    index.add(np.ascontiguousarray(embeddings))
    
    print(f"Saving index to {index_path}...")
    faiss.write_index(index, str(index_path))
    print("Done.")

if __name__ == "__main__":
    main()
