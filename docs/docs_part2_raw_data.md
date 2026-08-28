# PV-Coder Documentation — Part 2: Raw Data Processing

This document explains how we go from completely raw, messy source data files to the clean, compressed files that the AI uses at runtime. This all lives inside `src/data/`.

---

## 2.1 Overview: Two Raw Datasets, Two Parsers

We use two distinct raw datasets, each in a different file format and with a different structure. Each has its own dedicated parser module.

| Dataset | Format | Parser File | Purpose |
|---|---|---|---|
| TAC 2017 ADR | XML (multiple files) | `src/data/tac_parser.py` | Builds the MedDRA dictionary (.parquet) |
| PHEE | Parquet (3 files) | `src/data/phee_parser.py` | Provides labeled training events for evaluation |

---

## 2.2 TAC 2017 ADR Dataset — Building the MedDRA Dictionary

### What the Raw Data Looks Like

The TAC dataset consists of many individual `.xml` files, one per drug label (e.g., one for Aspirin, one for Methotrexate). Each XML file has this nested structure:

```xml
<Label drug="methotrexate">
  <Mentions>
    <Mention id="M1" section="S1" type="AdverseReaction" 
             str="hepatotoxicity" start="142" len="14"/>
    <Mention id="M2" type="AdverseReaction" str="nausea" start="200" len="6"/>
  </Mentions>
  <Relations>
    <Relation id="R1" type="Hypothetical" arg1="M1" arg2="M2"/>
  </Relations>
  <Reactions>
    <Reaction id="RX1" str="hepatotoxicity">
      <Normalization meddra_pt="Hepatotoxicity" meddra_pt_id="10019851"/>
    </Reaction>
    <Reaction id="RX2" str="nausea">
      <Normalization meddra_pt="Nausea" meddra_pt_id="10028813"/>
    </Reaction>
  </Reactions>
</Label>
```

This is the ground truth: the MedDRA ID for "hepatotoxicity" is 10019851. Our parser extracts this mapping for every drug and every reaction in the entire dataset.

### `src/data/tac_parser.py` — Full Explanation

**File purpose:** Parse the TAC XML files and extract three flat Pandas DataFrames: Mentions, Relations, and Reactions.

#### The Gold Guard

Right at the top of the file, before anything else, is an important safety mechanism:

```python
_GOLD_GUARD_MESSAGE = (
    "Attempted to parse TAC gold_xml without explicit allow_gold=True. ..."
)
```

The TAC dataset has two splits: `train_xml/` (used during development) and `gold_xml/` (the locked evaluation set). If you accidentally train or tune your model on the gold split, your evaluation results become meaningless — it would be like memorizing the answers before the test. The gold guard raises a `PermissionError` unless you explicitly pass `allow_gold=True`. Only dedicated evaluation scripts ever do this.

#### Function: `_parse_single_xml(path, split)` (Lines 38–120)

This is an internal helper (note the underscore prefix, meaning it is not meant to be called from outside the module). It takes one XML file path and produces three lists of dictionaries.

**Mentions parsing (Lines 62–82):**
```python
for m in mentions_el.findall("Mention"):
    start_raw = m.attrib.get("start", "")
    len_raw = m.attrib.get("len", "")
    is_discontinuous = "," in start_raw
    n_spans = len(start_raw.split(",")) if start_raw else 1
```
The `is_discontinuous` flag matters because some adverse reactions span non-adjacent text. For example, "nausea and vomiting" might be annotated as two separate spans with a comma-separated `start` attribute (e.g., `start="142,165"`). This flag preserves that information for downstream analysis.

Each mention record stores: which drug, which split (train/gold), the source filename, a unique mention ID, the section ID (drug labels have sections like Warnings, Contraindications), the mention type (AdverseReaction, Factor, etc.), the raw string text, and the character positions.

**Relations parsing (Lines 84–95):**
Relations capture relationships *between* mentions — for example, a `Hypothetical` relation between a drug and an effect means the effect is only theoretically possible, not observed. This feeds into our Context Filtering later.

**Reactions parsing (Lines 97–118):**
This is the most valuable part. The Reactions section is the *normalized* gold standard — the annotator's final verdict on which MedDRA PT code the raw mention maps to.

```python
norm = rx.find("Normalization")
if norm is not None:
    meddra_pt = norm.attrib.get("meddra_pt")
    meddra_pt_id = norm.attrib.get("meddra_pt_id")
```

This is where we collect all the (raw_string → MedDRA PT → MedDRA PT ID) triplets that form the basis of our dictionary.

#### Function: `parse_directory(xml_dir, split, allow_gold=False)` (Lines 123–169)

This is the public-facing function that orchestrates parsing an entire directory of XML files. It:
1. Checks the gold guard.
2. Glob-scans the directory for `*.xml` files.
3. Calls `_parse_single_xml` on each file and accumulates the results.
4. Returns three Pandas DataFrames: `mentions_df`, `relations_df`, `reactions_df`.

#### Functions: `parse_train()` and `parse_gold()` (Lines 172–206)

These are convenience wrappers. `parse_train()` is safe to call from any script. `parse_gold()` is only meant to be called from `scripts/run_evaluation.py` after all development is complete. The docstrings make this contract explicit.

### What Happens After Parsing

After we run the TAC parser and get the reactions DataFrame, a preprocessing script (in `scripts/`) takes the `meddra_pt` and `meddra_pt_id` columns, deduplicates them, and saves the final clean dictionary:

```
data/processed/tac_meddra_dict.parquet   ← The compressed MedDRA dictionary (80k+ terms)
```

The `.parquet` format (columnar storage) was chosen because it is much faster to read and much smaller than CSV — critical when loading 80,000 rows at API startup.

---

## 2.3 PHEE Dataset — The Event Structure Dataset

### What the Raw Data Looks Like

The PHEE dataset is fundamentally different from TAC. It contains real biomedical case reports with annotated *events* (not just entity spans). It is stored as three Parquet files: `train.parquet`, `dev.parquet`, `test.parquet`.

Each row in the PHEE dataset has a `context` field (the full narrative text) and an `annotations` field that contains a deeply nested JSON-encoded event structure. One single narrative can contain **multiple events**, and one event can involve **multiple drugs**.

A single event's `event_data` JSON might look like:

```json
{
  "Trigger": {"text": [["developed"]], "offset": [[45, 54]]},
  "Effect": {"text": [["hepatic necrosis"]], "offset": [[55, 70]]},
  "Treatment": {
    "Drug": {"text": [["methotrexate"]], "Route": {"text": [["oral"]]}},
    "Dosage": {"text": [["15mg"]]},
    "Freq": {"text": [["weekly"]]}
  },
  "Subject": {
    "text": [["patient"]],
    "Age": {"text": [["45-year-old"]]},
    "Gender": {"text": [["female"]]}
  },
  "Severity": {"value": "severe"},
  "Speculated": {"value": false}
}
```

This is far richer than TAC. It tells us not just *what* the adverse event was, but *who* it happened to, *what drug* caused it, *how* it was administered, *how severe* it was, and whether it was speculated or actually observed.

### `src/data/phee_parser.py` — Full Explanation

#### Function: `_extract_text_from_span(span_value)` (Lines 17–32)

This private helper handles the awkward span format that PHEE uses. Text spans are stored as a list of lists: `[[token, ...], ...]`. For single spans it looks like `[["hepatic necrosis"]]` and for discontinuous spans it might look like `[["nausea"], ["vomiting"]]`.

The function safely extracts just the first span's text. It wraps the extraction in a `try/except` to gracefully handle any malformed data without crashing the entire parse.

#### Function: `_extract_all_drug_texts(treatment)` (Lines 35–63)

This is more complex because a treatment can involve *multiple drugs* (combination therapy like Methotrexate + Etanercept). The function flattens all the drug text spans from `Treatment.Drug.text` into a deduplicated ordered list. It uses a `dict[str, None]` as an ordered set (a Python trick where dictionary keys are insertion-ordered but unique).

#### Function: `_flatten_event(ev_row, row_id, row_text, split, is_mult_event)` (Lines 66–133)

This is the core transformation function. It takes one deeply nested event dict and produces one flat record (one row in the output DataFrame). 

The key operations are:
1. Parse the JSON-encoded `event_data` string into a dictionary.
2. Extract Trigger, Effect, Treatment, Subject, Severity, and Speculated sub-dicts.
3. Call `_extract_text_from_span()` on each relevant field.
4. Call `_extract_all_drug_texts()` to get all the drugs.
5. Return a flat dictionary with 18 clean columns.

Notice that every field uses `.get()` with an `or {}` fallback: `trigger = ed.get("Trigger") or {}`. This defensive pattern ensures that if any field is missing from the JSON, the code gracefully produces `None` instead of crashing with a `KeyError`.

The `speculated` field is particularly important — it becomes the `is_speculated` flag in our `NormalizedEvent` data model. If a doctor writes "this drug *may* cause hepatotoxicity", that is a speculated event and should be treated differently from a confirmed observation.

#### Function: `parse_split(parquet_path, split)` (Lines 136–173)

Public function that reads one parquet file. It iterates over every row, then over every annotation block within that row, then over every event within each annotation block. This triple nesting is necessary because: one narrative can have multiple annotator annotations, and one annotation can describe multiple events.

#### Function: `parse_all(phee_dir)` (Lines 176–195)

Convenience wrapper that calls `parse_split` on all three splits (train, dev, test) and concatenates the results into one large DataFrame. The `split` column tells you which set each record came from, which is essential for preventing data leakage during model evaluation.

---

*Continue to Part 3: The NLP Pipeline (Extraction, Context, Normalization)*
