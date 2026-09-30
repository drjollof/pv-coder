"""
Context classification for extracted entity spans.

Uses MedSpaCy ConText for contextual modifiers and adds a small set of
pharmacovigilance-specific temporal rules.

Important distinction:
- "historical" means the event did not occur in the current episode.
- "hypothetical" means the event itself is only being described as a
  possibility/risk.
- "suspected" does NOT mean hypothetical. In pharmacovigilance narratives,
  "suspected reaction" normally means the event occurred but causality is
  uncertain.
"""

from __future__ import annotations

import re
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
    """Bit flags for contextual modifiers."""

    NEGATED = auto()
    HISTORICAL = auto()
    HYPOTHETICAL = auto()
    OTHER_EXPERIENCER = auto()


# These rules deliberately avoid broad verbs such as "had".
#
# "The patient had a rash" is a current event.
# "The patient had a rash several years ago" is historical.
#
# Likewise, "suspected reaction" is not hypothetical.
_PV_CONTEXT_RULES: list[tuple[str, str, str]] = [
    # Explicit historical references
    ("history of", "HISTORICAL", "FORWARD"),
    ("prior history of", "HISTORICAL", "FORWARD"),
    ("previous history of", "HISTORICAL", "FORWARD"),
    ("previous", "HISTORICAL", "FORWARD"),
    ("previously", "HISTORICAL", "FORWARD"),
    ("prior", "HISTORICAL", "FORWARD"),
    ("past", "HISTORICAL", "FORWARD"),
    ("former", "HISTORICAL", "FORWARD"),
    ("formerly", "HISTORICAL", "FORWARD"),
    ("previous episode", "HISTORICAL", "FORWARD"),
    ("prior episode", "HISTORICAL", "FORWARD"),
    ("previous occurrence", "HISTORICAL", "FORWARD"),
    ("prior occurrence", "HISTORICAL", "FORWARD"),

    # Hypothetical / risk language
    ("risk of", "HYPOTHETICAL", "FORWARD"),
    ("risk for", "HYPOTHETICAL", "FORWARD"),
    ("may cause", "HYPOTHETICAL", "FORWARD"),
    ("can cause", "HYPOTHETICAL", "FORWARD"),
    ("could cause", "HYPOTHETICAL", "FORWARD"),
    ("potential", "HYPOTHETICAL", "FORWARD"),
    ("associated with risk", "HYPOTHETICAL", "FORWARD"),
    ("to prevent", "HYPOTHETICAL", "FORWARD"),
    ("if untreated", "HYPOTHETICAL", "FORWARD"),
    ("may develop", "HYPOTHETICAL", "FORWARD"),

    # Negation
    ("no", "NEGATED_EXISTENCE", "FORWARD"),
    ("not", "NEGATED_EXISTENCE", "FORWARD"),
    ("denies", "NEGATED_EXISTENCE", "FORWARD"),
    ("denied", "NEGATED_EXISTENCE", "FORWARD"),
    ("without", "NEGATED_EXISTENCE", "FORWARD"),

    # Other experiencer
    ("family history", "FAMILY", "FORWARD"),
    ("familial", "FAMILY", "FORWARD"),
    ("mother", "FAMILY", "FORWARD"),
    ("father", "FAMILY", "FORWARD"),
    ("sibling", "FAMILY", "FORWARD"),
    ("brother", "FAMILY", "FORWARD"),
    ("sister", "FAMILY", "FORWARD"),
    ("other patients", "FAMILY", "FORWARD"),
]


_CATEGORY_TO_FLAG: dict[str, ContextLabel] = {
    "NEGATED_EXISTENCE": ContextLabel.NEGATED,
    "HISTORICAL": ContextLabel.HISTORICAL,
    "HYPOTHETICAL": ContextLabel.HYPOTHETICAL,
    "POSSIBLE_EXISTENCE": ContextLabel.HYPOTHETICAL,
    "FAMILY": ContextLabel.OTHER_EXPERIENCER,
}


# Temporal phrases that are especially useful in PV narratives.
#
# These are applied locally to the entity's sentence rather than globally.
# This prevents "several years earlier" from contaminating unrelated
# entities elsewhere in the narrative.
_HISTORICAL_TEMPORAL_PATTERNS = [
    re.compile(
        r"\b(?:several|many|a few|\d+)\s+years?\s+(?:ago|earlier|before)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:several|many|a few|\d+)\s+months?\s+(?:ago|earlier|before)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:several|many|a few|\d+)\s+weeks?\s+(?:ago|earlier|before)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:several|many|a few|\d+)\s+days?\s+(?:ago|earlier|before)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\byears?\s+earlier\b", re.IGNORECASE),
    re.compile(r"\bmonths?\s+earlier\b", re.IGNORECASE),
    re.compile(r"\bweeks?\s+earlier\b", re.IGNORECASE),
    re.compile(r"\bdays?\s+earlier\b", re.IGNORECASE),
    re.compile(r"\bpreviously\b", re.IGNORECASE),
    re.compile(r"\bprior(?:ly)?\b", re.IGNORECASE),
    re.compile(r"\bprevious\b", re.IGNORECASE),
    re.compile(r"\bin\s+the\s+past\b", re.IGNORECASE),
]


class ContextFilter:
    """
    Applies MedSpaCy ConText and pharmacovigilance-specific temporal rules.

    annotate() returns a new ExtractionResult.

    filter_current() returns only entities considered current.
    """

    def __init__(self) -> None:
        self._nlp = spacy.blank("en")
        self._nlp.add_pipe("sentencizer")
        self._nlp.add_pipe("medspacy_context")

        context_pipe = self._nlp.get_pipe("medspacy_context")

        for literal, category, direction in _PV_CONTEXT_RULES:
            context_pipe.add(
                [ConTextRule(literal, category, direction=direction)]
            )

    def annotate(self, result: ExtractionResult) -> ExtractionResult:
        """
        Apply context flags to all extracted entities.

        The input ExtractionResult is not modified in place.
        """

        if result.doc is None:
            return result

        doc = result.doc

        # Make sure sentence boundaries exist for our local temporal checks.
        # We deliberately do not run the complete pipeline again because
        # result.doc already contains the NER entities.
        if not list(doc.sents):
            self._nlp.get_pipe("sentencizer")(doc)

        # Run MedSpaCy ConText on the existing Doc.
        self._nlp.get_pipe("medspacy_context")(doc)

        return ExtractionResult(
            drugs=[self._apply_flags(e, doc) for e in result.drugs],
            diseases=[self._apply_flags(e, doc) for e in result.diseases],
            doc=doc,
        )

    def filter_current(self, result: ExtractionResult) -> ExtractionResult:
        """Annotate and remove non-current entities."""

        annotated = self.annotate(result)

        return ExtractionResult(
            drugs=[e for e in annotated.drugs if e.is_current],
            diseases=[e for e in annotated.diseases if e.is_current],
            doc=annotated.doc,
        )

    def _apply_flags(
        self,
        entity: ExtractedEntity,
        doc: Doc,
    ) -> ExtractedEntity:
        """
        Combine MedSpaCy context with local temporal rules.

        Important:
        "suspected" is intentionally NOT mapped to hypothetical.
        """

        span = doc.char_span(
            entity.start_char,
            entity.end_char,
            alignment_mode="expand",
        )

        if span is None:
            return entity

        negated = bool(
            getattr(span._, "is_negated", False)
        )

        historical = bool(
            getattr(span._, "is_historical", False)
        )

        hypothetical = bool(
            getattr(span._, "is_hypothetical", False)
        )

        uncertain = bool(
            getattr(span._, "is_uncertain", False)
        )

        other_experiencer = bool(
            getattr(span._, "is_family", False)
        )

        # Do not turn ordinary uncertainty/causality language into
        # hypothetical existence.
        #
        # Example:
        # "The doctor documented the suspected reaction."
        #
        # The reaction exists; its causality is uncertain.
        if self._has_suspected_language_before(span):
            hypothetical = False

        sentence_text = self._sentence_text(span)

        if self._has_historical_temporal_reference(sentence_text):
            historical = True

        return replace(
            entity,
            negated=negated,
            historical=historical,
            hypothetical=hypothetical,
            other_experiencer=other_experiencer,
        )

    @staticmethod
    def _sentence_text(span) -> str:
        """Return the text of the sentence containing the entity."""

        try:
            return span.sent.text
        except (AttributeError, ValueError):
            return ""

    @staticmethod
    def _has_suspected_language_before(span) -> bool:
        """
        Detect causality-uncertainty wording immediately before an entity.

        This is deliberately narrow.

        "suspected reaction" -> reaction is not hypothetical.
        "possible reaction" -> reaction may be hypothetical.
        """

        text = span.doc.text
        start = max(0, span.start_char - 80)
        before = text[start:span.start_char]

        return bool(
            re.search(
                r"\b(?:suspected|considered\s+suspected)\s*$",
                before,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _has_historical_temporal_reference(sentence_text: str) -> bool:
        """Return True if the sentence contains a historical time marker."""

        return any(
            pattern.search(sentence_text)
            for pattern in _HISTORICAL_TEMPORAL_PATTERNS
        )