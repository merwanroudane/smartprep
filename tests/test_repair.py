"""The repair engine: safety, auditability, reversibility, idempotence."""

from __future__ import annotations

import json

import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT
from smartprep.core import CompletionState
from smartprep.core.enums import Severity
from smartprep.core.health import SEVERITY_WEIGHT
from smartprep.core.operations import OperationScope
from smartprep.detectors.base import numeric_series, physical_type
from smartprep.exceptions import SmartPrepUnsafeRepairError

# -- the no-mutation guarantee --------------------------------------------


def test_auto_prepare_never_touches_the_input(synthetic: pd.DataFrame) -> None:
    before = synthetic.copy(deep=True)
    sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    pd.testing.assert_frame_equal(synthetic, before)


def test_raw_and_clean_are_separate_objects(prepared: sp.PreparationResult) -> None:
    assert prepared.raw_df is not prepared.clean_df


def test_shape_is_preserved(prepared: sp.PreparationResult) -> None:
    """Safe auto mode never adds or removes rows or columns."""
    assert prepared.clean_df.shape == prepared.raw_df.shape


# -- what actually got repaired -------------------------------------------


def test_numeric_columns_are_fully_parsed(prepared: sp.PreparationResult) -> None:
    for column in ("unit_price", "annual_revenue"):
        forms = {physical_type(v) for v in prepared.clean_df[column]}
        assert forms <= {"float", "missing"}, f"{column} still mixed: {forms}"


def test_only_unambiguous_dates_are_converted(prepared: sp.PreparationResult) -> None:
    """The invalid and ambiguous values must survive untouched, still flagged."""
    leftover = [v for v in prepared.clean_df["invoice_date"] if isinstance(v, str)]
    assert set(leftover) == {"31/02/2025", "2025-13-04", "04/05/2024"}


def test_mechanical_category_merges_applied(prepared: sp.PreparationResult) -> None:
    countries = set(prepared.clean_df["country"].dropna())
    assert "ALGERIA" not in countries
    assert " Algeria" not in countries
    assert "Algeria" in countries


def test_semantic_merges_are_not_applied(prepared: sp.PreparationResult) -> None:
    """Spelling and language variants need confirmation, so they survive."""
    assert "Algérie" in set(prepared.clean_df["country"].dropna())
    assert "Tourismm" in set(prepared.clean_df["sector"].dropna())


def test_confusable_is_folded(prepared: sp.PreparationResult) -> None:
    sectors = set(prepared.clean_df["sector"].dropna())
    assert "Manufacturıng" not in sectors
    assert "Manufacturing" in sectors


# -- what must never be repaired automatically ----------------------------


def test_conflicting_duplicates_survive(prepared: sp.PreparationResult) -> None:
    assert prepared.clean_df["invoice_id"].duplicated().sum() == 2
    assert any(i.id == "DUP-CONFLICT-invoice_id" for i in prepared.blocking_issues)


def test_range_violations_are_not_silently_corrected(prepared: sp.PreparationResult) -> None:
    assert (numeric_series(prepared.clean_df, "quantity") < 1).sum() == 2


def test_invoice_amounts_are_not_recomputed(prepared: sp.PreparationResult) -> None:
    """A 90%-fitting formula is not authority to overwrite recorded values."""
    assert 999.0 in set(numeric_series(prepared.clean_df, "invoice_amount"))


# -- audit ----------------------------------------------------------------


def test_every_applied_operation_is_recorded(prepared: sp.PreparationResult) -> None:
    assert len(prepared.audit.applied) == len(prepared.plan)
    for record in prepared.audit.applied:
        assert record.operation_id
        assert record.before_fingerprint and record.after_fingerprint
        assert record.reason


def test_refusals_are_recorded_too(prepared: sp.PreparationResult) -> None:
    """A log of only successful edits cannot explain what is still wrong."""
    assert prepared.audit.refused
    for record in prepared.audit.refused:
        assert record.reason, f"{record.operation_id} refused without a reason"


def test_audit_links_back_to_issues(prepared: sp.PreparationResult) -> None:
    records = prepared.audit.for_issue("DUP-CONFLICT-invoice_id")
    assert records and not records[0].applied


def test_cells_changed_is_counted(prepared: sp.PreparationResult) -> None:
    assert prepared.cells_changed > 0
    assert prepared.cells_changed == sum(r.cells_changed for r in prepared.audit.applied)


# -- ordering and dependencies --------------------------------------------


def test_representation_is_repaired_before_text(prepared: sp.PreparationResult) -> None:
    """Range checks on a text column answer the wrong question confidently."""
    scopes = [op.scope for op in prepared.plan.ordered()]
    if OperationScope.REPRESENTATION in scopes and OperationScope.TEXT in scopes:
        assert scopes.index(OperationScope.REPRESENTATION) < scopes.index(OperationScope.TEXT)


def test_repairs_invalidate_dependent_detectors(prepared: sp.PreparationResult) -> None:
    invalidated = prepared.plan.invalidated_detectors()
    assert "range_violation" in invalidated
    assert "formula_invariant" in invalidated


# -- reversibility --------------------------------------------------------


def test_rollback_restores_the_original(prepared: sp.PreparationResult) -> None:
    pd.testing.assert_frame_equal(prepared.rollback(0), prepared.raw_df)


def test_every_operation_leaves_a_snapshot(prepared: sp.PreparationResult) -> None:
    assert len(prepared.snapshots) == len(prepared.audit.applied) + 1


def test_rollback_to_unknown_version_is_explicit(prepared: sp.PreparationResult) -> None:
    with pytest.raises(KeyError, match="available"):
        prepared.rollback(9999)


# -- idempotence ----------------------------------------------------------


def test_cleaning_twice_changes_nothing_further(prepared: sp.PreparationResult) -> None:
    """clean(clean(df)) == clean(df) -- the property the plan calls for."""
    second = sp.auto_prepare(prepared.clean_df, **SCAN_CONTEXT)
    assert second.cells_changed == 0
    pd.testing.assert_frame_equal(second.clean_df, prepared.clean_df)


# -- completion state -----------------------------------------------------


def test_status_is_blocked_while_conflicts_remain(prepared: sp.PreparationResult) -> None:
    assert prepared.status is CompletionState.BLOCKED


def test_clean_data_reaches_a_clean_state() -> None:
    frame = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": ["x", "y", "z"]})
    assert sp.auto_prepare(frame).status is CompletionState.CLEAN


# -- verified_df and waivers ----------------------------------------------


def test_verified_df_is_refused_while_findings_remain(prepared: sp.PreparationResult) -> None:
    with pytest.raises(SmartPrepUnsafeRepairError, match="not available until finalize"):
        _ = prepared.verified_df


def test_finalize_refuses_and_names_what_is_open(prepared: sp.PreparationResult) -> None:
    with pytest.raises(SmartPrepUnsafeRepairError, match="still require a decision"):
        prepared.finalize()


def test_waivers_must_state_a_reason(synthetic: pd.DataFrame) -> None:
    result = sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    with pytest.raises(ValueError, match="must state a reason"):
        result.waive("DUP-CONFLICT-invoice_id", "  ")


def test_waiving_everything_unlocks_verified_df(synthetic: pd.DataFrame) -> None:
    result = sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    for open_issue in result.review_queue:
        result.waive(open_issue.id, "reviewed by the data owner for this test")
    result.finalize()
    assert result.verified_df.shape == result.clean_df.shape


def test_waiving_an_unknown_issue_fails(prepared: sp.PreparationResult) -> None:
    with pytest.raises(KeyError):
        prepared.waive("NO-SUCH-ISSUE", "reason")


# -- disclosure -----------------------------------------------------------


def test_what_auto_mode_did_not_do_is_reported(prepared: sp.PreparationResult) -> None:
    disclosure = prepared.what_auto_mode_did_not_do()
    assert "DUP-CONFLICT-invoice_id" in disclosure
    assert "why:" in disclosure


def test_summary_states_clean_df_is_not_verified(prepared: sp.PreparationResult) -> None:
    assert "not a verified dataset" in prepared.summary()


# -- clean() convenience --------------------------------------------------


def test_clean_returns_a_frame(synthetic: pd.DataFrame) -> None:
    assert isinstance(sp.clean(synthetic, **SCAN_CONTEXT), pd.DataFrame)


def test_clean_detailed_returns_the_full_result(synthetic: pd.DataFrame) -> None:
    assert isinstance(sp.clean(synthetic, detailed=True, **SCAN_CONTEXT), sp.PreparationResult)


def test_clean_warns_when_findings_remain(
    synthetic: pd.DataFrame, capsys: pytest.CaptureFixture[str]
) -> None:
    sp.clean(synthetic, **SCAN_CONTEXT)
    assert "need a decision" in capsys.readouterr().err


# -- health ---------------------------------------------------------------


def test_health_improves_and_is_decomposable(prepared: sp.PreparationResult) -> None:
    before, after = prepared.health_before, prepared.health_after
    assert after.overall > before.overall
    assert set(after.dimensions) == {
        "completeness",
        "validity",
        "consistency",
        "uniqueness",
        "semantic_quality",
    }


def test_health_never_leaves_the_scale(prepared: sp.PreparationResult) -> None:
    for dim in prepared.health_after.dimensions.values():
        assert 0.0 <= dim.score <= 100.0


def test_structural_missingness_costs_nothing() -> None:
    """Correctly-modelled absence must not be scored as a defect."""
    assert SEVERITY_WEIGHT[Severity.INFO] == 0.0


# -- serialisation --------------------------------------------------------


def test_result_serialises_to_json(prepared: sp.PreparationResult) -> None:
    payload = json.loads(prepared.to_json())
    assert payload["status"] == "BLOCKED"
    assert payload["schema_version"] == 1
    assert payload["audit"]
    assert payload["health"]["before"]["overall"] < payload["health"]["after"]["overall"]
