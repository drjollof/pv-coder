"""
Context classification for extracted entity spans.

Uses the MedSpaCy ConText algorithm to detect contextual modifiers —
negation, historical reference, hypothetical/risk language, and
other-experiencer mentions — around entity spans produced by ExtractionPipeline.

ConText propagates modifier labels to any entity within the modifier's
scope window. All attribute lookups on spaCy Span extensions are defensive
(getattr with False defaults) to remain compatible across medspacy patch versions.
"""

from __future__ import annotations

from dataclasses import replace
from enum import IntFlag, auto

import spacy
from spacy.tokens import Doc

try:
    from medspacy.context import ConTextRule
except ImportError as exc:
    raise ImportError(
        "medspacy is required for context filtering. "
        "Install with: pip install medspacy"
    ) from exc

from src.extraction.entities import ExtractedEntity, ExtractionResult


class ContextLabel(IntFlag):
    """Bit-flag encoding of context modifiers that exclude a current-event reading."""
    NEGATED           = auto()
    HISTORICAL        = auto()
    HYPOTHETICAL      = auto()
    OTHER_EXPERIENCER = auto()


# ConText modifier rules tuned for pharmacovigilance narratives.
# Each tuple: (literal_trigger, ConText_category, direction)
#
# ConText categories used here:
#   NEGATED_EXISTENCE  → NEGATED flag
#   HISTORICAL         → HISTORICAL flag
#   HYPOTHETICAL       → HYPOTHETICAL flag
#   POSSIBLE_EXISTENCE → HYPOTHETICAL flag (risk / uncertainty language)
#   FAMILY             → OTHER_EXPERIENCER flag
_PV_CONTEXT_RULES: list[tuple[str, str, str]] = [
    # Historical
    ("history of",           "HISTORICAL",          "FORWARD"),
    ("prior history of",     "HISTORICAL",          "FORWARD"),
    ("previous",             "HISTORICAL",          "FORWARD"),
    ("previously",           "HISTORICAL",          "FORWARD"),
    ("prior",                "HISTORICAL",          "FORWARD"),
    ("past",                 "HISTORICAL",          "FORWARD"),
    ("had",                  "HISTORICAL",          "FORWARD"),
    ("former",               "HISTORICAL",          "FORWARD"),
    ("resolved",             "HISTORICAL",          "BIDIRECTIONAL"),
    ("in the past",          "HISTORICAL",          "BIDIRECTIONAL"),
    # Hypothetical / risk language
    ("risk of",              "HYPOTHETICAL",        "FORWARD"),
    ("risk for",             "HYPOTHETICAL",        "FORWARD"),
    ("may cause",            "HYPOTHETICAL",        "FORWARD"),
    ("can cause",            "HYPOTHETICAL",        "FORWARD"),
    ("could cause",          "HYPOTHETICAL",        "FORWARD"),
    ("potential",            "HYPOTHETICAL",        "FORWARD"),
    ("associated with risk", "HYPOTHETICAL",        "FORWARD"),
    ("to prevent",           "HYPOTHETICAL",        "FORWARD"),
    ("if untreated",         "HYPOTHETICAL",        "FORWARD"),
    ("may develop",          "HYPOTHETICAL",        "FORWARD"),
    # Possible / uncertain existence (maps to HYPOTHETICAL here)
    ("possible",             "POSSIBLE_EXISTENCE",  "FORWARD"),
    ("probable",             "POSSIBLE_EXISTENCE",  "FORWARD"),
    ("suspected",            "POSSIBLE_EXISTENCE",  "FORWARD"),
    ("uncertain",            "POSSIBLE_EXISTENCE",  "FORWARD"),
    # Other-experiencer (family / other patients)
    ("family history",       "FAMILY",              "FORWARD"),
    ("familial",             "FAMILY",              "FORWARD"),
    ("mother",               "FAMILY",              "FORWARD"),
    ("father",               "FAMILY",              "FORWARD"),
    ("sibling",              "FAMILY",              "FORWARD"),
    ("other patients",       "FAMILY",              "FORWARD"),
]

_CATEGORY_TO_FLAG: dict[str, ContextLabel] = {
    "NEGATED_EXISTENCE": ContextLabel.NEGATED,
    "HISTORICAL":        ContextLabel.HISTORICAL,
    "HYPOTHETICAL":      ContextLabel.HYPOTHETICAL,
    "POSSIBLE_EXISTENCE": ContextLabel.HYPOTHETICAL,
    "FAMILY":            ContextLabel.OTHER_EXPERIENCER,
}


class ContextFilter:
    """
    Applies MedSpaCy ConText to ExtractionResult and exposes filtering helpers.

    ConText reads doc.ents (already populated by ExtractionPipeline) and looks
    for modifier triggers in a sliding window around each entity. Extension
    attributes (is_negated, is_historical, etc.) are registered at class level
    when medspacy_context is first added to any pipeline.

    annotate() returns a new ExtractionResult with context flags set.
    filter_current() returns only entities where is_current is True.
    Neither method modifies the input result in-place.
    """

    def __init__(self) -> None:
        self._nlp = spacy.blank("en")
        self._nlp.add_pipe("medspacy_context")

        context_pipe = self._nlp.get_pipe("medspacy_context")
        for literal, category, direction in _PV_CONTEXT_RULES:
            context_pipe.add([ConTextRule(literal, category, direction=direction)])

    def annotate(self, result: ExtractionResult) -> ExtractionResult:
        """
        Run ConText on result.doc and return a new ExtractionResult with
        context flags populated on every entity.

        If result.doc is None (e.g. doc not retained during extraction),
        the result is returned unchanged.
        """
        if result.doc is None:
            return result

        # Run only the ConText component on the existing Doc.
        # The Doc's ents are already set by ExtractionPipeline.
        self._nlp.get_pipe("medspacy_context")(result.doc)

        return ExtractionResult(
            drugs=[self._apply_flags(e, result.doc) for e in result.drugs],
            diseases=[self._apply_flags(e, result.doc) for e in result.diseases],
            doc=result.doc,
        )

    def filter_current(self, result: ExtractionResult) -> ExtractionResult:
        """Annotate and then discard any entity where is_current is False."""
        annotated = self.annotate(result)
        return ExtractionResult(
            drugs=[e for e in annotated.drugs if e.is_current],
            diseases=[e for e in annotated.diseases if e.is_current],
            doc=annotated.doc,
        )

    def _apply_flags(self, entity: ExtractedEntity, doc: Doc) -> ExtractedEntity:
        """
        Map ConText extension attributes back to ExtractedEntity context flags.

        Falls back to False for any attribute not registered by the installed
        medspacy version so that the module degrades gracefully on version bumps.
        """
        span = doc.char_span(entity.start_char, entity.end_char)
        if span is None:
            return entity

        return replace(
            entity,
            negated=getattr(span._, "is_negated", False),
            historical=getattr(span._, "is_historical", False),
            hypothetical=getattr(span._, "is_hypothetical", False)
            or getattr(span._, "is_uncertain", False),
            other_experiencer=getattr(span._, "is_family", False),
        )
