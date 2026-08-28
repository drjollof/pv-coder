---
title: PV-Coder API
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: "4.44.1"
app_file: app.py
pinned: false
hardware: cpu-basic
---

# PV-Coder

**AI-Assisted Pharmacovigilance Case Intake & Adverse Event Coding System**

`pv-coder` is an advanced clinical NLP system that automates the initial intake of pharmacovigilance (PV) safety reports. It accepts unstructured clinical narratives (e.g., patient emails, doctor notes), extracts adverse events and drugs, filters out negated/historical contexts, normalizes the events to the MedDRA dictionary using semantic vector search, and produces a structured ICH E2B-compliant case for human review.

This system is designed as a **Human-in-the-loop (HITL) decision support tool**, not an autonomous regulatory reporting system.

---

## 🏗️ Architecture

The system is fully decoupled into a modern Web architecture:

1. **NLP Engine (`src/`)**: Pure Python data science pipeline.
2. **Backend (`app.py`)**: Gradio Headless API serving the NLP engine.
3. **Frontend (`client/`)**: React.js (Vite) providing a premium, interactive user interface.

### NLP Pipeline
- **Extraction (NER):** Uses a HuggingFace Transformer (`d4data/biomedical-ner-all`) optimized into **INT8 ONNX** format for fast CPU inference.

- **Context Filtering:** Uses **MedSpaCy ConText** to aggressively filter out negated, historical, hypothetical, and other-experiencer mentions.

- **Semantic Normalization:** Converts extracted adverse events into 768-dimensional mathematical vectors using **SapBERT**, and queries a pre-computed **FAISS index** containing 80,000+ MedDRA Preferred Terms.
- **Seriousness Classification:** Rule-based ICH E2A keyword detection.

---

## 📂 Repository Layout

```text
pv-coder/
├── client/                 # React.js Frontend (Vite, CSS Modules)
├── app.py                  # Gradio Backend (Headless REST/WebSocket API)
├── src/                    # Core Python AI Engine
│   ├── data/               # Raw XML parsers for TAC/PHEE datasets
│   ├── extraction/         # NER (entities.py) & Context filtering (context.py)
│   ├── normalization/      # SapBERT semantic matching & hybrid retrieval
│   └── pv/                 # Case orchestrator (builder.py) & Pydantic schemas
├── data/                   # Processed data, dictionaries, and FAISS index
├── models/                 # Quantized INT8 ONNX models (managed via Git LFS)
├── scripts/                # Utility scripts (evaluations, data preprocessing)
├── tests/                  # Pytest unit tests
└── requirements.txt        # Python backend dependencies
```

---

## 🚀 Quickstart

Because the architecture is decoupled, you must run the backend and frontend in two separate terminals.

### 1. Start the Gradio Backend
Ensure you have Python 3.10+ installed.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the Gradio headless server
python app.py
```
*Note: The NLP engine is configured to intelligently check the environment. If run locally, it uses optimized INT8 ONNX models for fast CPU inference. If run on a Hugging Face ZeroGPU Space, it dynamically downloads the native PyTorch models to leverage GPU acceleration.*

### 2. Start the React Frontend
Ensure you have Node.js installed. Open a new terminal window:

```bash
cd client
npm install
npm run dev
```
Open `http://localhost:5173` in your browser to access the PV-Coder interface.

---

## 📊 Features

- **Single Intake Mode:** Paste a clinical narrative to see real-time extraction, MedDRA coding, and context parsing.
- **Batch Processing:** Upload a CSV of hundreds of narratives and process them concurrently.
- **Human-in-the-Loop:** Automatically flags ambiguous or low-confidence predictions for manual review via an interactive UI.
- **Enterprise Exports:** Generate printable PDF Reports or standard **E2B(R3) XML** files ready for ingestion into safety databases (Oracle Argus, Veeva Vault).

---

## 🛡️ TAC Gold Guard

If you are a developer interacting with the raw datasets (`data/TAC2017/`), note that the `gold_xml` split is the held-out evaluation set for the normalization pipeline.
`src/data/tac_parser.py` raises `PermissionError` if any code attempts to read the gold split without passing `allow_gold=True` explicitly to prevent data leakage during training.
