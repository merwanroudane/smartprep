"""The visual workflow, the pipeline canvas, faceting and multi-series.

A visual pipeline is where a data tool usually acquires a second execution
engine: the canvas grows its own idea of what "repair missing values" means,
the Python API keeps the original, and the two answers have to be reconciled
by hand forever afterwards. The first section of this file is the test that
would fail the day that happened.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT
from smartprep.core.enums import IssueCategory
from smartprep.viz import ChartSpec, Encoding, Mark, available_backends, render_svg
from smartprep.viz.compose import Composition, CompositionRefused, compose, fields_of
from smartprep.workflow import Stage, Workflow, WorkflowError, default_workflow, stage_for

HAS_MPL = available_backends()["matplotlib"]
HAS_PLOTLY = available_backends()["plotly"]


# ==========================================================================
# The invariant: visual replay == Python replay
# ==========================================================================


def _records(audit: Any) -> Counter[tuple[str, int, bool]]:
    return Counter((r.operation, r.cells_changed, r.applied) for r in audit)


def test_running_every_stage_equals_automatic_mode(synthetic: pd.DataFrame) -> None:
    """The whole safety claim of the workflow, in one assertion.

    A node is not an implementation -- it is a filter over the plan the core
    already built. So running all of them is not merely *similar* to
    ``auto_prepare``: it is the same operations, and it must produce the same
    frame and the same audit records.
    """
    automatic = sp.auto_prepare(synthetic, **SCAN_CONTEXT)
    run = default_workflow().run(synthetic, **SCAN_CONTEXT)

    pd.testing.assert_frame_equal(run.frame, automatic.clean_df)
    assert run.cells_changed == automatic.audit.cells_changed
    assert _records(run.audit) == _records(automatic.audit)


def test_the_workflow_writes_the_same_audit_not_a_parallel_one(
    synthetic: pd.DataFrame,
) -> None:
    """Every change a node makes is recorded by the core's audit log, with the
    confidence and rule source the core assigned. A canvas keeping its own
    log would be a second record to reconcile."""
    run = default_workflow().run(synthetic, **SCAN_CONTEXT)
    applied = [r for r in run.audit if r.applied and r.cells_changed]
    assert applied
    for record in applied:
        assert record.reason.strip()
        assert record.repair_confidence > 0
        assert record.rule_source is not None


def test_each_node_reports_only_its_own_work(synthetic: pd.DataFrame) -> None:
    """The stages share one audit log, so reading the log's running total per
    stage would count every earlier stage again in every later one -- the same
    double-count that once doubled the guided-mode handoff."""
    run = default_workflow().run(synthetic, **SCAN_CONTEXT)
    assert sum(o.cells_changed for o in run.outcomes) == run.audit.cells_changed


def test_disabling_a_stage_leaves_its_findings_open(synthetic: pd.DataFrame) -> None:
    workflow = default_workflow()
    workflow.disable("node-categories")
    run = workflow.run(synthetic, **SCAN_CONTEXT)

    outcome = run.outcome("node-categories")
    assert outcome.status == "skipped"
    assert any("left open" in w for w in outcome.warnings)

    full = default_workflow().run(synthetic, **SCAN_CONTEXT)
    assert run.cells_changed < full.cells_changed


def test_every_repair_belongs_to_a_stage() -> None:
    """A repair owned by no stage would never run, and the workflow would
    quietly do less than automatic mode while looking complete."""
    homeless = [c for c in IssueCategory if stage_for(c) is None]
    assert not homeless, f"these categories have no stage: {[c.value for c in homeless]}"


def test_a_homeless_repair_is_loud_rather_than_silent(
    synthetic: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If a new detector category is added and nobody assigns it a stage, the
    workflow must refuse rather than skip it."""
    import smartprep.workflow as module

    monkeypatch.setattr(module, "_stage_of", lambda operation, issues: None)
    with pytest.raises(WorkflowError, match="belong to no stage"):
        default_workflow().run(synthetic, **SCAN_CONTEXT)


# ==========================================================================
# Arranging a pipeline
# ==========================================================================


def test_stages_cannot_be_arranged_into_a_wrong_answer() -> None:
    """Types before ranges is not a convention: a range check on the string
    ``"1,200.50"`` is meaningless."""
    workflow = default_workflow()
    with pytest.raises(WorkflowError, match="must run before"):
        workflow.move("node-outliers", 0)


def test_a_dependency_cannot_point_forwards() -> None:
    workflow = default_workflow()
    with pytest.raises(WorkflowError, match="runs later"):
        workflow.connect("node-types", "node-outliers")


def test_a_stage_cannot_be_added_twice() -> None:
    workflow = default_workflow()
    with pytest.raises(WorkflowError, match="already in this workflow"):
        workflow.add(Stage.MISSING)


def test_a_workflow_without_a_scan_is_refused(synthetic: pd.DataFrame) -> None:
    workflow = Workflow()
    workflow.add(Stage.TYPES)
    assert any("Scan" in problem for problem in workflow.validate())
    with pytest.raises(WorkflowError):
        workflow.run(synthetic, **SCAN_CONTEXT)


def test_depending_on_a_disabled_stage_is_refused() -> None:
    workflow = default_workflow()
    workflow.connect("node-outliers", "node-types")
    workflow.disable("node-types")
    assert any("disabled" in problem for problem in workflow.validate())


# ==========================================================================
# Export -- a pipeline you can read
# ==========================================================================


def test_a_workflow_round_trips_through_json() -> None:
    workflow = default_workflow()
    workflow.disable("node-duplicates")
    workflow.configure("node-missing", strategy="median")

    rebuilt = Workflow.from_json(workflow.to_json())
    assert [n.stage for n in rebuilt.ordered()] == [n.stage for n in workflow.ordered()]
    assert not rebuilt.get("node-duplicates").enabled
    assert rebuilt.get("node-missing").parameters == {"strategy": "median"}


def test_the_exported_python_is_runnable(synthetic: pd.DataFrame) -> None:
    """A pipeline you cannot export is one you cannot review, put in version
    control, or run on a machine without a browser."""
    workflow = default_workflow()
    workflow.disable("node-outliers")
    source = workflow.to_python()

    assert "import smartprep as sp" in source
    assert "workflow.add(sp.Stage.SCAN)" in source
    assert "workflow.disable('node-outliers')" in source

    # Execute the definition, not the run: the point is that the exported
    # script rebuilds the same pipeline, and running it here would only
    # re-test the engine.
    definition = source.split("run = workflow.run(df)")[0]
    namespace: dict[str, Any] = {}
    exec(compile(definition, "<exported>", "exec"), namespace)  # noqa: S102
    rebuilt = namespace["workflow"]
    assert [n.stage for n in rebuilt.ordered()] == [n.stage for n in workflow.ordered()]
    assert not rebuilt.get("node-outliers").enabled


def test_the_run_summary_names_every_stage(synthetic: pd.DataFrame) -> None:
    summary = default_workflow().run(synthetic, **SCAN_CONTEXT).summary()
    for stage in Stage:
        assert stage.label in summary


def test_the_canvas_reports_what_each_stage_cost(synthetic: pd.DataFrame) -> None:
    """Status, timing, rows, cells, findings and health -- computed in Python
    and rendered as text. The canvas exposes execution; it does not perform
    it."""
    page = sp.studio(synthetic, **SCAN_CONTEXT).html
    assert "Preparation pipeline" in page
    assert "This pipeline as Python" in page
    assert "audit:" in page


def test_the_canvas_states_the_equivalence_it_relies_on(synthetic: pd.DataFrame) -> None:
    page = sp.studio(synthetic, **SCAN_CONTEXT).html
    assert "a test\nasserts it" in page or "a test asserts it" in page.replace("\n", " ")


# ==========================================================================
# Faceting -- small multiples
# ==========================================================================


def _faceted() -> ChartSpec:
    return ChartSpec(
        mark=Mark.BAR,
        data=[
            {"x": "a", "y": 1.0, "g": "north"},
            {"x": "b", "y": 2.0, "g": "north"},
            {"x": "a", "y": 30.0, "g": "south"},
            {"x": "b", "y": 5.0, "g": "south"},
        ],
        x=Encoding("x", "nominal"),
        y=Encoding("y"),
        facet=Encoding("g", "nominal"),
        title="By region",
    )


def test_a_facet_becomes_one_panel_per_group() -> None:
    panels = _faceted().panels()
    assert [p.title for p in panels] == ["g = north", "g = south"]
    assert all(p.facet is None for p in panels), "a panel must not facet again"


def test_panels_share_one_scale() -> None:
    """A grid of charts with private axes is a grid nobody may compare, and
    comparing them is the only reason to draw a grid."""
    domains = {p.y_domain for p in _faceted().panels()}
    assert domains == {(0.0, 30.0)}


def test_too_many_panels_is_refused() -> None:
    spec = ChartSpec(
        mark=Mark.BAR,
        data=[{"x": "a", "y": 1.0, "g": f"g{i}"} for i in range(40)],
        x=Encoding("x", "nominal"),
        y=Encoding("y"),
        facet=Encoding("g", "nominal"),
    )
    with pytest.raises(ValueError, match="cannot be compared at a glance"):
        spec.panels()


def test_every_renderer_draws_the_same_panels() -> None:
    """Faceting is done on the spec, so each backend draws ordinary panels
    with the code it already had and the three cannot drift apart."""
    spec = _faceted()
    expected = len(spec.panels())

    assert render_svg(spec).count("<g transform=") == expected

    if HAS_MPL:
        from smartprep.viz import to_matplotlib

        figure = to_matplotlib(spec)
        drawn = [a for a in figure.axes if a.get_title(loc="left")]
        assert len(drawn) == expected
        assert {tuple(round(v, 1) for v in a.get_ylim()) for a in drawn} == {(0.0, 30.0)}
        figure.clf()

    if HAS_PLOTLY:
        from smartprep.viz import to_plotly

        assert len(to_plotly(spec).data) == expected


def test_a_faceted_chart_keeps_its_row_keys() -> None:
    """Linked selection across facets comes free, but only because a panel is
    a filter over the data rather than a re-computation of it."""
    spec = ChartSpec(
        mark=Mark.BAR,
        data=[
            {"x": "a", "y": 1.0, "g": "north", "keys": ["k0"]},
            {"x": "a", "y": 2.0, "g": "south", "keys": ["k1"]},
        ],
        x=Encoding("x", "nominal"),
        y=Encoding("y"),
        facet=Encoding("g", "nominal"),
    )
    assert [p.data[0]["keys"] for p in spec.panels()] == [["k0"], ["k1"]]


def test_composing_a_facet_puts_every_point_in_the_right_panel(
    synthetic: pd.DataFrame,
) -> None:
    """The failure this guards is invisible: a point in the wrong panel still
    looks like a point."""
    from smartprep.core.identity import StableRowIndex

    identity = StableRowIndex.of(synthetic)
    spec = compose(
        synthetic,
        fields_of(sp.profile(synthetic)),
        Composition(x="quantity", y="invoice_amount", facet="sales_channel"),
        identity=identity,
    )
    for panel in spec.panels():
        wanted = panel.title.split(" = ")[1]
        for datum in panel.data:
            rows = identity.restrict(synthetic, datum["keys"])
            assert set(rows["sales_channel"].astype(str)) == {wanted}


def test_faceting_an_aggregate_is_refused(synthetic: pd.DataFrame) -> None:
    """Aggregated data no longer lines up row for row with the frame, so the
    groups cannot be attached honestly. Saying so beats attaching wrong ones.
    """
    fields = fields_of(sp.profile(synthetic))
    with pytest.raises(CompositionRefused, match="aggregates"):
        compose(
            synthetic,
            fields,
            Composition(x="country", y="invoice_amount", aggregate="mean", facet="sector"),
        )


def test_faceting_on_a_measurement_is_refused(synthetic: pd.DataFrame) -> None:
    fields = fields_of(sp.profile(synthetic))
    with pytest.raises(CompositionRefused, match="small multiples need groups"):
        compose(
            synthetic,
            fields,
            Composition(x="quantity", y="invoice_amount", facet="unit_price"),
        )


# ==========================================================================
# Multi-series
# ==========================================================================


def test_a_series_column_reaches_the_spec(synthetic: pd.DataFrame) -> None:
    spec = compose(
        synthetic,
        fields_of(sp.profile(synthetic)),
        Composition(x="quantity", y="invoice_amount", color="sales_channel"),
    )
    assert spec.color is not None and spec.color.field == "sales_channel"
    assert len(spec.colour_groups()) > 1


def test_a_series_keeps_its_colour_across_renderers(synthetic: pd.DataFrame) -> None:
    from smartprep.viz.svg import LIGHT

    spec = compose(
        synthetic,
        fields_of(sp.profile(synthetic)),
        Composition(x="quantity", y="invoice_amount", color="sales_channel"),
    )
    groups = spec.colour_groups()
    first = spec.colour_of({"sales_channel": groups[0]}, LIGHT.series)
    second = spec.colour_of({"sales_channel": groups[1]}, LIGHT.series)
    assert first != second

    if HAS_PLOTLY:
        from smartprep.viz import to_plotly

        drawn = set(to_plotly(spec).data[0].marker.color)
        assert {first, second} <= drawn


def test_a_missing_series_value_is_not_given_a_colour() -> None:
    """A blank group is not a group. Colouring it would invent a category the
    data does not have."""
    spec = ChartSpec(
        mark=Mark.SCATTER,
        data=[{"x": 1.0, "y": 1.0, "g": "north"}, {"x": 2.0, "y": 2.0, "g": ""}],
        x=Encoding("x"),
        y=Encoding("y"),
        color=Encoding("g", "nominal"),
    )
    assert spec.colour_groups() == ["north"]
    assert spec.colour_of(spec.data[1], ("#111111", "#222222")) is None


def test_the_capability_registry_knows_faceting_landed() -> None:
    from smartprep.capabilities import CAPABILITIES, Status

    facets = next(c for c in CAPABILITIES if c.name == "faceting")
    assert facets.status is Status.IMPLEMENTED, (
        "faceting works now; the registry still calls it planned"
    )


def test_a_workflow_node_serialises_completely() -> None:
    node = default_workflow().get("node-missing")
    payload = json.loads(json.dumps(node.to_dict()))
    assert set(payload) == {
        "id",
        "stage",
        "label",
        "enabled",
        "parameters",
        "depends_on",
        "note",
    }
