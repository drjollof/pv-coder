import pytest

from src.extraction.entities import (
    ExtractionResult,
    ExtractedEntity,
)

from src.extraction.events import (
    EventBuilder,
    EventType,
    RelationLevel,
)

from src.pv.seriousness import SeriousnessClassifier


@pytest.fixture
def builder():
    return EventBuilder()


@pytest.fixture
def seriousness():
    return SeriousnessClassifier()


def entity(text, full_text, label):
    start = full_text.index(text)

    return ExtractedEntity(
        text=text,
        label=label,
        start_char=start,
        end_char=start + len(text),
    )


def test_event_builder_explicit_relation(builder):
    text = (
        "The patient suffered from "
        "methotrexate-induced hepatotoxicity."
    )

    result = ExtractionResult(
        drugs=[
            entity(
                "methotrexate",
                text,
                "DRUG",
            )
        ],
        diseases=[
            entity(
                "hepatotoxicity",
                text,
                "DISEASE",
            )
        ],
    )

    events, _ = builder.build(
        result,
        text,
    )

    assert len(events) == 1

    event = events[0]

    assert event.event_type == EventType.ADVERSE_EVENT

    assert event.effect.text == "hepatotoxicity"

    assert len(event.drugs) == 1

    assert event.drugs[0].text == "methotrexate"

    assert event.relations[0].level == RelationLevel.EXPLICIT


def test_event_builder_temporal_relation(builder):
    text = (
        "After taking aspirin, "
        "the patient developed a severe rash."
    )

    result = ExtractionResult(
        drugs=[
            entity(
                "aspirin",
                text,
                "DRUG",
            )
        ],
        diseases=[
            entity(
                "rash",
                text,
                "DISEASE",
            )
        ],
    )

    events, _ = builder.build(
        result,
        text,
    )

    assert len(events) == 1

    event = events[0]

    assert len(event.drugs) == 1

    assert event.drugs[0].text == "aspirin"

    assert (
        event.relations[0].level
        == RelationLevel.EVENT_ASSOCIATION
    )


def test_unrelated_drug_is_not_linked(builder):
    text = (
        "Her regular medications included "
        "metformin and amlodipine. "
        "Three days after starting amoxicillin, "
        "she developed an itchy rash."
    )

    result = ExtractionResult(
        drugs=[
            entity("metformin", text, "DRUG"),
            entity("amlodipine", text, "DRUG"),
            entity("amoxicillin", text, "DRUG"),
        ],
        diseases=[
            entity("rash", text, "DISEASE"),
        ],
    )

    events, _ = builder.build(
        result,
        text,
    )

    assert len(events) == 1

    event = events[0]

    linked = {
        drug.text.lower()
        for drug in event.drugs
    }

    assert "amoxicillin" in linked

    assert "metformin" not in linked

    assert "amlodipine" not in linked


def test_same_sentence_event_association_can_link(builder):
    text = (
        "The patient developed rash after amoxicillin."
    )

    result = ExtractionResult(
        drugs=[
            entity(
                "amoxicillin",
                text,
                "DRUG",
            )
        ],
        diseases=[
            entity(
                "rash",
                text,
                "DISEASE",
            )
        ],
    )

    events, _ = builder.build(
        result,
        text,
    )

    assert len(events) == 1

    assert len(events[0].drugs) == 1


def test_cross_sentence_proximity_does_not_link(builder):
    text = (
        "The patient was taking amoxicillin. "
        "The patient developed a rash."
    )

    result = ExtractionResult(
        drugs=[
            entity(
                "amoxicillin",
                text,
                "DRUG",
            )
        ],
        diseases=[
            entity(
                "rash",
                text,
                "DISEASE",
            )
        ],
    )

    events, _ = builder.build(
        result,
        text,
    )

    assert len(events) == 1

    assert len(events[0].drugs) == 0


def test_historical_effect_is_excluded(builder):
    text = (
        "The patient developed a rash. "
        "She had a similar rash several years earlier."
    )

    current_start = text.index("rash")

    historical_start = text.index(
        "rash",
        current_start + 1,
    )

    result = ExtractionResult(
        drugs=[],
        diseases=[
            ExtractedEntity(
                "rash",
                "DISEASE",
                current_start,
                current_start + 4,
            ),
            ExtractedEntity(
                "rash",
                "DISEASE",
                historical_start,
                historical_start + 4,
                historical=True,
            ),
        ],
    )

    events, excluded = builder.build(
        result,
        text,
    )

    assert len(events) == 1

    assert events[0].effect.start_char == current_start

    assert any(
        item["reason"] == "Historical finding"
        for item in excluded
    )

def test_outcome_improved_in_following_sentence(builder):
    text = (
        "The patient developed a rash. "
        "The rash improved over the following four days."
    )

    result = ExtractionResult(
        drugs=[],
        diseases=[
            entity(
                "rash",
                text,
                "DISEASE",
            )
        ],
    )

    events, _ = builder.build(
        result,
        text,
    )

    assert len(events) == 1
    assert events[0].outcome == "improved"


def test_outcome_resolved_in_same_sentence(builder):
    text = (
        "The patient developed a rash which resolved "
        "after treatment."
    )

    result = ExtractionResult(
        drugs=[],
        diseases=[
            entity(
                "rash",
                text,
                "DISEASE",
            )
        ],
    )

    events, _ = builder.build(
        result,
        text,
    )

    assert len(events) == 1
    assert events[0].outcome == "resolved"


def test_outcome_for_different_effect_is_not_attached(builder):
    text = (
        "The patient developed a rash. "
        "Her headache improved the next day."
    )

    result = ExtractionResult(
        drugs=[],
        diseases=[
            entity(
                "rash",
                text,
                "DISEASE",
            ),
            entity(
                "headache",
                text,
                "DISEASE",
            ),
        ],
    )

    events, _ = builder.build(
        result,
        text,
    )

    assert len(events) == 2

    rash_event = next(
        event
        for event in events
        if event.effect.text == "rash"
    )

    headache_event = next(
        event
        for event in events
        if event.effect.text == "headache"
    )

    assert rash_event.outcome is None
    assert headache_event.outcome == "improved"


def test_seriousness_classifier(seriousness):
    assert seriousness.is_serious(
        "fatal stroke",
        "Patient had a fatal stroke.",
    )[0]

    assert seriousness.is_serious(
        "death",
        "Death due to cardiac arrest.",
    )[0]

    assert seriousness.is_serious(
        "nausea",
        "Patient developed nausea and was hospitalized.",
    )[0]

    assert not seriousness.is_serious(
        "headache",
        "Patient had a mild headache.",
    )[0]

def test_outcome_following_sentence_refers_to_different_effect(builder):
    text = (
        "The patient developed a rash. "
        "Her headache improved the next day."
    )

    result = ExtractionResult(
        drugs=[],
        diseases=[
            entity("rash", text, "DISEASE"),
            entity("headache", text, "DISEASE"),
        ],
    )

    events, _ = builder.build(result, text)

    rash_event = next(
        event for event in events
        if event.effect.text == "rash"
    )

    headache_event = next(
        event for event in events
        if event.effect.text == "headache"
    )

    assert rash_event.outcome is None
    assert headache_event.outcome == "improved"


def test_outcome_resolved_in_following_sentence(builder):
    text = (
        "The patient developed a rash. "
        "The rash resolved after treatment."
    )

    result = ExtractionResult(
        drugs=[],
        diseases=[
            entity("rash", text, "DISEASE")
        ],
    )

    events, _ = builder.build(result, text)

    assert len(events) == 1
    assert events[0].outcome == "resolved"


def test_outcome_persisted_in_following_sentence(builder):
    text = (
        "The patient developed a rash. "
        "The rash persisted despite treatment."
    )

    result = ExtractionResult(
        drugs=[],
        diseases=[
            entity("rash", text, "DISEASE")
        ],
    )

    events, _ = builder.build(result, text)

    assert len(events) == 1
    assert events[0].outcome == "persisted"


def test_unrelated_following_sentence_does_not_create_outcome(builder):
    text = (
        "The patient developed a rash. "
        "Treatment was continued and the patient was monitored."
    )

    result = ExtractionResult(
        drugs=[],
        diseases=[
            entity("rash", text, "DISEASE")
        ],
    )

    events, _ = builder.build(result, text)

    assert len(events) == 1
    assert events[0].outcome is None