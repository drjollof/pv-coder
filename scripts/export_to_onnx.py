#!/usr/bin/env python3
"""
Export Models to ONNX format.

Exports the NER model and SapBERT to ONNX format for faster CPU inference.
"""

from optimum.onnxruntime import ORTModelForTokenClassification, ORTModelForFeatureExtraction
from transformers import AutoTokenizer
from pathlib import Path

def export_ner(model_id: str = "d4data/biomedical-ner-all", output_dir: str = "models/ner_onnx"):
    print(f"Exporting NER model {model_id} to {output_dir}...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.save_pretrained(output_dir)
    
    model = ORTModelForTokenClassification.from_pretrained(model_id, export=True)
    model.save_pretrained(output_dir)
    print("NER export complete.")

def export_sapbert(model_id: str = "cambridgeltl/SapBERT-from-PubMedBERT-fulltext", output_dir: str = "models/sapbert_onnx"):
    print(f"Exporting SapBERT model {model_id} to {output_dir}...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.save_pretrained(output_dir)
    
    model = ORTModelForFeatureExtraction.from_pretrained(model_id, export=True)
    model.save_pretrained(output_dir)
    print("SapBERT export complete.")

if __name__ == "__main__":
    export_ner()
    export_sapbert()
