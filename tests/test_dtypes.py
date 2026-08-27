"""Every dtype pandas can hand us, and what the library does with it.

A data-preparation library whose central promise is honest reporting of data
quality has to be right about *all* the types real data arrives in -- not the
four that were convenient when the profiler was written. Each gap below was a
silent wrong answer rather than an error: a column reported complete when it
was not, an ordering discarded without a word, a duration filed as a label.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import pytest

import smartprep as sp
from smartprep.detectors.base import is_missing, to_number
from smartprep.eda.profile import ColumnKind

warnings.filterwarnings("ignore")


# ==========================================================================
# Missingness -- every null pandas can produce
# ==========================================================================


@pytest.mark.parametrize(
    "value",
    [None, np.nan, pd.NA, pd.NaT, np.datetime64("NaT"), np.timedelta64("NaT")],
)
def test_every_null_counts_as_missing(value: object) -> None:
    """``pd.NA`` is what Int64, boolean, Float64 and string columns use, and
    those are the modern defaults. Not recognising it meant reporting a column
    complete when it was not -- the exact failure this library exists to
    prevent."""
    assert is_missing(value)


@pytest.mark.parametrize("value", [0, 0.0, False, "", "0", [], {}, "text", b"bytes"])
def test_present_values_are_not_missing(value: object) -> None:
    """The negative case matters more here than the positive one: treating an
    empty string or a zero as absent would silently delete real data."""
    assert not is_missing(value)


@pytest.mark.parametrize("dtype", ["Int64", "Float64", "boolean", "string"])
def test_nullable_dtypes_report_their_missing_values(dtype: str) -> None:
    values = {
        "Int64": [1, 2, None, 4],
        "Float64": [1.0, 2.0, None, 4.0],
        "boolean": [True, False, None, True],
        "string": ["a", "b", None, "c"],
    }[dtype]
    frame = pd.DataFrame({"c": pd.array(values, dtype=dtype)})
    assert sp.profile(frame).get("c").missing == 1


def test_a_nullable_integer_is_a_number_not_a_category() -> None:
    """The knock-on effect of the missingness bug: one unrecognised null
    pushed the column below the numeric threshold, and every summary statistic
    was replaced by a category count."""
    frame = pd.DataFrame({"c": pd.array([1, 2, None, 4, 5, 6, 7, 8], dtype="Int64")})
    column = sp.profile(frame).get("c")
    assert column.kind is ColumnKind.NUMERIC
    assert column.numeric is not None


def test_a_nullable_boolean_is_still_boolean() -> None:
    frame = pd.DataFrame({"c": pd.array([True, False, None, True, False], dtype="boolean")})
    assert sp.profile(frame).get("c").kind is ColumnKind.BOOLEAN


# ==========================================================================
# Ordinal -- an order the caller already declared
# ==========================================================================


@pytest.fixture()
def ordered() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "severity": pd.Categorical(
                ["low", "high", "mid", "low", "mid", "high"],
                categories=["low", "mid", "high"],
                ordered=True,
            ),
            "colour": ["red", "blue", "red", "green", "red", "blue"],
            "y": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )


def test_an_ordered_categorical_is_its_own_kind(ordered: pd.DataFrame) -> None:
    """Ordinal is not nominal: a median exists for ordered levels and does not
    for unordered ones."""
    profile = sp.profile(ordered)
    assert profile.get("severity").kind is ColumnKind.ORDINAL
    assert profile.get("colour").kind is ColumnKind.CATEGORICAL


def test_the_declared_order_is_kept(ordered: pd.DataFrame) -> None:
    """Discarding an ordering the DataFrame states throws away information the
    user supplied, without saying so."""
    summary = sp.profile(ordered).get("severity").categorical
    assert summary is not None
    assert summary.is_ordered
    assert summary.ordered_levels == ("low", "mid", "high")


def test_a_nominal_category_claims_no_order(ordered: pd.DataFrame) -> None:
    summary = sp.profile(ordered).get("colour").categorical
    assert summary is not None
    assert not summary.is_ordered
    assert summary.ordered_levels == ()


def test_the_order_survives_serialisation(ordered: pd.DataFrame) -> None:
    payload = sp.profile(ordered).get("severity").to_dict()
    assert payload["categorical"]["ordered"] is True
    assert payload["categorical"]["ordered_levels"] == ["low", "mid", "high"]


def test_the_advisor_encodes_a_declared_order_rather_than_discarding_it(
    ordered: pd.DataFrame,
) -> None:
    """The usual objection to ordinal encoding is that it invents an order.
    When the caller declared one, one-hot is the lossy choice."""
    advice = {
        r.column: r
        for r in sp.recommend_preprocessing(ordered, target="y").recommendations
        if r.kind == "encode"
    }
    assert advice["severity"].method == "ordinal"
    assert advice["severity"].parameters["order"] == ["low", "mid", "high"]
    assert "declares an order" in advice["severity"].reason

    assert advice["colour"].method == "one_hot"


def test_the_encoder_uses_the_declared_order_not_the_alphabet(
    ordered: pd.DataFrame,
) -> None:
    """Alphabetically, "high" sorts below "low". Falling through to that would
    rank severity backwards and produce a model nobody could explain."""
    encoded = sp.Preprocessor().encode("severity", method="ordinal").fit_transform(ordered)
    assert list(encoded["severity"]) == [0, 2, 1, 0, 1, 2]


def test_an_ordinal_column_reaches_the_visual_grammar(ordered: pd.DataFrame) -> None:
    """The grammar has had an 'ordinal' field kind all along. A profile that
    never produced one meant nothing could ever use it."""
    fields = {f.name: f for f in sp.fields_of(sp.profile(ordered))}
    assert fields["severity"].kind == "ordinal"
    assert fields["colour"].kind == "nominal"


# ==========================================================================
# The rest of the dtype surface
# ==========================================================================


def test_a_duration_is_a_quantity_not_a_label() -> None:
    """Filed as a category, "3 days" is a label and no summary statistic means
    anything."""
    frame = pd.DataFrame({"elapsed": pd.to_timedelta(np.arange(1, 9), unit="D")})
    column = sp.profile(frame).get("elapsed")
    assert column.kind is ColumnKind.NUMERIC
    assert column.numeric is not None
    assert to_number(pd.Timedelta(days=1)) == 86400.0


def test_a_period_is_a_time_span() -> None:
    frame = pd.DataFrame({"month": pd.period_range("2024-01", periods=8, freq="M")})
    assert sp.profile(frame).get("month").kind is ColumnKind.DATETIME


@pytest.mark.parametrize(
    ("name", "values"),
    [
        ("complex", np.arange(6) + 1j * np.arange(6)),
        ("list", [[1, 2]] * 6),
        ("dict", [{"k": i} for i in range(6)]),
    ],
)
def test_a_column_nothing_can_summarise_says_so(name: str, values: object) -> None:
    """Named rather than silently filed under 'categorical'. A reader who sees
    a category count for a column of dictionaries will believe it."""
    column = sp.profile(pd.DataFrame({name: values})).get(name)
    assert column.kind is ColumnKind.UNSUPPORTED
    assert column.unsupported_reason
    assert name in column.unsupported_reason


def test_a_supported_column_claims_no_excuse() -> None:
    column = sp.profile(pd.DataFrame({"n": [1.0, 2.0, 3.0]})).get("n")
    assert column.unsupported_reason == ""


def test_profiling_survives_unhashable_cells() -> None:
    """``DataFrame.duplicated`` raises on a column of lists, and a profiler
    that dies on a JSON column is one nobody can point at real data."""
    frame = pd.DataFrame({"payload": [{"a": 1}, {"a": 2}], "n": [1.0, 2.0]})
    result = sp.profile(frame)
    assert result.columns == 2
    assert result.duplicate_rows == 0


def test_duplicates_are_still_counted_on_the_columns_that_can_be() -> None:
    """Skipping the unhashable column is not the same as giving up: the rows
    that *are* comparable still get their answer."""
    frame = pd.DataFrame({"payload": [[1], [1], [2]], "n": [1.0, 1.0, 2.0]})
    assert sp.profile(frame).duplicate_rows == 1


def test_the_whole_dtype_surface_neither_crashes_nor_lies() -> None:
    """One frame holding every dtype pandas offers. The scan must complete and
    every column must land somewhere it can be summarised honestly."""
    n = 8
    frame = pd.DataFrame(
        {
            "f64": np.linspace(1, 8, n),
            "i64": np.arange(n),
            "nullable_int": pd.array([1, 2, None, 4, 5, 6, 7, 8], dtype="Int64"),
            "nullable_bool": pd.array(
                [True, False, None, True, False, True, None, False], dtype="boolean"
            ),
            "string": pd.array(list("abacbacb"), dtype="string"),
            "ordered": pd.Categorical(
                ["low", "high", "mid"] * 2 + ["low", "high"],
                categories=["low", "mid", "high"],
                ordered=True,
            ),
            "nominal": pd.Categorical(list("xyxzyxzy")),
            "when": pd.date_range("2024-01-01", periods=n),
            "when_tz": pd.date_range("2024-01-01", periods=n, tz="UTC"),
            "elapsed": pd.to_timedelta(np.arange(n), unit="D"),
            "month": pd.period_range("2024-01", periods=n, freq="M"),
            "band": pd.arrays.IntervalArray.from_breaks(np.arange(n + 1)),
            "wave": np.arange(n) + 1j * np.arange(n),
            "payload": [{"k": i} for i in range(n)],
            "sparse": pd.arrays.SparseArray([0, 0, 1, 0, 0, 2, 0, 0]),
        }
    )

    profile = sp.profile(frame)
    assert len(profile.columns_profiled) == len(frame.columns)

    expected = {
        "f64": ColumnKind.NUMERIC,
        "i64": ColumnKind.NUMERIC,
        "nullable_int": ColumnKind.NUMERIC,
        "nullable_bool": ColumnKind.BOOLEAN,
        "ordered": ColumnKind.ORDINAL,
        "nominal": ColumnKind.CATEGORICAL,
        "when": ColumnKind.DATETIME,
        "when_tz": ColumnKind.DATETIME,
        "elapsed": ColumnKind.NUMERIC,
        "month": ColumnKind.DATETIME,
        "wave": ColumnKind.UNSUPPORTED,
        "payload": ColumnKind.UNSUPPORTED,
        "sparse": ColumnKind.NUMERIC,
    }
    for name, kind in expected.items():
        assert profile.get(name).kind is kind, f"{name} classified as {profile.get(name).kind}"

    # And the whole pipeline runs over it without raising.
    result = sp.scan(frame)
    assert result.column_count == len(frame.columns)
    before = frame.copy(deep=True)
    sp.auto_prepare(frame)
    pd.testing.assert_frame_equal(frame, before)


# ==========================================================================
# The type map -- what each type gets, declared once and enforced
# ==========================================================================


@pytest.fixture(scope="module")
def every_kind() -> dict[ColumnKind, object]:
    """One profiled column of every kind the library can produce."""
    frame = pd.DataFrame(
        {
            "amount": np.random.default_rng(0).normal(100, 20, 60),
            "sev": pd.Categorical(
                ["low"] * 20 + ["high"] * 12 + ["mid"] * 28,
                categories=["low", "mid", "high"],
                ordered=True,
            ),
            "city": ["Rabat", "Casablanca", "Fes"] * 20,
            "note": [f"a comment number {i} with words" if i % 2 else "x" for i in range(60)],
            "when": pd.date_range("2024-01-01", periods=60),
            "flag": [True, False] * 30,
            "const": ["same"] * 60,
            "blob": [{"k": i} for i in range(60)],
            "nothing": [None] * 60,
        }
    )
    profile = sp.profile(frame)
    return {c.kind: c for c in profile.columns_profiled.values()}


def test_every_kind_has_an_entry_in_the_type_map() -> None:
    """A kind with no entry is a kind nothing knows how to analyse, which
    shows up as an empty panel nobody can explain."""
    from smartprep.eda.typemap import SUPPORT

    missing = [k for k in ColumnKind if k not in SUPPORT]
    assert not missing, f"no type-map entry for: {[k.value for k in missing]}"


def test_every_declared_chart_is_actually_delivered(every_kind: dict) -> None:
    """The rule this project keeps rediscovering, applied to charts per type:
    declared or refused, never declared and silently absent."""
    from smartprep.eda.typemap import support_for
    from smartprep.viz.builders import column_charts

    for kind, column in every_kind.items():
        support = support_for(kind)
        drawn = list(column_charts(column))
        assert len(drawn) == len(support.charts), (
            f"{kind.value} declares {list(support.charts)} but delivered "
            f"{[c.mark.value for c in drawn]}"
        )


def test_every_declared_chart_names_a_real_builder() -> None:
    from smartprep.eda.typemap import SUPPORT
    from smartprep.viz.builders import _BUILDERS

    for support in SUPPORT.values():
        for name in support.charts:
            assert name in _BUILDERS, f"{support.kind.value} names an unknown chart {name!r}"


def test_a_type_with_no_honest_chart_gets_none(every_kind: dict) -> None:
    """An empty panel is better than a confident wrong one."""
    from smartprep.viz.builders import column_charts

    for kind in (ColumnKind.UNSUPPORTED, ColumnKind.CONSTANT):
        if kind in every_kind:
            assert len(list(column_charts(every_kind[kind]))) == 0


def test_an_ordinal_chart_keeps_the_declared_order(every_kind: dict) -> None:
    """Sorting an ordinal column by frequency destroys the one thing that
    distinguishes it from a nominal one, and the result looks reasonable."""
    from smartprep.viz.builders import column_charts

    column = every_kind[ColumnKind.ORDINAL]
    chart = list(column_charts(column))[0]
    assert [d["category"] for d in chart.data] == list(column.categorical.ordered_levels)


def test_a_nominal_chart_is_ordered_by_frequency(every_kind: dict) -> None:
    """The negative case: a rare level is what a reader needs to see, and it
    is invisible in alphabetical order."""
    from smartprep.viz.builders import column_charts

    chart = list(column_charts(every_kind[ColumnKind.CATEGORICAL]))[0]
    counts = [d["count"] for d in chart.data]
    assert counts == sorted(counts, reverse=True)


def test_every_type_explains_itself() -> None:
    from smartprep.eda.typemap import SUPPORT

    for support in SUPPORT.values():
        assert len(support.why.split()) >= 8, f"{support.kind.value} has no real rationale"


def test_an_analysed_type_names_its_summary() -> None:
    from smartprep.eda.typemap import SUPPORT

    for support in SUPPORT.values():
        if support.is_analysed:
            assert support.summary, f"{support.kind.value} computes statistics from nowhere"
        else:
            assert not support.charts, f"{support.kind.value} charts data it never analysed"


def test_the_map_renders_as_a_table() -> None:
    from smartprep.eda.typemap import SUPPORT, support_table

    table = support_table()
    for support in SUPPORT.values():
        assert f"`{support.kind.value}`" in table
