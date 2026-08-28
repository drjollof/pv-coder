#!/usr/bin/env python3
"""
Extraction Evaluation Script.

Evaluates the NER model's ability to extract Drugs and Diseases from the PHEE dataset.
"""

import pandas as pd
from pathlib import Path
from src.extraction.entities import ExtractionPipeline

def spans_overlap(span1: str, span2: str) -> bool:
    if not span1 or not span2:
        return False
    s1 = set(span1.lower().split())
    s2 = set(span2.lower().split())
    return len(s1.intersection(s2)) > 0

def main():
    phee_path = Path("data/processed/phee_events.parquet")
    if not phee_path.exists():
        print("PHEE parquet not found.")
        return
        
    df = pd.read_parquet(phee_path)
    df = df[df["split"] == "dev"]
    print(f"Evaluating {len(df)} dev records...")
    
    pipeline = ExtractionPipeline()
    
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    
    for idx, row in df.iterrows():
        text = str(row["text"])
        gold_drug = row.get("drug_text_primary")
        gold_effect = row.get("effect_text")
        
        result = pipeline.extract(text)
        pred_drugs = [d.text for d in result.drugs]
        pred_effects = [e.text for e in result.diseases]
        
        if gold_drug:
            if any(spans_overlap(gold_drug, pdrug) for pdrug in pred_drugs):
                true_positives += 1
            else:
                false_negatives += 1
                
        if gold_effect:
            if any(spans_overlap(gold_effect, peffect) for peffect in pred_effects):
                true_positives += 1
            else:
                false_negatives += 1
                
        false_positives += len(pred_drugs) + len(pred_effects) - 2
        
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")

if __name__ == "__main__":
    main()
