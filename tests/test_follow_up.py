import pytest

from src.pv.builder import CaseBuilder
from src.pv.case_schema import NormalizedEvent, ExtractedDrug


@pytest.fixture
def builder():
    return CaseBuilder.__new__(CaseBuilder)


def make_event(
    effect_text,
    meddra_pt_id,
    suspected_drugs=None,
    outcome=None,
    source_version=1,
):
    suspected_drugs = suspected_drugs or []

    drugs = [
        ExtractedDrug(
            text=drug,
            source_version=source_version,
        )
        for drug in suspected_drugs
    ]

    return NormalizedEvent(
        effect_text=effect_text,
        start_char=None,
        end_char=None,
        meddra_pt=effect_text,
        meddra_pt_id=meddra_pt_id,
        confidence_score=0.95,
        review_status="Auto-coded",
        top_candidates=[],
        suspected_drugs=drugs,
        drug_relationships={},
        is_serious=False,
        seriousness_evidence=None,
        seriousness_reason=None,
        is_speculated=False,
        causality=None,
        outcome=outcome,
        source_version=source_version,
    )


class TestFollowUpReconciliation:

    def test_follow_up_outcome_updates_existing_event(self, builder):
        previous = make_event("rash", "10037844", ["amoxicillin"])
        current = make_event(
            "rash", "10037844", outcome="improved", source_version=2
        )

        result = builder._reconcile_follow_up_events([previous], [current])

        assert len(result) == 1
        assert result[0].outcome == "improved"
        assert result[0].source_version == 1

    def test_follow_up_resolved_updates_existing_event(self, builder):
        previous = make_event("rash", "10037844", ["amoxicillin"])
        current = make_event(
            "rash", "10037844", outcome="resolved", source_version=2
        )

        result = builder._reconcile_follow_up_events([previous], [current])

        assert len(result) == 1
        assert result[0].outcome == "resolved"

    def test_follow_up_persisted_updates_existing_event(self, builder):
        previous = make_event("rash", "10037844", ["amoxicillin"])
        current = make_event(
            "rash", "10037844", outcome="persisted", source_version=2
        )

        result = builder._reconcile_follow_up_events([previous], [current])

        assert len(result) == 1
        assert result[0].outcome == "persisted"

    def test_new_event_is_preserved(self, builder):
        previous = make_event("rash", "10037844", ["amoxicillin"])
        current = make_event(
            "headache", "10019211", ["amoxicillin"], source_version=2
        )

        result = builder._reconcile_follow_up_events([previous], [current])

        assert len(result) == 2
        assert [event.effect_text for event in result] == ["rash", "headache"]

    def test_different_drug_is_not_automatically_merged(self, builder):
        previous = make_event("rash", "10037844", ["amoxicillin"])
        current = make_event(
            "rash",
            "10037844",
            ["ibuprofen"],
            outcome="improved",
            source_version=2,
        )

        result = builder._reconcile_follow_up_events([previous], [current])

        assert len(result) == 2

    def test_same_drug_and_outcome_are_merged(self, builder):
        previous = make_event("rash", "10037844", ["amoxicillin"])
        current = make_event(
            "rash",
            "10037844",
            ["amoxicillin"],
            outcome="improved",
            source_version=2,
        )

        result = builder._reconcile_follow_up_events([previous], [current])

        assert len(result) == 1
        assert result[0].outcome == "improved"
        assert result[0].source_version == 1

    def test_different_meddra_term_is_not_merged(self, builder):
        previous = make_event("rash", "10037844", ["amoxicillin"])
        current = make_event(
            "rash", "99999999", outcome="resolved", source_version=2
        )

        result = builder._reconcile_follow_up_events([previous], [current])

        assert len(result) == 2

    def test_matching_event_updated_without_affecting_other_events(self, builder):
        previous_rash = make_event("rash", "10037844", ["amoxicillin"])
        previous_headache = make_event(
            "headache", "10019211", ["amoxicillin"]
        )
        current = make_event(
            "rash", "10037844", outcome="improved", source_version=2
        )

        result = builder._reconcile_follow_up_events(
            [previous_rash, previous_headache], [current]
        )

        assert len(result) == 2
        assert result[0].outcome == "improved"
        assert result[1].outcome is None

    def test_unrelated_outcome_event_is_not_merged(self, builder):
        previous = make_event("rash", "10037844", ["amoxicillin"])
        current = make_event(
            "headache", "10019211", outcome="improved", source_version=2
        )

        result = builder._reconcile_follow_up_events([previous], [current])

        assert len(result) == 2

    def test_empty_previous_events_preserves_current_events(self, builder):
        current = make_event(
            "rash", "10037844", ["amoxicillin"], source_version=2
        )

        result = builder._reconcile_follow_up_events([], [current])

        assert len(result) == 1
        assert result[0].source_version == 2

    def test_empty_current_events_preserves_previous_events(self, builder):
        previous = make_event("rash", "10037844", ["amoxicillin"])

        result = builder._reconcile_follow_up_events([previous], [])

        assert len(result) == 1
        assert result[0].source_version == 1

    def test_multiple_follow_up_events_are_reconciled_independently(self, builder):
        previous_rash = make_event("rash", "10037844", ["amoxicillin"])
        previous_headache = make_event(
            "headache", "10019211", ["amoxicillin"]
        )
        current_rash = make_event(
            "rash", "10037844", outcome="improved", source_version=2
        )
        current_headache = make_event(
            "headache", "10019211", outcome="resolved", source_version=2
        )

        result = builder._reconcile_follow_up_events(
            [previous_rash, previous_headache],
            [current_rash, current_headache],
        )

        assert len(result) == 2
        assert result[0].outcome == "improved"
        assert result[1].outcome == "resolved"