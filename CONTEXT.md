# PV-Coder Project Context

## Project Goal
PV-Coder is an NLP-assisted Pharmacovigilance Case Intake System designed to automate the extraction and coding of adverse events from clinical narratives into MedDRA preferred terms. The system provides both a Single Intake view for deep-dive analysis and a Batch Upload dashboard for processing large CSV files, featuring Human-in-the-Loop (HitL) validation flows to ensure accuracy.

## Phase Tracker

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Model optimization (ONNX / Quantization) | `Done` |
| **Phase 2** | Local API setup (FastAPI + React) | `Done` |
| **Phase 3** | Zero-Shot Extraction Engine (LLM prompts) | `Done` |
| **Phase 4** | Normalization & Dictionary mapping (Faiss) | `Done` |
| **Phase 5** | Batch Processing & Reporting (E2B XML) | `Done` |
| **Phase 6** | UI Polishing & Human-in-the-Loop workflows | `Done` |
| **Phase 7** | Implement P0 Features & Frontend Refactoring | `Done` |
| **Phase 8** | Implement P1 Features | `Pending` |

## What Was Built
*   **FastAPI Backend**: Provides `/analyze` and `/batch` endpoints.
*   **React Frontend (Refactored)**: Clean, modularized architecture. Split monolithic `App.jsx` into smaller components (`SingleIntake.jsx`, `BatchUpload.jsx`, `HighlightedText.jsx`).
*   **Zero-Shot Extraction**: Prompts fine-tuned for Llama-3/Mistral to identify AEs and drugs.
*   **Faiss Indexing**: Uses SapBERT embeddings for semantic search over MedDRA.
*   **E2B(R3) Generation**: Creates XML reports per ICH standards.
*   **P0 Feature Set**: Fully implemented features P0.1 to P0.15 (including Recharts for batch analytics).

## Key Design Decisions
*   **Optimized Models**: Quantized models to ONNX to run locally on CPU without memory constraints.
*   **Hybrid NLP Pipeline**: Uses lightweight LLM for extraction, and dense retrieval (SapBERT + Faiss) for normalization (much faster and more reliable than pure LLM).
*   **Frontend Modularity**: The `App.jsx` was split into smaller components to keep context window manageable for AI agents moving forward.
*   **Dependency Pinning**: Strictly kept `sentence-transformers==3.0.1` and `gradio==4.44.1`. Used `_ONNXSapBERT` wrapper to bypass compatibility issues with `huggingface-hub`.

## Next Session Prompt
*Paste this to resume work in the next session:*
> "We have completed the P0 features and refactored the frontend React code into smaller components inside `client/src/components/`. Please review `CONTEXT.md` and `pv-coder-consolidated-feature-Improvement-specification.md` and let's begin implementing the P1 features."
