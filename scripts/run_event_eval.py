#!/usr/bin/env python3
"""
Event-Level Evaluation Script.

Evaluates the full PharmacovigilanceEvent reconstruction pipeline against the PHEE dev set.
"""

import pandas as pd
from pathlib import Path
from src.extraction.entities import ExtractionPipeline
from src.extraction.events import EventBuilder

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
    
    pipeline = ExtractionPipeline()
    builder = EventBuilder()
    
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    
    print(f"Evaluating {len(df)} dev records for event reconstruction...")
    
    for idx, row in df.iterrows():
        text = str(row["text"])
        gold_drug = row.get("drug_text_primary")
        gold_effect = row.get("effect_text")
        
        result = pipeline.extract(text)
        events = builder.build(result, text)
        
        matched = False
        if gold_drug and gold_effect:
            for ev in events:
                eff_overlap = spans_overlap(gold_effect, ev.effect.text)
                drug_overlap = any(spans_overlap(gold_drug, d.text) for d in ev.drugs)
                if eff_overlap and drug_overlap:
                    matched = True
                    break
                    
            if matched:
                true_positives += 1
            else:
                false_negatives += 1
                
        false_positives += len(events) - (1 if matched else 0)
        
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")

if __name__ == "__main__":
    main()
