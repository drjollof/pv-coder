import pytest
from src.extraction.entities import ExtractionResult, ExtractedEntity
from src.extraction.events import EventBuilder, EventType, RelationLevel
from src.pv.seriousness import SeriousnessClassifier

@pytest.fixture
def builder():
    return EventBuilder()

@pytest.fixture
def seriousness():
    return SeriousnessClassifier()

def test_event_builder_explicit_relation(builder):
    text = "The patient suffered from methotrexate-induced hepatotoxicity."
    result = ExtractionResult(
        drugs=[ExtractedEntity("methotrexate", "DRUG", 26, 38)],
        diseases=[ExtractedEntity("hepatotoxicity", "DISEASE", 47, 61)]
    )
    
    events = builder.build(result, text)
    assert len(events) == 1
    
    ev = events[0]
    assert ev.event_type == EventType.ADVERSE_EVENT
    assert ev.effect.text == "hepatotoxicity"
    assert len(ev.drugs) == 1
    assert ev.drugs[0].text == "methotrexate"
    assert ev.relations[0].level == RelationLevel.EXPLICIT

def test_event_builder_temporal_relation(builder):
    text = "After taking aspirin, the patient developed a severe rash."
    result = ExtractionResult(
        drugs=[ExtractedEntity("aspirin", "DRUG", 13, 20)],
        diseases=[ExtractedEntity("rash", "DISEASE", 53, 57)]
    )
    
    events = builder.build(result, text)
    assert len(events) == 1
    assert events[0].relations[0].level == RelationLevel.EVENT_ASSOCIATION

def test_seriousness_classifier(seriousness):
    assert seriousness.is_serious("fatal stroke", "Patient had a fatal stroke.")
    assert seriousness.is_serious("death", "Death due to cardiac arrest.")
    
    assert seriousness.is_serious("nausea", "Patient developed nausea and was hospitalized.")
    
    assert not seriousness.is_serious("headache", "Patient had a mild headache.")
