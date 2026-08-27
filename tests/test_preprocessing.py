"""Preprocessing: fit/transform discipline and the leakage guard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import smartprep as sp
from smartprep.core.enums import Severity
from smartprep.exceptions import SmartPrepError
from smartprep.preprocessing import Preprocessor


@pytest.fixture
def frame() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    return pd.DataFrame(
        {
            "income": list(rng.lognormal(10, 1, 40)) + [None] * 5,
            "age": list(rng.normal(40, 10, 40)) + [None] * 5,
            "sector": (["ICT", "Retail", "Tourism"] * 15)[:45],
            "city": [f"city_{i % 20}" for i in range(45)],
            "target": list(rng.integers(0, 2, 45)),
        }
    )


# -- separation from cleaning ---------------------------------------------


def test_auto_prepare_never_preprocesses(frame: pd.DataFrame) -> None:
    """Cleaning fixes what is wrong; preprocessing transforms what is right."""
    result = sp.auto_prepare(frame)
    assert list(result.clean_df.columns) == list(frame.columns)
    assert result.clean_df["income"].isna().sum() == 5, "imputation is not cleaning"


# -- fit / transform ------------------------------------------------------


def test_transform_before_fit_is_refused(frame: pd.DataFrame) -> None:
    """Fitting on everything then transforming is the leakage this prevents."""
    prep = Preprocessor().impute("income", method="median")
    with pytest.raises(SmartPrepError, match="before fit"):
        prep.transform(frame)


def test_parameters_come_from_training_only(frame: pd.DataFrame) -> None:
    train, test = frame.iloc[:30], frame.iloc[30:]
    prep = Preprocessor().impute("income", method="median").fit(train)

    learned = prep.steps[0].learned["income"]
    expected = float(train["income"].dropna().median())
    assert learned == pytest.approx(expected)

    out = prep.transform(test)
    filled = out.loc[test["income"].isna(), "income"]
    assert all(v == pytest.approx(expected) for v in filled)


def test_fit_does_not_modify_the_frame(frame: pd.DataFrame) -> None:
    before = frame.copy(deep=True)
    Preprocessor().impute("income", method="median").fit(frame)
    pd.testing.assert_frame_equal(frame, before)


def test_missing_columns_are_reported_clearly(frame: pd.DataFrame) -> None:
    prep = Preprocessor().scale("no_such_column")
    with pytest.raises(SmartPrepError, match="not in the frame"):
        prep.fit(frame)


def test_transforming_the_target_is_refused() -> None:
    with pytest.raises(SmartPrepError, match="target column"):
        Preprocessor(target="y").scale("y")


# -- imputation -----------------------------------------------------------


@pytest.mark.parametrize("method", ["mean", "median", "mode", "constant"])
def test_imputation_fills_everything(frame: pd.DataFrame, method: str) -> None:
    out = Preprocessor().impute("income", method=method).fit_transform(frame)
    assert out["income"].isna().sum() == 0


def test_group_imputation_uses_the_group(frame: pd.DataFrame) -> None:
    out = Preprocessor().impute("income", method="group_median", by="sector").fit_transform(frame)
    assert out["income"].isna().sum() == 0


def test_unknown_method_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown imputation method"):
        Preprocessor().impute("x", method="telepathy")


def test_missing_indicator_runs_before_imputation(frame: pd.DataFrame) -> None:
    """Otherwise there is nothing left to indicate."""
    advice = sp.recommend_preprocessing(frame, target="target")
    prep = advice.to_preprocessor(target="target")
    out = prep.fit_transform(frame)
    assert out["income__was_missing"].sum() == 5
    assert out["income"].isna().sum() == 0


# -- encoding -------------------------------------------------------------


def test_one_hot_replaces_the_column(frame: pd.DataFrame) -> None:
    out = Preprocessor().encode("sector", method="one_hot").fit_transform(frame)
    assert "sector" not in out.columns
    assert {"sector__ICT", "sector__Retail", "sector__Tourism"} <= set(out.columns)


def test_unseen_category_is_kept_visible(frame: pd.DataFrame) -> None:
    """An unseen level is a real event, not silently one of the known ones."""
    prep = Preprocessor().encode("sector", method="ordinal").fit(frame)
    unseen = pd.DataFrame({**{c: frame[c].iloc[:1] for c in frame.columns}})
    unseen.loc[unseen.index[0], "sector"] = "Aerospace"
    assert prep.transform(unseen)["sector"].iloc[0] == -1


def test_target_encoding_requires_a_target(frame: pd.DataFrame) -> None:
    with pytest.raises(SmartPrepError, match="needs a target column"):
        Preprocessor().encode("city", method="target")


def test_target_encoding_warns_about_leakage(frame: pd.DataFrame) -> None:
    prep = Preprocessor(target="target").encode("city", method="target").fit(frame)
    assert any(w.severity is Severity.HIGH_WARNING for w in prep.warnings)
    assert any("leaks" in w.message for w in prep.warnings)


def test_frequency_encoding_is_leak_free(frame: pd.DataFrame) -> None:
    prep = Preprocessor(target="target").encode("city", method="frequency").fit(frame)
    assert not [w for w in prep.warnings if "target encoding" in w.message]


# -- scaling --------------------------------------------------------------


@pytest.mark.parametrize(
    "method", ["standard", "minmax", "robust", "maxabs", "log1p", "yeo_johnson", "quantile_rank"]
)
def test_scaling_produces_finite_numbers(frame: pd.DataFrame, method: str) -> None:
    out = (
        Preprocessor()
        .impute("age", method="median")
        .scale("age", method=method)
        .fit_transform(frame)
    )
    assert np.isfinite(out["age"].to_numpy()).all()


def test_standard_scaling_centres_and_scales(frame: pd.DataFrame) -> None:
    out = (
        Preprocessor()
        .impute("age", method="median")
        .scale("age", method="standard")
        .fit_transform(frame)
    )
    assert out["age"].mean() == pytest.approx(0.0, abs=1e-9)
    assert out["age"].std(ddof=0) == pytest.approx(1.0, abs=1e-9)


def test_constant_column_does_not_divide_by_zero() -> None:
    """A column with no spread has nothing to scale; inf is not the answer."""
    constant = pd.DataFrame({"x": [5.0] * 10})
    out = Preprocessor().scale("x", method="standard").fit_transform(constant)
    assert np.isfinite(out["x"].to_numpy()).all()
    assert (out["x"] == 0).all()


def test_minmax_stays_within_bounds_on_training_data(frame: pd.DataFrame) -> None:
    out = (
        Preprocessor()
        .impute("age", method="median")
        .scale("age", method="minmax")
        .fit_transform(frame)
    )
    assert out["age"].min() >= 0.0 and out["age"].max() <= 1.0


# -- leakage guard --------------------------------------------------------


def test_a_feature_that_encodes_the_target_is_flagged() -> None:
    frame = pd.DataFrame({"y": range(50), "leaky": [v * 2 for v in range(50)]})
    prep = Preprocessor(target="y").scale("leaky", method="standard").fit(frame)
    assert any(w.severity is Severity.CRITICAL_REVIEW for w in prep.warnings)


def test_sequential_fills_warn_about_using_the_future(frame: pd.DataFrame) -> None:
    prep = Preprocessor().impute("income", method="interpolate").fit(frame)
    assert any("future observations" in w.message for w in prep.warnings)


# -- advisor --------------------------------------------------------------


def test_advice_explains_itself(frame: pd.DataFrame) -> None:
    advice = sp.recommend_preprocessing(frame, target="target")
    assert advice.recommendations
    for rec in advice.recommendations:
        assert rec.reason, f"{rec.column}/{rec.method} recommended without a reason"


def test_advice_offers_alternatives(frame: pd.DataFrame) -> None:
    advice = sp.recommend_preprocessing(frame, target="target")
    encodes = [r for r in advice.recommendations if r.kind == "encode"]
    assert any(r.alternatives for r in encodes)


def test_econometrics_goal_does_not_scale_or_encode(frame: pd.DataFrame) -> None:
    """Standardising for a descriptive model changes how coefficients read."""
    advice = sp.recommend_preprocessing(frame, goal="econometrics", target="target")
    assert not [r for r in advice.recommendations if r.kind in {"scale", "encode"}]
    assert advice.notes


def test_tree_models_are_not_offered_scaling(frame: pd.DataFrame) -> None:
    advice = sp.recommend_preprocessing(frame, goal="tree_model", target="target")
    assert not [r for r in advice.recommendations if r.kind == "scale"]


def test_time_series_prefers_forward_fill(frame: pd.DataFrame) -> None:
    advice = sp.recommend_preprocessing(frame, goal="time_series")
    imputes = [r for r in advice.recommendations if r.kind == "impute"]
    assert any(r.method == "forward_fill" for r in imputes)


def test_high_cardinality_avoids_one_hot(frame: pd.DataFrame) -> None:
    advice = sp.recommend_preprocessing(frame, target="target")
    city = next(r for r in advice.recommendations if r.column == "city" and r.kind == "encode")
    assert city.method != "one_hot"


def test_mostly_missing_column_is_flagged_not_imputed() -> None:
    """Imputing more than half a column invents most of it."""
    frame = pd.DataFrame({"sparse": [1.0] + [None] * 19})
    advice = sp.recommend_preprocessing(frame)
    assert any("consider dropping" in n for n in advice.notes)
    assert not [r for r in advice.recommendations if r.kind == "impute"]


def test_advice_builds_a_working_pipeline(frame: pd.DataFrame) -> None:
    advice = sp.recommend_preprocessing(frame, target="target")
    out = advice.to_preprocessor(target="target").fit_transform(frame)
    assert len(out) == len(frame)
    assert out.drop(columns=["target"]).isna().sum().sum() == 0


def test_report_serialises(frame: pd.DataFrame) -> None:
    import json

    prep = sp.recommend_preprocessing(frame, target="target").to_preprocessor(target="target")
    prep.fit(frame)
    payload = json.loads(json.dumps(prep.report.to_dict()))
    assert payload["schema_version"] == 1
    assert payload["steps"]


# -- P0 regressions -------------------------------------------------------


def test_target_encoding_is_cross_fitted() -> None:
    """A row must never be encoded using its own outcome.

    The naive implementation built one mean per category from the whole
    training set, so each row's own target sat inside the number encoding it.
    On this data the encoding tracked `y` exactly.
    """
    frame = pd.DataFrame({"cat": ["a", "b", "c", "d"], "y": [0, 0, 1, 1]})
    prep = Preprocessor(target="y").encode("cat", method="target")

    out_of_fold = prep.fit_transform(frame)["cat"].tolist()
    full_mapping = prep.transform(frame)["cat"].tolist()

    # The leaked version produced values ordered exactly like y.
    assert full_mapping[0] < full_mapping[2], "full mapping should track the target"
    assert out_of_fold != full_mapping, "fit_transform must not reuse the leaked mapping"

    # Each row's own outcome is excluded from its own code.
    assert sorted(set(out_of_fold)) != sorted(set(full_mapping))


def test_fit_transform_and_transform_differ_only_for_target_encoding() -> None:
    """The asymmetry is deliberate, and confined to the encoder that needs it."""
    rng = np.random.default_rng(3)
    frame = pd.DataFrame(
        {"x": rng.normal(0, 1, 30), "cat": list("abc") * 10, "y": rng.integers(0, 2, 30)}
    )

    plain = Preprocessor().scale("x", method="standard")
    pd.testing.assert_frame_equal(plain.fit_transform(frame), plain.fit(frame).transform(frame))

    encoded = Preprocessor(target="y").encode("cat", method="target")
    assert not encoded.fit_transform(frame)["cat"].equals(
        encoded.fit(frame).transform(frame)["cat"]
    )


def test_smoothed_mean_target_is_available_and_named_honestly() -> None:
    """The leaky variant is still useful sometimes -- under its real name."""
    frame = pd.DataFrame({"cat": ["a", "b", "a", "b"], "y": [0, 1, 0, 1]})
    prep = Preprocessor(target="y").encode("cat", method="smoothed_mean_target")
    assert prep.fit_transform(frame)["cat"].equals(prep.fit(frame).transform(frame)["cat"])


def test_quantile_rank_preserves_missing_values() -> None:
    """searchsorted places NaN past every element, which silently promoted a
    missing value to the top quantile -- a fabricated extreme observation."""
    out = (
        Preprocessor()
        .scale("x", method="quantile_rank")
        .fit_transform(pd.DataFrame({"x": [1.0, 2.0, None, 4.0]}))
    )
    assert pd.isna(out["x"].iloc[2])
    assert out["x"].iloc[0] == 0.0


@pytest.mark.parametrize(
    "method", ["standard", "minmax", "robust", "maxabs", "log1p", "yeo_johnson", "quantile_rank"]
)
def test_every_scaler_preserves_missing_values(method: str) -> None:
    frame = pd.DataFrame({"x": [1.0, 2.0, None, 4.0]})
    out = Preprocessor().scale("x", method=method).fit_transform(frame)
    assert pd.isna(out["x"].iloc[2]), f"{method} did not preserve NaN"
