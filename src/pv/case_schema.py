from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class PatientDemographics(BaseModel):
    age: Optional[str] = Field(None, description="Patient age (e.g. 45, 12 months)")
    gender: Optional[str] = Field(None, description="Patient gender (e.g. Male, Female)")
    weight: Optional[str] = Field(None, description="Patient weight (e.g. 70kg)")

class ExtractedDrug(BaseModel):
    text: str = Field(..., description="Raw drug text.")
    start_char: Optional[int] = Field(None, description="Starting character offset in the narrative.")
    end_char: Optional[int] = Field(None, description="Ending character offset in the narrative.")
    canonical_name: Optional[str] = Field(None, description="Normalized canonical name of the drug.")
    identifiers: Optional[Dict[str, str]] = Field(None, description="Dictionary of identifiers like rxnorm.")
    dose: Optional[str] = Field(None, description="Extracted dose (e.g. 50mg)")
    frequency: Optional[str] = Field(None, description="Extracted frequency (e.g. BID, daily)")
    route: Optional[str] = Field(None, description="Extracted route (e.g. PO, IV)")

class NormalizedEvent(BaseModel):
    effect_text: str = Field(..., description="The raw text span of the extracted adverse event.")
    start_char: Optional[int] = Field(None, description="Starting character offset in the narrative.")
    end_char: Optional[int] = Field(None, description="Ending character offset in the narrative.")
    meddra_pt: str = Field(..., description="The normalized MedDRA Preferred Term.")
    meddra_pt_id: str = Field(..., description="The unique MedDRA PT identifier.")
    confidence_score: float = Field(..., description="Normalization confidence score (0-1).")
    review_status: str = Field(default="Human Review", description="Auto-coded or Human Review.")
    top_candidates: List[dict] = Field(default_factory=list, description="Top MedDRA candidates.")
    suspected_drugs: List[ExtractedDrug] = Field(..., description="List of drugs linked to this event.")
    is_serious: bool = Field(..., description="Whether this specific event was classified as serious.")
    seriousness_evidence: Optional[str] = Field(None, description="The exact phrase that triggered the seriousness flag.")
    seriousness_reason: Optional[str] = Field(None, description="The category of seriousness (e.g., Hospitalization, Death).")
    is_speculated: bool = Field(..., description="Whether the event was mentioned hypothetically/speculatively.")
    causality: Optional[str] = Field(None, description="Explicit investigator causality assessment.")
    outcome: Optional[str] = Field(None, description="Explicit patient outcome for this event.")

class PharmacovigilanceCase(BaseModel):
    case_id: str = Field(..., description="Unique identifier for the case.")
    narrative: str = Field(..., description="The raw clinical narrative.")
    events: List[NormalizedEvent] = Field(default_factory=list, description="List of normalized events extracted from the narrative.")
    extracted_drugs: List[ExtractedDrug] = Field(default_factory=list, description="List of drugs extracted from the narrative.")
    excluded_findings: List[dict] = Field(default_factory=list, description="List of negated, historical, or hypothetical findings filtered out.")
    is_serious_case: bool = Field(..., description="True if ANY event in the case is serious.")
    case_seriousness_reason: Optional[str] = Field(None, description="The primary reason this case was flagged as serious.")
    case_seriousness_evidence: Optional[str] = Field(None, description="The primary evidence from the narrative for case seriousness.")
    demographics: Optional[PatientDemographics] = Field(None, description="Extracted patient demographics.")
    pipeline_timings: Optional[Dict[str, float]] = Field(None, description="Execution time for each pipeline stage.")
    meddra_version: Optional[str] = Field(None, description="The loaded MedDRA version.")
