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
        Direct causal wording or explicit causality assessment.

    EVENT_ASSOCIATION:
        A structured exposure/suspect-medication relationship.

    PROXIMITY:
        Entities are close but the text does not establish a
        meaningful pharmacovigilance relationship.

    NONE:
        No defensible relationship.
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
    Constructs pharmacovigilance events from extracted entities.

    The relationship layer distinguishes:

        1. clinical event identification,
        2. drug exposure / event association,
        3. explicit causal language,
        4. explicit negative causality,
        5. medication-role scope,
        6. event consolidation.

    This prevents simple drug/event co-occurrence from becoming
    a pharmacovigilance relationship.
    """

    EXPLICIT_PATTERNS = [
        re.compile(r"\binduced\s+by\b", re.IGNORECASE),
        re.compile(r"\bdue\s+to\b", re.IGNORECASE),
        re.compile(r"\bcaused\s+by\b", re.IGNORECASE),
        re.compile(r"\bsecondary\s+to\b", re.IGNORECASE),
        re.compile(r"\battributable\s+to\b", re.IGNORECASE),
    ]

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
        re.compile(r"\btreated\s+with\b", re.IGNORECASE),
        re.compile(r"\bafter\b", re.IGNORECASE),
    ]

    INDICATION_PATTERNS = [
        re.compile(r"\bfor\s+(?:a|an|the)?\s*$", re.IGNORECASE),
        re.compile(r"\bhistory\s+of\s*$", re.IGNORECASE),
        re.compile(r"\btreated\s+for\s*$", re.IGNORECASE),
        re.compile(r"\btreatment\s+of\s*$", re.IGNORECASE),
        
    ]

    THERAPEUTIC_PATTERNS = [
        re.compile(r"\bbeneficial\s+in\b", re.IGNORECASE),
        re.compile(r"\bsuccessfully\s+treated\b", re.IGNORECASE),
        re.compile(r"\beffective\s+for\b", re.IGNORECASE),
        re.compile(r"\bresponded\s+to\s+treatment\b", re.IGNORECASE),
        re.compile(r"\btherapeutic\s+response\b", re.IGNORECASE),
    ]

    CAUSALITY_PATTERNS = [
        re.compile(
            r"(?:investigator|authority|reviewer|assessor|committee|"
            r"regulator|sponsor|physician|doctor|clinician)\s+"
            r"(?:considered|judged|assessed|determined)\s+"
            r"the\s+event\s+(?:to\s+be\s+)?"
            r"(not(?:\s+likely)?|possibly|probably|likely)\s+"
            r"related\s+to\s+(?:the\s+)?"
            r"(?:study\s+)?(?:drug|medications?)",
            re.IGNORECASE,
        ),
    ]

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
        re.compile(r"(died\s+from)", re.IGNORECASE),
        re.compile(r"\b(improved)\b", re.IGNORECASE),
        re.compile(r"\b(resolved)\b", re.IGNORECASE),
        re.compile(r"\b(persisted)\b", re.IGNORECASE),
    ]

    _SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|(?:\r?\n)+")

    # Explicit statements that an exposure predates the event.
    HISTORICAL_EXPOSURE_PATTERNS = (
        "stopped before",
        "stopped prior to",
        "discontinued before",
        "discontinued prior to",
        "ended before",
        "ended prior to",
        "had been stopped",
        "had been discontinued",
        "no longer receiving",
        "no longer taking",
        "previously received",
        "previously treated with",
    )

    # These indicate that a drug is being described as an exposure
    # associated with the event, without asserting causality.
    EXPOSURE_PATTERNS = (
        "after starting",
        "after taking",
        "after receiving",
        "after initiating",
        "following treatment with",
        "following administration of",
        "while receiving",
        "while taking",
        "while using",
        "during treatment with",
        "during therapy with",
        "at the time of the event",
        "at the time of onset",
        "when the event occurred",
        "when the event developed",
        "receiving",
        "taking",
        "using",
        "on treatment with",
        "treated with",
    )

    # Medication-role predicates. Their scope is deliberately local.
    SUSPECT_MEDICATION_PATTERNS = (
        "suspect medication",
        "suspect medications",
        "suspected medication",
        "suspected medications",
        "suspect drug",
        "suspect drugs",
        "suspected drug",
        "suspected drugs",
    )

    CONCOMITANT_MEDICATION_PATTERNS = (
        "concomitant medication",
        "concomitant medications",
        "concomitant drug",
        "concomitant drugs",
        "other medications",
        "other medication",
        "background medication",
        "background medications",
    )

    
    # NER classes that represent clinical findings capable of becoming
    # pharmacovigilance event candidates.
    #
    # Disease_disorder is the strongest general-purpose event class.
    # Sign_symptom represents symptoms/signs that may also constitute
    # reportable adverse events.
    #
    # Clinical_event is intentionally excluded from automatic event
    # construction. It contains procedural/action concepts such as
    # "withdrawn" and "hospitalized" that may be clinically important
    # but are not themselves adverse-event concepts.
    EVENT_CANDIDATE_RAW_LABELS = frozenset(
        {
            "DISEASE_DISORDER",
            "SIGN_SYMPTOM",
        }
    )

    # Biomedical NER classes that should not become PV events simply
    # because they were normalized into the broad DISEASE role.
    EXCLUDED_EVENT_RAW_LABELS = frozenset(
        {
            "CLINICAL_EVENT",
        }
    )



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
        # Separate usable findings from excluded findings
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

            raw_label = (
                disease.raw_label.strip().upper()
                if getattr(disease, "raw_label", None)
                else ""
            )

            # If raw-label information is available, use it to determine
            # whether this biomedical entity can represent an event.
            #
            # The fallback preserves compatibility with older
            # ExtractedEntity objects that do not contain raw_label.
            if raw_label:
                if raw_label not in self.EVENT_CANDIDATE_RAW_LABELS:
                    excluded_findings.append(
                        {
                            "text": disease.text,
                            "reason": f"Non-event NER class: {raw_label}",
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
        # Consolidate repeated/overlapping clinical mentions
        # --------------------------------------------------------------

        effects = self._consolidate_effects(effects, text)

        # --------------------------------------------------------------
        # Build one event per clinically meaningful effect
        # --------------------------------------------------------------

        for effect in effects:
            sentence_text = self._sentence_for_entity(effect, text)

            is_therapeutic = self._is_therapeutic_event(
                effect,
                sentence_text,
                text,
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

            best_indication = self._best_indication(
                effect,
                indications,
                text,
            )

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

        # Explicit causality assessments may occur after the event sentence.
        # Resolve only explicit event-reference constructions; do not use
        # unrestricted cross-sentence proximity.
        self._apply_explicit_event_reference_causality(
            events,
            result.drugs,
            text,
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
        """
        Determine the relationship between one drug and one event.

        The decision hierarchy is:

            1. entity/context exclusion
            2. historical exposure exclusion
            3. explicit negative causality
            4. explicit positive causality
            5. suspect-medication scope
            6. strong same-sentence causal/exposure evidence
            7. no relationship

        Ordinary drug-event association requires the drug and event to occur
        within the same sentence. Explicit causality, suspect-medication
        declarations, and historical-exposure exclusions are handled separately
        because they may legitimately span sentence boundaries.
        """

        # --------------------------------------------------------------
        # 1. Entity-level exclusion
        # --------------------------------------------------------------

        if (
            not getattr(drug, "is_current", True)
            or getattr(drug, "negated", False)
            or getattr(drug, "historical", False)
            or getattr(drug, "hypothetical", False)
            or getattr(drug, "other_experiencer", False)
        ):
            return RelationLevel.NONE, None

        if (
            not getattr(effect, "is_current", True)
            or getattr(effect, "negated", False)
            or getattr(effect, "historical", False)
            or getattr(effect, "hypothetical", False)
            or getattr(effect, "other_experiencer", False)
        ):
            return RelationLevel.NONE, None

        if drug.start_char is None or drug.end_char is None:
            return RelationLevel.NONE, None

        if effect.start_char is None or effect.end_char is None:
            return RelationLevel.NONE, None

        drug_text = drug.text.strip().lower()
        effect_text = effect.text.strip().lower()
        lower_text = text.lower()

        # --------------------------------------------------------------
        # 2. Historical exposure exclusion
        # --------------------------------------------------------------

        historical_relation = self._historical_exposure_relation(
            drug,
            effect,
            lower_text,
        )

        if historical_relation:
            return RelationLevel.NONE, None

        # --------------------------------------------------------------
        # 3. Explicit negative causality
        # --------------------------------------------------------------

        negative_relation = self._negative_causality_relation(
            drug,
            lower_text,
        )

        if negative_relation:
            return RelationLevel.NONE, None

        # --------------------------------------------------------------
        # 4. Explicit positive causality
        # --------------------------------------------------------------

        positive_relation = self._positive_causality_relation(
            drug,
            lower_text,
        )

        if positive_relation:
            return RelationLevel.EXPLICIT, positive_relation

        # --------------------------------------------------------------
        # 5. Suspect-medication scope
        # --------------------------------------------------------------

        suspect_relation = self._suspect_medication_relation(
            drug,
            effect,
            text,
        )

        if suspect_relation:
            return suspect_relation

        # --------------------------------------------------------------
        # 6. Same-sentence evidence
        # --------------------------------------------------------------

        sentence_context = self._sentence_context_for_pair(
            drug,
            effect,
            text,
        )

        # If the drug and event are in different sentences, ordinary
        # exposure/association evidence is not sufficient to link them.
        if sentence_context is None:
            return RelationLevel.NONE, None

        relation = self._same_sentence_relation(
            drug_text,
            effect_text,
            sentence_context,
        )

        if relation:
            return relation

        # --------------------------------------------------------------
        # 7. No relationship
        # --------------------------------------------------------------

        return RelationLevel.NONE, None


    # ==================================================================
    # Negative causality
    # ==================================================================

    def _negative_causality_relation(
        self,
        drug: ExtractedEntity,
        lower_text: str,
    ) -> bool:
        """
        Detect explicit negative causal assessments referring to a drug.

        Supported constructions include:

            not related to methotrexate
            not likely related to methotrexate
            not considered related to methotrexate
            unrelated to methotrexate

        Generic statements such as "not related to the study drug" are
        intentionally handled conservatively because they do not identify
        which extracted drug is being referenced when several drugs exist.
        """

        drug_text = drug.text.strip().lower()

        patterns = (
            "not likely related to",
            "not related to",
            "not considered related to",
            "not considered to be related to",
            "unrelated to",
        )

        start = max(0, drug.start_char - 350)
        end = min(len(lower_text), drug.end_char + 150)

        context = lower_text[start:end]

        for pattern in patterns:
            position = context.find(pattern)

            while position != -1:
                absolute_position = start + position

                after = lower_text[
                    absolute_position + len(pattern):
                    absolute_position + len(pattern) + 120
                ]

                if re.search(
                    rf"\b{re.escape(drug_text)}\b",
                    after,
                ):
                    return True

                position = context.find(
                    pattern,
                    position + 1,
                )

        return False

    # ==================================================================
    # Positive causality
    # ==================================================================

    def _positive_causality_relation(
        self,
        drug: ExtractedEntity,
        lower_text: str,
    ) -> Optional[str]:

        drug_text = drug.text.strip().lower()

        patterns = (
            "possibly related to",
            "probably related to",
            "likely related to",
            "related to",
        )

        start = max(0, drug.start_char - 350)
        end = min(len(lower_text), drug.end_char + 150)

        context = lower_text[start:end]

        for pattern in patterns:
            position = context.find(pattern)

            while position != -1:
                absolute_position = start + position

                preceding = lower_text[
                    max(0, absolute_position - 40):
                    absolute_position
                ]

                if re.search(
                    r"(?:not|never)\s*$",
                    preceding,
                    re.IGNORECASE,
                ):
                    position = context.find(
                        pattern,
                        position + 1,
                    )
                    continue

                after = lower_text[
                    absolute_position + len(pattern):
                    absolute_position + len(pattern) + 120
                ]

                if re.search(
                    rf"\b{re.escape(drug_text)}\b",
                    after,
                ):
                    return pattern

                position = context.find(
                    pattern,
                    position + 1,
                )

        return None

    # ==================================================================
    # Suspect-medication scope
    # ==================================================================

    def _suspect_medication_relation(
        self,
        drug: ExtractedEntity,
        effect: ExtractedEntity,
        text: str,
    ) -> Optional[tuple[RelationLevel, str]]:

        lower_text = text.lower()
        drug_text = drug.text.strip().lower()

        for predicate in self.SUSPECT_MEDICATION_PATTERNS:
            search_start = max(0, drug.start_char - 500)
            search_end = min(len(text), drug.end_char + 500)

            position = lower_text.find(
                predicate,
                search_start,
                search_end,
            )

            while position != -1:
                scope_start = position + len(predicate)
                scope_end = self._medication_clause_end(
                    lower_text,
                    scope_start,
                )

                scope = lower_text[scope_start:scope_end]

                # The drug must actually occur inside the suspect
                # medication clause.
                if re.search(
                    rf"\b{re.escape(drug_text)}\b",
                    scope,
                ):
                    # Ensure the suspect clause belongs to this event.
                    if self._scope_is_relevant_to_effect(
                        effect,
                        text,
                        position,
                        scope_end,
                    ):
                        return (
                            RelationLevel.EVENT_ASSOCIATION,
                            "suspect medication",
                        )

                position = lower_text.find(
                    predicate,
                    position + len(predicate),
                    search_end,
                )

        return None

    def _medication_clause_end(
        self,
        lower_text: str,
        start: int,
    ) -> int:
        """
        Determine the local end of a medication-role clause.

        Stops at sentence boundaries and common clause transitions.
        This prevents a suspect-medication declaration from swallowing
        later concomitant medications.
        """

        candidates = []

        for marker in (
            ".",
            "!",
            "?",
            "\n",
            ";",
        ):
            position = lower_text.find(marker, start)

            if position != -1:
                candidates.append(position)

        # Coordinating transitions commonly introduce a new medication
        # role or an independent clause.
        for marker in (
            " concomitant medications",
            " concomitant medication",
            " other medications",
            " other medication",
            " background medications",
            " background medication",
        ):
            position = lower_text.find(marker, start)

            if position != -1:
                candidates.append(position)

        if not candidates:
            return len(lower_text)

        return min(candidates)

    
    def _scope_is_relevant_to_effect(
        self,
        effect: ExtractedEntity,
        text: str,
        scope_start: int,
        scope_end: int,
    ) -> bool:
        """
        Determine whether a suspect-medication declaration belongs to
        the supplied clinical event.

        The medication-role declaration itself establishes which drugs
        are suspect. Event relevance is then determined structurally:

        1. Same sentence as the event, or
        2. Explicit event reference in the surrounding sentence, or
        3. A nearby event-trigger sentence referring to the same event.

        Arbitrary character-distance thresholds are deliberately avoided.
        """

        effect_sentence_start, effect_sentence_end = (
            self._sentence_bounds(effect.start_char, text)
        )

        # Case 1: suspect declaration occurs in the same sentence.
        if (
            effect_sentence_start <= scope_start <= effect_sentence_end
            or effect_sentence_start <= scope_end <= effect_sentence_end
        ):
            return True

        # Determine the sentence containing the suspect declaration.
        scope_sentence_start, scope_sentence_end = (
            self._sentence_bounds(scope_start, text)
        )

        scope_sentence = text[
            scope_sentence_start:scope_sentence_end
        ].lower()

        # Case 2: explicit reference to the event.
        effect_reference = re.search(
            rf"\b(?:the|this|that)\s+"
            rf"{re.escape(effect.text.strip())}\b",
            scope_sentence,
            re.IGNORECASE,
        )

        if effect_reference:
            return True

        # Case 3: event-trigger language explicitly appears in the
        # suspect-medication sentence and the actual effect is nearby.
        if self._has_event_trigger(scope_sentence):
            effect_distance = min(
                abs(effect.start_char - scope_sentence_end),
                abs(scope_sentence_start - effect.end_char),
            )

            # This is deliberately a sentence-level relationship rather
            # than an unrestricted character-distance rule. Only adjacent
            # narrative structure is accepted.
            sentence_distance = self._sentence_distance(
                effect_sentence_start,
                scope_sentence_start,
                text,
            )

            if sentence_distance <= 1 and effect_distance <= 1:
                return True

        # Case 4: the suspect declaration is immediately followed by
        # an event sentence. This is common in structured safety narratives.
        if scope_sentence_end <= effect_sentence_start:
            intervening = text[
                scope_sentence_end:effect_sentence_start
            ].strip()

            if not intervening:
                return True

        return False



    # ==================================================================
    # Historical exposure
    # ==================================================================

    def _historical_exposure_relation(
        self,
        drug: ExtractedEntity,
        effect: ExtractedEntity,
        lower_text: str,
    ) -> bool:

        start = max(
            0,
            min(drug.start_char, effect.start_char) - 300,
        )

        end = min(
            len(lower_text),
            max(drug.end_char, effect.end_char) + 300,
        )

        context = lower_text[start:end]

        for pattern in self.HISTORICAL_EXPOSURE_PATTERNS:
            position = context.find(pattern)

            if position == -1:
                continue

            absolute_position = start + position

            # For constructions such as:
            #
            # methotrexate was stopped one year before onset
            #
            # the drug must be associated with the historical predicate,
            # and the event must occur after it.
            pattern_end = absolute_position + len(pattern)

            drug_before_pattern = (
                drug.start_char <= absolute_position
            )

            drug_after_pattern = (
                drug.start_char >= pattern_end
            )

            event_after_pattern = (
                effect.start_char >= pattern_end
            )

            if (
                drug_before_pattern
                and event_after_pattern
            ):
                return True

            if (
                drug_after_pattern
                and effect.start_char >= pattern_end
            ):
                return True

        return False

    # ==================================================================
    # Same-sentence relationship logic
    # ==================================================================

    def _same_sentence_relation(
        self,
        drug_text: str,
        effect_text: str,
        sentence_context: str,
    ) -> Optional[tuple[RelationLevel, str]]:

        # --------------------------------------------------------------
        # Explicit causal language
        # --------------------------------------------------------------

        explicit_patterns = (
            "induced by",
            "caused by",
            "due to",
            "secondary to",
            "attributable to",
        )

        for pattern in explicit_patterns:
            position = sentence_context.find(pattern)

            if position == -1:
                continue

            after_pattern = sentence_context[
                position + len(pattern):
            ]

            if re.search(
                rf"\b{re.escape(drug_text)}\b",
                after_pattern,
            ):
                return (
                    RelationLevel.EXPLICIT,
                    pattern,
                )

        # --------------------------------------------------------------
        # Compound causal construction
        # --------------------------------------------------------------

        compound_patterns = (
            f"{drug_text}-induced",
            f"{drug_text} induced",
            f"{drug_text}-associated",
            f"{drug_text} associated",
            f"{drug_text}-related",
            f"{drug_text} related",
        )

        for pattern in compound_patterns:
            if pattern in sentence_context:
                evidence = (
                    pattern
                    .replace(drug_text, "", 1)
                    .strip(" -")
                )

                return (
                    RelationLevel.EXPLICIT,
                    evidence,
                )

        # --------------------------------------------------------------
        # Active causal construction
        # --------------------------------------------------------------

        if " caused " in sentence_context:
            position = sentence_context.find(" caused ")

            before = sentence_context[:position]
            after = sentence_context[
                position + len(" caused "):
            ]

            if (
                re.search(
                    rf"\b{re.escape(drug_text)}\b",
                    before,
                )
                and re.search(
                    rf"\b{re.escape(effect_text)}\b",
                    after,
                )
            ):
                return (
                    RelationLevel.EXPLICIT,
                    "caused",
                )

        # --------------------------------------------------------------
        # Temporal/exposure relationship
        # --------------------------------------------------------------

        for pattern in self.EXPOSURE_PATTERNS:
            position = sentence_context.find(pattern)

            if position == -1:
                continue

            before = sentence_context[:position]
            after = sentence_context[
                position + len(pattern):
            ]

            if re.search(
                rf"\b{re.escape(drug_text)}\b",
                after,
            ):
                return (
                    RelationLevel.EVENT_ASSOCIATION,
                    pattern,
                )

            if re.search(
                rf"\b{re.escape(drug_text)}\b",
                before,
            ):
                return (
                    RelationLevel.EVENT_ASSOCIATION,
                    pattern,
                )

        # --------------------------------------------------------------
        # Event verbs
        # --------------------------------------------------------------

        event_patterns = (
            "developed",
            "experienced",
            "suffered",
            "presented with",
            "showed",
            "reported",
        )

        for pattern in event_patterns:
            position = sentence_context.find(pattern)

            if position == -1:
                continue

            before = sentence_context[:position]
            after = sentence_context[
                position + len(pattern):
            ]

            if (
                re.search(
                    rf"\b{re.escape(drug_text)}\b",
                    before,
                )
                or re.search(
                    rf"\b{re.escape(drug_text)}\b",
                    after,
                )
            ):
                return (
                    RelationLevel.EVENT_ASSOCIATION,
                    pattern,
                )

        return None

    # ==================================================================
    # Cross-sentence exposure logic
    # ==================================================================

    def _cross_sentence_exposure_relation(
        self,
        drug: ExtractedEntity,
        effect: ExtractedEntity,
        text: str,
    ) -> Optional[tuple[RelationLevel, str]]:

        """
        Connect an exposure statement to a nearby event without using
        unrestricted proximity.

        Example:

            The patient was receiving methotrexate.
            He subsequently developed squamous cell carcinoma.

        This is an event association.

        A drug merely appearing somewhere earlier in the narrative is
        not sufficient.
        """

        drug_sentence_start, drug_sentence_end = (
            self._sentence_bounds(drug.start_char, text)
        )

        effect_sentence_start, effect_sentence_end = (
            self._sentence_bounds(effect.start_char, text)
        )

        if (
            drug_sentence_start == effect_sentence_start
            and drug_sentence_end == effect_sentence_end
        ):
            return None

        sentence_distance = self._sentence_distance(
            drug_sentence_start,
            effect_sentence_start,
            text,
        )

        if sentence_distance > 2:
            return None

        drug_sentence = text[
            drug_sentence_start:drug_sentence_end
        ].lower()

        effect_sentence = text[
            effect_sentence_start:effect_sentence_end
        ].lower()

        drug_text = drug.text.strip().lower()
        effect_text = effect.text.strip().lower()

        # --------------------------------------------------------------
        # Exposure sentence
        # --------------------------------------------------------------

        exposure_evidence = None

        for pattern in self.EXPOSURE_PATTERNS:
            if pattern in drug_sentence:
                if re.search(
                    rf"\b{re.escape(drug_text)}\b",
                    drug_sentence,
                ):
                    exposure_evidence = pattern
                    break

        if exposure_evidence is None:
            # Common clinical construction:
            #
            # "The patient was receiving methotrexate..."
            #
            # already covered by "receiving", but this explicit check
            # makes the grammatical role clear.
            if re.search(
                rf"\b(?:receiving|taking|using|on)\s+"
                rf"{re.escape(drug_text)}\b",
                drug_sentence,
            ):
                exposure_evidence = "drug exposure"

        if exposure_evidence is None:
            return None

        # --------------------------------------------------------------
        # Event sentence must contain an event trigger or temporal
        # development language.
        # --------------------------------------------------------------

        event_trigger = re.search(
            r"\b(?:developed|experienced|suffered|"
            r"presented\s+with|reported|diagnosed\s+with|"
            r"was\s+diagnosed\s+with|occurred|onset)\b",
            effect_sentence,
            re.IGNORECASE,
        )

        effect_present = re.search(
            rf"\b{re.escape(effect_text)}\b",
            effect_sentence,
        )

        if not effect_present:
            return None

        if not event_trigger:
            return None

        # --------------------------------------------------------------
        # Directionality:
        #
        # Exposure before event is the safest cross-sentence pattern.
        # Event followed by an explicit "receiving..." sentence is also
        # acceptable when the exposure clearly refers to the event.
        # --------------------------------------------------------------

        if drug.start_char < effect.start_char:
            return (
                RelationLevel.EVENT_ASSOCIATION,
                exposure_evidence,
            )

        if (
            effect.start_char < drug.start_char
            and sentence_distance <= 1
            and re.search(
                r"\b(?:at\s+the\s+time|when|while|during)\b",
                drug_sentence,
                re.IGNORECASE,
            )
        ):
            return (
                RelationLevel.EVENT_ASSOCIATION,
                exposure_evidence,
            )

        return None

    # ==================================================================
    # Therapeutic event logic
    # ==================================================================

    def _is_therapeutic_event(
        self,
        effect: ExtractedEntity,
        sentence_text: str,
        text: str,
    ) -> bool:

        if re.search(
            r"\b(?:improved|resolved|persisted)\b",
            sentence_text,
            re.IGNORECASE,
        ):
            return any(
                pattern.search(sentence_text)
                for pattern in self.THERAPEUTIC_PATTERNS
            )

        return any(
            pattern.search(sentence_text)
            for pattern in self.THERAPEUTIC_PATTERNS
        )

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
            sentence_start:disease.start_char
        ]

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
    # Explicit event-reference causality
    # ==================================================================

    def _apply_explicit_event_reference_causality(
        self,
        events: list[PharmacovigilanceEvent],
        drugs: list[ExtractedEntity],
        text: str,
    ) -> None:
        """
        Resolve explicit causality assessments that refer to "the event".

        This is discourse-level evidence, not generic cross-sentence
        proximity. The statement must explicitly identify the event and
        explicitly name one of the extracted drugs.
        """
        if not events or not drugs:
            return

        pattern = re.compile(
            r"\\b(?:considered|judged|assessed|determined)\\s+"
            r"(?:the|this|that)\\s+event\\s+"
            r"(?:to\\s+be\\s+)?"
            r"(?P<assessment>not\\s+likely|possibly|probably|likely|not)"
            r"\\s+related\\s+to\\b",
            re.IGNORECASE,
        )

        for match in pattern.finditer(text):
            assessment = match.group("assessment").strip().lower()

            # The drug must be explicitly named immediately after the
            # causality construction. Do not infer it from general proximity.
            statement_tail = text[match.end():match.end() + 120]
            matched_drugs = [
                drug
                for drug in drugs
                if re.search(
                    rf"\\b{re.escape(drug.text.strip())}\\b",
                    statement_tail,
                    re.IGNORECASE,
                )
            ]

            if len(matched_drugs) != 1:
                continue

            # Resolve "the event" conservatively. Prefer a unique event that
            # already has an explicit outcome; otherwise prefer a unique
            # disease/disorder event. If neither makes the reference unique,
            # leave the causality unresolved rather than guessing.
            with_outcome = [event for event in events if event.outcome]

            if len(with_outcome) == 1:
                target = with_outcome[0]
            else:
                disease_events = [
                    event
                    for event in events
                    if getattr(event.effect, "raw_label", "").strip().upper()
                    == "DISEASE_DISORDER"
                ]

                if len(disease_events) == 1:
                    target = disease_events[0]
                elif len(events) == 1:
                    target = events[0]
                else:
                    continue

            target.causality = assessment
            drug = matched_drugs[0]

            existing = next(
                (
                    relation
                    for relation in target.relations
                    if relation.drug.text.strip().casefold()
                    == drug.text.strip().casefold()
                ),
                None,
            )

            if existing is not None:
                existing.level = RelationLevel.EXPLICIT
                existing.evidence = "explicit event causality assessment"
            else:
                target.relations.append(
                    DrugEffectRelation(
                        drug=drug,
                        effect=target.effect,
                        level=RelationLevel.EXPLICIT,
                        evidence="explicit event causality assessment",
                    )
                )

            if not any(
                existing_drug.text.strip().casefold()
                == drug.text.strip().casefold()
                for existing_drug in target.drugs
            ):
                target.drugs.append(drug)

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

        sentence = text[
            sentence_start:sentence_end
        ]

        for pattern in self.OUTCOME_PATTERNS:
            match = pattern.search(sentence)

            if match:
                return match.group(1).strip()

        next_text = text[sentence_end:]

        if not next_text.strip():
            return None

        segments = [
            segment.strip()
            for segment in self._SENTENCE_PATTERN.split(next_text)
            if segment.strip()
        ]

        if not segments:
            return None

        next_sentence = segments[0]

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
        """
        Consolidate NER spans that represent one clinical mention.

        NER identifies candidate biomedical spans; it does not decide whether
        adjacent spans form one clinical expression.  This method therefore
        performs only structurally supported consolidation:

        * exact repeated mentions are deduplicated;
        * overlapping spans are resolved;
        * same-sentence spans forming a continuous clinical phrase are merged.

        The method does not use disease-specific vocabulary such as
        "pneumocystis".  The intervening text must be short, punctuation-free,
        and free of coordinating conjunctions that normally separate findings.
        """
        if not effects:
            return []

        ordered = sorted(
            effects,
            key=lambda x: (
                x.start_char if x.start_char is not None else 0,
                -(x.end_char - x.start_char)
                if x.start_char is not None and x.end_char is not None
                else 0,
            ),
        )

        consolidated: list[ExtractedEntity] = []

        for effect in ordered:
            if not consolidated:
                consolidated.append(effect)
                continue

            merged = False

            for previous in reversed(consolidated[-3:]):
                if (
                    previous.start_char is None
                    or previous.end_char is None
                    or effect.start_char is None
                    or effect.end_char is None
                ):
                    continue

                previous_text = previous.text.strip().lower()
                current_text = effect.text.strip().lower()

                # Exact repeated mention: keep the first canonical span.
                if previous_text == current_text:
                    if effect.start_char >= previous.end_char:
                        between = text[
                            previous.end_char:effect.start_char
                        ]
                        if (
                            len(between) <= 500
                            and not re.search(r"[.!?]", between)
                            and not self._contains_historical_marker(between)
                        ):
                            merged = True
                            break

                # Overlapping candidates represent the same local mention.
                if self._spans_overlap(previous, effect):
                    merged = True
                    break

                # Structurally continuous compound clinical expression.
                if self._can_merge_compound_effects(
                    previous,
                    effect,
                    text,
                ):
                    merged_effect = self._merge_effect_entities(
                        previous,
                        effect,
                        text,
                    )
                    consolidated[-1] = merged_effect
                    merged = True
                    break

            if not merged:
                consolidated.append(effect)

        consolidated = self._remove_contained_effects(
            consolidated,
            text,
        )

        # Repeated exact mentions of the same clinical finding are one event
        # unless the intervening text explicitly marks the later mention as
        # historical. This handles confirmation sentences without collapsing
        # distinct findings that merely happen to be nearby.
        return self._deduplicate_exact_effects(consolidated, text)

    @staticmethod
    def _deduplicate_exact_effects(
        effects: list[ExtractedEntity],
        text: str,
    ) -> list[ExtractedEntity]:
        result: list[ExtractedEntity] = []

        for effect in effects:
            duplicate = False
            for existing in result:
                if (
                    existing.start_char is None
                    or existing.end_char is None
                    or effect.start_char is None
                    or effect.end_char is None
                ):
                    continue

                if (
                    existing.text.strip().casefold()
                    != effect.text.strip().casefold()
                ):
                    continue

                if effect.start_char <= existing.end_char:
                    duplicate = True
                    break

                between = text[
                    existing.end_char:effect.start_char
                ]

                if not EventBuilder._contains_historical_marker(between):
                    duplicate = True
                    break

            if not duplicate:
                result.append(effect)

        return result

    @staticmethod
    def _can_merge_compound_effects(
        previous: ExtractedEntity,
        current: ExtractedEntity,
        text: str,
    ) -> bool:
        """Return True when two same-sentence spans form one compound phrase."""
        if (
            previous.start_char is None
            or previous.end_char is None
            or current.start_char is None
            or current.end_char is None
            or current.start_char < previous.end_char
        ):
            return False

        sentence_start = text.rfind(".", 0, previous.end_char) + 1
        sentence_start = max(
            sentence_start,
            text.rfind("!", 0, previous.end_char) + 1,
            text.rfind("?", 0, previous.end_char) + 1,
        )
        sentence_end_candidates = [
            p for p in (
                text.find(".", current.start_char),
                text.find("!", current.start_char),
                text.find("?", current.start_char),
            )
            if p != -1
        ]
        sentence_end = min(sentence_end_candidates) if sentence_end_candidates else len(text)

        if previous.end_char > sentence_end or current.start_char > sentence_end:
            return False

        between = text[previous.end_char:current.start_char]
        stripped = between.strip()

        # Keep the structural window deliberately narrow.  It should capture
        # modifiers such as "jirovecii" without becoming a general proximity
        # linker between unrelated clinical findings.
        if not stripped or len(stripped) > 40:
            return False

        if re.search(r"[.!?;:]", stripped):
            return False

        if re.search(
            r"\b(?:and|or|but|versus|with|without|followed\s+by)\b",
            stripped,
            re.IGNORECASE,
        ):
            return False

        # A comma generally separates independent findings rather than
        # completing a single noun phrase.
        if "," in stripped:
            return False

        return True

    @staticmethod
    def _merge_effect_entities(
        previous: ExtractedEntity,
        current: ExtractedEntity,
        text: str,
    ) -> ExtractedEntity:
        """Create one entity covering two structurally merged spans."""
        start = min(previous.start_char, current.start_char)
        end = max(previous.end_char, current.end_char)

        return ExtractedEntity(
            text=text[start:end],
            label=previous.label,
            start_char=start,
            end_char=end,
            raw_label=(
                previous.raw_label
                if previous.ner_score >= current.ner_score
                else current.raw_label
            ),
            ner_score=max(previous.ner_score, current.ner_score),
            negated=previous.negated or current.negated,
            historical=previous.historical or current.historical,
            hypothetical=previous.hypothetical or current.hypothetical,
            other_experiencer=(
                previous.other_experiencer
                or current.other_experiencer
            ),
        )

    def _remove_contained_effects(
        self,
        effects: list[ExtractedEntity],
        text: str,
    ) -> list[ExtractedEntity]:

        if len(effects) < 2:
            return effects

        ordered = sorted(
            effects,
            key=lambda x: (
                x.start_char if x.start_char is not None else 0,
                -(x.end_char - x.start_char)
                if x.start_char is not None and x.end_char is not None
                else 0,
            ),
        )

        result: list[ExtractedEntity] = []

        for candidate in ordered:
            if (
                candidate.start_char is None
                or candidate.end_char is None
            ):
                result.append(candidate)
                continue

            candidate_text = candidate.text.strip().lower()

            contained = False

            for existing in result:
                if (
                    existing.start_char is None
                    or existing.end_char is None
                ):
                    continue

                if (
                    existing.start_char <= candidate.start_char
                    and existing.end_char >= candidate.end_char
                    and existing != candidate
                ):
                    existing_text = existing.text.strip().lower()

                    if (
                        candidate_text in existing_text
                        or self._spans_overlap(
                            existing,
                            candidate,
                        )
                    ):
                        contained = True
                        break

            if not contained:
                result.append(candidate)

        return sorted(
            result,
            key=lambda x: (
                x.start_char if x.start_char is not None else 0
            ),
        )

    @staticmethod
    def _spans_overlap(
        first: ExtractedEntity,
        second: ExtractedEntity,
    ) -> bool:

        return (
            first.start_char < second.end_char
            and second.start_char < first.end_char
        )

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

        left_matches = list(
            re.finditer(
                r"[.!?]|\r?\n",
                text[:char_pos],
            )
        )

        if left_matches:
            start = left_matches[-1].end()

        right_match = re.search(
            r"[.!?]|\r?\n",
            text[char_pos:],
        )

        if right_match:
            end = char_pos + right_match.start() + (
                1 if text[
                    char_pos + right_match.start()
                ] in ".!?"
                else 0
            )

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

    def _sentence_context_for_pair(
        self,
        drug: ExtractedEntity,
        effect: ExtractedEntity,
        text: str,
    ) -> Optional[str]:

        first = min(
            drug.start_char,
            effect.start_char,
        )

        last = max(
            drug.end_char,
            effect.end_char,
        )

        between = text[first:last]

        if re.search(
            r"[.!?]|\r?\n",
            between,
        ):
            return None

        start, end = self._sentence_bounds(
            first,
            text,
        )

        return text[start:end].lower()

    def _sentence_distance(
        self,
        first_start: int,
        second_start: int,
        text: str,
    ) -> int:

        if first_start == second_start:
            return 0

        low = min(first_start, second_start)
        high = max(first_start, second_start)

        segment = text[low:high]

        return len(
            re.findall(
                r"[.!?]|\r?\n",
                segment,
            )
        )

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