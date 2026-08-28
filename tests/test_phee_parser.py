import pytest
import pandas as pd
from src.data.phee_parser import _extract_text_from_span, _extract_all_drug_texts, _flatten_event

def test_extract_text_from_span():
    assert _extract_text_from_span([["aspirin"]]) == "aspirin"
    assert _extract_text_from_span([["severe"], ["headache"]]) == "severe"
    assert _extract_text_from_span(None) is None
    assert _extract_text_from_span([]) is None
    assert _extract_text_from_span(["not a list of lists"]) == "not a list of lists"

def test_extract_all_drug_texts():
    treatment = {
        "Drug": {
            "text": [["aspirin"], ["ibuprofen", "advil"]]
        }
    }
    assert _extract_all_drug_texts(treatment) == ["aspirin", "ibuprofen", "advil"]
    
    treatment_empty = {"Drug": None}
    assert _extract_all_drug_texts(treatment_empty) == []

def test_flatten_event():
    import json
    event_data = {
        "Trigger": {"text": [["developed"]]},
        "Effect": {"text": [["nausea"]]},
        "Treatment": {"Drug": {"text": [["methotrexate"]]}}
    }
    ev_row = {
        "event_id": "ev1",
        "event_type": "AdverseEvent",
        "event_data": json.dumps(event_data)
    }
    
    res = _flatten_event(ev_row, "row1", "Patient developed nausea on methotrexate.", "train", False)
    
    assert res["id"] == "row1"
    assert res["trigger_text"] == "developed"
    assert res["effect_text"] == "nausea"
    assert res["drug_text_primary"] == "methotrexate"
