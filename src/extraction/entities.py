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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import spacy
from spacy.util import filter_spans
from spacy.tokens import Doc



# Explicit mapping from model entity_group → internal role.
# Keys are the uppercased entity_group strings returned by the transformers
# pipeline with aggregation_strategy="simple" (i.e., the BIO prefix is stripped).
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
    label: str        # DRUG | DISEASE
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
    """

    drugs: list[ExtractedEntity] = field(default_factory=list)
    diseases: list[ExtractedEntity] = field(default_factory=list)
    doc: Optional[Doc] = field(default=None, compare=False, repr=False)

    def all_entities(self) -> list[ExtractedEntity]:
        return self.drugs + self.diseases

    def current_drugs(self) -> list[ExtractedEntity]:
        return [e for e in self.drugs if e.is_current]

    def current_diseases(self) -> list[ExtractedEntity]:
        """Current-context disease candidates — not yet classified as AE vs. indication."""
        return [e for e in self.diseases if e.is_current]


class ExtractionPipeline:
    """
    NER-based entity extraction backed by a HuggingFace token-classification model.

    The pipeline loads once at construction and is reused across calls. A spaCy
    blank pipeline is used only to create Doc objects so that MedSpaCy ConText
    can operate on the extracted spans.
    """

    DEFAULT_MODEL = "d4data/biomedical-ner-all"
    ONNX_MODEL_DIR = "models/ner_onnx_quantized"

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
            
        # Check if ONNX model exists locally
        if Path(self.ONNX_MODEL_DIR).exists():
            print(f"Loading optimized ONNX NER model from {self.ONNX_MODEL_DIR}...")
            tokenizer = AutoTokenizer.from_pretrained(self.ONNX_MODEL_DIR)
            ort_model = ORTModelForTokenClassification.from_pretrained(self.ONNX_MODEL_DIR)
            
            self._ner: Pipeline = hf_pipeline(
                "ner",
                model=ort_model,
                tokenizer=tokenizer,
                aggregation_strategy="first",
            )
        else:
            print(f"Loading native PyTorch NER model: {model}...")
            self._ner: Pipeline = hf_pipeline(
                "ner",
                model=model,
                aggregation_strategy="first",
            )
            
        # Blank spaCy pipeline used only to create Doc containers for ConText.
        # The sentencizer is required because MedSpaCy ConText uses sentence
        # boundaries to scope modifier propagation.
        self._nlp = spacy.blank("en")
        self._nlp.add_pipe("sentencizer")

    def extract(self, text: str) -> ExtractionResult:
        """
        Detect DRUG and DISEASE spans in a single text.

        Context flags on all returned entities are False. Pass the result
        through ContextFilter to populate them.
        """
        ner_out = self._ner(text)
        return self._build_result(text, ner_out)

    def extract_batch(
        self, texts: list[str], batch_size: int = 64
    ) -> list[ExtractionResult]:
        """
        Batch extraction using HuggingFace pipeline batching.

        The transformers pipeline with a list of inputs returns a list of lists
        (one list of entity dicts per input text).
        """
        all_ner = self._ner(texts, batch_size=batch_size)
        if texts and not isinstance(all_ner[0], list):
            # Single-text edge case — wrap so zip works
            all_ner = [all_ner]
        return [self._build_result(t, ents) for t, ents in zip(texts, all_ner)]

    def _build_result(self, text: str, ner_output: list[dict]) -> ExtractionResult:
        # Run through the blank pipeline (sentencizer sets boundaries for ConText).
        doc     = self._nlp(text)
        drugs:    list[ExtractedEntity] = []
        diseases: list[ExtractedEntity] = []
        spans = []

        for ent in ner_output:
            raw_group = ent.get("entity_group", ent.get("entity", ""))
            # Normalise to uppercase with underscores to match _GROUP_TO_ROLE keys.
            # aggregation_strategy="simple" strips BIO prefix; handle both cases.
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
