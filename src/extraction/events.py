from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import re

from src.extraction.entities import ExtractedEntity, ExtractionResult


class EventType(Enum):
    ADVERSE_EVENT = auto()
    POTENTIAL_THERAPEUTIC_EVENT = auto()


class RelationLevel(Enum):
    """
    Strength of evidence connecting a drug to an event.

    EXPLICIT:
        Direct causal wording.

    EVENT_ASSOCIATION:
        Strong event-structure relationship such as:
        "after taking aspirin, developed rash."

    PROXIMITY:
        Entities are close but the text does not establish a
        pharmacovigilance relationship.

    NONE:
        No meaningful relationship.
    """

    EXPLICIT = 1
    EVENT_ASSOCIATION = 2
    PROXIMITY = 3
    NONE = 4


@dataclass
class DrugEffectRelation:
    drug: ExtractedEntity
    effect: ExtractedEntity
    level: RelationLevel
    evidence: Optional[str] = None


@dataclass
class PharmacovigilanceEvent:
    event_type: EventType
    effect: ExtractedEntity
    drugs: list[ExtractedEntity] = field(default_factory=list)
    indication: Optional[ExtractedEntity] = None
    is_speculated: bool = False
    causality: Optional[str] = None
    outcome: Optional[str] = None
    relations: list[DrugEffectRelation] = field(default_factory=list)

    @property
    def is_combination(self) -> bool:
        return len(self.drugs) > 1


class EventBuilder:
    """
    Constructs pharmacovigilance events using event-local evidence.

    The previous implementation linked every extracted drug to every
    extracted adverse event. This implementation only creates a drug-event
    relationship when the surrounding text provides evidence for it.
    """

    # ------------------------------------------------------------------
    # Explicit causal relationships
    # ------------------------------------------------------------------

    EXPLICIT_PATTERNS = [
        re.compile(
            r"\binduced\s+by\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bdue\s+to\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bcaused\s+by\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bsecondary\s+to\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bfollowing\s+(?:administration|infusion|treatment|therapy)"
            r"\s+of\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bafter\s+(?:taking|receiving|starting|initiating)\b",
            re.IGNORECASE,
        ),
    ]

    # ------------------------------------------------------------------
    # Event-association patterns
    # ------------------------------------------------------------------

    EVENT_ASSOCIATION_PATTERNS = [
        re.compile(
            r"\b(?:developed|experienced|suffered|presented\s+with|"
            r"showed|reported)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bafter\s+(?:taking|receiving|starting|initiating)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:following|subsequent\s+to)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\btreated\s+with\b",
            re.IGNORECASE,
        ),

        re.compile(
            r"\bafter\b",
            re.IGNORECASE,
        ),
    ]

    # ------------------------------------------------------------------
    # Indication detection
    # ------------------------------------------------------------------

    INDICATION_PATTERNS = [
        re.compile(
            r"\bfor\s+(?:a|an|the)?\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bhistory\s+of\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"\btreated\s+for\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"\btreatment\s+of\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bdiagnosed\s+with\s*$",
            re.IGNORECASE,
        ),
    ]

    # ------------------------------------------------------------------
    # Therapeutic event detection
    # ------------------------------------------------------------------

    THERAPEUTIC_PATTERNS = [
        re.compile(
            r"\bbeneficial\s+in\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bsuccessfully\s+treated\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bresolved\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bimproved\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bcured\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\beffective\s+for\b",
            re.IGNORECASE,
        ),
    ]

    # ------------------------------------------------------------------
    # Causality assessment
    # ------------------------------------------------------------------

    CAUSALITY_PATTERNS = [
        re.compile(
            r"investigator\s+considered\s+the\s+event\s+"
            r"(not(?:\s+likely)?\s+related\s+to\s+"
            r"(?:the\s+)?(?:study\s+)?(?:drug|medications?))",
            re.IGNORECASE,
        ),
        re.compile(
            r"investigator\s+considered\s+the\s+event\s+"
            r"(related\s+to\s+(?:the\s+)?"
            r"(?:study\s+)?(?:drug|medications?))",
            re.IGNORECASE,
        ),
    ]

    # ------------------------------------------------------------------
    # Outcome
    # ------------------------------------------------------------------

    OUTCOME_PATTERNS = [
        re.compile(
            r"(did\s+not\s+recover"
            r"(?:\s+during\s+the\s+follow-?up\s+period)?)",
            re.IGNORECASE,
        ),
        re.compile(
            r"patient\s+was\s+reported\s+"
            r"(recovered\s+with\s+no\s+sequelae)",
            re.IGNORECASE,
        ),
        re.compile(
            r"patient\s+"
            r"(had\s+not\s+recovered\s+at\s+the\s+time\s+of\s+reporting)",
            re.IGNORECASE,
        ),
        re.compile(
            r"(died\s+from)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(improved)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(resolved)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(persisted)\b",
            re.IGNORECASE,
        ),
    ]

    # Sentence boundaries are deliberately conservative.
    _SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")

    def build(
        self,
        result: ExtractionResult,
        text: str,
    ) -> tuple[list[PharmacovigilanceEvent], list[dict]]:

        events: list[PharmacovigilanceEvent] = []
        effects: list[ExtractedEntity] = []
        indications: list[ExtractedEntity] = []
        excluded_findings: list[dict] = []

        # --------------------------------------------------------------
        # 1. Separate usable findings from excluded findings
        # --------------------------------------------------------------

        for disease in result.diseases:

            if disease.negated:
                excluded_findings.append(
                    {
                        "text": disease.text,
                        "reason": "Negated finding",
                        "start_char": disease.start_char,
                        "end_char": disease.end_char,
                    }
                )
                continue

            if disease.historical:
                excluded_findings.append(
                    {
                        "text": disease.text,
                        "reason": "Historical finding",
                        "start_char": disease.start_char,
                        "end_char": disease.end_char,
                    }
                )
                continue

            if disease.other_experiencer:
                excluded_findings.append(
                    {
                        "text": disease.text,
                        "reason": "Other experiencer",
                        "start_char": disease.start_char,
                        "end_char": disease.end_char,
                    }
                )
                continue

            if disease.hypothetical:
                excluded_findings.append(
                    {
                        "text": disease.text,
                        "reason": "Hypothetical finding",
                        "start_char": disease.start_char,
                        "end_char": disease.end_char,
                    }
                )
                continue

            if self._looks_like_indication(disease, text):
                indications.append(disease)
            else:
                effects.append(disease)

        # --------------------------------------------------------------
        # 2. Consolidate repeated mentions of the same current event
        # --------------------------------------------------------------

        effects = self._consolidate_effects(effects, text)

        # --------------------------------------------------------------
        # 3. Build one event per clinically meaningful effect
        # --------------------------------------------------------------

        for effect in effects:

            sentence_text = self._sentence_for_entity(effect, text)

            is_therapeutic = any(
                pattern.search(sentence_text)
                for pattern in self.THERAPEUTIC_PATTERNS
            )

            event_type = (
                EventType.POTENTIAL_THERAPEUTIC_EVENT
                if is_therapeutic
                else EventType.ADVERSE_EVENT
            )

            relations: list[DrugEffectRelation] = []
            linked_drugs: list[ExtractedEntity] = []

            for drug in result.drugs:

                level, evidence = self._determine_relation(
                    drug,
                    effect,
                    text,
                )

                # NONE means there is no evidence to call the drug a
                # suspected drug for this event.
                if level == RelationLevel.NONE:
                    continue

                relation = DrugEffectRelation(
                    drug=drug,
                    effect=effect,
                    level=level,
                    evidence=evidence,
                )

                relations.append(relation)
                linked_drugs.append(drug)

            # ----------------------------------------------------------
            # Event-local indication
            # ----------------------------------------------------------

            best_indication = self._best_indication(
                effect,
                indications,
                text,
            )

            # ----------------------------------------------------------
            # Event-local causality and outcome
            # ----------------------------------------------------------

            causality = self._extract_local_causality(
                effect,
                text,
            )

            outcome = self._extract_local_outcome(
                effect,
                text,
            )

            events.append(
                PharmacovigilanceEvent(
                    event_type=event_type,
                    effect=effect,
                    drugs=linked_drugs,
                    indication=best_indication,
                    is_speculated=effect.hypothetical,
                    causality=causality,
                    outcome=outcome,
                    relations=relations,
                )
            )

        return events, excluded_findings

    # ==================================================================
    # Relationship logic
    # ==================================================================

    
    def _determine_relation(
        self,
        drug: ExtractedEntity,
        effect: ExtractedEntity,
        text: str,
    ) -> tuple[RelationLevel, Optional[str]]:

        # Exclude drugs that cannot be considered current candidates.
        if (
            not drug.is_current
            or drug.negated
            or drug.historical
            or drug.hypothetical
        ):
            return RelationLevel.NONE, None

        drug_sentence = self._sentence_bounds(
            drug.start_char, text
        )
        effect_sentence = self._sentence_bounds(
            effect.start_char, text
        )

        # Sentence proximity alone is insufficient evidence.
        if drug_sentence != effect_sentence:
            return RelationLevel.NONE, None

        sentence_start, sentence_end = drug_sentence
        sentence = text[sentence_start:sentence_end]

        # Text between the two candidate entities.
        if drug.end_char <= effect.start_char:
            between = text[drug.end_char:effect.start_char]
            drug_precedes_effect = True
        elif effect.end_char <= drug.start_char:
            between = text[effect.end_char:drug.start_char]
            drug_precedes_effect = False
        else:
            return RelationLevel.NONE, None

        # --------------------------------------------------
        # 1. Explicit causal evidence
        # --------------------------------------------------

        causal_patterns = (
            r"\binduced\s+by\b",
            r"\bdue\s+to\b",
            r"\bcaused\s+by\b",
            r"\bsecondary\s+to\b",
            r"\battributable\s+to\b",
        )

        for pattern in causal_patterns:
            match = re.search(
                pattern, between, re.IGNORECASE
            )
            if match:
                return RelationLevel.EXPLICIT, match.group(0)

        # Drug-name compounds, e.g. methotrexate-induced
        # hepatotoxicity.
        if drug_precedes_effect:
            drug_to_effect = text[
                drug.end_char:effect.start_char
            ]
            if re.match(
                r"^\s*-\s*(?:induced|associated)\b",
                drug_to_effect,
                re.IGNORECASE,
            ):
                return RelationLevel.EXPLICIT, "induced"

        # Active causal construction:
        # "amoxicillin caused the rash"
        if drug_precedes_effect and re.search(
            r"\b(?:caused|induced|triggered|provoked)\b",
            between,
            re.IGNORECASE,
        ):
            match = re.search(
                r"\b(?:caused|induced|triggered|provoked)\b",
                between,
                re.IGNORECASE,
            )
            return RelationLevel.EXPLICIT, match.group(0)

        # --------------------------------------------------
        # 2. Local temporal association
        # --------------------------------------------------

        # Examine only the text immediately preceding the
        # candidate drug, within its current sentence.
        prefix_start = max(
            sentence_start,
            drug.start_char - 100,
        )
        drug_prefix = text[prefix_start:drug.start_char]

        # The trigger must be directly connected to this drug:
        # "after taking aspirin"
        # "three days after starting amoxicillin"
        # "following treatment with penicillin"
        temporal_prefix_patterns = (
            r"\b(?:after|following)\s+"
            r"(?:taking|starting|receiving|initiating)\s*$",
            r"\b(?:after|following)\s+"
            r"(?:administration\s+of|treatment\s+with)\s*$",
            r"\b(?:after|following)\s*$",
        )

        for pattern in temporal_prefix_patterns:
            match = re.search(
                pattern,
                drug_prefix,
                re.IGNORECASE,
            )
            if match:
                return (
                    RelationLevel.EVENT_ASSOCIATION,
                    match.group(0).strip(),
                )

        return RelationLevel.NONE, None

    # ==================================================================
    # Indication logic
    # ==================================================================

    def _looks_like_indication(
        self,
        disease: ExtractedEntity,
        text: str,
    ) -> bool:

        sentence_start, _ = self._sentence_bounds(
            disease.start_char,
            text,
        )

        pre_text = text[
            sentence_start:
            disease.start_char
        ]

        # Only inspect the local clause immediately before the finding.
        local_pre = pre_text[-80:]

        return any(
            pattern.search(local_pre)
            for pattern in self.INDICATION_PATTERNS
        )

    def _best_indication(
        self,
        effect: ExtractedEntity,
        indications: list[ExtractedEntity],
        text: str,
    ) -> Optional[ExtractedEntity]:

        if not indications:
            return None

        effect_sentence = self._sentence_bounds(
            effect.start_char,
            text,
        )

        same_sentence = [
            indication
            for indication in indications
            if self._sentence_bounds(
                indication.start_char,
                text,
            ) == effect_sentence
        ]

        if same_sentence:
            return min(
                same_sentence,
                key=lambda x: abs(
                    x.start_char - effect.start_char
                ),
            )

        # Do not pull an indication from an unrelated sentence.
        return None

    # ==================================================================
    # Causality
    # ==================================================================

    def _extract_local_causality(
        self,
        effect: ExtractedEntity,
        text: str,
    ) -> Optional[str]:

        sentence = self._sentence_for_entity(
            effect,
            text,
        )

        for pattern in self.CAUSALITY_PATTERNS:
            match = pattern.search(sentence)

            if match:
                return match.group(1).strip()

        return None

    # ==================================================================
    # Outcome
    # ==================================================================

    def _extract_local_outcome(
    self,
    effect: ExtractedEntity,
    text: str,
) -> Optional[str]:

        sentence_start, sentence_end = self._sentence_bounds(
            effect.start_char,
            text,
        )

        sentence = text[sentence_start:sentence_end]

        # First, check the sentence containing the adverse event.
        for pattern in self.OUTCOME_PATTERNS:
            match = pattern.search(sentence)

            if match:
                return match.group(1).strip()

        # If no outcome is found, inspect the immediately following
        # sentence. Do not attach an outcome unless that sentence
        # explicitly refers back to the same effect.
        next_text = text[sentence_end:]

        boundary = self._SENTENCE_PATTERN.search(next_text)

        if boundary:
            next_sentence_start = boundary.end()
            next_boundary = self._SENTENCE_PATTERN.search(
                next_text,
                next_sentence_start,
            )

            if next_boundary:
                next_sentence = next_text[
                    next_sentence_start:next_boundary.start()
                ].strip()
            else:
                next_sentence = next_text[
                    next_sentence_start:
                ].strip()
        else:
            next_sentence = next_text.strip()

        if not next_sentence:
            return None

        # Require an explicit reference to this effect:
        # "The rash improved..."
        # "This rash resolved..."
        effect_reference = re.search(
            rf"\b(?:the|this|that)\s+"
            rf"{re.escape(effect.text)}\b",
            next_sentence,
            re.IGNORECASE,
        )

        if not effect_reference:
            return None

        for pattern in self.OUTCOME_PATTERNS:
            match = pattern.search(next_sentence)

            if match:
                return match.group(1).strip()

        return None
    # ==================================================================
    # Event consolidation
    # ==================================================================

    def _consolidate_effects(
        self,
        effects: list[ExtractedEntity],
        text: str,
    ) -> list[ExtractedEntity]:

        if not effects:
            return []

        ordered = sorted(
            effects,
            key=lambda x: x.start_char,
        )

        consolidated: list[ExtractedEntity] = []

        for effect in ordered:

            if not consolidated:
                consolidated.append(effect)
                continue

            previous = consolidated[-1]

            same_text = (
                effect.text.strip().lower()
                == previous.text.strip().lower()
            )

            distance = (
                effect.start_char
                - previous.end_char
            )

            # "rash ... the rash improved"
            #
            # Identical effect mentions in adjacent narrative are usually
            # references to the same event rather than separate adverse
            # events.
            if same_text and distance <= 160:

                # Do not consolidate across an explicit historical marker.
                between = text[
                    previous.end_char:
                    effect.start_char
                ]

                if not self._contains_historical_marker(between):
                    continue

            consolidated.append(effect)

        return consolidated

    # ==================================================================
    # Sentence helpers
    # ==================================================================

    def _sentence_bounds(
        self,
        char_pos: int,
        text: str,
    ) -> tuple[int, int]:

        start = 0
        end = len(text)

        left = list(
            re.finditer(
                r"[.!?]",
                text[:char_pos],
            )
        )

        if left:
            start = left[-1].end()

        right = re.search(
            r"[.!?]",
            text[char_pos:],
        )

        if right:
            end = char_pos + right.start() + 1

        return start, end

    def _sentence_for_entity(
        self,
        entity: ExtractedEntity,
        text: str,
    ) -> str:

        start, end = self._sentence_bounds(
            entity.start_char,
            text,
        )

        return text[start:end]

    @staticmethod
    def _has_event_trigger(text: str) -> bool:
        return bool(
            re.search(
                r"\b(?:developed|experienced|suffered|"
                r"presented\s+with|showed|reported)\b",
                text,
                re.IGNORECASE,
            )
        )

    @staticmethod
    def _contains_historical_marker(text: str) -> bool:

        return bool(
            re.search(
                r"\b(?:history\s+of|previous(?:ly)?|prior(?:ly)?|"
                r"past|years?\s+(?:ago|earlier)|"
                r"months?\s+(?:ago|earlier)|"
                r"weeks?\s+(?:ago|earlier)|"
                r"days?\s+(?:ago|earlier))\b",
                text,
                re.IGNORECASE,
            )
        )