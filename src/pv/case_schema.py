from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class PatientDemographics(BaseModel):
    age: Optional[str] = Field(
        None,
        description="Patient age (e.g. 45, 12 months)",
    )
    gender: Optional[str] = Field(
        None,
        description="Patient gender (e.g. Male, Female)",
    )
    weight: Optional[str] = Field(
        None,
        description="Patient weight (e.g. 70kg)",
    )


class ExtractedDrug(BaseModel):
    text: str = Field(
        ...,
        description="Raw drug text.",
    )
    start_char: Optional[int] = Field(
        None,
        description="Starting character offset in the narrative.",
    )
    end_char: Optional[int] = Field(
        None,
        description="Ending character offset in the narrative.",
    )
    canonical_name: Optional[str] = Field(
        None,
        description="Normalized canonical name of the drug.",
    )
    identifiers: Optional[Dict[str, str]] = Field(
        None,
        description="Dictionary of identifiers like RxNorm.",
    )
    dose: Optional[str] = Field(
        None,
        description="Extracted dose.",
    )
    frequency: Optional[str] = Field(
        None,
        description="Extracted frequency.",
    )
    route: Optional[str] = Field(
        None,
        description="Extracted route.",
    )
    source_version: int = Field(
        default=1,
        description="The case version this drug was extracted in.",
    )


class DrugEventRelation(BaseModel):
    """
    Evidence connecting a drug to a specific event.
    """

    relation_level: str = Field(
        ...,
        description=(
            "Relationship strength: EXPLICIT, "
            "EVENT_ASSOCIATION, PROXIMITY."
        ),
    )

    evidence: Optional[str] = Field(
        None,
        description="Textual evidence supporting the relationship.",
    )


class NormalizedEvent(BaseModel):
    effect_text: str = Field(
        ...,
        description="Raw text span of the extracted adverse event.",
    )
    start_char: Optional[int] = Field(
        None,
        description="Starting character offset in the narrative.",
    )
    end_char: Optional[int] = Field(
        None,
        description="Ending character offset in the narrative.",
    )

    meddra_pt: str = Field(
        ...,
        description="Normalized MedDRA Preferred Term.",
    )
    meddra_pt_id: str = Field(
        ...,
        description="Unique MedDRA PT identifier.",
    )
    confidence_score: float = Field(
        ...,
        description="Normalization confidence score.",
    )
    review_status: str = Field(
        default="Human Review",
        description="Auto-coded or Human Review.",
    )

    top_candidates: List[dict] = Field(
        default_factory=list,
        description="Top MedDRA candidates.",
    )

    suspected_drugs: List[ExtractedDrug] = Field(
        default_factory=list,
        description="Drugs actually linked to this event.",
    )

    drug_relationships: Dict[str, DrugEventRelation] = Field(
        default_factory=dict,
        description=(
            "Relationship evidence for each suspected drug. "
            "Keys are normalized raw drug strings."
        ),
    )

    is_serious: bool = Field(
        ...,
        description="Whether this specific event was classified as serious.",
    )

    seriousness_evidence: Optional[str] = Field(
        None,
        description="Exact phrase triggering the seriousness flag.",
    )

    seriousness_reason: Optional[str] = Field(
        None,
        description="Category of seriousness.",
    )

    is_speculated: bool = Field(
        ...,
        description="Whether the event was hypothetical/speculative.",
    )

    causality: Optional[str] = Field(
        None,
        description="Explicit investigator causality assessment.",
    )

    outcome: Optional[str] = Field(
        None,
        description="Explicit patient outcome for this event.",
    )

    source_version: int = Field(
        default=1,
        description="The case version this event was extracted in.",
    )


class PharmacovigilanceCase(BaseModel):
    case_id: str = Field(
        ...,
        description="Unique identifier for the case.",
    )

    narrative: str = Field(
        ...,
        description="Raw clinical narrative.",
    )

    events: List[NormalizedEvent] = Field(
        default_factory=list,
        description="Normalized events extracted from the narrative.",
    )

    extracted_drugs: List[ExtractedDrug] = Field(
        default_factory=list,
        description="All drugs extracted from the narrative.",
    )

    excluded_findings: List[dict] = Field(
        default_factory=list,
        description=(
            "Negated, historical, hypothetical, or other-experiencer "
            "findings excluded from event construction."
        ),
    )

    is_serious_case: bool = Field(
        ...,
        description="True if ANY event in the case is serious.",
    )

    case_seriousness_reason: Optional[str] = Field(
        None,
        description="Primary reason the case was flagged serious.",
    )

    case_seriousness_evidence: Optional[str] = Field(
        None,
        description="Primary evidence for case seriousness.",
    )

    demographics: Optional[PatientDemographics] = Field(
        None,
        description="Extracted patient demographics.",
    )

    pipeline_timings: Optional[Dict[str, float]] = Field(
        None,
        description="Execution time for each pipeline stage.",
    )

    meddra_version: Optional[str] = Field(
        None,
        description="Loaded MedDRA version.",
    )

    case_version: int = Field(
        default=1,
        description="Version of the case.",
    )