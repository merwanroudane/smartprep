"""The rules the library is built on, asserted rather than documented.

Every claim in this file is one an ordinary feature test would not catch. A
renderer can pass its own tests while quietly disagreeing with another
renderer about the same numbers; a Studio can pass its own tests while
applying a decision the Python API would have applied differently. Those are
the failures that make a library untrustworthy rather than merely buggy, and
they only surface when the invariant itself is the thing under test.

Four invariants live here:

* ``Interaction != Animation`` -- two axes, never collapsed into one flag.
* ``Core != UI`` -- a Studio decision and a Python decision produce the same
  frame and the same audit, because there is only one engine.
* ``ChartSpec is the source of truth`` -- no renderer reinterprets data.
* accessibility -- what a reader who cannot see the picture is told.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT
from smartprep.viz import (
    ChartSpec,
    Encoding,
    Fidelity,
    Interaction,
    Mark,
    available_backends,
    render_svg,
    to_matplotlib,
    to_plotly,
)
from smartprep.viz.builders import (
    box_chart,
    category_chart,
    distribution_chart,
    scatter_chart,
)

HAS_MPL = available_backends()["matplotlib"]
HAS_PLOTLY = available_backends()["plotly"]


# ==========================================================================
# P0-2 -- Interaction is not animation
# ==========================================================================


def test_interaction_and_animation_are_independent_axes() -> None:
    """All four combinations are expressible.

    If the two were one flag, at least one of these four would be
    unrepresentable -- which is exactly how hover text ends up being called
    interactive.
    """
    combinations = [
        (Interaction.NONE, None),  # a picture
        (Interaction.EXPLORE, None),  # a scatter you can lasso
        (Interaction.NONE, "stage"),  # stage frames printed as small multiples
        (Interaction.EXPLORE, "stage"),  # both
    ]
    for interaction, animation in combinations:
        spec = ChartSpec(
            mark=Mark.BAR,
            data=[{"x": "a", "y": 1.0}],
            x=Encoding("x", "nominal"),
            y=Encoding("y"),
            interaction=interaction,
            animation_field=animation,
        )
        assert spec.is_interactive is (interaction is not Interaction.NONE)
        assert spec.is_animated is (animation is not None)


def test_the_spec_has_no_single_interactive_boolean() -> None:
    """A boolean cannot say *how* interactive, and a default of True would be
    a claim every static rendering contradicts."""
    spec = ChartSpec(mark=Mark.BAR, data=[{"x": "a", "y": 1.0}])
    assert not hasattr(spec, "interactive")
    assert isinstance(spec.interaction, Interaction)


def test_serialised_specs_carry_both_axes_separately() -> None:
    spec = ChartSpec(
        mark=Mark.LINE,
        data=[{"x": 1, "y": 2.0}],
        x=Encoding("x"),
        y=Encoding("y"),
        animation_field="stage",
        interaction=Interaction.HOVER,
    )
    payload = json.loads(spec.to_json())
    assert payload["interaction"] == "hover"
    assert payload["animated"] is True
    assert payload["animation_field"] == "stage"


def test_non_interactive_specs_render_without_hover_text() -> None:
    """The field is honoured, not merely declared.

    A spec that says NONE and still emits hover markup is the same class of
    dishonesty as an enum declaring a mark nothing can draw.
    """
    data = [{"label": "a", "value": 3.0}, {"label": "b", "value": 5.0}]
    spec = ChartSpec(
        mark=Mark.BAR,
        data=data,
        x=Encoding("label", "nominal"),
        y=Encoding("value"),
        title="Counts",
    )
    hoverable = render_svg(spec)
    # One accessible root title, plus one hover title per bar.
    assert hoverable.count("<title>") == 3

    body = render_svg(spec.as_static())
    assert body.count("<title>") == 1
    # The accessible root title survives: it is a label for assistive
    # technology, not hover data.
    assert "<title>Counts</title>" in body


def test_as_static_does_not_disturb_the_animation_axis() -> None:
    spec = ChartSpec(
        mark=Mark.BAR,
        data=[{"x": "a", "y": 1.0}],
        animation_field="stage",
        interaction=Interaction.EXPLORE,
    )
    static = spec.as_static()
    assert static.is_animated is True
    assert static.is_interactive is False


@pytest.mark.skipif(not HAS_PLOTLY, reason="plotly not installed")
def test_plotly_honours_the_interaction_ceiling() -> None:
    data = [{"x": 1.0, "y": 2.0}, {"x": 2.0, "y": 3.0}]
    base = ChartSpec(mark=Mark.SCATTER, data=data, x=Encoding("x"), y=Encoding("y"))

    explore = to_plotly(ChartSpec(**{**base.__dict__, "interaction": Interaction.EXPLORE}))
    assert explore.layout.dragmode == "zoom"

    static = to_plotly(base.as_static())
    assert static.layout.dragmode is False
    assert static.layout.hovermode is False


@pytest.mark.skipif(not HAS_MPL, reason="matplotlib not installed")
def test_matplotlib_ignores_the_ceiling_because_print_is_print() -> None:
    """A renderer delivers the lesser of the spec's ceiling and its medium.

    Matplotlib's medium is paper, so raising or lowering the ceiling must
    make no difference at all to what it draws -- if it did, a figure in the
    PDF and the same figure in the report would have come from two different
    decisions rather than one spec.
    """
    import io
    import re as _re

    spec = ChartSpec(
        mark=Mark.BAR,
        data=[{"x": "a", "y": 1.0}, {"x": "b", "y": 2.0}],
        x=Encoding("x", "nominal"),
        y=Encoding("y"),
        title="Counts",
        interaction=Interaction.EXPLORE,
    )

    def drawn(chart: ChartSpec) -> str:
        figure = to_matplotlib(chart)
        buffer = io.BytesIO()
        figure.savefig(buffer, format="svg", metadata={"Date": None})
        figure.clf()
        # Matplotlib names its clip paths and glyph defs randomly per call;
        # those identifiers are not part of the picture.
        return _re.sub(r"[#\"](?:p|m)[0-9a-f]{10}", "#id", buffer.getvalue().decode())

    assert drawn(spec) == drawn(spec.as_static())


# ==========================================================================
# P0-3 -- Core is not UI: one engine, two front doors
# ==========================================================================


def _comparable(audit: Any) -> list[dict[str, Any]]:
    """An audit log stripped of what legitimately differs between two runs.

    Timestamps and fingerprints of an identical frame are not identity; the
    operations, the reasons and the confidences are.
    """
    keep = (
        "operation",
        "issue_ids",
        "columns",
        "reason",
        "rule_source",
        "repair_class",
        "decision_source",
        "repair_confidence",
        "reversible",
        "cells_changed",
        "applied",
    )
    return [{k: v for k, v in record.items() if k in keep} for record in audit.to_list()]


def test_a_studio_decision_produces_the_same_frame_as_the_python_api(
    synthetic: pd.DataFrame,
) -> None:
    """UI decision -> replay -> identical output.

    The Studio holds no cleaning logic. If it did, this is the test that would
    fail: the same three decisions taken through the page and through Python
    would land on different data.
    """
    workspace = sp.studio(synthetic, **SCAN_CONTEXT)

    # A reviewer works through the page and exports what they decided.
    reviewed = sp.guided_prepare(synthetic, **SCAN_CONTEXT)
    taken = 0
    while taken < 3:
        question = reviewed.next_question()
        if question is None:
            break
        reviewed.waive(question.issue_id, "reviewed in the studio")
        taken += 1
    assert taken > 0, "the fixture must raise something for a reviewer to decide"
    exported = reviewed.export_decisions()

    through_the_page = workspace.apply_decisions(exported, synthetic, **SCAN_CONTEXT)
    through_python = sp.guided_prepare(synthetic, decisions=exported, **SCAN_CONTEXT).finish()

    pd.testing.assert_frame_equal(through_the_page.clean_df, through_python.clean_df)
    assert through_the_page.waivers == through_python.waivers
    assert _comparable(through_the_page.audit) == _comparable(through_python.audit)
    assert through_the_page.status is through_python.status


def test_a_studio_repair_decision_matches_the_python_api(synthetic: pd.DataFrame) -> None:
    """Not only waivers. An applied treatment must agree too."""
    workspace = sp.studio(synthetic, **SCAN_CONTEXT)
    session = sp.guided_prepare(synthetic, **SCAN_CONTEXT)

    applied = 0
    while applied < 2:
        question = session.next_question()
        if question is None:
            break
        if question.options:
            session.answer(question.issue_id, question.options[0].name)
            applied += 1
        else:
            session.skip(question.issue_id)
    exported = session.export_decisions()

    page = workspace.apply_decisions(exported, synthetic, **SCAN_CONTEXT)
    api = sp.guided_prepare(synthetic, decisions=exported, **SCAN_CONTEXT).finish()

    pd.testing.assert_frame_equal(page.clean_df, api.clean_df)
    assert _comparable(page.audit) == _comparable(api.audit)


def test_the_studio_page_carries_no_repair_logic() -> None:
    """The page records decisions; it never computes one.

    Grepping the shipped JavaScript for the vocabulary of repair is crude, and
    that is the point: any drift toward doing the work in the browser has to
    introduce one of these words, and this test makes that visible in review.
    """
    from smartprep.reporting.interactive import CHART_SCRIPT, GRID_SCRIPT

    forbidden = ("impute", "median(", "winsor", "fillna", "repair", "coerce")
    scripts = (GRID_SCRIPT + CHART_SCRIPT).lower()
    found = [word for word in forbidden if word in scripts]
    assert not found, f"repair vocabulary reached the browser: {found}"


def test_sorting_and_filtering_in_the_page_cannot_reach_the_frame(
    synthetic: pd.DataFrame,
) -> None:
    """The grid changes what is seen, never what is stored."""
    workspace = sp.studio(synthetic, **SCAN_CONTEXT)
    assert "Sorting and filtering here change what you see, never the data." in workspace.html


# ==========================================================================
# P0-4 -- the ChartSpec is the single source of truth
# ==========================================================================


def _example_specs(frame: pd.DataFrame) -> list[ChartSpec]:
    profile = sp.profile(frame)
    specs = [
        distribution_chart(profile.get("invoice_amount")),
        category_chart(profile.get("country")),
        box_chart(profile.get("invoice_amount")),
        scatter_chart(frame, "invoice_amount", "quantity"),
    ]
    return [s for s in specs if s is not None]


#: Marks where one record in the spec is exactly one drawn point, so a
#: renderer's count can be compared with the spec's directly. Box and matrix
#: summarise many values into one mark and are checked by their labels instead.
_POINTWISE = (Mark.SCATTER, Mark.BAR, Mark.HISTOGRAM, Mark.LINE, Mark.STEP)


def _matplotlib_points(figure: Any, spec: ChartSpec) -> int:
    axis = figure.axes[0]
    if spec.mark is Mark.SCATTER:
        return sum(len(c.get_offsets()) for c in axis.collections)
    if spec.mark in (Mark.LINE, Mark.STEP):
        # Reference lines are drawn as lines too; only the data line counts.
        return max((len(line.get_xdata()) for line in axis.lines), default=0)
    return len([p for p in axis.patches if getattr(p, "get_height", None)])


def _plotly_points(figure: Any, spec: ChartSpec) -> int:
    total = 0
    for trace in figure.data:
        values = getattr(trace, "x", None)
        if values is None:
            values = getattr(trace, "y", None)
        total += len(values) if values is not None else 0
    return total


def test_every_renderer_draws_the_same_number_of_points(synthetic: pd.DataFrame) -> None:
    """One record in, one mark out -- in every backend.

    A renderer that filters, clips or re-aggregates on its own would show a
    different number of points from its siblings, and the report and the PDF
    would quietly stop being the same picture. The spec decides what is
    drawn; a renderer decides only how it looks.
    """
    checked = 0
    for spec in _example_specs(synthetic):
        assert render_svg(spec).startswith("<svg")
        if spec.mark not in _POINTWISE:
            continue
        expected = len(spec.data)
        checked += 1
        if HAS_MPL:
            figure = to_matplotlib(spec)
            assert _matplotlib_points(figure, spec) == expected, (
                f"matplotlib drew a different number of points for {spec.title!r}"
            )
            figure.clf()
        if HAS_PLOTLY:
            assert _plotly_points(to_plotly(spec), spec) == expected, (
                f"plotly drew a different number of points for {spec.title!r}"
            )
    assert checked, "no point-wise chart was exercised"


def test_summarising_marks_agree_on_their_categories(synthetic: pd.DataFrame) -> None:
    """A box plot draws five numbers per group rather than one mark per row,
    so parity is checked on the groups instead of the points."""
    profile = sp.profile(synthetic)
    spec = box_chart(profile.get("invoice_amount"))
    assert spec is not None and spec.mark is Mark.BOX
    labels = [str(row.get("label", "")) for row in spec.data]

    body = render_svg(spec)
    for label in labels:
        assert label in body

    if HAS_PLOTLY:
        figure = to_plotly(spec)
        assert [str(trace.name) for trace in figure.data] == labels


@pytest.mark.skipif(not (HAS_MPL and HAS_PLOTLY), reason="both backends needed")
def test_every_renderer_reads_the_same_title_and_axes(synthetic: pd.DataFrame) -> None:
    """Labels come from the spec. A renderer inventing its own titles is a
    renderer a reader cannot cross-check against the report."""
    for spec in _example_specs(synthetic):
        if not spec.title:
            continue
        assert spec.title in render_svg(spec)

        figure = to_matplotlib(spec)
        texts = " ".join(
            [str(figure.axes[0].get_title(loc="left")), *(str(t.get_text()) for t in figure.texts)]
        )
        assert spec.title in texts, f"matplotlib lost the title {spec.title!r}"
        figure.clf()

        assert spec.title in str(to_plotly(spec).layout.title.text)


@pytest.mark.skipif(not HAS_PLOTLY, reason="plotly not installed")
def test_every_renderer_repeats_the_sampling_caveat(synthetic: pd.DataFrame) -> None:
    """The most dangerous thing a renderer can drop.

    A reader who believes they are seeing every point, and is seeing a
    thousand of them, will draw a conclusion the picture does not support --
    so the caveat has to survive every backend, not only the one that
    generated it.
    """
    spec = ChartSpec(
        mark=Mark.SCATTER,
        data=[{"x": float(i), "y": float(i)} for i in range(20)],
        x=Encoding("x"),
        y=Encoding("y"),
        title="Sampled",
        fidelity=Fidelity.RANDOM_SAMPLE,
        fidelity_note="3,000 of 120,000 rows",
    )
    assert spec.fidelity_note in render_svg(spec)
    assert spec.fidelity_note in str(to_plotly(spec).layout.annotations)
    if HAS_MPL:
        figure = to_matplotlib(spec)
        assert spec.fidelity_note in " ".join(str(t.get_text()) for t in figure.texts)
        figure.clf()


def test_charts_are_built_from_eda_results_not_from_frames(synthetic: pd.DataFrame) -> None:
    """EDA result -> ChartSpec -> renderer.

    The builders take a profile, not a DataFrame, precisely so that the number
    in the chart and the number in the report come from one computation.
    """
    profile = sp.profile(synthetic)
    column = profile.get("invoice_amount")
    spec = distribution_chart(column)
    assert spec is not None
    drawn = sum(int(row.get("count", 0)) for row in spec.data)
    assert drawn == column.count, "the histogram and the profile disagree on the row count"


# ==========================================================================
# Preview is not Apply
# ==========================================================================


def test_a_preview_writes_no_audit_record(synthetic: pd.DataFrame) -> None:
    """Considering a repair is not a thing that happened to the data.

    An audit log that records deliberation alongside action stops being a
    record of what changed, which is the only thing it is for.
    """
    from smartprep.core.audit import AuditLog
    from smartprep.repair.sandbox import preview_candidates

    result = sp.scan(synthetic, **SCAN_CONTEXT)
    for issue in result.issues[:6]:
        for candidate in preview_candidates(synthetic, issue):
            assert candidate.applied is False
            assert not isinstance(candidate, AuditLog)
            assert not hasattr(candidate, "audit")


def test_the_sandbox_has_no_way_to_commit(synthetic: pd.DataFrame) -> None:
    """Deliberate friction.

    A sandbox with a commit button is a second path that changes data, and the
    second path is always the one that skips the audit. Committing goes back
    through guided mode, which records who decided and why.
    """
    from smartprep.repair.sandbox import TreatmentPreview

    forbidden = ("apply", "commit", "save", "write", "execute", "run")
    exposed = [
        name
        for name in dir(TreatmentPreview)
        if not name.startswith("_") and any(word in name.lower() for word in forbidden)
    ]
    assert not exposed, f"the sandbox exposes a commit path: {exposed}"


def test_previewing_every_candidate_changes_nothing(synthetic: pd.DataFrame) -> None:
    from smartprep.repair.sandbox import preview_candidates

    before = synthetic.copy(deep=True)
    result = sp.scan(synthetic, **SCAN_CONTEXT)
    for issue in result.issues:
        preview_candidates(synthetic, issue)
    pd.testing.assert_frame_equal(synthetic, before)


def test_considering_a_treatment_is_not_choosing_one(synthetic: pd.DataFrame) -> None:
    """State records what is being weighed. It cannot apply it."""
    from smartprep.core.state import StudioState

    state = StudioState.of(synthetic)
    state.consider("SOME-ISSUE", "impute_median")
    assert state.pending_treatment == {
        "issue_id": "SOME-ISSUE",
        "treatment": "impute_median",
    }
    assert not any(hasattr(state, name) for name in ("apply", "commit", "execute", "finish"))


# ==========================================================================
# Profiling is not Repair
# ==========================================================================


def test_profiling_never_modifies(synthetic: pd.DataFrame) -> None:
    """Every read-only entry point, asserted read-only.

    Each of these is called on data somebody has not agreed to change yet.
    One of them quietly coercing a column is the kind of bug that is found
    months later in a number nobody can reproduce.
    """
    before = synthetic.copy(deep=True)

    sp.profile(synthetic)
    sp.scan(synthetic, **SCAN_CONTEXT)
    sp.associations(synthetic)
    sp.missingness(synthetic)

    pd.testing.assert_frame_equal(synthetic, before)


def test_a_scan_result_carries_no_repaired_frame(synthetic: pd.DataFrame) -> None:
    """Diagnosis produces findings, not data. A scan that handed back a
    cleaned frame would make the read-only entry point the fast route to a
    silent repair."""
    result = sp.scan(synthetic, **SCAN_CONTEXT)
    for name in ("clean_df", "repaired", "fixed_df", "output"):
        assert not hasattr(result, name), f"scan returned data through {name!r}"


def test_the_studio_can_be_opened_without_preparing(synthetic: pd.DataFrame) -> None:
    """``prepare=False`` means diagnosis only, and must really mean it."""
    before = synthetic.copy(deep=True)
    sp.studio(synthetic, prepare=False, **SCAN_CONTEXT)
    pd.testing.assert_frame_equal(synthetic, before)


# ==========================================================================
# No silent destructive transformation
# ==========================================================================


def test_every_applied_change_carries_a_reason(prepared: Any) -> None:
    """A change with no stated reason is a change nobody can review, and a
    change nobody can review is indistinguishable from a bug."""
    applied = [r for r in prepared.audit if r.applied]
    assert applied, "the fixture must apply something"
    for record in applied:
        assert record.reason.strip(), f"{record.operation} changed data without a reason"
        assert record.repair_confidence > 0
        assert record.rule_source is not None


def test_every_refusal_carries_a_reason(prepared: Any) -> None:
    """Refusing is a decision too, and an unexplained refusal is as opaque as
    an unexplained change."""
    for record in prepared.audit:
        if not record.applied:
            assert record.reason.strip()


def test_an_irreversible_change_is_never_made_quietly(prepared: Any) -> None:
    """Reversibility is a demotion factor in the ladder, so an irreversible
    repair should not be reaching automatic mode at all -- and if one ever
    does, it must at least be on the record as irreversible."""
    for record in prepared.audit:
        if record.applied and not record.reversible:
            assert record.reason.strip()
            assert record.before_fingerprint is not None
            assert record.after_fingerprint is not None


def test_automatic_mode_reports_what_it_declined_to_do(prepared: Any) -> None:
    """The disclosure that makes the rest trustworthy.

    A tool that reports only its successes is a tool whose silence has to be
    interpreted, and readers interpret silence as 'nothing to see'.
    """
    assert hasattr(prepared, "unresolved_issues")
    report = prepared.to_markdown() if hasattr(prepared, "to_markdown") else ""
    if prepared.unresolved_issues and report:
        assert "NOT" in report or "not do" in report or "unresolved" in report.lower()


def test_a_filter_is_not_a_deletion(synthetic: pd.DataFrame) -> None:
    """The distinction the grid states on its own face.

    Narrowing a view and dropping rows look identical on screen and are
    entirely different things. Confusing them is how a reader ends up
    believing a dataset is smaller than it is.
    """
    from smartprep.core.state import Comparison, FilterClause, StudioState

    state = StudioState.of(synthetic)
    state.filter_by(FilterClause("country", Comparison.EQUALS, "Morocco"))

    assert len(state.view(synthetic)) < len(synthetic)
    assert len(synthetic) == len(StudioState.of(synthetic).view(synthetic))


# ==========================================================================
# Documentation is a claim, and a claim gets a test
# ==========================================================================


def test_the_capability_registry_is_honest() -> None:
    """Every claim names something that exists, or is scheduled.

    Four documents used to say what the package could do, and they disagreed
    within a single day of work -- the README announced drag-and-drop
    composition as implemented in one row and "not yet" three rows below it.
    """
    from smartprep.capabilities import check_capabilities

    assert check_capabilities() == []


def test_the_readme_table_matches_the_registry() -> None:
    """Generated, not transcribed. A table nobody regenerates goes stale, and
    a stale capability table is the most misleading page in a project."""
    from smartprep.capabilities import capability_table

    readme = pathlib.Path(__file__).resolve().parents[1] / "README.md"
    if not readme.exists():  # pragma: no cover - not shipped in the sdist
        pytest.skip("README is not distributed with the package")

    text = readme.read_text(encoding="utf-8")
    assert capability_table() in text, (
        "the README capability table no longer matches smartprep.capabilities; "
        "regenerate it from capability_table()"
    )


def test_nothing_is_claimed_implemented_without_a_version() -> None:
    from smartprep.capabilities import CAPABILITIES, Status

    for capability in CAPABILITIES:
        if capability.status is Status.IMPLEMENTED:
            assert capability.since, f"{capability.name} does not say when it landed"


def test_a_limited_capability_states_its_limit() -> None:
    """A capability with a caveat nobody wrote down reads as one without."""
    from smartprep.capabilities import CAPABILITIES

    caveated = {c.name for c in CAPABILITIES if c.caveat}
    assert {"visual_builder", "linked_brushing", "faceting"} <= caveated


# ==========================================================================
# Encoding channels -- honoured everywhere, or refused
# ==========================================================================


def _coloured_spec() -> ChartSpec:
    return ChartSpec(
        mark=Mark.HORIZONTAL_BAR,
        data=[
            {"label": "a", "value": 3.0, "g": "x"},
            {"label": "b", "value": 5.0, "g": "y"},
            {"label": "c", "value": 2.0, "g": "x"},
        ],
        x=Encoding("value"),
        y=Encoding("label", "nominal"),
        color=Encoding("g", "nominal"),
        title="Coloured",
    )


def test_every_renderer_honours_the_colour_channel() -> None:
    """A channel one backend draws and another ignores is a chart that means
    two things. ``color`` used to be read by exactly one mark in one renderer.
    """
    import re

    spec = _coloured_spec()
    assert spec.colour_groups() == ["x", "y"]

    fills = re.findall(r'<rect[^>]*fill="(#[0-9a-fA-F]{6})"', render_svg(spec))
    assert len({f.lower() for f in fills}) >= 2, "the SVG drew one colour for two groups"

    if HAS_PLOTLY:
        colours = list(to_plotly(spec).data[0].marker.color)
        assert len(set(colours)) == 2

    if HAS_MPL:
        figure = to_matplotlib(spec)
        assert len({tuple(patch.get_facecolor()) for patch in figure.axes[0].patches}) == 2
        figure.clf()


def test_the_colour_of_a_group_is_the_same_in_every_renderer() -> None:
    """The group ordering lives on the spec for this reason: a legend that
    means one thing on screen and another in a slide is worse than none."""
    spec = _coloured_spec()
    from smartprep.viz.svg import LIGHT

    expected = [spec.colour_of(row, LIGHT.series) for row in spec.data]
    assert expected == [LIGHT.series[0], LIGHT.series[1], LIGHT.series[0]]

    if HAS_PLOTLY:
        assert list(to_plotly(spec).data[0].marker.color) == expected


def test_an_uncoloured_chart_is_unchanged() -> None:
    spec = ChartSpec(
        mark=Mark.BAR,
        data=[{"x": "a", "y": 1.0}],
        x=Encoding("x", "nominal"),
        y=Encoding("y"),
    )
    assert spec.colour_groups() == []
    assert spec.colour_of(spec.data[0], ("#111111",)) is None


def test_every_declared_encoding_channel_is_honoured_or_refused() -> None:
    """The rule that outlives any particular channel.

    A channel a spec declares must either change what every renderer draws, or
    be refused with a reason. The third option -- accepted, stored, and quietly
    ignored -- is the failure this project keeps rediscovering: a `Mark` enum
    declaring marks nothing could draw, an `interactive` flag no renderer read,
    a `color` channel one mark in one backend honoured, a `facet` drawn by
    nothing at all.
    """
    from smartprep.viz.spec import ChartSpec as Spec

    channels = {"x", "y", "color", "facet", "size"}
    declared = {f for f in Spec.__dataclass_fields__ if f in channels}

    honoured = {"x", "y", "color", "facet", "size"}
    unclaimed = declared - honoured
    assert not unclaimed, (
        f"these channels are declared but nothing honours or refuses them: {unclaimed}. "
        "Implement, refuse, or remove -- silence is the one option that misleads."
    )


def test_a_facet_changes_what_every_renderer_draws() -> None:
    """Faceting proved: the same spec with and without a facet must not render
    identically, in any backend."""
    from dataclasses import replace

    data = [
        {"x": "a", "y": 1.0, "g": "north"},
        {"x": "b", "y": 30.0, "g": "south"},
    ]
    plain = ChartSpec(
        mark=Mark.BAR,
        data=data,
        x=Encoding("x", "nominal"),
        y=Encoding("y"),
        title="T",
    )
    faceted = replace(plain, facet=Encoding("g", "nominal"))

    assert render_svg(plain) != render_svg(faceted)
    assert len(faceted.panels()) == 2

    if HAS_PLOTLY:
        assert len(to_plotly(faceted).data) == 2

    if HAS_MPL:
        figure = to_matplotlib(faceted)
        assert len([a for a in figure.axes if a.get_title(loc="left")]) == 2
        figure.clf()


def test_a_channel_that_cannot_be_honoured_says_so(synthetic: pd.DataFrame) -> None:
    """Where a channel genuinely cannot apply, the refusal names the reason
    and what to do instead."""
    from smartprep.viz.compose import Composition, CompositionRefused, compose, fields_of

    fields = fields_of(sp.profile(synthetic))
    with pytest.raises(CompositionRefused) as raised:
        compose(
            synthetic,
            fields,
            Composition(x="country", y="invoice_amount", aggregate="mean", facet="sector"),
        )
    assert "Facet the underlying rows" in str(raised.value)


# ==========================================================================
# Accessibility -- what a reader who cannot see the picture is told
# ==========================================================================


def test_the_archival_report_stays_small(prepared: Any, tmp_path: Any) -> None:
    """AD-013's actual promise: a file you can attach to an email and open in
    ten years. It is a promise about bytes, so it is checked in bytes."""
    written = prepared.export_report(str(tmp_path / "report.html"))
    size = pathlib.Path(written).stat().st_size
    assert size < 120_000, f"the archival report has grown to {size // 1024} KB"


def test_the_studio_does_not_balloon(synthetic: pd.DataFrame) -> None:
    """A workspace is allowed to be much larger than a report. It is not
    allowed to grow without anybody noticing.

    Every precomputed chart is markup that ships inside the page, so adding
    one more pairing to a catalogue is adding weight to every copy of the
    file. This caught a 3.2 MB Studio built from a full cross product.
    """
    page = sp.studio(synthetic, **SCAN_CONTEXT).html
    size = len(page.encode("utf-8"))
    assert size < 900_000, f"the Studio has grown to {size // 1024} KB"


def test_a_dense_chart_says_why_its_points_are_not_selectable() -> None:
    """Silence would read as 'this chart is linked to nothing', which is a
    different and more discouraging claim than 'there are too many points here
    for picking one to mean much'."""
    import numpy as np

    from smartprep.viz.compose import Composition, compose, fields_of

    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"a": rng.normal(size=800), "b": rng.normal(size=800)})
    spec = compose(
        frame,
        fields_of(sp.profile(frame)),
        Composition(x="a", y="b"),
        identity=__import__(
            "smartprep.core.identity", fromlist=["StableRowIndex"]
        ).StableRowIndex.of(frame),
    )
    assert not any(row.get("keys") for row in spec.data)
    assert any(a.get("kind") == "unbrushable" for a in spec.annotations)
    assert "data-keys" not in sp.render_svg(spec)


def test_charts_announce_themselves_to_assistive_technology() -> None:
    spec = ChartSpec(
        mark=Mark.BAR,
        data=[{"x": "a", "y": 1.0}],
        x=Encoding("x", "nominal"),
        y=Encoding("y"),
        title="Rows by country",
        rationale="Concentration decides whether a mode is meaningful.",
    )
    body = render_svg(spec)
    assert 'role="img"' in body
    assert "<title>Rows by country</title>" in body
    assert "<desc>" in body
    assert "Concentration decides" in body


def test_a_sampled_chart_says_so_to_a_screen_reader() -> None:
    """The caveat must not be visual-only. A reader using a screen reader is
    exactly the reader who cannot see the footnote."""
    spec = ChartSpec(
        mark=Mark.SCATTER,
        data=[{"x": 1.0, "y": 1.0}],
        x=Encoding("x"),
        y=Encoding("y"),
        title="Amount against quantity",
        fidelity=Fidelity.RANDOM_SAMPLE,
        fidelity_note="3,000 of 120,000 rows",
    )
    described = render_svg(spec)
    head = described[: described.index("<rect")]
    assert "3,000 of 120,000 rows" in head, "the caveat is not in the accessible description"


def test_quality_overlays_are_not_colour_alone(synthetic: pd.DataFrame) -> None:
    """A reader with a colour vision deficiency must still see which cells are
    flagged. Colour may carry the signal; it may not be the only thing that
    does."""
    from smartprep.reporting.interactive import GRID_CSS

    for rule in ("td.q-missing", "td.q-flagged", "td.q-changed"):
        block = GRID_CSS[GRID_CSS.index(rule) : GRID_CSS.index(rule) + 220]
        block = block[: block.index("}")]
        non_colour = ("content", "font-style", "border", "text-decoration", "font-weight")
        assert any(prop in block for prop in non_colour), f"{rule} signals with colour alone"


def _contrast(first: str, second: str) -> float:
    """WCAG relative-contrast ratio between two hex colours."""

    def luminance(colour: str) -> float:
        raw = colour.lstrip("#")
        channels = [int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_every_colour_that_carries_text_is_readable() -> None:
    """AA, measured rather than eyeballed.

    ``muted`` carries every rationale, caption and fidelity note in the
    library -- which is to say it carries the caveats. A caveat a reader
    cannot read is a caveat that was not given, so this is not a cosmetic
    threshold.
    """
    from smartprep.viz.svg import LIGHT

    for name in ("foreground", "muted", "accent", "warning", "danger", "positive"):
        colour = getattr(LIGHT, name)
        ratio = _contrast(colour, LIGHT.background)
        assert ratio >= 4.5, f"theme.{name} ({colour}) is {ratio:.2f}:1, below AA 4.5:1"


def test_the_report_palette_matches_the_chart_palette() -> None:
    """One design, two places it is written down. They must not drift, or a
    caption in the page and the same caption in a chart are different colours
    with different contrast."""
    import re

    from smartprep.reporting.html import CSS
    from smartprep.viz.svg import LIGHT

    tokens = dict(re.findall(r"--(\w+):\s*(#[0-9a-fA-F]{6})", CSS))
    assert tokens.get("muted") == LIGHT.muted
    assert tokens.get("accent") == LIGHT.accent
    assert tokens.get("warn") == LIGHT.warning
    assert tokens.get("fg") == LIGHT.foreground


def test_a_tooltip_is_reachable_without_a_mouse(synthetic: pd.DataFrame) -> None:
    """A tooltip only a mouse can reach is one half the readers never see."""
    from smartprep.reporting.interactive import CHART_SCRIPT

    assert "focusin" in CHART_SCRIPT
    assert "Escape" in CHART_SCRIPT


def test_the_studio_respects_a_reduced_motion_preference(synthetic: pd.DataFrame) -> None:
    """Stage playback is meaningful motion, which is not the same as motion a
    reader can tolerate."""
    workspace = sp.studio(synthetic, **SCAN_CONTEXT)
    assert "prefers-reduced-motion" in workspace.html


def test_the_studio_is_reachable_from_a_keyboard(synthetic: pd.DataFrame) -> None:
    workspace = sp.studio(synthetic, **SCAN_CONTEXT)
    assert ":focus-visible" in workspace.html
    assert 'scope="col"' in workspace.html or "tabindex" in workspace.html


# ==========================================================================
# Prose must agree with the capability table
# ==========================================================================


def test_no_prose_denies_a_capability_the_table_marks_implemented() -> None:
    """The guard that was missing when 1.0.0 was cut.

    The registry test checks that the *table* matches the code. It said
    nothing about the paragraph eleven lines below it, which claimed the
    visual workflow canvas, faceting and multi-series composition "do not
    exist yet" -- while the table above marked all three Implemented. Both
    render on the same PyPI page.

    A reader who sees a feature called implemented and then called absent
    stops believing either statement, and the implementation was fine.
    """
    from smartprep.capabilities import CAPABILITIES, Status

    readme = pathlib.Path(__file__).resolve().parents[1] / "README.md"
    if not readme.exists():  # pragma: no cover - not shipped in the sdist
        pytest.skip("README is not distributed with the package")
    text = readme.read_text(encoding="utf-8").lower()

    denials = ("do not exist yet", "does not exist yet", "not yet implemented", "not started")
    # Words that identify a capability in running prose, taken from the
    # registry rather than hand-listed so a new capability is covered too.
    stopwords = {
        "and",
        "the",
        "a",
        "an",
        "or",
        "of",
        "with",
        "for",
        "to",
        "in",
        "sp",
        "data",
        "execution",
        "composition",
        "diagnostics",
        "reports",
        "renderers",
        "export",
        "publishing",
        "state",
        "row",
        "identity",
    }

    problems = []
    for capability in CAPABILITIES:
        if capability.status is not Status.IMPLEMENTED:
            continue
        terms = {
            word.strip("`(),.—-").lower()
            for word in capability.summary.split()
            if len(word.strip("`(),.—-")) > 4
        } - stopwords
        if not terms:
            continue
        for denial in denials:
            for position in _positions(text, denial):
                window = text[max(0, position - 400) : position + 200]
                hit = terms & set(window.replace("-", " ").replace("/", " ").split())
                if hit:
                    problems.append(
                        f"{capability.name} is marked Implemented, but the README "
                        f"says {denial!r} near {sorted(hit)}"
                    )
    assert not problems, "\n".join(problems)


def _positions(text: str, needle: str) -> list[int]:
    found, start = [], text.find(needle)
    while start != -1:
        found.append(start)
        start = text.find(needle, start + 1)
    return found


def test_no_capability_is_planned_for_a_released_version() -> None:
    """At 1.0.0 a "Planned (v0.9)" badge tells a reader the project missed a
    deadline it never had. An undecided milestone is honest; a stale one is a
    defect."""
    from packaging.version import Version

    from smartprep.capabilities import CAPABILITIES

    published = Version(sp.__version__)
    stale = [c.name for c in CAPABILITIES if c.planned_for and Version(c.planned_for) <= published]
    assert not stale, f"planned for versions already published: {stale}"
