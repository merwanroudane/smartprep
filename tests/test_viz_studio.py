"""Chart specifications, the SVG renderer, HTML reports and the Studio."""

from __future__ import annotations

import json
import re

import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT
from smartprep.eda import associations, missingness, profile
from smartprep.viz import (
    ChartSpec,
    Fidelity,
    Mark,
    association_heatmap,
    category_chart,
    distribution_chart,
    issue_chart,
    missingness_chart,
    overview_charts,
    render_svg,
)


@pytest.fixture(scope="module")
def prepared_result(request) -> sp.PreparationResult:
    from synthetic import build

    return sp.auto_prepare(build(), **SCAN_CONTEXT)


# -- specs ----------------------------------------------------------------


def test_a_spec_is_serialisable(synthetic: pd.DataFrame) -> None:
    """A chart bound to plotting code cannot become HTML, PDF and a slide."""
    chart = distribution_chart(profile(synthetic).get("unit_price"))
    assert chart is not None
    payload = json.loads(chart.to_json())
    assert payload["schema_version"] == 1
    assert payload["mark"] == "histogram"
    assert payload["data"]


def test_every_chart_states_why_it_exists(synthetic: pd.DataFrame) -> None:
    """A chart nobody can justify is decoration."""
    dataset = profile(synthetic)
    charts = overview_charts(dataset, associations(synthetic, dataset), missingness(synthetic))
    assert len(charts) > 0
    for chart in charts:
        assert chart.rationale, f"{chart.title} has no rationale"


def test_sampled_charts_declare_it(synthetic: pd.DataFrame) -> None:
    """A reader who thinks they see every point will over-read the picture."""
    chart = distribution_chart(profile(synthetic).get("unit_price"))
    assert chart is not None
    assert chart.fidelity is Fidelity.BINNED
    assert chart.is_sampled
    assert chart.fidelity_note


def test_an_empty_spec_says_so_rather_than_looking_empty() -> None:
    """A blank chart reads as 'no signal' when it means 'no data arrived'."""
    chart = ChartSpec(mark=Mark.BAR, data=[], title="Nothing")
    assert any(a.get("kind") == "empty" for a in chart.annotations)


def test_histogram_marks_the_outlier_fences(synthetic: pd.DataFrame) -> None:
    chart = distribution_chart(profile(synthetic).get("employee_count"))
    assert chart is not None
    assert any("fence" in label for _, _, label in chart.rules)


def test_category_chart_marks_rare_levels() -> None:
    frame = pd.DataFrame({"c": ["common"] * 200 + ["rare"]})
    chart = category_chart(profile(frame).get("c"))
    assert chart is not None
    assert any(row["rare"] for row in chart.data)


def test_association_heatmap_names_its_measures(synthetic: pd.DataFrame) -> None:
    dataset = profile(synthetic)
    chart = association_heatmap(associations(synthetic, dataset))
    assert chart is not None
    assert "not interchangeable" in chart.rationale


def test_issue_chart_counts_by_decision_class(scanned: sp.ScanResult) -> None:
    chart = issue_chart(scanned.issues)
    assert chart is not None
    assert sum(row["count"] for row in chart.data) == len(scanned.issues)


def test_missingness_chart_omits_complete_columns(synthetic: pd.DataFrame) -> None:
    chart = missingness_chart(missingness(synthetic))
    assert chart is not None
    assert all(row["missing"] > 0 for row in chart.data)


def test_no_chart_for_a_column_with_nothing_to_show() -> None:
    assert missingness_chart(missingness(pd.DataFrame({"a": [1, 2, 3]}))) is None


# -- SVG ------------------------------------------------------------------


def test_svg_renders_without_a_plotting_library(synthetic: pd.DataFrame) -> None:
    """A report that cannot draw its own charts is not self-contained."""
    chart = distribution_chart(profile(synthetic).get("unit_price"))
    svg = render_svg(chart)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "<rect" in svg


def test_svg_escapes_values_from_the_data() -> None:
    """Cell values reach the output; a crafted one must not inject markup."""
    frame = pd.DataFrame({"c": ["<script>alert(1)</script>"] * 5 + ["ok"] * 5})
    svg = render_svg(category_chart(profile(frame).get("c")))
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_svg_has_an_accessible_label(synthetic: pd.DataFrame) -> None:
    svg = render_svg(distribution_chart(profile(synthetic).get("unit_price")))
    assert 'role="img"' in svg
    assert "aria-label=" in svg


def test_svg_carries_hover_titles(synthetic: pd.DataFrame) -> None:
    svg = render_svg(distribution_chart(profile(synthetic).get("unit_price")))
    assert "<title>" in svg


def test_empty_data_renders_a_message_not_a_blank_box() -> None:
    svg = render_svg(ChartSpec(mark=Mark.BAR, data=[], title="Nothing"))
    assert "No data to display" in svg


def test_constant_column_does_not_divide_by_zero() -> None:
    chart = distribution_chart(profile(pd.DataFrame({"x": [5.0] * 30})).get("x"))
    if chart is not None:
        assert render_svg(chart).startswith("<svg")


# -- HTML reports ---------------------------------------------------------


def test_scan_html_is_self_contained(scanned: sp.ScanResult, synthetic: pd.DataFrame) -> None:
    """No CDN, no build step -- a report that needs a network stops working
    the moment it is archived."""
    page = scanned.report("html", synthetic)
    assert page.startswith("<!doctype html>")
    assert not re.search(r'(src|href)\s*=\s*"https?://', page)


def test_scan_html_marks_the_data_as_unmodified(
    scanned: sp.ScanResult, synthetic: pd.DataFrame
) -> None:
    assert "BEFORE CLEANING" in scanned.report("html", synthetic)


def test_scan_html_separates_coverage_from_correctness(scanned: sp.ScanResult) -> None:
    page = scanned.report("html")
    assert "Coverage is not correctness" in page


def test_preparation_html_discloses_inaction(prepared_result: sp.PreparationResult) -> None:
    page = prepared_result.report("preparation", "html")
    assert "What auto mode did NOT do" in page
    assert "not a verified dataset" in page
    assert "DUP-CONFLICT-invoice_id" in page


def test_preparation_html_embeds_charts(prepared_result: sp.PreparationResult) -> None:
    assert prepared_result.report("preparation", "html").count("<svg") >= 2


def test_report_format_is_validated(prepared_result: sp.PreparationResult) -> None:
    with pytest.raises(ValueError, match="unknown format"):
        prepared_result.report("preparation", "interpretive-dance")


def test_export_infers_format_from_the_suffix(
    prepared_result: sp.PreparationResult, tmp_path
) -> None:
    target = tmp_path / "report.html"
    prepared_result.export_report(str(target))
    assert target.read_text(encoding="utf-8").startswith("<!doctype html>")

    markdown = tmp_path / "report.md"
    prepared_result.export_report(str(markdown))
    assert markdown.read_text(encoding="utf-8").startswith("# ")


# -- Studio ---------------------------------------------------------------


def test_studio_renders_from_a_result(prepared_result: sp.PreparationResult) -> None:
    workspace = sp.studio(prepared_result)
    assert workspace.html.startswith("<!doctype html>")
    assert "SmartPrep Studio" in workspace.html


def test_studio_applies_nothing_in_the_browser(
    prepared_result: sp.PreparationResult,
) -> None:
    """The interface must never become a second implementation."""
    page = sp.studio(prepared_result).html
    assert "This view applies nothing" in page
    assert "guided_prepare(decisions" in page


def test_studio_offers_only_workable_treatments(
    prepared_result: sp.PreparationResult,
) -> None:
    from smartprep.repair.actions import ACTIONS

    page = sp.studio(prepared_result).html
    offered = set(re.findall(r"data-treatment='([^']+)'", page))
    assert offered <= set(ACTIONS), f"offered unimplemented treatments: {offered - set(ACTIONS)}"


def test_studio_exposes_the_guided_queue(prepared_result: sp.PreparationResult) -> None:
    page = sp.studio(prepared_result).html
    for issue in prepared_result.review_queue[:5]:
        assert issue.id in page


def test_studio_works_from_a_scan_alone(scanned: sp.ScanResult) -> None:
    assert sp.studio(scanned).html.startswith("<!doctype html>")


def test_studio_works_from_a_frame(synthetic: pd.DataFrame) -> None:
    workspace = sp.studio(synthetic, **SCAN_CONTEXT)
    assert "Guided decisions" in workspace.html


def test_studio_diagnosis_only_mode(synthetic: pd.DataFrame) -> None:
    workspace = sp.studio(synthetic, prepare=False, **SCAN_CONTEXT)
    assert isinstance(workspace.source, sp.ScanResult)


def test_studio_saves_to_disk(prepared_result: sp.PreparationResult, tmp_path) -> None:
    path = sp.studio(prepared_result).save(str(tmp_path / "studio.html"))
    assert pd.io.common.file_exists(path)


def test_studio_rejects_the_wrong_type() -> None:
    with pytest.raises(TypeError, match="expects a DataFrame"):
        sp.studio([1, 2, 3])


def test_studio_decisions_replay_through_guided_mode(synthetic: pd.DataFrame) -> None:
    """The whole contract between interface and engine: the page emits JSON,
    guided mode applies it."""
    workspace = sp.studio(synthetic, **SCAN_CONTEXT)
    session = sp.guided_prepare(synthetic, **SCAN_CONTEXT)
    first = session.next_question()
    session.waive(first.issue_id, "reviewed in the studio")

    result = workspace.apply_decisions(session.export_decisions(), synthetic, **SCAN_CONTEXT)
    assert first.issue_id in result.waivers


def test_studio_escapes_data_values() -> None:
    frame = pd.DataFrame({"c": ["<img src=x onerror=alert(1)>"] * 3 + ["fine"] * 3, "n": [1.0] * 6})
    page = sp.studio(frame, prepare=False).html
    assert "onerror=alert" not in page or "&lt;img" in page
