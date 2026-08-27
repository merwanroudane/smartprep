"""Shared interaction state, stable identity, the visual builder, the sandbox.

The v0.6 foundation. These five surfaces were built together and against one
state deliberately: built separately, each grows its own answer to "what is
selected", and reconciling four almost-identical state models afterwards is
the work nobody schedules.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT
from smartprep.core.identity import IdentitySource, StableRowIndex
from smartprep.core.state import Comparison, FilterClause, StudioState
from smartprep.repair.sandbox import preview, preview_candidates
from smartprep.viz.compose import (
    Composition,
    CompositionRefused,
    compose,
    fields_of,
    recommend,
)

# ==========================================================================
# Stable row identity
# ==========================================================================


def test_a_unique_index_is_the_identity() -> None:
    frame = pd.DataFrame({"a": [1, 2, 3]}, index=["x", "y", "z"])
    identity = StableRowIndex.of(frame)
    assert identity.source is IdentitySource.INDEX
    assert identity.keys == ("x", "y", "z")
    assert identity.is_stable


def test_duplicate_indexes_fall_back_to_row_contents() -> None:
    frame = pd.DataFrame({"a": [1, 2, 3], "b": ["p", "q", "r"]}, index=[7, 7, 7])
    identity = StableRowIndex.of(frame)
    assert identity.source is IdentitySource.CONTENT
    assert identity.is_stable
    assert len(set(identity.keys)) == 3


def test_identical_rows_leave_only_position_and_it_says_so() -> None:
    """The honest failure. Position is an identity; it is just not a stable
    one, and a caller told nothing would assume otherwise."""
    frame = pd.DataFrame({"a": [1, 1, 1]}, index=[0, 0, 0])
    identity = StableRowIndex.of(frame)
    assert identity.source is IdentitySource.POSITIONAL
    assert not identity.is_stable
    assert "NOT survive" in identity.note


def test_keys_survive_a_repair() -> None:
    """The whole point. A selection taken before a repair must still name the
    same rows after it -- which positional indexes do not guarantee."""
    frame = pd.DataFrame({"n": ["1,200.50", "340", "18"], "k": ["a", "b", "c"]})
    before = StableRowIndex.of(frame)
    picked = before.keys_for([0, 2])

    repaired = frame.copy()
    repaired["n"] = [1200.5, 340.0, 18.0]
    after = StableRowIndex.of(repaired)

    assert after.positions_for(picked) == (0, 2)
    assert list(after.restrict(repaired, picked)["k"]) == ["a", "c"]


def test_a_key_that_no_longer_exists_leaves_quietly() -> None:
    """A selection naturally outlives the rows it names."""
    frame = pd.DataFrame({"a": [1, 2, 3]})
    identity = StableRowIndex.of(frame)
    assert identity.positions_for(["0", "999"]) == (0,)


# ==========================================================================
# StudioState -- one state, and it changes nothing
# ==========================================================================


def test_filters_narrow_a_view_and_touch_no_data(synthetic: pd.DataFrame) -> None:
    state = StudioState.of(synthetic)
    original = synthetic.copy(deep=True)

    state.filter_by(FilterClause("country", Comparison.EQUALS, "Morocco"))
    viewed = state.view(synthetic)

    assert len(viewed) < len(synthetic)
    pd.testing.assert_frame_equal(synthetic, original)


def test_a_view_cannot_be_written_through(synthetic: pd.DataFrame) -> None:
    """``view`` is a view in English and a copy in pandas: a caller who edits
    what they were shown must not reach the dataset."""
    state = StudioState.of(synthetic)
    viewed = state.view(synthetic)
    if len(viewed):
        viewed.iloc[0, 0] = "CLOBBERED"
    assert "CLOBBERED" not in set(synthetic.iloc[:, 0].astype(str))


def test_every_comparison_is_evaluable(synthetic: pd.DataFrame) -> None:
    """All ten, so a clause the page can build is a clause Python can answer.
    A comparison that exists in one and not the other is a filter that means
    two different things."""
    for comparison in Comparison:
        clause = FilterClause("country", comparison, "Morocco")
        mask = clause.mask(synthetic)
        assert len(mask) == len(synthetic)
        assert mask.dtype == bool
        assert clause.describe()


def test_a_filter_on_a_vanished_column_selects_nothing(synthetic: pd.DataFrame) -> None:
    """A view outlives a schema change; a page that crashes on a stale filter
    is worse than one that shows nothing and says why."""
    clause = FilterClause("no_such_column", Comparison.EQUALS, "x")
    assert not clause.mask(synthetic).any()


def test_uncomparable_cells_drop_out_of_an_ordered_filter() -> None:
    """A word is not smaller than a number. It is uncomparable, and counting
    it as a match either way is a quiet wrong answer."""
    frame = pd.DataFrame({"n": [1, 5, "not a number", None]})
    mask = FilterClause("n", Comparison.GREATER_THAN, 2).mask(frame)
    assert list(mask) == [False, True, False, False]


def test_a_selection_records_whether_it_will_survive() -> None:
    unstable = pd.DataFrame({"a": [1, 1, 1]}, index=[0, 0, 0])
    state = StudioState.of(unstable)
    state.select_rows(["p0", "p1"])
    assert not state.selection.stable
    assert "will not survive" in state.describe()


def test_state_round_trips_through_json(synthetic: pd.DataFrame) -> None:
    """The contract with the browser. A view assembled by clicking has to come
    back as the same view."""
    state = StudioState.of(synthetic)
    state.filter_by(FilterClause("country", Comparison.EQUALS, "Morocco"))
    state.select_rows(["0", "3"], origin="grid")
    state.consider("MISS-city", "impute_mode")

    payload = state.to_json()
    rebuilt = StudioState.from_json(payload, StableRowIndex.of(synthetic))

    assert rebuilt.filters == state.filters
    assert rebuilt.selection.rows == state.selection.rows
    assert rebuilt.pending_treatment == {"issue_id": "MISS-city", "treatment": "impute_mode"}
    pd.testing.assert_frame_equal(rebuilt.view(synthetic), state.view(synthetic))


def test_the_page_cannot_assert_a_selection_is_stable(synthetic: pd.DataFrame) -> None:
    """Identity belongs to the frame in hand, not to the payload. A page
    claiming stability this frame cannot provide must not be believed."""
    unstable = pd.DataFrame({"a": [1, 1, 1]}, index=[0, 0, 0])
    lying = {"selection": {"rows": ["p0"], "stable": True}, "filters": []}
    rebuilt = StudioState.from_dict(lying, StableRowIndex.of(unstable))
    rebuilt.select_rows(["p0"])
    assert not rebuilt.selection.stable


def test_a_state_with_nothing_in_it_says_so(synthetic: pd.DataFrame) -> None:
    assert StudioState.of(synthetic).describe() == "the whole dataset, nothing selected"


def test_selection_is_intersected_with_the_filters(synthetic: pd.DataFrame) -> None:
    """Selecting a row and then filtering it away must not resurrect it."""
    state = StudioState.of(synthetic)
    everything = state.identity.keys_for(range(len(synthetic)))
    state.select_rows(everything)
    state.filter_by(FilterClause("country", Comparison.EQUALS, "Morocco"))
    assert len(state.selected_frame(synthetic)) == len(state.view(synthetic))


# ==========================================================================
# Duplicated indexes -- where label-based lookups go wrong
# ==========================================================================
#
# A frame with a repeated index is ordinary: concat two months of data and you
# have one. Every bug below was real, and all three were the same mistake --
# resolving a row by its index label when several rows answer to that label.
# They are grouped here because the failure is invisible from outside: the
# wrong rows are still rows, the counts are still plausible, and nothing
# raises.


@pytest.fixture()
def repeated() -> pd.DataFrame:
    """Two groups, three rows each, and only three distinct index labels."""
    return pd.DataFrame(
        {"g": ["a", "b"] * 3, "v": [1.0, 2, 3, 4, 5, 6], "w": [9.0, 8, 7, 6, 5, 4]},
        index=[0, 0, 1, 1, 2, 2],
    )


def test_a_filtered_selection_does_not_pull_in_its_index_twins(
    repeated: pd.DataFrame,
) -> None:
    """Selecting everything and then filtering must leave the filtered rows.

    Matching on the index label instead returned all six, because each label
    names one row in each group.
    """
    state = StudioState.of(repeated)
    state.select_rows(state.identity.keys_for(range(len(repeated))))
    state.filter_by(FilterClause("g", Comparison.EQUALS, "a"))

    selected = state.selected_frame(repeated)
    assert len(selected) == 3
    assert set(selected["g"]) == {"a"}


def test_a_bar_names_only_the_rows_inside_it(repeated: pd.DataFrame) -> None:
    """Brushing a bar must select that category and nothing else.

    A label-keyed lookup resolved every duplicate to whichever row came last,
    so a bar for group 'a' carried keys pointing into group 'b'.
    """
    fields = fields_of(sp.profile(repeated))
    identity = StableRowIndex.of(repeated)
    spec = compose(
        repeated,
        fields,
        Composition(x="g", y="v", aggregate="mean"),
        identity=identity,
    )
    for datum in spec.data:
        rows = identity.restrict(repeated, datum["keys"])
        assert set(rows["g"]) == {datum["label"]}
        assert len(rows) == 3


def test_a_filtered_scatter_names_only_the_filtered_rows(
    repeated: pd.DataFrame,
) -> None:
    fields = fields_of(sp.profile(repeated))
    identity = StableRowIndex.of(repeated)
    spec = compose(
        repeated,
        fields,
        Composition(x="v", y="w", filters=(FilterClause("g", Comparison.EQUALS, "a"),)),
        identity=identity,
    )
    assert len(spec.data) == 3
    for datum in spec.data:
        assert set(identity.restrict(repeated, datum["keys"])["g"]) == {"a"}


def test_a_time_series_point_names_exactly_one_row() -> None:
    frame = pd.DataFrame(
        {"t": pd.date_range("2024-01-01", periods=6), "v": [1.0, 2, 3, 4, 5, 6]},
        index=[0, 0, 1, 1, 2, 2],
    )
    identity = StableRowIndex.of(frame)
    spec = compose(
        frame, fields_of(sp.profile(frame)), Composition(x="t", y="v"), identity=identity
    )
    assert len(spec.data) == 6
    for datum in spec.data:
        assert len(identity.restrict(frame, datum["keys"])) == 1


def test_every_chart_key_resolves_to_a_grid_row(repeated: pd.DataFrame) -> None:
    """The end-to-end claim: brushing a mark highlights a row that exists.

    A key in a chart that the grid has never heard of is a selection that
    lands nowhere, and looks from the outside exactly like a selection that
    matched nothing.
    """
    import json
    import re

    page = sp.studio(repeated, prepare=False).html
    catalogue = json.loads(
        re.search(r"window\.__SMARTPREP_COMPOSITIONS__ = (.*?);window\.", page, re.S).group(1)
    )
    grid = json.loads(
        re.search(r"window\.__SMARTPREP_GRID__ = (.*?);window\.", page, re.S).group(1)
    )

    known = {row["key"] for row in grid["rows"]}
    assert len(known) == len(grid["rows"]), "grid keys are not unique"

    seen = set()
    for spec in catalogue["specs"].values():
        for group in re.findall(r'data-keys="([^"]+)"', spec["svg"]):
            seen.update(group.split(","))
    assert seen, "no chart in the catalogue was brushable"
    assert not (seen - known), f"chart keys the grid does not have: {sorted(seen - known)[:5]}"


def test_the_page_says_when_a_selection_runs_past_the_loaded_rows(
    synthetic: pd.DataFrame,
) -> None:
    """Charts are drawn from every row; the grid holds only the first page.

    A count that quietly dropped the rest would read as "those rows are not
    selected" rather than "those rows are not loaded here".
    """
    from smartprep.reporting.linked import STATE_SCRIPT

    assert "beyond the rows loaded into this grid" in STATE_SCRIPT


# ==========================================================================
# The visual builder
# ==========================================================================


def test_fields_come_from_the_profile(synthetic: pd.DataFrame) -> None:
    """Not from the frame. The builder must describe the same columns the
    report describes, or a reader comparing them compares two analyses."""
    dataset_profile = sp.profile(synthetic)
    fields = fields_of(dataset_profile)
    assert len(fields) == len(dataset_profile.columns_profiled)
    for field in fields:
        assert field.distinct == dataset_profile.get(field.name).distinct


def test_an_identifier_is_not_offered_as_an_axis(synthetic: pd.DataFrame) -> None:
    fields = fields_of(sp.profile(synthetic))
    blocked = {f.name: f.plottable for f in fields if f.plottable}
    assert "invoice_id" in blocked
    assert "key" in blocked["invoice_id"]


def test_a_date_is_not_mistaken_for_a_key(synthetic: pd.DataFrame) -> None:
    """A date column is nearly all-distinct because that is what dates are.
    Blocking it would remove every time-series chart from the builder."""
    fields = fields_of(sp.profile(synthetic))
    dates = [f for f in fields if f.is_temporal]
    assert dates
    assert all(f.plottable is None for f in dates)


def test_composing_refuses_an_unreadable_chart(synthetic: pd.DataFrame) -> None:
    """A wall of nine thousand bars is worse than an empty panel, and the
    refusal has to say what to do instead."""
    frame = pd.DataFrame({"id": [f"k{i}" for i in range(200)], "v": range(200)})
    fields = fields_of(sp.profile(frame))
    # Force the categorical path with a field the profile did not block.
    wide = [f for f in fields if f.name == "id"]
    if wide and wide[0].plottable is None:
        with pytest.raises(CompositionRefused, match="wall of|distinct"):
            compose(frame, fields, Composition(x="id", y="v", aggregate="mean"))


def test_composing_refuses_an_empty_result(synthetic: pd.DataFrame) -> None:
    fields = fields_of(sp.profile(synthetic))
    impossible = FilterClause("country", Comparison.EQUALS, "Atlantis")
    with pytest.raises(CompositionRefused, match="no rows"):
        compose(synthetic, fields, Composition(x="invoice_amount", filters=(impossible,)))


def test_a_filtered_chart_says_it_is_filtered(synthetic: pd.DataFrame) -> None:
    """The same rule as a sampled chart. A reader must never have to guess
    which rows a picture was drawn from."""
    fields = fields_of(sp.profile(synthetic))
    clause = FilterClause("country", Comparison.EQUALS, "Morocco")
    spec = compose(synthetic, fields, Composition(x="invoice_amount", filters=(clause,)))
    assert "filtered where" in spec.subtitle
    assert any(a.get("kind") == "filter" for a in spec.annotations)


@pytest.mark.parametrize(
    ("composition", "expected"),
    [
        (Composition(x="quantity", y="invoice_amount"), "scatter"),
        (Composition(x="country", y="invoice_amount", aggregate="mean"), "horizontal_bar"),
        (Composition(x="invoice_date", y="quantity"), "line"),
        (Composition(x="invoice_amount"), "histogram"),
    ],
)
def test_the_pairing_decides_the_chart(
    synthetic: pd.DataFrame, composition: Composition, expected: str
) -> None:
    """Nobody is asked to justify a chart type the data has already implied."""
    fields = fields_of(sp.profile(synthetic))
    assert compose(synthetic, fields, composition).mark.value == expected


def test_every_recommendation_carries_its_reason(synthetic: pd.DataFrame) -> None:
    """A recommendation a reader cannot argue with is one they cannot learn
    from. The score alone is not a reason."""
    for suggestion in recommend(fields_of(sp.profile(synthetic))):
        assert suggestion.why.strip()
        assert suggestion.label.strip()
        assert len(suggestion.why.split()) >= 6


def test_recommendations_are_all_composable(synthetic: pd.DataFrame) -> None:
    """Suggesting a chart that cannot be built is worse than suggesting
    nothing."""
    fields = fields_of(sp.profile(synthetic))
    for suggestion in recommend(fields):
        compose(synthetic, fields, suggestion.composition)


def test_a_composition_round_trips(synthetic: pd.DataFrame) -> None:
    """Drag and keyboard build the same object, and so does a saved view."""
    original = Composition(x="country", y="invoice_amount", aggregate="mean", title="T")
    assert Composition.from_dict(json.loads(json.dumps(original.to_dict()))) == original


# ==========================================================================
# Brushing -- a mark knows which rows it came from
# ==========================================================================


def test_marks_carry_the_rows_behind_them(synthetic: pd.DataFrame) -> None:
    fields = fields_of(sp.profile(synthetic))
    identity = StableRowIndex.of(synthetic)
    spec = compose(
        synthetic,
        fields,
        Composition(x="country", y="invoice_amount", aggregate="mean"),
        identity=identity,
    )
    assert all(datum["keys"] for datum in spec.data)

    # Following a bar's keys back to the data must land on rows that really
    # do belong to that category -- otherwise brushing highlights the wrong
    # records, which looks exactly like brushing the right ones.
    first = spec.data[0]
    rows = identity.restrict(synthetic, first["keys"])
    assert set(rows["country"].astype(str)) == {first["label"]}


def test_a_mark_without_keys_is_not_brushable(synthetic: pd.DataFrame) -> None:
    """No identity, no selection. Doing something with the mark's *position*
    instead is how a selection lands on the wrong rows."""
    fields = fields_of(sp.profile(synthetic))
    spec = compose(synthetic, fields, Composition(x="country"))
    assert all(not datum.get("keys") for datum in spec.data)
    assert "data-keys" not in sp.render_svg(spec)


def test_brushable_marks_are_reachable_from_a_keyboard(synthetic: pd.DataFrame) -> None:
    fields = fields_of(sp.profile(synthetic))
    spec = compose(
        synthetic, fields, Composition(x="country"), identity=StableRowIndex.of(synthetic)
    )
    body = sp.render_svg(spec)
    assert 'data-keys="' in body
    assert 'tabindex="0"' in body
    assert 'role="button"' in body


# ==========================================================================
# The treatment sandbox
# ==========================================================================


def test_a_preview_leaves_the_frame_alone(synthetic: pd.DataFrame) -> None:
    original = synthetic.copy(deep=True)
    result = sp.scan(synthetic, **SCAN_CONTEXT)
    for issue in result.issues:
        for candidate in issue.treatments:
            preview(synthetic, issue, candidate, with_charts=False)
    pd.testing.assert_frame_equal(synthetic, original)


def test_a_preview_reports_what_a_repair_would_cost(synthetic: pd.DataFrame) -> None:
    """Imputation always improves completeness -- that is what it is for. A
    sandbox reporting only completeness would recommend imputing everything,
    so the spread is shown beside it."""
    result = sp.scan(synthetic, **SCAN_CONTEXT)
    moved = [
        p
        for issue in result.issues
        for p in preview_candidates(synthetic, issue)
        if p.changes_anything
    ]
    assert moved, "the fixture must offer at least one repair worth previewing"

    with_stats = [p for p in moved if any(d.measure == "std" for d in p.deltas)]
    assert with_stats, "no preview reported what a repair does to the spread"
    for candidate in with_stats:
        measures = {d.measure for d in candidate.deltas}
        assert {"missing", "distinct", "mean", "std"} <= measures


def test_a_preview_shows_concrete_examples(synthetic: pd.DataFrame) -> None:
    """A reviewer trusts three real before/after pairs more than a count, and
    rightly so."""
    result = sp.scan(synthetic, **SCAN_CONTEXT)
    for issue in result.issues:
        for candidate in preview_candidates(synthetic, issue):
            if candidate.changes_anything:
                assert candidate.examples
                first = candidate.examples[0]
                assert {"row", "column", "before", "after"} <= set(first)
                assert first["before"] != first["after"]
                return
    pytest.fail("no preview produced an example")


def test_an_unimplemented_treatment_abstains_rather_than_showing_nothing(
    synthetic: pd.DataFrame,
) -> None:
    """An empty comparison reads as 'no effect'. Abstention is a result and
    has to be said out loud."""
    result = sp.scan(synthetic, **SCAN_CONTEXT)
    refusals = [
        p
        for issue in result.issues
        for p in preview_candidates(synthetic, issue)
        if not p.is_possible
    ]
    assert refusals
    for refusal in refusals:
        assert refusal.refusal
        assert "cannot be previewed" in refusal.summary()


def test_previewing_an_unknown_treatment_refuses(synthetic: pd.DataFrame) -> None:
    result = sp.scan(synthetic, **SCAN_CONTEXT)
    issue = next(i for i in result.issues if i.treatments)
    outcome = preview(synthetic, issue, "no_such_treatment")
    assert not outcome.is_possible
    assert "not a candidate" in (outcome.refusal or "")


def test_candidates_are_ordered_but_the_order_is_not_the_answer(
    synthetic: pd.DataFrame,
) -> None:
    result = sp.scan(synthetic, **SCAN_CONTEXT)
    issue = next(i for i in result.issues if len(i.treatments) > 1)
    confidences = [p.repair_confidence for p in preview_candidates(synthetic, issue)]
    assert confidences == sorted(confidences, reverse=True)


def test_preview_and_apply_run_the_same_operation(synthetic: pd.DataFrame) -> None:
    """What a reviewer is shown cannot drift from what they get.

    Preview and apply do not merely agree -- they are the same operation over
    a copy, so previewing a treatment and executing it against the *same*
    frame must give the identical count. This is the test that would fail the
    day somebody gives the sandbox its own faster approximation, which is
    exactly the shortcut a sandbox invites.
    """
    from smartprep.core.operations import RepairPlan
    from smartprep.repair.actions import build_operation
    from smartprep.repair.executor import RepairExecutor

    scanned = sp.scan(synthetic, **SCAN_CONTEXT)
    compared = 0

    for issue in scanned.issues:
        for candidate in issue.treatments:
            operation = build_operation(issue, candidate)
            if operation is None:
                continue
            plan = RepairPlan()
            plan.add(operation)
            executed = RepairExecutor().run(synthetic, plan)
            if executed.refused:
                continue

            previewed = preview(synthetic, issue, candidate, with_charts=False)
            assert previewed.cells_changed == executed.cells_changed, (
                f"the sandbox and the engine disagree about {candidate.name!r} on {issue.id}"
            )
            pd.testing.assert_frame_equal(
                executed.frame, previewed._previewed_frame, check_dtype=False
            )
            compared += 1

    assert compared, "no treatment could be compared against its execution"


def test_a_preview_says_which_frame_it_was_computed_against(
    synthetic: pd.DataFrame,
) -> None:
    """A preview is only true of one dataset.

    Run the same treatment after three other repairs and it touches a
    different number of cells, because some of them are already fixed. A
    sandbox that does not say which frame it was looking at invites a reader
    to compare two numbers that were never about the same data.
    """
    scanned = sp.scan(synthetic, **SCAN_CONTEXT)
    issue = next(i for i in scanned.issues if i.treatments)
    first = preview(synthetic, issue, issue.treatments[0], with_charts=False)
    assert first.against

    altered = synthetic.copy()
    altered.iloc[0, 0] = "changed"
    second = preview(altered, issue, issue.treatments[0], with_charts=False)
    assert second.against != first.against


# ==========================================================================
# The page
# ==========================================================================


@pytest.fixture(scope="module")
def page(synthetic: pd.DataFrame) -> str:
    return sp.studio(synthetic, **SCAN_CONTEXT).html


def test_the_studio_carries_one_state_for_every_panel(page: str) -> None:
    assert "__SMARTPREP_STATE__" in page
    assert "window.SP" in page


def test_the_studio_has_the_five_visual_surfaces(page: str) -> None:
    for section in ("grid", "build", "sandbox", "stages", "pipeline"):
        assert f'id="{section}"' in page or f"id='{section}'" in page


def test_folding_explore_into_build_kept_its_chart_types(page: str) -> None:
    """The merge removed a duplicated panel, not a capability.

    ECDF, box and target-by-category are readings the composition grammar
    cannot express -- an ECDF is an alternative view of one field rather than
    a pairing of two -- so they are offered in the builder explicitly.
    """
    import json
    import re

    catalogue = json.loads(
        re.search(r"window\.__SMARTPREP_COMPOSITIONS__ = (.*?);window\.", page, re.S).group(1)
    )
    signatures = set(catalogue["specs"])
    for suffix in ("ecdf", "box", "target"):
        assert any(s.endswith(f"|{suffix}") or s.endswith(f"||{suffix}") for s in signatures), (
            f"the builder offers no {suffix} chart; folding Explore in dropped it"
        )


def test_every_chart_offers_its_numbers(page: str) -> None:
    """A picture is not an accessible format. Alt text says what a chart is
    about; only the numbers say what it shows."""
    assert page.count("Show the numbers behind this chart") > 3


def test_the_builder_offers_a_keyboard_route(page: str) -> None:
    assert "press <kbd>1</kbd>" in page or "<kbd>1</kbd>" in page
    assert "the keyboard is not a lesser" in page


def test_the_sandbox_says_it_applies_nothing(page: str) -> None:
    assert "Preview only" in page
    assert "that is the only path that writes an audit" in page
