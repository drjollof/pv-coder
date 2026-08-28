# PV-Coder Documentation — Part 3: The NLP Pipeline

This is the core of PV-Coder. When you submit a narrative, it travels through four sequential stages. This document explains each stage in complete technical and conceptual depth.

---

## Stage 1: Named Entity Recognition (NER)

**File:** `src/extraction/entities.py`

### What is Named Entity Recognition?

Named Entity Recognition (NER) is an NLP task where a machine learning model reads text and highlights specific spans (contiguous pieces of text) that belong to a predefined category. In standard NLP, these categories might be "Person", "Place", "Organization". In clinical NLP, we care about "Drug" and "Disease/Symptom".

NER does **not** reason about the text. It simply pattern-matches based on what it learned during training. It is purely a span highlighter.

### The Model: `d4data/biomedical-ner-all`

We use a model from HuggingFace called `d4data/biomedical-ner-all`. This is a BERT-based Transformer model that was **pre-trained on PubMed biomedical text** (so it already understands medical vocabulary from reading millions of research papers), and then **fine-tuned on the BioNLP 2013 Cancer Genetics annotation scheme**.

The model's label space (the categories it can detect) includes:
- `Medication` — names of drugs, chemicals, supplements
- `Disease_disorder` — named diseases and conditions
- `Sign_symptom` — symptoms reported by or observed in a patient
- `Clinical_event` — events like "hospitalization", "admission"
- Several other biological entity types (gene, protein, etc.)

We only care about three of those for PV. The label mapping is defined in a constant at the top of `entities.py`:

```python
_GROUP_TO_ROLE: dict[str, str] = {
    "MEDICATION":       "DRUG",
    "DISEASE_DISORDER": "DISEASE",
    "SIGN_SYMPTOM":     "DISEASE",
    "CLINICAL_EVENT":   "DISEASE",
}
```

Notice that `Disease_disorder`, `Sign_symptom`, and `Clinical_event` all get mapped to the same internal role: `"DISEASE"`. This is because at this early stage, we cannot tell if something is the patient's background condition (an "indication") or an actual adverse event — that distinction happens later, in the Context stage and in the `EventBuilder`.

### How Transformers Tokenize Text

Transformer models cannot read raw text. They first pass the text through a **tokenizer**, which breaks the text into subword tokens. For example:

```
"hepatotoxicity" → ["hepato", "##toxic", "##ity"]
```

Each token gets a numeric ID from a vocabulary of 30,000+ subwords. The model processes these numeric sequences, not the original text. The `aggregation_strategy="first"` setting in our HuggingFace pipeline ensures that when multiple consecutive subword tokens all have the same entity label, they get merged back into a single span.

### ONNX Quantization — Why We Did It

The base PyTorch model is large (around 400MB) and runs slowly on CPU. To make it practical on a standard laptop, we converted it to the **ONNX (Open Neural Network Exchange)** format with **INT8 quantization**.

Normally, neural network weights are stored as 32-bit floating point numbers (FP32). INT8 quantization converts those weights to 8-bit integers. This reduces the model's memory footprint by 4x and speeds up inference because modern CPUs have hardware-accelerated integer arithmetic units.

The quantized model lives in `models/ner_onnx_quantized/`. The `ExtractionPipeline.__init__()` method checks if this folder exists first:

```python
if Path(self.ONNX_MODEL_DIR).exists():
    tokenizer = AutoTokenizer.from_pretrained(self.ONNX_MODEL_DIR)
    ort_model = ORTModelForTokenClassification.from_pretrained(self.ONNX_MODEL_DIR)
    self._ner = hf_pipeline("ner", model=ort_model, tokenizer=tokenizer, ...)
else:
    # Fall back to downloading the full PyTorch model from HuggingFace Hub
    self._ner = hf_pipeline("ner", model=model, ...)
```

The `ORTModelForTokenClassification` class comes from **HuggingFace Optimum** — a library that wraps the ONNX Runtime (ORT) to make ONNX models behave exactly like regular HuggingFace models.

### The `ExtractedEntity` Dataclass (Lines 48–74)

This is the core data structure representing one extracted span:

```python
@dataclass(frozen=True)
class ExtractedEntity:
    text: str            # The raw text, e.g., "hepatotoxicity"
    label: str           # "DRUG" or "DISEASE"
    start_char: int      # Character index where the span starts in the original text
    end_char: int        # Character index where the span ends
    negated: bool        # Will be set by ContextFilter
    historical: bool     # Will be set by ContextFilter
    hypothetical: bool   # Will be set by ContextFilter
    other_experiencer: bool  # Will be set by ContextFilter
```

The `frozen=True` argument makes instances **immutable**. Once an `ExtractedEntity` is created, its fields cannot be changed. When `ContextFilter` needs to set the context flags, it uses `dataclasses.replace()` to create a *new* entity object with the updated flags, leaving the original untouched. This is a functional programming pattern that prevents subtle bugs.

The `is_current` property (Lines 66–74) is a computed boolean that returns `True` only when none of the four context flags are set — i.e., the event is happening right now, to this patient, and is a real observation.

### The `ExtractionResult` Dataclass (Lines 77–100)

Groups all entities from one text into one object:
```python
@dataclass
class ExtractionResult:
    drugs: list[ExtractedEntity]    # All drug entities found
    diseases: list[ExtractedEntity] # All disease/symptom entities found
    doc: Optional[Doc]              # The spaCy Doc object (needed by ContextFilter)
```

The `doc` field stores a spaCy `Doc` object. This is not a string — it is a special object that spaCy uses to store the text along with its linguistic annotations (sentence boundaries, token information). We keep it here so that `ContextFilter` can run its analysis on the same tokenized representation of the text, rather than re-tokenizing.

### The `ExtractionPipeline` Class (Lines 103–213)

The constructor does two things: loads the NER model and creates a minimal spaCy blank pipeline with a `sentencizer`. The sentencizer just splits text into sentences — no grammar analysis happens here. We need sentence boundaries because the ConText algorithm (Stage 2) uses them to limit how far a modifier can propagate.

`extract(text)` — takes a single string, runs NER, returns an `ExtractionResult`.

`extract_batch(texts, batch_size=64)` — for the batch processing endpoint. Sends all texts to the HuggingFace pipeline at once with `batch_size=64`, which is much faster than calling `extract()` in a loop because the GPU/CPU can process multiple texts in parallel.

`_build_result(text, ner_output)` — the internal method that converts the raw list-of-dicts from HuggingFace into our typed `ExtractionResult`. It normalizes the entity group labels (handling BIO prefix stripping), creates `ExtractedEntity` objects, and importantly calls `filter_spans()` on the spaCy doc. `filter_spans()` resolves any overlapping spans by keeping the longest one, preventing the same text region from being annotated twice.

---

## Stage 2: Context Filtering

**File:** `src/extraction/context.py`

### The Core Problem — Why NER Alone Is Not Enough

If you only use the NER model from Stage 1, you will extract every mention of a disease or symptom, including ones that are:
- **Negated:** *"The patient did not develop hepatotoxicity."* — "hepatotoxicity" gets extracted but it never happened.
- **Historical:** *"Medical history included hypertension."* — "hypertension" is a pre-existing condition, not a new drug side effect.
- **Hypothetical/Risk:** *"Methotrexate may cause bone marrow suppression."* — This is drug label language warning about a risk, not a report of something that occurred.
- **Belonging to someone else:** *"Family history of cancer."* — This is about the patient's relative, not the patient themselves.

In pharmacovigilance, accidentally coding these as adverse events would severely corrupt the company's safety database. The Context Filtering stage exists to systematically eliminate all of them.

### MedSpaCy ConText

We use the **MedSpaCy** library's implementation of the **ConText algorithm**. ConText was originally published in academic NLP literature and is the standard algorithm used in clinical NLP systems worldwide.

ConText works on the linguistic principle that **modifier words propagate their meaning in a specific direction within a sentence**. The word "no" in *"patient had no nausea"* is a modifier that negates the word "nausea" to its **right** (forward direction). The phrase "history of" in *"history of diabetes"* labels "diabetes" as historical.

### PV-Specific Context Rules (Lines 49–83)

We defined a custom set of rules specifically tuned for pharmacovigilance language, grouped by modifier category:

**Historical modifiers:**
- `"history of"` → HISTORICAL, FORWARD
- `"previous"`, `"prior"`, `"past"`, `"had"`, `"former"` → HISTORICAL, FORWARD
- `"resolved"` → HISTORICAL, BIDIRECTIONAL (works in both directions)

**Hypothetical/Risk language modifiers:**
- `"risk of"`, `"may cause"`, `"can cause"`, `"could cause"` → HYPOTHETICAL, FORWARD
- `"to prevent"` → HYPOTHETICAL, FORWARD (e.g., *"given anticoagulants to prevent thrombosis"*)

**Other-Experiencer modifiers:**
- `"family history"`, `"mother"`, `"father"`, `"sibling"` → FAMILY, FORWARD

Each rule is a `ConTextRule(literal_trigger, category, direction)`. The `FORWARD` direction means the modifier affects entities that appear *after* it in the sentence. `BIDIRECTIONAL` means it affects entities both before and after.

### The `ContextLabel` IntFlag (Lines 32–37)

```python
class ContextLabel(IntFlag):
    NEGATED           = auto()   # value = 1
    HISTORICAL        = auto()   # value = 2
    HYPOTHETICAL      = auto()   # value = 4
    OTHER_EXPERIENCER = auto()   # value = 8
```

`IntFlag` allows bitwise operations. You can combine labels: `NEGATED | HISTORICAL` produces a value of `3`. This compact representation lets us efficiently check if *any* context flag is set: `label_flags != 0`.

### The `ContextFilter` Class (Lines 95–165)

The constructor creates its own blank spaCy pipeline and adds the `medspacy_context` component to it. It then populates that component with all the custom PV rules.

**`annotate(result)` (Lines 117–136):**
Takes an `ExtractionResult` (with the spaCy `doc` already set by `ExtractionPipeline`), runs *only* the ConText component on the doc, then rebuilds the `ExtractionResult` by calling `_apply_flags()` on each entity.

Critically, it does NOT re-run the full NER — it just runs ConText on the existing doc. This is efficient and avoids redundant computation.

**`filter_current(result)` (Lines 138–145):**
Calls `annotate()` and then throws away any entity where `is_current` is `False`. This is the method `CaseBuilder` uses in production.

**`_apply_flags(entity, doc)` (Lines 147–165):**
This method bridges between MedSpaCy's attribute system and our own `ExtractedEntity` dataclass.

After ConText runs, it stores its analysis results as **custom SpaCy span extensions** — attributes attached to the span object using SpaCy's `_.` extension system. We use `getattr(span._, "is_negated", False)` with a safe fallback default of `False` in case the attribute doesn't exist in an older version of medspacy. This defensive coding ensures our pipeline does not crash on version bumps.

It then uses `dataclasses.replace()` to return a *new*, immutable `ExtractedEntity` with the context flags set — without modifying the original.

---

## Stage 3: Lexical Normalization

**File:** `src/normalization/lexical.py`

### Why We Need Two Normalization Approaches

After Context Filtering, we have clean strings like `"hepatotoxicity"` or `"nausea"`. We need to find their official MedDRA Preferred Term. We use two complementary approaches:

1. **Lexical:** Based on comparing characters. Fast. Works well for standard medical terminology.
2. **Semantic:** Based on comparing meaning (vectors). Slower. Works for informal/slang terms.

Both are combined by the `HybridRetriever`.

### The `LexicalNormalizer` Class

The constructor pre-computes two data structures from the MedDRA dictionary:

**Exact match dictionary (Lines 16–19):**
A plain Python dictionary mapping every lowercase MedDRA PT string to its ID. Lookup is O(1) (instantaneous). If the patient typed the exact MedDRA term, we find it immediately and return a confidence of `1.0`.

**TF-IDF Matrix (Lines 22–25):**
TF-IDF (Term Frequency-Inverse Document Frequency) is a classical information retrieval technique. We initialize it with `analyzer='char_wb'` and `ngram_range=(3, 5)`. This means instead of treating whole words as features, we treat **character n-grams** (overlapping sequences of 3 to 5 characters) as features.

*Why character n-grams?* Because they handle spelling variations gracefully. "hepatotoxicity" and "hepatotoxic" share many 3-character n-grams (`hep`, `epa`, `pat`, `ato`, `tot`...), so they will have a high cosine similarity even though they are different words.

**`match_exact(query)` (Lines 27–34):** Simple dictionary lookup. Returns immediately with confidence 1.0 if found.

**`match_tfidf(query, top_k=5)` (Lines 36–53):** Transforms the query into its character n-gram TF-IDF vector. Computes cosine similarity against the entire pre-computed dictionary matrix. Returns the top K results. Filters out any result with similarity below 0.1 (noise threshold).

**`match_fuzzywuzzy(query, top_k=5)` (Lines 55–75):** Uses the Levenshtein edit distance algorithm via the `thefuzz` library. The `token_sort_ratio` variant sorts the tokens alphabetically before comparing, which handles word order variations well (e.g., "pain severe" vs "severe pain" would still match). This is slower (O(n) where n = 80,000 dictionary entries) but more robust for heavily misspelled text.

---

## Stage 4: Semantic Normalization with SapBERT & FAISS

**File:** `src/normalization/embeddings.py`

### The Core Idea: Words as Points in Space

The fundamental insight of semantic normalization is that **meaning can be represented as a point in a high-dimensional mathematical space**. Similar meanings are close together. Dissimilar meanings are far apart.

SapBERT converts every piece of text into a **vector** — an array of 768 numbers. These 768 numbers encode the semantic meaning of the text. This vector is the text's "address" in a 768-dimensional mathematical space.

### Why SapBERT Specifically

SapBERT (**Self-Aligning Pretrained BERT**) was released by Cambridge LTL and published at NAACL 2021. It was built specifically for biomedical entity linking — the exact problem we are solving.

SapBERT was pre-trained on the **UMLS (Unified Medical Language System)** — a massive database containing 3.5 million medical concepts from 150+ controlled vocabularies worldwide, with their synonyms. During training, SapBERT used a technique called **self-alignment**: it trained the model to produce *identical* (or very similar) vectors for any two strings that refer to the same medical concept.

This means after training, the model learned that:
- `"tummy ache"` ≈ `"abdominal pain"` ≈ `"stomach hurts"` ≈ `"epigastric discomfort"`

They all map to nearly the same point in the 768-dimensional space. This is the superpower that makes PV-Coder work on informal patient language.

### `SemanticNormalizer.__init__()` (Lines 11–46)

The constructor:
1. Copies the MedDRA dictionary DataFrame.
2. Loads SapBERT (checks for ONNX-optimized version first at `models/sapbert_onnx_quantized/`).
3. If a pre-computed FAISS index path is provided and the file exists, loads the index from disk.
4. Otherwise (slower, first-time setup), encodes all 80,000 MedDRA PTs into vectors, normalizes them, and builds a FAISS index on the fly.

The `faiss.normalize_L2(embeddings)` call is important. It normalizes every vector to have a length of 1 (unit norm). After normalization, computing the **dot product** between two vectors is equivalent to computing **cosine similarity**. This is important for FAISS because `IndexFlatIP` (Inner Product) is much faster than a cosine similarity index.

### FAISS — Facebook AI Similarity Search

FAISS is an open-source library for efficient similarity search developed by Facebook AI Research. It solves this problem: given a query vector, find the K most similar vectors out of 80,000 vectors, as fast as possible.

Doing this naively in Python would be a loop over all 80,000 entries — slow. FAISS uses highly optimized C++ and BLAS (Basic Linear Algebra Subprograms) routines to do this in microseconds. For our 80,000-term dictionary, `faiss.IndexFlatIP` (the brute-force inner product index) is fast enough.

The index is saved once to `data/processed/faiss.index` and loaded every time the server starts. This means we never have to re-compute the 80,000 vectors — they are permanently stored in the pre-built index.

### `match(query, top_k=3, threshold=0.70, margin=0.05)` (Lines 48–86)

This is the main normalization method. Here is exactly what it does:

1. Encodes the query string into a 768-dimensional vector using SapBERT.
2. Normalizes that vector (same L2 normalization as the index).
3. Calls `self.faiss_index.search(query_embedding, top_k)` which returns two arrays: `scores` (inner products = cosine similarities) and `indices` (positions in the dictionary).
4. Maps each index back to the actual MedDRA row to get the PT string and ID.

**The Margin Logic (Lines 73–86):**

The most nuanced part. After getting the top 3 results, we decide whether to `Auto-code` or send to `Human Review`.

The rule is: `Auto-coded` if **and only if**:
- `top_1_score >= 0.70` (the best match is at least 70% confident), **AND**
- `top_1_score - top_2_score >= 0.05` (there is a clear winner — the best match is at least 5 percentage points more confident than the second-best)

This margin check is critical. Imagine the query is "pain". SapBERT might find:
- "Abdominal pain" — score 0.80
- "Back pain" — score 0.79

Without the margin check, we would auto-code to "Abdominal pain" with 80% confidence — but it's barely better than "Back pain". The margin rule catches this ambiguity and sends it to human review instead.

---

## Stage 5: Hybrid Retrieval & Orchestration

**File:** `src/normalization/retrieval.py` and `src/pv/builder.py`

### The `HybridRetriever` (retrieval.py)

`HybridRetriever` combines both the `LexicalNormalizer` and `SemanticNormalizer` for best-of-both-worlds retrieval:

1. **Exact match shortcut:** If the text perfectly matches an MedDRA PT, return immediately (confidence 1.0).
2. **Lexical match:** Run TF-IDF (or FuzzyWuzzy if configured).
3. **Semantic match:** Run SapBERT + FAISS.
4. **Fusion:** For each unique PT ID that appeared in *either* result list, take the **maximum** score across both methods. Sort the fused results by score descending.

This fusion strategy means a term that scores mediocrely in both lexical and semantic search but consistently shows up in both is ranked higher than a term that only appears in one.

### The `CaseBuilder` — The Grand Orchestrator

**File:** `src/pv/builder.py`

`CaseBuilder` is the single class that coordinates the entire pipeline. Its constructor initializes everything once:
- `self.ner = ExtractionPipeline()` — loads the ONNX NER model
- `self.event_builder = EventBuilder()` — (from `src/extraction/events.py`) applies context filtering and event type classification
- `self.semantic = SemanticNormalizer(dictionary, ...)` — loads SapBERT and FAISS
- `self.seriousness = SeriousnessClassifier()` — compiles the regex patterns

Its `process(narrative, case_id)` method is the single entry point called by the API:

```python
def process(self, narrative: str, case_id: str) -> PharmacovigilanceCase:
    candidates = self.ner.extract(narrative)           # Stage 1: NER
    events = self.event_builder.build(candidates, narrative)  # Stage 2: Context + Event classification
    adverse_events = [e for e in events if e.event_type == EventType.ADVERSE_EVENT]  # Filter
    
    for ae in adverse_events:
        norm_results, review_status = self.semantic.match(ae.effect.text, top_k=3)  # Stage 3+4: Normalization
        is_serious = self.seriousness.is_serious(ae.effect.text, narrative)  # Seriousness check
        # ... build NormalizedEvent ...
    
    return PharmacovigilanceCase(...)
```

### The `SeriousnessClassifier` (seriousness.py)

Implements ICH E2A seriousness criteria as compiled regular expressions. The `SERIOUS_KEYWORDS` list contains regex patterns for: fatal, death, died, life-threatening, hospitalized/hospitalization, inpatient, disabled/disability, incapacitated, congenital, anomaly, severe, ICU, intensive care.

The classifier checks **both** the event text itself and the **entire narrative**. The document-level check is a conservative but standard PV triage strategy: if any part of the report mentions hospitalization, all extracted events in that report are flagged as potentially serious. It is much safer to over-flag and require a human to downgrade than to miss a fatal case.

---

*Continue to Part 4: The Backend API, Data Models, and Frontend Architecture*
