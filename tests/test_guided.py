"""Guided mode: the same engine, with the abstentions turned into questions."""

from __future__ import annotations

import json

import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT
from smartprep.core import CompletionState, RepairClass
from smartprep.exceptions import SmartPrepAmbiguityError


@pytest.fixture
def session(synthetic: pd.DataFrame) -> sp.GuidedSession:
    return sp.guided_prepare(synthetic, **SCAN_CONTEXT)


# -- the queue ------------------------------------------------------------


def test_queue_is_exactly_what_auto_mode_refused(
    synthetic: pd.DataFrame, session: sp.GuidedSession
) -> None:
    """Guided mode is not a second implementation -- it asks what auto skipped."""
    auto = sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    assert {i.id for i in session.queue} >= {i.id for i in auto.before_scan.blocking}
    assert all(not i.repair_class.is_autonomous for i in session.queue)


def test_questions_are_ordered_by_dependency_then_urgency(
    session: sp.GuidedSession,
) -> None:
    """Asking about an outlier in a text column asks about an uncomputed number."""
    severities = [q.issue.severity for q in session.questions]
    assert severities[0] >= severities[-1]


def test_question_level_controls_how_much_is_asked(synthetic: pd.DataFrame) -> None:
    counts = {
        level: len(sp.guided_prepare(synthetic, level=level, **SCAN_CONTEXT).queue)
        for level in ("minimal", "important_only", "standard", "expert")
    }
    assert counts["minimal"] < counts["important_only"] <= counts["standard"]
    assert counts["standard"] <= counts["expert"]


def test_progress_is_reported(session: sp.GuidedSession) -> None:
    assert session.progress == 0.0
    session.answer(session.next_question().issue_id, "leave_unresolved")
    assert 0.0 < session.progress < 1.0


# -- decision cards -------------------------------------------------------


def test_card_shows_evidence_and_why_auto_abstained(session: sp.GuidedSession) -> None:
    card = session.next_question().render()
    assert "Problem" in card
    assert "Evidence" in card
    assert "Why automatic mode did not act:" in card


def test_card_offers_only_treatments_that_can_be_carried_out(
    session: sp.GuidedSession,
) -> None:
    """A menu item that does nothing is worse than no menu item."""
    from smartprep.repair.actions import has_action

    for question in session.questions:
        assert all(has_action(option.name) for option in question.options)


def test_card_says_so_when_nothing_can_be_done(session: sp.GuidedSession) -> None:
    invalid = next(q for q in session.questions if q.issue_id.startswith("DATE-INVALID"))
    assert "No treatment can be carried out" in invalid.render()
    assert invalid.recommended is None


# -- answering ------------------------------------------------------------


def test_answers_are_recorded_not_applied(session: sp.GuidedSession) -> None:
    before = session.frame.copy(deep=True)
    for question in list(session.questions):
        session.answer(question.issue_id, "leave_unresolved")
    pd.testing.assert_frame_equal(session.frame, before)


def test_use_recommendation_needs_a_recommendation(session: sp.GuidedSession) -> None:
    invalid = next(q for q in session.questions if q.issue_id.startswith("DATE-INVALID"))
    with pytest.raises(SmartPrepAmbiguityError, match="not inferable"):
        session.answer(invalid.issue_id, "use_recommendation")


def test_choose_alternative_validates_the_name(session: sp.GuidedSession) -> None:
    question = next(q for q in session.questions if q.issue_id.startswith("RANGE-"))
    with pytest.raises(ValueError, match="not a treatment"):
        session.answer(question.issue_id, "choose_alternative", treatment="invent_a_value")


def test_choosing_an_unimplemented_treatment_is_refused(
    session: sp.GuidedSession,
) -> None:
    question = next(q for q in session.questions if q.issue_id.startswith("RANGE-"))
    with pytest.raises(SmartPrepAmbiguityError, match="not implemented yet"):
        session.answer(
            question.issue_id, "choose_alternative", treatment="quarantine_violating_rows"
        )


def test_waiving_requires_a_reason(session: sp.GuidedSession) -> None:
    with pytest.raises(ValueError, match="requires a reason"):
        session.waive("DUP-CONFLICT-invoice_id", "   ")


def test_accept_all_leaves_unworkable_findings_alone(session: sp.GuidedSession) -> None:
    """A bulk accept must not force a decision nobody can make."""
    session.accept_all_recommendations()
    assert session.remaining == 0
    invalid = session.decisions["DATE-INVALID-invoice_date"]
    assert invalid.action is sp.Action.LEAVE_UNRESOLVED


# -- applying -------------------------------------------------------------


def test_finish_applies_safe_repairs_too(
    synthetic: pd.DataFrame, session: sp.GuidedSession
) -> None:
    """A guided run is never worse-informed than an automatic one."""
    auto = sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    result = session.accept_all_recommendations().finish()
    assert len(result.audit.applied) == len(auto.audit.applied)
    assert result.cells_changed == auto.cells_changed


def test_finish_does_not_double_count_after_a_handoff(
    synthetic: pd.DataFrame,
) -> None:
    """The handoff rebuilds the plan; carrying the audit log inflated it."""
    auto = sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    result = auto.open_guided().accept_all_recommendations().finish()
    assert len(result.audit.applied) == len(auto.audit.applied)
    assert result.cells_changed == auto.cells_changed


def test_decisions_are_recorded_in_the_audit(session: sp.GuidedSession) -> None:
    session.waive("DUP-CONFLICT-invoice_id", "both source records retained on purpose")
    result = session.accept_all_recommendations().finish()

    records = result.audit.for_issue("DUP-CONFLICT-invoice_id")
    assert any("waived" in r.reason for r in records)
    assert all(r.decision_source.value in {"user", "automatic"} for r in result.audit)


def test_waivers_survive_into_the_result(session: sp.GuidedSession) -> None:
    session.waive("DUP-CONFLICT-invoice_id", "known duplicate feed")
    result = session.accept_all_recommendations().finish()
    assert result.waivers["DUP-CONFLICT-invoice_id"] == "known duplicate feed"


def test_waiving_everything_reaches_a_finalisable_state(
    synthetic: pd.DataFrame,
) -> None:
    session = sp.guided_prepare(synthetic, level="expert", **SCAN_CONTEXT)
    for question in list(session.questions):
        session.waive(question.issue_id, "reviewed by the data owner")
    result = session.finish()

    assert result.status is not CompletionState.BLOCKED
    for issue in result.review_queue:
        result.waive(issue.id, "reviewed by the data owner")
    result.finalize()
    assert result.verified_df.shape == result.clean_df.shape


def test_blocking_findings_are_still_never_auto_repaired(
    session: sp.GuidedSession,
) -> None:
    result = session.accept_all_recommendations().finish()
    conflict = result.after_scan.get("DUP-CONFLICT-invoice_id")
    assert conflict.repair_class is RepairClass.DO_NOT_TOUCH


# -- replay ---------------------------------------------------------------


def test_decisions_round_trip_through_json(session: sp.GuidedSession) -> None:
    session.accept_all_recommendations()
    payload = json.loads(session.export_decisions())
    assert payload["schema_version"] == 1
    assert len(payload["decisions"]) == session.answered


def test_replaying_a_session_reproduces_the_output(synthetic: pd.DataFrame) -> None:
    """A decision you cannot replay is a click, and a click is not reproducible."""
    first = sp.guided_prepare(synthetic, **SCAN_CONTEXT)
    first.waive("DUP-CONFLICT-invoice_id", "known duplicate feed")
    first.accept_all_recommendations()
    result_a = first.finish()

    second = sp.guided_prepare(synthetic, decisions=first.export_decisions(), **SCAN_CONTEXT)
    assert second.remaining == 0
    result_b = second.finish()

    pd.testing.assert_frame_equal(result_a.clean_df, result_b.clean_df)
    assert result_a.waivers == result_b.waivers


def test_replay_ignores_decisions_for_findings_that_are_gone(
    synthetic: pd.DataFrame,
) -> None:
    """Data changes; a stale answer must not block a run."""
    payload = {
        "schema_version": 1,
        "decisions": [
            {"issue_id": "NO-LONGER-PRESENT", "action": "skip", "treatment": None, "reason": ""}
        ],
    }
    session = sp.guided_prepare(synthetic, decisions=payload, **SCAN_CONTEXT)
    assert session.answered == 0


# -- handoff --------------------------------------------------------------


def test_handoff_carries_the_scan_forward(synthetic: pd.DataFrame) -> None:
    """The user must not have to restart the analysis."""
    auto = sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    session = auto.open_guided()
    assert session.scan_result is auto.before_scan
    assert session.context == SCAN_CONTEXT


def test_handoff_queue_matches_the_auto_review_queue(synthetic: pd.DataFrame) -> None:
    auto = sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    session = auto.open_guided()
    assert {i.id for i in session.queue} <= {i.id for i in auto.before_scan.issues}


def test_guided_prepare_rejects_non_dataframe() -> None:
    with pytest.raises(TypeError, match="expects a DataFrame"):
        sp.guided_prepare([1, 2, 3])  # type: ignore[arg-type]


def test_session_summary_reports_the_queue(session: sp.GuidedSession) -> None:
    summary = session.summary()
    assert "Guided Review Queue" in summary
    assert "remaining" in summary
