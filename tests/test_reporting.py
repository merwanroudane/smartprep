"""Reports must disclose, not flatter."""

from __future__ import annotations

import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT


def test_scan_report_marks_the_data_as_unmodified(scanned: sp.ScanResult) -> None:
    report = scanned.report()
    assert "BEFORE CLEANING" in report
    assert "says nothing about whether the data is correct" in report


def test_scan_report_lists_skipped_checks_with_reasons() -> None:
    import pandas as pd

    report = sp.scan(pd.DataFrame({"a": [1, 2, 3]})).report()
    assert "Checks that did not run" in report
    assert "duplicate_identifier" in report


def test_preparation_report_always_discloses_inaction(
    prepared: sp.PreparationResult,
) -> None:
    """The section that must never be buried in an appendix (AD-001)."""
    report = prepared.report("preparation")
    assert "## What auto mode did NOT do" in report
    assert "This section is mandatory" in report
    assert "not a verified dataset" in report
    assert "DUP-CONFLICT-invoice_id" in report


def test_preparation_report_answers_the_status_questions(
    prepared: sp.PreparationResult,
) -> None:
    report = prepared.report("preparation")
    for question in (
        "Scan complete",
        "Scan coverage",
        "All issues resolved",
        "Manual review required",
    ):
        assert question in report


def test_preparation_report_shows_every_applied_operation(
    prepared: sp.PreparationResult,
) -> None:
    report = prepared.report("preparation")
    for record in prepared.audit.applied:
        assert record.operation_id in report


def test_comparison_report_marks_resolved_and_surviving(
    prepared: sp.PreparationResult,
) -> None:
    report = prepared.report("comparison")
    assert "**resolved**" in report
    assert "DUP-CONFLICT-invoice_id" in report


def test_report_kind_is_validated(prepared: sp.PreparationResult) -> None:
    with pytest.raises(ValueError, match="unknown report kind"):
        prepared.report("nonsense")


def test_report_exports_to_disk(prepared: sp.PreparationResult, tmp_path) -> None:
    target = tmp_path / "report.md"
    prepared.export_report(str(target))
    assert "What auto mode did NOT do" in target.read_text(encoding="utf-8")


def test_reports_render_for_clean_data() -> None:
    """A report on flawless data must not crash on its empty sections."""
    import pandas as pd

    result = sp.auto_prepare(pd.DataFrame({"a": [1.0, 2.0], "b": ["x", "y"]}))
    assert "Nothing was left open" in result.report("preparation")


def test_waivers_appear_in_the_report(synthetic) -> None:
    result = sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    result.waive("DUP-CONFLICT-invoice_id", "two source systems, both retained on purpose")
    report = result.report("preparation")
    assert "## Waivers" in report
    assert "both retained on purpose" in report


def test_report_records_the_environment(prepared: sp.PreparationResult) -> None:
    report = prepared.report("preparation")
    assert "## Reproducibility" in report
    assert "smartprep" in report
