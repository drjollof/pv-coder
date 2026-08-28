#!/usr/bin/env python3
"""
Quantize ONNX Models.

Applies INT8 quantization to the exported ONNX models for faster CPU inference.
"""

from optimum.onnxruntime import ORTQuantizer
from optimum.onnxruntime.configuration import AutoQuantizationConfig
from pathlib import Path
import shutil

def quantize_model(input_dir: str, output_dir: str):
    print(f"Quantizing model in {input_dir} to {output_dir}...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    quantizer = ORTQuantizer.from_pretrained(input_dir)
    dqconfig = AutoQuantizationConfig.avx512_vnni(is_static=False, per_channel=True)
    
    quantizer.quantize(save_dir=output_dir, quantization_config=dqconfig)
    
    for file in Path(input_dir).glob("*.json"):
        if not (Path(output_dir) / file.name).exists():
            shutil.copy(file, Path(output_dir) / file.name)
            
    for file in Path(input_dir).glob("*.txt"):
        if not (Path(output_dir) / file.name).exists():
            shutil.copy(file, Path(output_dir) / file.name)
            
    print(f"Quantization complete for {input_dir}.")

if __name__ == "__main__":
    quantize_model("models/ner_onnx", "models/ner_onnx_quantized")
    quantize_model("models/sapbert_onnx", "models/sapbert_onnx_quantized")
