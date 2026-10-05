"""
Clinical/PV entity extraction pipeline — HuggingFace NER backend.

Default model: d4data/biomedical-ner-all

The production and local ONNX paths both use Hugging Face's
aggregation_strategy="first" so that subword token predictions are
reconstructed using the tokenizer's word-boundary information rather than
custom BIO heuristics.

Model label space (d4data/biomedical-ner-all — BioNLP13CG schema):
    Medication        → DRUG role
    Disease_disorder  → DISEASE role
    Sign_symptom      → DISEASE role
    Clinical_event    → DISEASE role

All other labels are ignored at this stage.

Whether a detected Disease_disorder or Sign_symptom span represents an
adverse event is determined downstream by event/context logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import spacy
from spacy.tokens import Doc
from spacy.util import filter_spans


_GROUP_TO_ROLE: dict[str, str] = {
    "MEDICATION": "DRUG",
    "DISEASE_DISORDER": "DISEASE",
    "SIGN_SYMPTOM": "DISEASE",
    "CLINICAL_EVENT": "DISEASE",
}



@dataclass(frozen=True)
class ExtractedEntity:
    """
    One detected entity span with its original NER semantics and
    downstream context classification.

    `label` is the application's normalized role:
        DRUG / DISEASE

    `raw_label` preserves the model's original biomedical class:
        MEDICATION
        DISEASE_DISORDER
        SIGN_SYMPTOM
        CLINICAL_EVENT
        etc.

    `ner_score` preserves the model confidence for the span.

    Keeping both representations allows downstream event logic to reason
    about semantic distinctions that would otherwise be lost when several
    biomedical classes are collapsed into the same application role.
    """

    text: str
    label: str
    start_char: int
    end_char: int

    raw_label: str = ""
    ner_score: float = 0.0

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

    drugs:
        Spans whose entity group maps to DRUG.

    diseases:
        Spans whose entity group maps to DISEASE. This includes both potential
        adverse events and background conditions.

    doc:
        spaCy Doc with extracted spans assigned to doc.ents.
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
    NER-based entity extraction backed by a HuggingFace token-classification
    model.

    The model is loaded once during construction and reused.

    Local development:
        Uses the repository's quantized ONNX model when available.

    Production / HF Space:
        Uses the configured HuggingFace model directly.

    Both paths deliberately use:
        aggregation_strategy="first"

    This keeps subword aggregation consistent between local and production
    inference and avoids custom reconstruction of BIO tokens.
    """

    DEFAULT_MODEL = "d4data/biomedical-ner-all"

    _ROOT = Path(__file__).parent.parent.parent
    ONNX_MODEL_DIR = str(_ROOT / "models" / "ner_onnx_quantized")

    _MAX_CHUNK_TOKENS: int = 400

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        try:
            from transformers import AutoTokenizer, Pipeline, pipeline as hf_pipeline
            from optimum.onnxruntime import ORTModelForTokenClassification
        except ImportError as exc:
            raise ImportError(
                "transformers/optimum is required for entity extraction. "
                "Install with: pip install transformers optimum[onnxruntime]"
            ) from exc

        import os

        if Path(self.ONNX_MODEL_DIR).exists() and not os.environ.get("SPACE_ID"):
            try:
                print(
                    f"Loading optimized ONNX NER model from "
                    f"{self.ONNX_MODEL_DIR}...",
                    flush=True,
                )

                tokenizer = AutoTokenizer.from_pretrained(
                    self.ONNX_MODEL_DIR
                )

                model_onnx = ORTModelForTokenClassification.from_pretrained(
                    self.ONNX_MODEL_DIR
                )

                self._ner = hf_pipeline(
                    "ner",
                    model=model_onnx,
                    tokenizer=tokenizer,
                    aggregation_strategy="first",
                )

            except Exception as exc:
                print(
                    f"ONNX NER load warning: {exc}. "
                    f"Falling back to native model: {model}...",
                    flush=True,
                )

                self._ner = hf_pipeline(
                    "ner",
                    model=model,
                    aggregation_strategy="first",
                )

        else:
            print(
                f"Loading native PyTorch NER model: {model}...",
                flush=True,
            )

            self._ner = hf_pipeline(
                "ner",
                model=model,
                aggregation_strategy="first",
            )

        # Blank spaCy pipeline is used only to create Doc containers for
        # MedSpaCy ConText and sentence boundaries.
        self._nlp = spacy.blank("en")
        self._nlp.add_pipe("sentencizer")

    def _chunk_text(self, text: str) -> list[tuple[str, int]]:
        """
        Split text into sentence-aligned chunks within the model token budget.

        Returns:
            List of (chunk_text, character_offset) pairs.

        Sentence boundaries are preserved so that context-sensitive processing
        remains meaningful. A single sentence exceeding the token budget is
        passed through as-is as a degenerate edge case.
        """

        doc = self._nlp(text)
        sentences = list(doc.sents)

        chunks: list[tuple[str, int]] = []
        current_sents: list = []
        current_token_count = 0
        chunk_start = 0

        for sent in sentences:
            token_count = len(
                self._ner.tokenizer.tokenize(sent.text)
            )

            if (
                current_sents
                and current_token_count + token_count > self._MAX_CHUNK_TOKENS
            ):
                chunk_end = current_sents[-1].end_char

                chunks.append(
                    (
                        text[chunk_start:chunk_end],
                        chunk_start,
                    )
                )

                chunk_start = sent.start_char
                current_sents = [sent]
                current_token_count = token_count

            else:
                current_sents.append(sent)
                current_token_count += token_count

        if current_sents:
            chunk_end = current_sents[-1].end_char

            chunks.append(
                (
                    text[chunk_start:chunk_end],
                    chunk_start,
                )
            )

        return chunks or [(text, 0)]

    def extract(self, text: str) -> ExtractionResult:
        """
        Detect DRUG and DISEASE spans in a single text.

        Primary inference is performed on sentence-aligned chunks. A secondary
        sentence-level recovery pass is then used to recover target entities that
        may be missed when the same text is presented in a larger context.

        Both passes use the same NER model and the same aggregation strategy.
        The recovery pass does not assign event meaning; it only recovers candidate
        entity spans for downstream context and event processing.
        """

        chunks = self._chunk_text(text)

        merged_ner: list[dict] = []
        seen_spans: set[tuple[int, int]] = set()

        # ------------------------------------------------------------------
        # Pass 1: primary chunk-level inference
        # ------------------------------------------------------------------
        for chunk_text, char_offset in chunks:
            for ent in self._run_ner(chunk_text):
                orig_start = ent["start"] + char_offset
                orig_end = ent["end"] + char_offset

                span_key = (orig_start, orig_end)

                if span_key in seen_spans:
                    continue

                seen_spans.add(span_key)

                merged_ner.append(
                    {
                        **ent,
                        "start": orig_start,
                        "end": orig_end,
                    }
                )

        # ------------------------------------------------------------------
        # Pass 2: sentence-level entity recovery
        #
        # Some biomedical NER predictions are context-sensitive. An entity that
        # is recognized when its sentence is processed independently can be missed
        # when the same sentence is embedded in a longer clinical narrative.
        #
        # We therefore run the same NER model on each sentence and merge only
        # entity spans that were not already recovered by the primary pass.
        # ------------------------------------------------------------------
        doc = self._nlp(text)

        for sent in doc.sents:
            sentence_text = sent.text

            if not sentence_text.strip():
                continue

            for ent in self._run_ner(sentence_text):
                orig_start = ent["start"] + sent.start_char
                orig_end = ent["end"] + sent.start_char

                span_key = (orig_start, orig_end)

                if span_key in seen_spans:
                    continue

                seen_spans.add(span_key)

                merged_ner.append(
                    {
                        **ent,
                        "start": orig_start,
                        "end": orig_end,
                    }
                )

        return self._build_result(
            text,
            merged_ner,
        )

    def _run_ner(self, text: str) -> list[dict]:
        """
        Run NER and return HuggingFace-aggregated entity dictionaries.

        aggregation_strategy="first" guarantees that normal WordPiece/subword
        fragmentation is handled by the Transformers pipeline rather than
        by custom BIO reconstruction.
        """

        return self._ner(text)

    def extract_batch(
        self,
        texts: list[str],
        batch_size: int = 64,
    ) -> list[ExtractionResult]:
        """
        Batch extraction.

        Each text is independently chunked so that long narratives do not
        exceed the model's context window.

        batch_size is retained for API compatibility. The current implementation
        processes each narrative independently because chunking occurs per text.
        """

        return [self.extract(text) for text in texts]

    def _build_result(
        self,
        text: str,
        ner_output: list[dict],
    ) -> ExtractionResult:
        """
        Convert HuggingFace aggregated entities into internal ExtractedEntity
        objects and a spaCy Doc.

        HuggingFace's aggregation_strategy="first" returns entity_group
        directly, so no BIO reconstruction is performed here.
        """

        doc = self._nlp(text)

        drugs: list[ExtractedEntity] = []
        diseases: list[ExtractedEntity] = []
        spans = []

        for ent in ner_output:
            raw_group = ent.get(
                "entity_group",
                ent.get("entity", ""),
            )

            raw_group = str(raw_group).upper().strip()

            # Defensive handling in case a pipeline implementation still
            # returns a BIO-prefixed label.
            if raw_group.startswith("B-") or raw_group.startswith("I-"):
                raw_group = raw_group[2:]

            group = (
                raw_group
                .replace("-", "_")
                .replace(" ", "_")
            )

            label = _GROUP_TO_ROLE.get(group)

            if label is None:
                continue

            start = int(ent["start"])
            end = int(ent["end"])

            span_text = text[start:end]

            span = doc.char_span(
                start,
                end,
                label=label,
                alignment_mode="expand",
            )

            if span is not None:
                spans.append(span)

            
            entity = ExtractedEntity(
                text=span_text,
                label=label,
                start_char=start,
                end_char=end,
                raw_label=group,
                ner_score=float(ent.get("score", 0.0)),
            )


            if label == "DRUG":
                drugs.append(entity)
            else:
                diseases.append(entity)

        doc.set_ents(filter_spans(spans))

        return ExtractionResult(
            drugs=drugs,
            diseases=diseases,
            doc=doc,
        )