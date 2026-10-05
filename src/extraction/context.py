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

        if not list(doc.sents):
            self._nlp.get_pipe("sentencizer")(doc)

        self._nlp.get_pipe("medspacy_context")(doc)

        return ExtractionResult(
            drugs=[self._apply_flags(e, doc, result) for e in result.drugs],
            diseases=[self._apply_flags(e, doc, result) for e in result.diseases],
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
        result: ExtractionResult,
    ) -> ExtractedEntity:
        """
        Combine MedSpaCy context with local pharmacovigilance rules.

        Context modifiers from MedSpaCy are treated as candidate evidence.
        Their scope is validated against the extracted entities before
        assigning historical status.
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

        hypothetical = bool(
            getattr(span._, "is_hypothetical", False)
        )

        other_experiencer = bool(
            getattr(span._, "is_family", False)
        )

        historical = self._historical_context_applies(
            entity=entity,
            span=span,
            doc=doc,
            result=result,
        )

        if self._has_suspected_language_before(span):
            hypothetical = False

        historical = historical or self._entity_has_local_historical_time(
            entity,
            span,
        )

        return replace(
            entity,
            negated=negated,
            historical=historical,
            hypothetical=hypothetical,
            other_experiencer=other_experiencer,
        )

    def _historical_context_applies(
    self,
    entity: ExtractedEntity,
    span,
    doc: Doc,
    result: ExtractionResult,
) -> bool:
        """
        Validate historical ConText modifiers against extracted-entity scope.

        MedSpaCy may attach one forward-scoped modifier to several entities.
        We therefore do not trust span._.is_historical directly.

        A historical modifier applies when:

        1. the modifier occurs before the entity,
        2. the modifier and entity are in the same sentence,
        3. no clause boundary intervenes,
        4. no unrelated extracted entity intervenes.

        Coordinated entities remain eligible when they form part of the
        same local historical phrase.
        """

        modifiers = getattr(span._, "modifiers", ())

        for modifier in modifiers:
            if getattr(modifier, "category", "") != "HISTORICAL":
                continue

            modifier_start = getattr(modifier, "_start", None)
            modifier_end = getattr(modifier, "_end", None)

            if modifier_start is None or modifier_end is None:
                continue

            if modifier_end > span.start:
                continue

            modifier_span = doc[modifier_start:modifier_end]

            if modifier_span.sent.start != span.sent.start:
                continue

            between = doc.text[
                modifier_span.end_char:span.start_char
            ]

            if self._contains_clause_boundary(between):
                continue

            intervening_entities = self._intervening_entities(
                entity,
                modifier_span,
                result,
            )

            if not intervening_entities:
                return True

            if self._is_part_of_same_coordination(
                between,
                intervening_entities,
            ):
                return True

        return False
    @staticmethod
    def _contains_clause_boundary(text: str) -> bool:
        """
        Identify punctuation or discourse markers that normally terminate
        forward contextual scope.
        """

        if re.search(r"[.;:!?]", text):
            return True

        return bool(
            re.search(
                r"\b(?:however|but|then|later|although|although|whereas)\b",
                text,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _intervening_entities(
        entity: ExtractedEntity,
        modifier_span,
        result: ExtractionResult,
    ) -> list[ExtractedEntity]:
        """Return extracted entities between the modifier and target entity."""

        all_entities = [*result.drugs, *result.diseases]

        return sorted(
            [
                candidate
                for candidate in all_entities
                if candidate is not entity
                and candidate.start_char >= modifier_span.end_char
                and candidate.end_char <= entity.start_char
            ],
            key=lambda item: item.start_char,
        )

    @staticmethod
    def _is_part_of_same_coordination(
        between: str,
        intervening_entities: list[ExtractedEntity],
    ) -> bool:
        """
        Allow historical scope to continue through a simple coordinated list.

        Example:
            "history of hypertension and diabetes"

        The conjunction must occur after the intervening entity rather than
        introducing a new clause.
        """

        if not intervening_entities:
            return False

        return bool(
            re.search(
                r"\b(?:and|or)\b",
                between,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _entity_has_local_historical_time(
        entity: ExtractedEntity,
        span,
    ) -> bool:
        """
        Detect temporal historical language local to the entity.

        Unlike the previous implementation, this does not inspect the entire
        sentence. The temporal phrase must occur close to the entity and
        before or immediately after it.
        """

        sentence_text = span.sent.text

        for pattern in _HISTORICAL_TEMPORAL_PATTERNS:
            for match in pattern.finditer(sentence_text):
                absolute_start = span.sent.start_char + match.start()
                absolute_end = span.sent.start_char + match.end()

                distance_before = entity.start_char - absolute_end
                distance_after = absolute_start - entity.end_char

                if 0 <= distance_before <= 80:
                    return True

                if 0 <= distance_after <= 80:
                    return True

        return False

    @staticmethod
    def _has_suspected_language_before(span) -> bool:
        """
        Detect causality-uncertainty wording immediately before an entity.

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