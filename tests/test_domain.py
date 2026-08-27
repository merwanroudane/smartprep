"""Domain-aware diagnostics: time-series, panel data, entity resolution.

All three answer questions about *shape* rather than values, and all three
refuse to act on their own answers. A gap, an unbalanced panel and a probable
duplicate entity are each a decision somebody has to make with knowledge the
data does not contain.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import smartprep as sp
from smartprep.core.enums import Severity
from smartprep.linkage import link
from smartprep.panel import panel
from smartprep.timeseries import timeseries


@pytest.fixture()
def series() -> pd.DataFrame:
    """Daily, with one gap, one duplicate, one row out of order."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-02",
                    "2024-01-05",
                    "2024-01-04",
                    "2024-01-06",
                ]
            ),
            "value": [1.0, 2.0, 2.0, 3.0, 4.0, 5.0],
        }
    )


@pytest.fixture()
def firms() -> pd.DataFrame:
    """Three firms, five years, one leaving early."""
    rng = np.random.default_rng(0)
    rows = []
    for name in ("A", "B", "C"):
        for year in range(2018, 2023):
            if name == "C" and year > 2020:
                continue
            rows.append(
                {
                    "firm": name,
                    "year": year,
                    "output": float(rng.normal(10, 2)),
                    "sector": {"A": 1, "B": 2, "C": 3}[name],
                    "region_size": 100 + {"A": 0, "B": 50, "C": 90}[name] + year * 1e-6,
                }
            )
    return pd.DataFrame(rows)


# ==========================================================================
# Time series
# ==========================================================================


def test_diagnosis_never_touches_the_data(series: pd.DataFrame) -> None:
    before = series.copy(deep=True)
    timeseries(series, "date")
    pd.testing.assert_frame_equal(series, before)


def test_cadence_is_inferred_and_its_agreement_reported(series: pd.DataFrame) -> None:
    """A daily series with gaps and a weekly series with noise both infer
    'daily'. Only the agreement figure separates them, so it travels with the
    cadence everywhere."""
    cadence = timeseries(series, "date").cadence
    assert cadence.name == "daily"
    assert 0.0 < cadence.agreement <= 1.0
    assert f"{cadence.agreement:.0%}" in cadence.describe()


def test_gaps_duplicates_and_disorder_are_all_found(series: pd.DataFrame) -> None:
    report = timeseries(series, "date")
    assert report.duplicates == 1
    assert len(report.missing_periods) == 1
    assert report.out_of_order == 1
    assert report.coverage < 1.0


def test_a_gap_offers_no_automatic_repair(series: pd.DataFrame) -> None:
    """Filling a gap and dropping it give different answers, and nothing in
    the data says which is right."""
    gap = next(i for i in timeseries(series, "date").issues if i.id.startswith("TS-GAP"))
    assert gap.detection_confidence > 0.5
    assert all(t.repair_confidence == 0.0 for t in gap.treatments)
    assert not gap.triage()[0].is_autonomous


def test_disorder_is_the_one_thing_safe_to_fix(series: pd.DataFrame) -> None:
    """Sorting by time changes no value and loses nothing, which is why it is
    the only time-series finding with a confident repair."""
    order = next(i for i in timeseries(series, "date").issues if i.id.startswith("TS-ORDER"))
    treatment = order.recommended_treatment
    assert treatment is not None
    assert treatment.repair_confidence > 0.9


def test_mixed_timezones_are_blocking() -> None:
    """Comparing an aware timestamp with a naive one is an error in pandas and
    a silent hour's difference nearly everywhere else."""
    frame = pd.DataFrame(
        {
            "t": [
                pd.Timestamp("2024-01-01", tz="UTC"),
                pd.Timestamp("2024-01-02"),
                pd.Timestamp("2024-01-03", tz="UTC"),
            ]
        }
    )
    report = timeseries(frame, "t")
    assert report.mixed_timezones
    finding = next(i for i in report.issues if "TIMEZONE" in i.id)
    assert finding.severity is Severity.BLOCKING


def test_a_stale_run_that_reaches_the_end_is_still_reported() -> None:
    """Without a closing sentinel the final run never ends, and a feed that
    died and stayed dead is exactly the case a reader most wants."""
    frame = pd.DataFrame(
        {"t": pd.date_range("2024-01-01", periods=8), "v": [1.0, 2, 3, 9, 9, 9, 9, 9]}
    )
    assert [r["length"] for r in timeseries(frame, "t", stale_after=4).stale_runs] == [5]


def test_a_stale_run_is_reported_but_not_judged() -> None:
    frame = pd.DataFrame({"t": pd.date_range("2024-01-01", periods=10), "v": [5.0] * 10})
    finding = next(i for i in timeseries(frame, "t", stale_after=5).issues if "STALE" in i.id)
    assert not finding.treatments
    assert "stopped updating" in finding.notes


def test_a_series_too_short_to_judge_says_so() -> None:
    frame = pd.DataFrame({"t": pd.to_datetime(["2024-01-01", "2024-01-02"])})
    cadence = timeseries(frame, "t").cadence
    assert cadence.step is None
    assert "fewer than three" in cadence.note


def test_an_unknown_column_is_named() -> None:
    with pytest.raises(KeyError, match="nope"):
        timeseries(pd.DataFrame({"a": [1]}), "nope")


# ==========================================================================
# Panel data
# ==========================================================================


def test_panel_diagnosis_never_touches_the_data(firms: pd.DataFrame) -> None:
    before = firms.copy(deep=True)
    panel(firms, "firm", "year")
    pd.testing.assert_frame_equal(firms, before)


def test_an_unbalanced_panel_is_reported_as_a_notice(firms: pd.DataFrame) -> None:
    """Usually fine, occasionally a survivorship filter, and the counts alone
    cannot tell you which -- so it is surfaced, not escalated."""
    report = panel(firms, "firm", "year")
    assert not report.is_balanced
    assert 0.0 < report.completeness < 1.0

    finding = next(i for i in report.issues if "UNBALANCED" in i.id)
    assert finding.severity is Severity.NOTICE
    assert "survivorship" in finding.notes


def test_a_constant_within_variable_is_flagged(firms: pd.DataFrame) -> None:
    """Collinear with an entity fixed effect, so a within estimator drops it
    and takes its coefficient with it."""
    report = panel(firms, "firm", "year")
    assert [v.column for v in report.constant_within] == ["sector"]
    finding = next(i for i in report.issues if "CONSTANT-WITHIN" in i.id)
    assert finding.severity is Severity.HIGH_WARNING


def test_weak_within_variation_is_flagged_more_urgently_than_none(
    firms: pd.DataFrame,
) -> None:
    """No variation drops the term visibly. Weak variation keeps it and
    returns something that looks like an answer."""
    report = panel(firms, "firm", "year")
    weak = [v.column for v in report.weak_within]
    assert "region_size" in weak
    finding = next(i for i in report.issues if "WEAK-WITHIN" in i.id)
    assert "looks like an answer" in finding.notes


def test_a_genuinely_varying_column_is_not_flagged(firms: pd.DataFrame) -> None:
    """The negative case. Flagging a well-behaved regressor would train a
    reader to ignore the warning."""
    report = panel(firms, "firm", "year")
    flagged = {v.column for v in report.constant_within + report.weak_within}
    assert "output" not in flagged


def test_duplicate_entity_time_pairs_block() -> None:
    """If the two keys do not identify a row, the panel index is not what it
    claims and an estimator will silently average the pair."""
    frame = pd.DataFrame(
        {"firm": ["A", "A", "B"], "year": [2020, 2020, 2020], "v": [1.0, 2.0, 3.0]}
    )
    report = panel(frame, "firm", "year")
    assert report.duplicate_pairs == 1
    finding = next(i for i in report.issues if "DUPLICATE" in i.id)
    assert finding.severity is Severity.BLOCKING
    assert all(t.repair_confidence == 0.0 for t in finding.treatments)


def test_a_balanced_panel_raises_nothing() -> None:
    rng = np.random.default_rng(1)
    frame = pd.DataFrame(
        [
            {"firm": f, "year": y, "v": float(rng.normal())}
            for f in ("A", "B")
            for y in (2020, 2021, 2022)
        ]
    )
    report = panel(frame, "firm", "year")
    assert report.is_balanced
    assert report.completeness == 1.0
    assert not [i for i in report.issues if "UNBALANCED" in i.id]


def test_the_completeness_matrix_shows_the_panel_shape(firms: pd.DataFrame) -> None:
    matrix = panel(firms, "firm", "year").completeness_matrix()
    assert matrix.shape == (3, 5)
    assert not bool(matrix.loc["C", 2022])
    assert bool(matrix.loc["A", 2022])


# ==========================================================================
# Entity resolution
# ==========================================================================


@pytest.fixture()
def records() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": [
                "Société Générale",
                "Societe Generale",
                "Attijariwafa Bank",
                "Attijariwafa Bnk",
                "البنك الشعبي",
                "البنك الشعبى",
                "Maroc Telecom",
            ],
            "city": ["Casablanca"] * 2 + ["Rabat"] * 2 + ["Casablanca"] * 2 + ["Rabat"],
            "staff": [1200, 1205, 800, 800, 500, 500, 3000],
        }
    )


def test_linkage_merges_nothing(records: pd.DataFrame) -> None:
    before = records.copy(deep=True)
    link(records, ("name", "city", "staff"), block_prefix=3)
    pd.testing.assert_frame_equal(records, before)


def test_similarity_orders_the_queue_and_decides_nothing(
    records: pd.DataFrame,
) -> None:
    """At 0.85 two branches of one company become one; at 0.86 they stay
    apart. A dataset's conclusions must not turn on a constant somebody chose
    on a Tuesday.
    """
    report = link(records, ("name", "city", "staff"), block_prefix=3)
    assert report.pairs

    scores = [p.score for p in report.pairs]
    assert scores == sorted(scores, reverse=True)

    for finding in report.issues:
        assert finding.detection_confidence > 0
        assert all(t.repair_confidence == 0.0 for t in finding.treatments)
        assert not finding.triage()[0].is_autonomous


def test_non_latin_names_are_matched_not_erased(records: pd.DataFrame) -> None:
    """Folding must never ASCII-encode: that erases every Arabic name to the
    empty string, and empty strings match each other perfectly."""
    report = link(records, ("name", "city", "staff"), block_prefix=3)
    pairs = {(p.left, p.right) for p in report.pairs}
    assert (4, 5) in pairs, "the two spellings of the Arabic name were not linked"


def test_every_pair_offers_a_reversible_alternative_to_merging(
    records: pd.DataFrame,
) -> None:
    """Merging is irreversible. Recording that two rows name one entity is
    not, and a reviewer should always be able to choose the recoverable
    option."""
    finding = link(records, ("name", "city", "staff"), block_prefix=3).issues[0]
    names = {t.name for t in finding.treatments}
    assert {"merge_records", "keep_separate", "map_to_canonical"} == names

    merge = next(t for t in finding.treatments if t.name == "merge_records")
    mapped = next(t for t in finding.treatments if t.name == "map_to_canonical")
    assert merge.reversibility.name == "IRREVERSIBLE"
    assert mapped.reversibility.name == "REVERSIBLE"


def test_a_missing_value_argues_for_neither_side() -> None:
    """Scoring an absent value as agreement would let missing data vote for a
    merge."""
    frame = pd.DataFrame({"name": ["Acme", "Acme"], "tax_id": [None, "X1"]})
    pair = link(frame, ("name", "tax_id"), minimum=0.0).pairs[0]
    unknown = next(m for m in pair.matches if m.field == "tax_id")
    assert unknown.score == 0.5
    assert "missing" in unknown.comparator


def test_blocking_reports_what_it_skipped(records: pd.DataFrame) -> None:
    """A linkage run that shows only what it found reads as exhaustive."""
    report = link(records, ("name", "city"), block_prefix=3)
    assert report.skipped > 0
    assert "blocking skipped the rest" in report.recall_note
    assert f"{report.compared:,}" in report.recall_note


def test_evidence_names_the_comparator_it_used(records: pd.DataFrame) -> None:
    """'90% similar' means different things for a name and a staff count."""
    pair = link(records, ("name", "staff"), block_prefix=3).pairs[0]
    comparators = {m.comparator for m in pair.matches}
    assert any("numeric" in c for c in comparators)
    assert any("sequence" in c or "exact" in c for c in comparators)


def test_linkage_needs_something_to_compare() -> None:
    with pytest.raises(ValueError, match="at least one field"):
        link(pd.DataFrame({"a": [1]}), ())


def test_an_unknown_field_is_named() -> None:
    with pytest.raises(KeyError, match="nope"):
        link(pd.DataFrame({"a": [1]}), ("nope",))


# ==========================================================================
# All three route through the ordinary machinery
# ==========================================================================


@pytest.mark.parametrize("which", ["timeseries", "panel", "linkage"])
def test_findings_are_ordinary_issues(which: str, series: pd.DataFrame) -> None:
    """Not a parallel finding type. A gap in a series, an unbalanced panel and
    a probable duplicate entity go through one triage, one ladder and one
    review queue.
    """
    if which == "timeseries":
        issues = timeseries(series, "date").issues
    elif which == "panel":
        frame = pd.DataFrame({"e": ["a", "a", "b"], "t": [1, 1, 2], "v": [1.0, 2.0, 3.0]})
        issues = panel(frame, "e", "t").issues
    else:
        frame = pd.DataFrame({"name": ["Acme Ltd", "Acme Limited"], "city": ["X", "X"]})
        issues = link(frame, ("name", "city"), block_prefix=3).issues

    assert issues
    for finding in issues:
        assert finding.id and finding.detector
        assert 0.0 <= finding.detection_confidence <= 1.0
        assert finding.evidence.summary.strip()
        repair_class, reasons = finding.triage()
        assert repair_class is not None
        # A refusal must justify itself; an autonomous class needs no excuse.
        assert reasons or repair_class.is_autonomous


def test_the_registry_records_all_three_as_landed() -> None:
    from smartprep.capabilities import CAPABILITIES, Status

    for name in ("entity_resolution", "time_series"):
        capability = next(c for c in CAPABILITIES if c.name == name)
        assert capability.status is Status.IMPLEMENTED
        assert capability.caveat, f"{name} shipped without stating its limits"


def test_the_public_api_exposes_them() -> None:
    for name in ("timeseries", "panel", "link"):
        assert hasattr(sp, name)
        assert name in sp.__all__
