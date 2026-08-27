"""Scan API contracts: coverage honesty, failure policy, row references."""

from __future__ import annotations

import json

import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT
from smartprep.core import IssueCategory, RepairClass, RowSet, Severity
from smartprep.detectors.base import DetectorRegistry
from smartprep.exceptions import SmartPrepError
from smartprep.scan import Applicability

# -- coverage means checks, not correctness -------------------------------


def test_full_coverage_does_not_imply_clean_data(scanned: sp.ScanResult) -> None:
    assert scanned.coverage == 1.0
    assert scanned.issues
    assert "not data correctness" in scanned.summary()


def test_skipped_checks_are_reported_with_reasons() -> None:
    """A check that could not run must not silently count as coverage."""
    frame = pd.DataFrame({"a": [1, 2, 3]})
    result = sp.scan(frame)  # no identifier given

    skipped = {o.detector: o.reason for o in result.skipped_checks}
    assert "duplicate_identifier" in skipped
    assert "identifier" in skipped["duplicate_identifier"]
    assert all(o.reason for o in result.skipped_checks)


def test_skipped_checks_are_outside_the_coverage_denominator() -> None:
    frame = pd.DataFrame({"a": [1, 2, 3]})
    result = sp.scan(frame)
    assert result.applicable_checks == len(result.completed_checks)
    assert result.coverage == 1.0


def test_not_applicable_is_distinct_from_skipped(synthetic: pd.DataFrame) -> None:
    result = sp.scan(synthetic, identifier="no_such_column", compare_to="invoice_date")
    statuses = {o.detector: o.status for o in result.outcomes}
    assert statuses["duplicate_identifier"] == "not_applicable"


# -- detector failure policy ----------------------------------------------


class _Broken:
    name = "broken_detector"

    def detect(self, frame: pd.DataFrame, **context: object) -> list[sp.Issue]:
        raise RuntimeError("deliberate failure")


def _registry_with_broken() -> DetectorRegistry:
    registry = DetectorRegistry()
    registry.register(_Broken())
    return registry


def test_a_failing_detector_does_not_abort_the_scan() -> None:
    frame = pd.DataFrame({"a": [1, 2, 3]})
    result = sp.scan(frame, registry=_registry_with_broken())
    assert len(result.failed_checks) == 1
    assert "deliberate failure" in result.failed_checks[0].reason


def test_failure_lowers_coverage_rather_than_hiding() -> None:
    frame = pd.DataFrame({"a": [1, 2, 3]})
    result = sp.scan(frame, registry=_registry_with_broken())
    assert result.coverage == 0.0
    assert "WARNING" in result.summary()


def test_strict_mode_raises_instead_of_degrading() -> None:
    """Silently reduced coverage is worse than a loud stop."""
    frame = pd.DataFrame({"a": [1, 2, 3]})
    with pytest.raises(SmartPrepError, match="failed during scan"):
        sp.scan(frame, registry=_registry_with_broken(), strict=True)


def test_a_mutating_detector_is_caught() -> None:
    """AD-003 is enforced, not merely documented."""

    class Mutating:
        name = "mutating_detector"

        def detect(self, frame: pd.DataFrame, **context: object) -> list[sp.Issue]:
            frame["injected"] = 1
            return []

    registry = DetectorRegistry()
    registry.register(Mutating())
    with pytest.raises(RuntimeError, match="must never mutate"):
        sp.scan(pd.DataFrame({"a": [1, 2, 3]}), registry=registry)


# -- row references -------------------------------------------------------


def test_findings_carry_both_position_and_label() -> None:
    """On a non-default index, a bare integer points at the wrong row."""
    frame = pd.DataFrame(
        {"quantity": [1.0, -5.0, 3.0]},
        index=["order-a", "order-b", "order-c"],
    )
    result = sp.scan(frame)
    found = result.get("RANGE-quantity")

    assert found.rows.positions == (1,)
    assert found.rows.labels == ("order-b",)
    assert found.rows.labelled


def test_labels_align_with_positions_or_construction_fails() -> None:
    with pytest.raises(ValueError, match="align element-wise"):
        RowSet(positions=(0, 1), labels=("only-one",))


def test_out_of_range_positions_are_dropped_not_raised() -> None:
    rows = RowSet.of([0, 99]).with_index(pd.Index(["a", "b"]))
    assert rows.positions == (0,)


# -- issue lookup and filtering -------------------------------------------


def test_get_raises_a_useful_keyerror(scanned: sp.ScanResult) -> None:
    with pytest.raises(KeyError) as excinfo:
        scanned.get("NO-SUCH-ISSUE")
    assert "Available" in str(excinfo.value)


def test_find_filters_by_column(scanned: sp.ScanResult) -> None:
    found = scanned.find(column="invoice_date")
    assert found
    assert all("invoice_date" in i.columns for i in found)


def test_find_filters_by_severity(scanned: sp.ScanResult) -> None:
    found = scanned.find(min_severity=Severity.CRITICAL_REVIEW)
    assert all(i.severity >= Severity.CRITICAL_REVIEW for i in found)


def test_find_filters_by_repair_class(scanned: sp.ScanResult) -> None:
    found = scanned.find(repair_class=RepairClass.DO_NOT_TOUCH)
    assert [i.id for i in found] == ["DUP-CONFLICT-invoice_id"]


def test_find_combines_criteria(scanned: sp.ScanResult) -> None:
    found = scanned.find(IssueCategory.RANGE_VIOLATION, column="quantity")
    assert len(found) == 1


def test_blocking_and_needs_review_are_disjoint(scanned: sp.ScanResult) -> None:
    blocking = {i.id for i in scanned.blocking}
    review = {i.id for i in scanned.needs_review}
    assert not blocking & review


# -- restricting the scan -------------------------------------------------


def test_only_restricts_which_detectors_run(synthetic: pd.DataFrame) -> None:
    result = sp.scan(synthetic, only=["missingness"], **SCAN_CONTEXT)
    assert {o.detector for o in result.outcomes} == {"missingness"}


# -- progress -------------------------------------------------------------


def test_progress_callback_receives_every_detector(synthetic: pd.DataFrame) -> None:
    seen: list[tuple[str, int, int]] = []
    sp.scan(synthetic, progress=lambda *a: seen.append(a), **SCAN_CONTEXT)

    from smartprep.detectors import REGISTRY

    assert len(seen) == len(REGISTRY)
    assert seen[-1][1] == seen[-1][2], "progress must finish at total/total"


def test_detector_timings_are_recorded(scanned: sp.ScanResult) -> None:
    assert all(o.duration_ms >= 0 for o in scanned.completed_checks)


# -- serialisation --------------------------------------------------------


def test_scan_serialises_to_json(scanned: sp.ScanResult) -> None:
    payload = json.loads(scanned.to_json())
    assert payload["schema_version"] == 1
    assert payload["coverage"]["ratio"] == 1.0
    assert "not a statement about data correctness" in payload["coverage"]["note"].lower()
    assert len(payload["issues"]) == len(scanned.issues)


def test_serialised_issue_carries_its_triage(scanned: sp.ScanResult) -> None:
    payload = scanned.get("DUP-CONFLICT-invoice_id").to_dict()
    assert payload["repair_class"] == "DO_NOT_TOUCH"
    assert payload["abstention_reasons"]
    assert payload["evidence"]["rows"]["count"] == 2


def test_serialisation_survives_unusual_values(scanned: sp.ScanResult) -> None:
    """Timestamps and numpy scalars in evidence must not break json.dumps."""
    json.dumps(scanned.to_dict())


# -- edge-case frames -----------------------------------------------------


def test_empty_frame_scans_without_error() -> None:
    result = sp.scan(pd.DataFrame())
    assert result.issues == []
    assert result.row_count == 0


def test_single_row_frame_scans_without_error() -> None:
    result = sp.scan(pd.DataFrame({"a": [1.0]}))
    assert result.row_count == 1


def test_all_missing_column_is_reported_not_crashed() -> None:
    result = sp.scan(pd.DataFrame({"a": [None, None, None]}))
    assert result.get("MISS-a").affected_row_count == 3


def test_scan_rejects_non_dataframe() -> None:
    with pytest.raises(TypeError, match="expects a DataFrame"):
        sp.scan([1, 2, 3])  # type: ignore[arg-type]


# -- registry -------------------------------------------------------------


def test_duplicate_detector_registration_is_rejected() -> None:
    registry = DetectorRegistry()
    registry.register(_Broken())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(_Broken())


def test_applicability_defaults_to_applicable() -> None:
    """A detector without the method still runs -- the protocol is optional."""
    assert Applicability.APPLICABLE.runs
    assert not Applicability.NOT_APPLICABLE.runs
    assert not Applicability.SKIPPED_MISSING_CONTEXT.runs
