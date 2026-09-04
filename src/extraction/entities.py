"""
Clinical/PV entity extraction pipeline — EXPERIMENTAL HuggingFace NER backend.

Default model: d4data/biomedical-ner-all
This is an experimental replacement for en_ner_bc5cdr_md, adopted due to a
three-way incompatibility between spaCy 3.7, pydantic >=2, and Python 3.12.
Equivalence to en_ner_bc5cdr_md has NOT been established; the PHEE dev
evaluation in scripts/run_extraction_eval.py is the empirical basis for
any quality judgment.

Model label space (d4data/biomedical-ner-all — BioNLP13CG schema):
    Medication        → DRUG role
    Disease_disorder  → DISEASE role (background diagnoses, disorders)
    Sign_symptom      → DISEASE role (symptoms — most common AE presentation)
    Clinical_event    → DISEASE role (clinical events such as hospitalisations)
    All other labels are ignored at this stage.

Why DISEASE and not ADVERSE_EVENT:
    Whether a detected Disease_disorder or Sign_symptom span is an adverse
    event requires event-structure and context logic that is downstream of
    entity recognition. This module only detects spans; classification is
    the responsibility of ContextFilter and pv.case_schema.


Explicit mapping from model entity_group → internal role.
Keys are the uppercased entity_group strings returned by the transformers
pipeline with aggregation_strategy="simple" (i.e., the BIO prefix is stripped).

Blank spaCy pipeline used only to create Doc containers for ConText.
The sentencizer is required because MedSpaCy ConText uses sentence 
boundaries to scope modifier propagation.


DistilBERT max is 512 tokens; leave headroom for special tokens and
subword expansion (each word can split into 2-3 pieces).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import spacy
from spacy.util import filter_spans
from spacy.tokens import Doc



_GROUP_TO_ROLE: dict[str, str] = {
    "MEDICATION":       "DRUG",
    "DISEASE_DISORDER": "DISEASE",
    "SIGN_SYMPTOM":     "DISEASE",
    "CLINICAL_EVENT":   "DISEASE",
}


@dataclass(frozen=True)
class ExtractedEntity:
    """
    One detected entity span with its context classification flags.

    Context flags default to False. ContextFilter populates them by running
    MedSpaCy ConText on the parent Doc. Callers must not set them manually.
    """

    text: str
    label: str        
    start_char: int
    end_char: int
    negated: bool = False
    historical: bool = False
    hypothetical: bool = False
    other_experiencer: bool = False

    @property
    def is_current(self) -> bool:
        """True when no context modifier excludes a present-event interpretation."""
        return not (
            self.negated
            or self.historical
            or self.hypothetical
            or self.other_experiencer
        )


@dataclass
class ExtractionResult:
    """
    Structured output for a single input text.

    drugs    — spans whose entity group maps to DRUG
    diseases — spans whose entity group maps to DISEASE;
               includes AE candidates and background conditions
    doc      — spaCy Doc with ents set (required by ContextFilter)
    Current-context disease candidates — not yet classified as AE vs. indication.
    """

    drugs: list[ExtractedEntity] = field(default_factory=list)
    diseases: list[ExtractedEntity] = field(default_factory=list)
    doc: Optional[Doc] = field(default=None, compare=False, repr=False)

    def all_entities(self) -> list[ExtractedEntity]:
        return self.drugs + self.diseases

    def current_drugs(self) -> list[ExtractedEntity]:
        return [e for e in self.drugs if e.is_current]

    def current_diseases(self) -> list[ExtractedEntity]:
        return [e for e in self.diseases if e.is_current]


class ExtractionPipeline:
    """
    NER-based entity extraction backed by a HuggingFace token-classification model.

    The pipeline loads once at construction and is reused across calls. A spaCy
    blank pipeline is used only to create Doc objects so that MedSpaCy ConText
    can operate on the extracted spans.

    Use absolute path based on repository root.
    """

    DEFAULT_MODEL = "d4data/biomedical-ner-all"
    
    
    from pathlib import Path
    _ROOT = Path(__file__).parent.parent.parent
    ONNX_MODEL_DIR = str(_ROOT / "models" / "ner_onnx_quantized")

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        from pathlib import Path
        try:
            from transformers import pipeline as hf_pipeline, Pipeline, AutoTokenizer
            from optimum.onnxruntime import ORTModelForTokenClassification
        except ImportError as exc:
            raise ImportError(
                "transformers/optimum is required for entity extraction. "
                "Install with: pip install transformers optimum[onnxruntime]"
            ) from exc
            
        import os
        if Path(self.ONNX_MODEL_DIR).exists() and not os.environ.get("SPACE_ID"):
            try:
                print(f"Loading optimized ONNX NER model from {self.ONNX_MODEL_DIR}...", flush=True)
                tokenizer = AutoTokenizer.from_pretrained(self.ONNX_MODEL_DIR)
                model_onnx = ORTModelForTokenClassification.from_pretrained(self.ONNX_MODEL_DIR)
                self._ner = hf_pipeline(
                    "ner",
                    model=model_onnx,
                    tokenizer=tokenizer,
                    aggregation_strategy=None
                )
            except Exception as e:
                print(f"ONNX NER load warning: {e}. Falling back to native model: {model}...", flush=True)
                self._ner = hf_pipeline(
                    "ner",
                    model=model,
                    aggregation_strategy="first"
                )
        else:
            print(f"Loading native PyTorch NER model: {model}...", flush=True)
            self._ner = hf_pipeline(
                "ner",
                model=model,
                aggregation_strategy="first"
            )
            
        
        self._nlp = spacy.blank("en")
        self._nlp.add_pipe("sentencizer")


    _MAX_CHUNK_TOKENS: int = 400

    def _chunk_text(self, text: str) -> list[tuple[str, int]]:
        """
        Split text into sentence-aligned chunks within the model's token budget.

        Returns a list of (chunk_text, char_offset) pairs where char_offset is
        the character position of that chunk's start in the original text.
        Sentences that individually exceed the budget are passed as-is and let
        the model handle truncation internally (degenerate edge case).
        """
        doc = self._nlp(text)
        sentences = list(doc.sents)

        chunks: list[tuple[str, int]] = []
        current_sents: list = []
        current_token_count: int = 0
        chunk_start: int = 0

        for sent in sentences:
            token_count = len(self._ner.tokenizer.tokenize(sent.text))

            if current_sents and (current_token_count + token_count) > self._MAX_CHUNK_TOKENS:
                chunk_end = current_sents[-1].end_char
                chunks.append((text[chunk_start:chunk_end], chunk_start))
                chunk_start = sent.start_char
                current_sents = [sent]
                current_token_count = token_count
            else:
                current_sents.append(sent)
                current_token_count += token_count

        if current_sents:
            chunk_end = current_sents[-1].end_char
            chunks.append((text[chunk_start:chunk_end], chunk_start))

        return chunks or [(text, 0)]

    def extract(self, text: str) -> ExtractionResult:
        """
        Detect DRUG and DISEASE spans in a single text.

        Long narratives are split into sentence-aligned token-safe chunks before
        inference to prevent DistilBERT's 512-token limit from silently dropping
        entity B- tags near the truncation boundary. Chunk-relative offsets are
        remapped to original-text coordinates and duplicate spans are discarded.

        Context flags on all returned entities are False. Pass the result
        through ContextFilter to populate them.
        """
        chunks = self._chunk_text(text)

        if len(chunks) == 1:
            return self._build_result(text, self._run_ner(text))

        merged_ner: list[dict] = []
        seen_spans: set[tuple[int, int]] = set()

        for chunk_text, char_offset in chunks:
            for ent in self._run_ner(chunk_text):
                orig_start = ent["start"] + char_offset
                orig_end   = ent["end"]   + char_offset
                span_key   = (orig_start, orig_end)
                if span_key not in seen_spans:
                    seen_spans.add(span_key)
                    merged_ner.append({**ent, "start": orig_start, "end": orig_end})

        return self._build_result(text, merged_ner)

    def _aggregate_bio_tokens(self, tokens: list[dict], text: str) -> list[dict]:
        """
        Merge raw BIO token dicts into entity-group dicts.

        Quantized ONNX models sometimes emit I- tokens without a preceding B-
        token, or hallucinate a new B- token mid-word (a known INT8 artifact).
        This aggregator robustly merges any adjacent/overlapping tokens of the
        same label into a single span, and walks back to word boundaries to
        ensure no part of the surface form is lost.

        Merge if the label is the same and the token is contiguous or overlapping
        with the current span, regardless of whether it's a B- or I- tag.
        Before saving, expand forward to the end of the word in case
        suffix tokens were dropped (predicted O) by the model.

        Walk back to the start of the word if this is a continuation subword.
        Stop at space or punctuation (except internal hyphens which are common in drugs).

        Continuation — extend the span.
        """
        if not tokens:
            return []

        groups: list[dict] = []
        current: dict | None = None

        for tok in tokens:
            raw_label = tok["entity"]
            bio, _, label = raw_label.partition("-")
            if not label:
                label, bio = bio, "B"

            
            is_contiguous = current is not None and label == current["_label"] and tok["start"] <= current["end"]

            if not is_contiguous:
                if current is not None:
                    
                    end_idx = current["end"]
                    while end_idx < len(text) and (text[end_idx].isalnum() or text[end_idx] == '-'):
                        end_idx += 1
                    current["end"] = end_idx
                    groups.append(current)

                start = tok["start"]
                
                while start > 0 and (text[start - 1].isalnum() or text[start - 1] == '-'):
                    start -= 1
                current = {
                    "entity_group": label,
                    "score": tok["score"],
                    "start": start,
                    "end": tok["end"],
                    "_label": label,
                }
            else:
                
                current["end"] = max(current["end"], tok["end"])
                current["score"] = min(current["score"], tok["score"])

        if current is not None:
            end_idx = current["end"]
            while end_idx < len(text) and (text[end_idx].isalnum() or text[end_idx] == '-'):
                end_idx += 1
            current["end"] = end_idx
            groups.append(current)

        return groups

    def _run_ner(self, text: str) -> list[dict]:
        """Run the NER pipeline and normalise output to entity_group dicts.
        If the output already has 'entity_group', it was aggregated by the pipeline.
        Otherwise it's raw BIO tokens (from the ONNX quantized model).
        """
        raw = self._ner(text)
        if not raw:
            return raw
        
        if "entity_group" in raw[0]:
            return raw
        
        return self._aggregate_bio_tokens(raw, text)

    def extract_batch(
        self, texts: list[str], batch_size: int = 64
    ) -> list[ExtractionResult]:
        """
        Batch extraction. Each text is chunked independently so that long
        narratives do not exceed the model's context window.
        """
        return [self.extract(t) for t in texts]


    def _build_result(self, text: str, ner_output: list[dict]) -> ExtractionResult:
        """
        Run through the blank pipeline (sentencizer sets boundaries for ConText).
        Normalise to uppercase with underscores to match _GROUP_TO_ROLE keys.
        aggregation_strategy="simple" strips BIO prefix; handle both cases.
        """
        doc     = self._nlp(text)
        drugs:    list[ExtractedEntity] = []
        diseases: list[ExtractedEntity] = []
        spans = []

        for ent in ner_output:
            raw_group = ent.get("entity_group", ent.get("entity", ""))

            
            group = raw_group.upper().lstrip("BI-").replace("-", "_").replace(" ", "_")
            label = _GROUP_TO_ROLE.get(group)
            if label is None:
                continue

            start     = ent["start"]
            end       = ent["end"]
            span_text = text[start:end]

            span = doc.char_span(start, end, label=label, alignment_mode="expand")
            if span is not None:
                spans.append(span)

            entity = ExtractedEntity(
                text=span_text,
                label=label,
                start_char=start,
                end_char=end,
            )
            if label == "DRUG":
                drugs.append(entity)
            else:
                diseases.append(entity)

        doc.set_ents(filter_spans(spans))
        return ExtractionResult(drugs=drugs, diseases=diseases, doc=doc)
