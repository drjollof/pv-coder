import pytest
from src.extraction.entities import ExtractionPipeline, ExtractionResult, ExtractedEntity
from src.extraction.context import ContextFilter

@pytest.fixture
def pipeline():
    return ExtractionPipeline()

@pytest.fixture
def context_filter():
    return ContextFilter()

def test_pipeline_extraction(pipeline):
    text = "The patient developed severe nausea after taking 500mg of methotrexate."
    result = pipeline.extract(text)
    
    drugs = [d.text.lower() for d in result.drugs]
    assert "methotrexate" in drugs
    
    diseases = [d.text.lower() for d in result.diseases]
    assert "nausea" in diseases

def test_context_filter_negation(context_filter):
    import spacy
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    text = "Patient denies any history of nausea."
    doc = nlp(text)
    span = doc.char_span(30, 36, label="DISEASE")
    doc.ents = [span] if span else []
    
    result = ExtractionResult(
        diseases=[ExtractedEntity("nausea", "DISEASE", 30, 36)],
        drugs=[],
        doc=doc
    )
    filtered_result = context_filter.annotate(result)
    assert filtered_result.diseases[0].negated

def test_context_filter_family(context_filter):
    import spacy
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    text = "Her father had lung cancer."
    doc = nlp(text)
    span = doc.char_span(15, 26, label="DISEASE")
    doc.ents = [span] if span else []
    
    result = ExtractionResult(
        diseases=[ExtractedEntity("lung cancer", "DISEASE", 15, 26)],
        drugs=[],
        doc=doc
    )
    filtered_result = context_filter.annotate(result)
    assert filtered_result.diseases[0].other_experiencer

def test_context_filter_hypothetical(context_filter):
    import spacy
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    text = "This medication may cause hepatotoxicity."
    doc = nlp(text)
    span = doc.char_span(26, 40, label="DISEASE")
    doc.ents = [span] if span else []
    
    result = ExtractionResult(
        diseases=[ExtractedEntity("hepatotoxicity", "DISEASE", 26, 40)],
        drugs=[],
        doc=doc
    )
    filtered_result = context_filter.annotate(result)
    assert filtered_result.diseases[0].hypothetical


def test_had_does_not_make_current_event_historical(context_filter):
    import spacy

    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")

    text = "The patient had a rash."

    start = text.index("rash")

    doc = nlp(text)

    span = doc.char_span(
        start,
        start + len("rash"),
        label="DISEASE",
    )

    doc.ents = [span]

    result = ExtractionResult(
        diseases=[
            ExtractedEntity(
                "rash",
                "DISEASE",
                start,
                start + len("rash"),
            )
        ],
        drugs=[],
        doc=doc,
    )

    filtered = context_filter.annotate(result)

    assert not filtered.diseases[0].historical


def test_suspected_reaction_is_not_hypothetical(context_filter):
    import spacy

    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")

    text = (
        "The doctor documented the suspected reaction."
    )

    start = text.index("reaction")

    doc = nlp(text)

    span = doc.char_span(
        start,
        start + len("reaction"),
        label="DISEASE",
    )

    doc.ents = [span]

    result = ExtractionResult(
        diseases=[
            ExtractedEntity(
                "reaction",
                "DISEASE",
                start,
                start + len("reaction"),
            )
        ],
        drugs=[],
        doc=doc,
    )

    filtered = context_filter.annotate(result)

    assert not filtered.diseases[0].hypothetical


def test_several_years_earlier_is_historical(context_filter):
    import spacy

    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")

    text = (
        "The patient reported a similar rash several years earlier."
    )

    start = text.index("rash")

    doc = nlp(text)

    span = doc.char_span(
        start,
        start + len("rash"),
        label="DISEASE",
    )

    doc.ents = [span]

    result = ExtractionResult(
        diseases=[
            ExtractedEntity(
                "rash",
                "DISEASE",
                start,
                start + len("rash"),
            )
        ],
        drugs=[],
        doc=doc,
    )

    filtered = context_filter.annotate(result)

    assert filtered.diseases[0].historical