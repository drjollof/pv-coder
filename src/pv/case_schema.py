from pydantic import BaseModel, Field
from typing import List, Optional

class NormalizedEvent(BaseModel):
    effect_text: str = Field(..., description="The raw text span of the extracted adverse event.")
    meddra_pt: str = Field(..., description="The normalized MedDRA Preferred Term.")
    meddra_pt_id: str = Field(..., description="The unique MedDRA PT identifier.")
    confidence_score: float = Field(..., description="Normalization confidence score (0-1).")
    review_status: str = Field(default="Human Review", description="Auto-coded or Human Review.")
    top_candidates: List[dict] = Field(default_factory=list, description="Top MedDRA candidates.")
    suspected_drugs: List[str] = Field(..., description="List of drugs linked to this event.")
    is_serious: bool = Field(..., description="Whether this specific event was classified as serious.")
    is_speculated: bool = Field(..., description="Whether the event was mentioned hypothetically/speculatively.")
    causality: Optional[str] = Field(None, description="Explicit investigator causality assessment.")
    outcome: Optional[str] = Field(None, description="Explicit patient outcome for this event.")

class PharmacovigilanceCase(BaseModel):
    case_id: str = Field(..., description="Unique identifier for the case.")
    narrative: str = Field(..., description="The raw clinical narrative.")
    events: List[NormalizedEvent] = Field(default_factory=list, description="List of normalized events extracted from the narrative.")
    is_serious_case: bool = Field(..., description="True if ANY event in the case is serious.")
