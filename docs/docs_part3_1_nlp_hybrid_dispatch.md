# PV-Coder Documentation — Part 3.1: Hybrid Model Dispatching

---

## 3.1.1 The Hardware Constraint Problem

In standard clinical NLP deployments, developers face a difficult tradeoff regarding model formats:
1. **Native PyTorch Models**: These are the original models loaded directly via Hugging Face. They are incredibly fast if you have access to a GPU (like an NVIDIA A100), but they are extremely slow and memory-intensive on standard CPUs (like a developer's local laptop).
2. **Quantized ONNX Models**: These models are compiled and compressed (INT8 quantization) specifically for CPU inference. They run very fast locally without needing a GPU, but they are rigid—they cannot easily take advantage of cloud GPUs.

Originally, PV-Coder relied exclusively on ONNX models. However, when deploying to **Hugging Face ZeroGPU Spaces** (which provides dynamic A100 GPU acceleration for free), the environment attempted to force the ONNX models onto the GPU, causing severe dependency conflicts and crashes.

To solve this without sacrificing local development speed, we implemented an **Intelligent Hybrid Dispatch** architecture.

---

## 3.1.2 The `SPACE_ID` Environment Variable

The core mechanism relies on detecting where the code is currently running. Hugging Face Spaces automatically inject a specific environment variable called `SPACE_ID` into all of its active containers. 

By checking for the existence of `SPACE_ID`, the NLP engine can deduce its environment:
- **If `SPACE_ID` exists**: The code is running in the Hugging Face cloud, where ZeroGPU acceleration is available.
- **If `SPACE_ID` is missing**: The code is running on a local machine (e.g., a developer's laptop) where no GPU is guaranteed.

---

## 3.1.3 Stage 1: NER Hybrid Loading

**File:** `src/extraction/entities.py`

In the `ExtractionPipeline.__init__` method, we introduced the following logic:

```python
import os
# Use ONNX if models exist locally AND we are not running on HuggingFace Spaces (where ZeroGPU is available)
if Path(self.ONNX_MODEL_DIR).exists() and not os.environ.get("SPACE_ID"):
    print(f"Loading optimized ONNX NER model from {self.ONNX_MODEL_DIR}...", flush=True)
    # ... ONNX loading logic ...
else:
    print(f"Loading native PyTorch NER model: {model}...", flush=True)
    self._ner: Pipeline = hf_pipeline(
        "ner",
        model=model,
        aggregation_strategy="first",
        # Let ZeroGPU move it to CUDA automatically
    )
```

**How it works:**
1. **Local Development**: The developer clones the repository (including the ONNX files via Git LFS). When they run the code, `os.environ.get("SPACE_ID")` returns `None`. The code safely loads the INT8 ONNX models using the `CPUExecutionProvider`.
2. **Cloud Production**: On Hugging Face, `SPACE_ID` is present. The `if` statement evaluates to `False`. The code ignores the local ONNX files and downloads the native PyTorch `d4data/biomedical-ner-all` model. The ZeroGPU infrastructure automatically intercepts this model and moves it to the A100 GPU.

---

## 3.1.4 Stage 3: Semantic Normalization Hybrid Loading

**File:** `src/normalization/embeddings.py`

The exact same intelligent dispatch pattern is applied to the **SapBERT** embeddings model:

```python
import os
if onnx_dir.exists() and not os.environ.get("SPACE_ID"):
    print(f"Loading optimized ONNX SapBERT model from {onnx_dir}...", flush=True)
    # ... ONNX loading logic ...
else:
    print(f"Loading native PyTorch SapBERT model: {model_name}...", flush=True)
    self.model = SentenceTransformer(model_name)
```

By explicitly instantiating `SentenceTransformer(model_name)` without forcing the device to CPU in the cloud environment, ZeroGPU is given full permission to accelerate the heavy vector mathematical operations.

### Benefits of the Hybrid Architecture
- **Zero-Config Developer Experience**: A new developer can clone the `dev` branch and run the app locally on a MacBook immediately. The ONNX models ensure it runs fast without them needing to configure PyTorch CUDA drivers.
- **Maximized Production Speed**: When pushed to Hugging Face, the app automatically scales up to utilize enterprise-grade GPU hardware, achieving millisecond inference times for the clinical pipeline.
