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
    EXPLICIT = 1
    EVENT_ASSOCIATION = 2
    PROXIMITY = 3


@dataclass
class DrugEffectRelation:
    drug: ExtractedEntity
    effect: ExtractedEntity
    level: RelationLevel


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
    Constructs PharmacovigilanceEvents from an ExtractionResult using
    contextual triggers and event structure logic.
    """

    # Explicit causal relation patterns — "induced by", "due to", "secondary to", etc.
    L1_PATTERNS = [
        re.compile(r"induced\s+by", re.IGNORECASE),
        re.compile(r"due\s+to", re.IGNORECASE),
        re.compile(r"caused\s+by", re.IGNORECASE),
        re.compile(r"secondary\s+to", re.IGNORECASE),
        re.compile(r"following\s+(?:administration|infusion|treatment|therapy)\s+of", re.IGNORECASE),
    ]

    # Temporal / event association patterns — "developed", "after receiving", etc.
    L2_PATTERNS = [
        re.compile(r"(?:developed|experienced|suffered|presented\s+with|showed).{0,50}", re.IGNORECASE),
        re.compile(r"after\s+(?:taking|receiving|initiation\s+of|starting).{0,50}", re.IGNORECASE),
        re.compile(r"treated\s+with.{0,50}and\s+(?:developed|experienced)", re.IGNORECASE),
    ]

    INDICATION_PATTERNS = [
        re.compile(r"(?:for|history\s+of|treated\s+for|treatment\s+of|diagnosed\s+with)\s+$", re.IGNORECASE),
    ]

    THERAPEUTIC_PATTERNS = [
        re.compile(r"(?:beneficial\s+in|successfully\s+treated|resolved|improved|cured|effective\s+for)", re.IGNORECASE),
    ]

    CAUSALITY_PATTERNS = [
        re.compile(r"investigator\s+considered\s+the\s+event\s+(not(?:\s+likely)?\s+related\s+to\s+(?:the\s+)?(?:study\s+)?(?:drug|medications?))", re.IGNORECASE),
        re.compile(r"investigator\s+considered\s+the\s+event\s+(related\s+to\s+(?:the\s+)?(?:study\s+)?(?:drug|medications?))", re.IGNORECASE),
    ]

    OUTCOME_PATTERNS = [
        re.compile(r"(did\s+not\s+recover(?:\s+during\s+the\s+follow-?up\s+period)?)", re.IGNORECASE),
        re.compile(r"patient\s+was\s+reported\s+(recovered\s+with\s+no\s+sequelae)", re.IGNORECASE),
        re.compile(r"patient\s+(had\s+not\s+recovered\s+at\s+the\s+time\s+of\s+reporting)", re.IGNORECASE),
        re.compile(r"(died\s+from)", re.IGNORECASE)
    ]

    def build(self, result: ExtractionResult, text: str) -> tuple[list[PharmacovigilanceEvent], list[dict]]:
        events = []
        effects = []
        indications = []
        excluded_findings = []

        for disease in result.diseases:
            if disease.negated:
                excluded_findings.append({"text": disease.text, "reason": "Negated finding", "start_char": disease.start_char, "end_char": disease.end_char})
                continue
            if disease.historical:
                excluded_findings.append({"text": disease.text, "reason": "Historical finding", "start_char": disease.start_char, "end_char": disease.end_char})
                continue
            if disease.other_experiencer:
                excluded_findings.append({"text": disease.text, "reason": "Other experiencer", "start_char": disease.start_char, "end_char": disease.end_char})
                continue
            if disease.hypothetical:
                excluded_findings.append({"text": disease.text, "reason": "Hypothetical finding", "start_char": disease.start_char, "end_char": disease.end_char})
                continue

            pre_text = text[max(0, disease.start_char - 30):disease.start_char]
            if any(p.search(pre_text) for p in self.INDICATION_PATTERNS):
                indications.append(disease)
            else:
                effects.append(disease)

        for effect in effects:
            pre_text = text[max(0, effect.start_char - 50):effect.start_char]
            is_therapeutic = any(p.search(pre_text) for p in self.THERAPEUTIC_PATTERNS)
            event_type = EventType.POTENTIAL_THERAPEUTIC_EVENT if is_therapeutic else EventType.ADVERSE_EVENT

            linked_drugs = []
            relations = []
            for drug in result.drugs:
                level = self._determine_relation_level(drug, effect, text)
                linked_drugs.append(drug)
                relations.append(DrugEffectRelation(drug, effect, level))

            best_indication = None
            if indications:
                best_indication = min(indications, key=lambda i: abs(i.start_char - effect.start_char))

            causality = None
            for p in self.CAUSALITY_PATTERNS:
                match = p.search(text)
                if match:
                    causality = match.group(1).strip()
                    break

            outcome = None
            for p in self.OUTCOME_PATTERNS:
                match = p.search(text)
                if match:
                    outcome = match.group(1).strip()
                    break
            if not outcome and "died from" in text.lower():
                outcome = "died"

            events.append(PharmacovigilanceEvent(
                event_type=event_type,
                effect=effect,
                drugs=linked_drugs,
                indication=best_indication,
                is_speculated=effect.hypothetical,
                causality=causality,
                outcome=outcome,
                relations=relations
            ))

        return events, excluded_findings

    def _determine_relation_level(self, drug: ExtractedEntity, effect: ExtractedEntity, text: str) -> RelationLevel:
        start = min(drug.end_char, effect.end_char)
        end = max(drug.start_char, effect.start_char)
        between_text = text[start:end]

        # Adjacency check for "drug-induced" pattern
        if abs(start - end) < 15:
            if re.search(r"induced", text[drug.end_char:drug.end_char + 10], re.IGNORECASE):
                return RelationLevel.EXPLICIT

        if any(p.search(between_text) for p in self.L1_PATTERNS):
            return RelationLevel.EXPLICIT

        if any(p.search(between_text) for p in self.L2_PATTERNS):
            return RelationLevel.EVENT_ASSOCIATION

        return RelationLevel.PROXIMITY
