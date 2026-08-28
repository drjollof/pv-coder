#!/usr/bin/env python3
"""
Normalization Evaluation Script.

Evaluates the HybridRetriever against TAC 2017 raw mentions to see if it predicts
the correct MedDRA PT ID.
"""

import pandas as pd
from pathlib import Path
from src.normalization.embeddings import SemanticNormalizer

def main():
    mentions_path = Path("data/processed/tac_mentions.parquet")
    dict_path = Path("data/processed/tac_meddra_dict.parquet")
    index_path = Path("data/processed/faiss.index")
    
    if not mentions_path.exists() or not dict_path.exists() or not index_path.exists():
        print("Required processed data not found. Run preprocessing and precompute_faiss first.")
        return

    df = pd.read_parquet(mentions_path)
    reactions = pd.pd.read_parquet("data/processed/tac_reactions.parquet")
    
    print(f"Loading SemanticNormalizer...")
    dictionary = pd.read_parquet(dict_path)
    semantic = SemanticNormalizer(dictionary, faiss_index_path=str(index_path))
    
    correct_top1 = 0
    correct_top3 = 0
    total = min(100, len(reactions)) 
    
    print(f"Evaluating {total} reactions...")
    for idx, row in reactions.head(total).iterrows():
        raw_str = row["reaction_str"]
        gold_id = row["meddra_pt_id"]
        
        if not gold_id:
            continue
            
        results, _ = semantic.match(raw_str, top_k=3)
        if not results:
            continue
            
        pred_ids = [res[1] for res in results]
        if pred_ids[0] == gold_id:
            correct_top1 += 1
        if gold_id in pred_ids:
            correct_top3 += 1
            
    print(f"Top-1 Accuracy: {correct_top1/total:.4f}")
    print(f"Top-3 Accuracy: {correct_top3/total:.4f}")

if __name__ == "__main__":
    main()
