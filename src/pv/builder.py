from typing import Optional
import pandas as pd
from pathlib import Path

from src.extraction.entities import ExtractionPipeline
from src.extraction.events import EventBuilder, EventType
from src.normalization.retrieval import HybridRetriever
from src.normalization.lexical import LexicalNormalizer
from src.normalization.embeddings import SemanticNormalizer
from src.normalization.drugs import DrugNormalizer
from src.pv.case_schema import PharmacovigilanceCase, NormalizedEvent, ExtractedDrug
from src.pv.seriousness import SeriousnessClassifier
import time
from src.normalization.synonyms import SynonymNormalizer
from src.extraction.demographics import DemographicsExtractor
from src.extraction.drug_attributes import DrugAttributeExtractor
from src.extraction.context import ContextFilter


class CaseBuilder:
    """
    Orchestrates the end-to-end PV case processing pipeline.

    MedDRA version is stored in the dictionary if available, otherwise default
    In a real scenario, extract from dictionary metadata
    """
    def __init__(self, dict_path: str, faiss_index_path: str = None):
        print("Initializing NER Pipeline...", flush=True)
        self.ner = ExtractionPipeline()
        
        print("Initializing Context Filter...", flush=True)
        self.context_filter = ContextFilter()

        print("Initializing Event Builder...", flush=True)
        self.event_builder = EventBuilder()

        print("Initializing Normalizer...", flush=True)
        dictionary = pd.read_parquet(dict_path)
        self.semantic = SemanticNormalizer(dictionary, faiss_index_path=faiss_index_path)

        print("Initializing Drug Normalizer...", flush=True)
        self.drug_normalizer = DrugNormalizer()

        print("Initializing Seriousness Classifier...", flush=True)
        self.seriousness = SeriousnessClassifier()

        print("Initializing Synonym Normalizer...", flush=True)
        self.synonym_normalizer = SynonymNormalizer()

        print("Initializing Demographics Extractor...", flush=True)
        self.demographics_extractor = DemographicsExtractor()

        print("Initializing Drug Attribute Extractor...", flush=True)
        self.drug_attr_extractor = DrugAttributeExtractor()

        
        self.meddra_version = "27.0 (Default)" 

    def process(self, narrative: str, case_id: str, previous_case_dict: Optional[dict] = None) -> PharmacovigilanceCase:
        """
        Processes a raw clinical narrative into a structured PharmacovigilanceCase.
        If previous_case_dict is provided, processes the narrative as a follow-up and merges it.
        
        Using dict unpacking if demographic data is found, otherwise None
        """
        timings = {}
        t0 = time.time()
        
        print(f"[{case_id}] Extracting demographics...", flush=True)
        demographics_data = self.demographics_extractor.extract(narrative)
        
        from src.pv.case_schema import PatientDemographics
        demographics = PatientDemographics(**demographics_data) if demographics_data else None

        print(f"[{case_id}] Extracting entities...", flush=True)
        candidates = self.ner.extract(narrative)
        candidates = self.context_filter.annotate(candidates)
        t1 = time.time()
        timings["Extraction"] = round(t1 - t0, 3)
        
        print(f"[{case_id}] Building events...", flush=True)
        events, excluded_findings = self.event_builder.build(candidates, narrative)
        t2 = time.time()
        timings["Context"] = round(t2 - t1, 3)
        
        # Handle Follow-up offset logic
        prev_case = None
        offset = 0
        current_version = 1
        if previous_case_dict:
            prev_case = PharmacovigilanceCase(**previous_case_dict)
            offset = len(prev_case.narrative) + len("\n\n--- FOLLOW-UP ---\n\n")
            current_version = prev_case.case_version + 1
            
            # Shift excluded findings
            for exc in excluded_findings:
                if 'start_char' in exc and exc['start_char'] is not None:
                    exc['start_char'] += offset
                if 'end_char' in exc and exc['end_char'] is not None:
                    exc['end_char'] += offset

        adverse_events = [e for e in events if e.event_type == EventType.ADVERSE_EVENT]

        normalized_events = []
        for ae in adverse_events:
            expanded_effect = self.synonym_normalizer.normalize(ae.effect.text)
            norm_results, review_status = self.semantic.match(expanded_effect, top_k=3)

            top_candidates = []
            if norm_results:
                meddra_pt, meddra_pt_id, conf = norm_results[0]
                for pt, pt_id, score in norm_results:
                    top_candidates.append({"pt": pt, "id": pt_id, "score": score})
            else:
                meddra_pt, meddra_pt_id, conf = "Unknown", "Unknown", 0.0

            suspected_drugs = []
            seen_drugs = set()
            for d in ae.drugs:
                d_key = d.text.lower().strip()
                if d_key in seen_drugs:
                    continue
                seen_drugs.add(d_key)
                norm_dict = self.drug_normalizer.normalize(d.text)
                attrs = self.drug_attr_extractor.extract_for_drug(d.end_char, narrative)
                suspected_drugs.append(ExtractedDrug(
                    text=d.text,
                    start_char=d.start_char + offset if d.start_char is not None else None,
                    end_char=d.end_char + offset if d.end_char is not None else None,
                    canonical_name=norm_dict.get('canonical_name') if norm_dict else None,
                    identifiers=norm_dict.get('identifiers') if norm_dict else None,
                    dose=attrs.get("dose"),
                    frequency=attrs.get("frequency"),
                    route=attrs.get("route"),
                    source_version=current_version
                ))

            is_serious, seriousness_reason, seriousness_evidence = self.seriousness.is_serious(ae.effect.text, narrative)

            causality = getattr(ae, 'causality', None)
            outcome = getattr(ae, 'outcome', None)

            normalized_events.append(NormalizedEvent(
                effect_text=ae.effect.text,
                start_char=ae.effect.start_char + offset if ae.effect.start_char is not None else None,
                end_char=ae.effect.end_char + offset if ae.effect.end_char is not None else None,
                meddra_pt=meddra_pt,
                meddra_pt_id=meddra_pt_id,
                confidence_score=conf,
                review_status=review_status,
                top_candidates=top_candidates,
                suspected_drugs=suspected_drugs,
                is_serious=is_serious,
                seriousness_reason=seriousness_reason,
                seriousness_evidence=seriousness_evidence,
                is_speculated=ae.is_speculated,
                causality=causality,
                outcome=outcome,
                source_version=current_version
            ))

        t3 = time.time()
        timings["MedDRA coding"] = round(t3 - t2, 3)

        extracted_drugs = []
        seen_all_drugs = set()
        for d in candidates.drugs:
            d_key = d.text.lower().strip()
            if d_key in seen_all_drugs:
                continue
            seen_all_drugs.add(d_key)
            norm_dict = self.drug_normalizer.normalize(d.text)
            attrs = self.drug_attr_extractor.extract_for_drug(d.end_char, narrative)
            extracted_drugs.append(ExtractedDrug(
                text=d.text,
                start_char=d.start_char + offset if d.start_char is not None else None,
                end_char=d.end_char + offset if d.end_char is not None else None,
                canonical_name=norm_dict.get('canonical_name') if norm_dict else None,
                identifiers=norm_dict.get('identifiers') if norm_dict else None,
                dose=attrs.get("dose"),
                frequency=attrs.get("frequency"),
                route=attrs.get("route"),
                source_version=current_version
            ))

        # Merge with previous case if provided
        final_narrative = narrative
        if prev_case:
            final_narrative = prev_case.narrative + "\n\n--- FOLLOW-UP ---\n\n" + narrative
            normalized_events = prev_case.events + normalized_events
            extracted_drugs = prev_case.extracted_drugs + extracted_drugs
            excluded_findings = prev_case.excluded_findings + excluded_findings
            if prev_case.demographics and not demographics:
                demographics = prev_case.demographics

        # Re-evaluate seriousness for the whole merged case
        is_serious_case = False
        case_seriousness_reason = None
        case_seriousness_evidence = None
        for e in normalized_events:
            if e.is_serious:
                is_serious_case = True
                case_seriousness_reason = e.seriousness_reason
                case_seriousness_evidence = e.seriousness_evidence
                break

        t4 = time.time()
        timings["Case building"] = round(t4 - t3, 3)
        timings["Total"] = round(t4 - t0, 3)

        return PharmacovigilanceCase(
            case_id=case_id,
            narrative=final_narrative,
            events=normalized_events,
            extracted_drugs=extracted_drugs,
            excluded_findings=excluded_findings,
            is_serious_case=is_serious_case,
            case_seriousness_reason=case_seriousness_reason,
            case_seriousness_evidence=case_seriousness_evidence,
            demographics=demographics,
            pipeline_timings=timings,
            meddra_version=self.meddra_version,
            case_version=current_version
        )
