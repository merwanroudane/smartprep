"""Preprocessing: transforming clean data to suit an analysis.

This is a **different job from cleaning**, and the separation is deliberate.

    Cleaning       "this value is wrong"
    Preprocessing  "this value is right, but the model needs it differently"

Conflating them is how a scaled column ends up in a descriptive report, and how
an imputed value ends up indistinguishable from an observed one. So
preprocessing never runs inside ``auto_prepare``. You ask for it explicitly.

Everything here follows ``fit`` / ``transform`` semantics, because that is the
only structure that prevents leakage: parameters are learned from training data
and applied to everything else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..core.enums import Severity
from ..detectors.base import is_missing, to_number
from ..exceptions import SmartPrepError

__all__ = ["Step", "LeakageWarning", "Preprocessor", "PreprocessingReport"]


@dataclass(frozen=True)
class LeakageWarning:
    """A way this pipeline could let information reach it that it should not."""

    step: str
    columns: tuple[str, ...]
    severity: Severity
    message: str
    remedy: str

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"[{self.severity.name}] {self.step} on {list(self.columns)}: {self.message}"


@dataclass
class Step:
    """One fitted transformation, with the parameters it learned."""

    name: str
    kind: str
    columns: tuple[str, ...]
    parameters: dict[str, Any] = field(default_factory=dict)
    learned: dict[str, Any] = field(default_factory=dict)
    fitted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "columns": list(self.columns),
            "parameters": {str(k): str(v) for k, v in self.parameters.items()},
            "learned_keys": sorted(self.learned),
        }


@dataclass
class PreprocessingReport:
    """What the pipeline did, and what it is worried about."""

    steps: list[Step] = field(default_factory=list)
    warnings: list[LeakageWarning] = field(default_factory=list)
    columns_added: list[str] = field(default_factory=list)
    columns_removed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "steps": [s.to_dict() for s in self.steps],
            "warnings": [
                {
                    "step": w.step,
                    "columns": list(w.columns),
                    "severity": w.severity.name,
                    "message": w.message,
                    "remedy": w.remedy,
                }
                for w in self.warnings
            ],
            "columns_added": list(self.columns_added),
            "columns_removed": list(self.columns_removed),
        }

    def summary(self) -> str:
        lines = [f"{len(self.steps)} steps fitted"]
        for step in self.steps:
            lines.append(f"  {step.kind:12s} {step.name:24s} {', '.join(step.columns)}")
        if self.columns_added:
            lines.append(f"\nColumns added: {', '.join(self.columns_added)}")
        if self.warnings:
            lines.append(f"\n{len(self.warnings)} leakage warning(s):")
            for warning in self.warnings:
                lines.append(f"  {warning}")
                lines.append(f"      remedy: {warning.remedy}")
        return "\n".join(lines)


class Preprocessor:
    """A fit/transform pipeline with a leakage guard.

    Built explicitly, never inferred::

        prep = sp.Preprocessor()
        prep.impute("income", method="median")
        prep.encode("sector", method="one_hot")
        prep.scale(["income", "age"], method="standard")

        train_out = prep.fit_transform(train)
        test_out = prep.transform(test)     # uses the training parameters

    Calling ``fit_transform`` on the full dataset before splitting is the
    classic leakage mistake, so ``transform`` on unfitted state raises rather
    than quietly refitting.
    """

    def __init__(self, *, target: str | None = None) -> None:
        self.target = target
        self.steps: list[Step] = []
        self.report = PreprocessingReport()
        self._fitted = False
        #: True only while ``fit_transform`` is applying steps, so target
        #: encoding can hand back out-of-fold values for the training rows.
        self._cross_fitted_pass = False

    # -- declaration --------------------------------------------------------

    def _add(
        self, kind: str, name: str, columns: str | list[str], **parameters: Any
    ) -> Preprocessor:
        cols = (columns,) if isinstance(columns, str) else tuple(columns)
        if self.target is not None and self.target in cols:
            raise SmartPrepError(
                f"{name} was asked to transform the target column {self.target!r}. "
                "Transforming the target changes what the model is predicting; if "
                "that is intended, do it explicitly outside the pipeline."
            )
        self.steps.append(Step(name=name, kind=kind, columns=cols, parameters=parameters))
        return self

    def impute(
        self, columns: str | list[str], *, method: str = "median", **kwargs: Any
    ) -> Preprocessor:
        """Fill missing values.

        Methods: ``mean``, ``median``, ``mode``, ``constant``, ``group_median``,
        ``forward_fill``, ``backward_fill``, ``interpolate``.
        """
        if method not in _IMPUTERS:
            raise ValueError(f"unknown imputation method {method!r}; expected {sorted(_IMPUTERS)}")
        return self._add("impute", f"impute_{method}", columns, method=method, **kwargs)

    def encode(
        self, columns: str | list[str], *, method: str = "one_hot", **kwargs: Any
    ) -> Preprocessor:
        """Represent categories numerically.

        Methods: ``one_hot``, ``ordinal``, ``frequency``, ``count``, ``target``,
        ``smoothed_mean_target``.

        ``target`` is cross-fitted: ``fit_transform`` returns out-of-fold
        encodings so no row is encoded using its own outcome.
        ``smoothed_mean_target`` is the plain version, which leaks on the
        training rows and is named accordingly.
        """
        if method not in _ENCODERS:
            raise ValueError(f"unknown encoding method {method!r}; expected {sorted(_ENCODERS)}")
        if method == "target" and self.target is None:
            raise SmartPrepError(
                "target encoding needs a target column. Pass Preprocessor(target='y')."
            )
        return self._add("encode", f"encode_{method}", columns, method=method, **kwargs)

    def scale(
        self, columns: str | list[str], *, method: str = "standard", **kwargs: Any
    ) -> Preprocessor:
        """Rescale numeric columns.

        Methods: ``standard``, ``minmax``, ``robust``, ``maxabs``, ``log1p``,
        ``yeo_johnson``, ``quantile_rank``.
        """
        if method not in _SCALERS:
            raise ValueError(f"unknown scaling method {method!r}; expected {sorted(_SCALERS)}")
        return self._add("scale", f"scale_{method}", columns, method=method, **kwargs)

    def add_missing_indicator(self, columns: str | list[str]) -> Preprocessor:
        """Record where values were missing, before imputation hides it."""
        return self._add("indicator", "missing_indicator", columns)

    # -- fitting ------------------------------------------------------------

    def fit(self, frame: pd.DataFrame) -> Preprocessor:
        """Learn parameters. The frame is not modified."""
        self._check_columns(frame)
        working = frame.copy(deep=True)
        self._cross_fitted_pass = True
        try:
            for step in self.steps:
                _FITTERS[step.kind](self, step, working)
                step.fitted = True
                working = _APPLIERS[step.kind](self, step, working)
        finally:
            self._cross_fitted_pass = False
        self._fitted = True
        self.report.steps = list(self.steps)
        self._check_leakage(frame)
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Apply the learned parameters to new data."""
        if not self._fitted:
            raise SmartPrepError(
                "transform() before fit(). Fit on the training partition only -- "
                "fitting on everything and then transforming is the leakage this "
                "class exists to prevent."
            )
        self._check_columns(frame)
        out = frame.copy(deep=True)
        for step in self.steps:
            out = _APPLIERS[step.kind](self, step, out)
        return out

    def fit_transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Fit, then transform the same data.

        For target encoding this deliberately differs from
        ``fit(X).transform(X)``: it returns the **out-of-fold** encodings, so a
        row is never encoded using its own outcome. Everything else behaves
        identically either way.
        """
        self.fit(frame)
        self._cross_fitted_pass = True
        try:
            return self.transform(frame)
        finally:
            self._cross_fitted_pass = False

    # -- guards -------------------------------------------------------------

    def _check_columns(self, frame: pd.DataFrame) -> None:
        for step in self.steps:
            missing = [c for c in step.columns if c not in frame.columns]
            if missing:
                raise SmartPrepError(
                    f"{step.name} needs columns {missing}, which are not in the frame. "
                    f"Available: {sorted(frame.columns)}"
                )

    def _check_leakage(self, frame: pd.DataFrame) -> None:
        """Flag the ways this pipeline could see what it should not."""
        self.report.warnings.clear()

        for step in self.steps:
            if step.kind == "encode" and step.parameters.get("method") == "target":
                self.report.warnings.append(
                    LeakageWarning(
                        step=step.name,
                        columns=step.columns,
                        severity=Severity.HIGH_WARNING,
                        message=(
                            "target encoding learns from the outcome, so any fit on "
                            "data the model will later be scored on leaks"
                        ),
                        remedy=(
                            "fit on the training partition only, and prefer "
                            "cross-fitted encoding for model selection"
                        ),
                    )
                )
            if step.kind == "impute" and step.parameters.get("method") in {
                "forward_fill",
                "backward_fill",
                "interpolate",
            }:
                self.report.warnings.append(
                    LeakageWarning(
                        step=step.name,
                        columns=step.columns,
                        severity=Severity.WARNING,
                        message=(
                            "this fills from neighbouring rows, which uses future "
                            "observations unless the frame is sorted by time"
                        ),
                        remedy=(
                            "sort by the time index first, and use forward fill "
                            "rather than interpolation in a forecasting context"
                        ),
                    )
                )

        if self.target is not None:
            for step in self.steps:
                for column in step.columns:
                    if column == self.target:  # pragma: no cover - blocked at declaration
                        continue
                    correlation = _correlation(frame, column, self.target)
                    if correlation is not None and abs(correlation) > 0.98:
                        self.report.warnings.append(
                            LeakageWarning(
                                step=step.name,
                                columns=(column,),
                                severity=Severity.CRITICAL_REVIEW,
                                message=(
                                    f"{column!r} correlates with the target at "
                                    f"{correlation:.3f}; it may encode the answer"
                                ),
                                remedy=(
                                    "check whether this feature is available at "
                                    "prediction time, or is derived from the outcome"
                                ),
                            )
                        )

    @property
    def warnings(self) -> list[LeakageWarning]:
        return self.report.warnings


def _correlation(frame: pd.DataFrame, left: str, right: str) -> float | None:
    a = frame[left].map(to_number)
    b = frame[right].map(to_number)
    usable = a.notna() & b.notna()
    if usable.sum() < 3 or a[usable].nunique() < 2 or b[usable].nunique() < 2:
        return None
    return float(np.corrcoef(a[usable], b[usable])[0, 1])


# --------------------------------------------------------------------------
# Imputation
# --------------------------------------------------------------------------


def _fit_impute(prep: Preprocessor, step: Step, frame: pd.DataFrame) -> None:
    method = step.parameters["method"]
    for column in step.columns:
        step.learned[column] = _IMPUTERS[method](frame, column, step.parameters)


def _apply_impute(prep: Preprocessor, step: Step, frame: pd.DataFrame) -> pd.DataFrame:
    method = step.parameters["method"]
    out = frame
    for column in step.columns:
        learned = step.learned.get(column)
        if method in {"forward_fill", "backward_fill", "interpolate"}:
            out[column] = _sequential_fill(out[column], method)
        elif method == "group_median":
            out[column] = _fill_by_group(out, column, step.parameters["by"], learned or {})
        else:
            out[column] = [learned if is_missing(v) else v for v in out[column]]
    return out


def _fill_by_group(
    frame: pd.DataFrame, column: str, by: str, learned: dict[str, float]
) -> list[Any]:
    """Fill each missing value with its group's statistic.

    A named function rather than a lambda inside the loop: a closure over the
    loop variable would silently use the last column for every iteration.
    """
    fallback = learned.get("__global__")
    return [
        learned.get(group, fallback) if is_missing(value) else value
        for value, group in zip(frame[column], frame[by], strict=True)
    ]


def _sequential_fill(series: pd.Series, method: str) -> pd.Series:
    if method == "forward_fill":
        return series.ffill()
    if method == "backward_fill":
        return series.bfill()
    return pd.to_numeric(series, errors="coerce").interpolate()


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame[column].map(to_number).dropna()


_IMPUTERS = {
    "mean": lambda f, c, p: float(_numeric(f, c).mean()),
    "median": lambda f, c, p: float(_numeric(f, c).median()),
    "mode": lambda f, c, p: (
        f[c].dropna().mode().iloc[0] if not f[c].dropna().mode().empty else None
    ),
    "constant": lambda f, c, p: p.get("value", 0),
    "group_median": lambda f, c, p: {
        **{
            key: float(group.map(to_number).median())
            for key, group in f.groupby(p["by"])[c]
            if group.map(to_number).notna().any()
        },
        "__global__": float(_numeric(f, c).median()),
    },
    "forward_fill": lambda f, c, p: None,
    "backward_fill": lambda f, c, p: None,
    "interpolate": lambda f, c, p: None,
}


# --------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------


def _fit_encode(prep: Preprocessor, step: Step, frame: pd.DataFrame) -> None:
    method = step.parameters["method"]
    for column in step.columns:
        step.learned[column] = _ENCODERS[method](frame, column, step.parameters, prep.target)


def _apply_encode(prep: Preprocessor, step: Step, frame: pd.DataFrame) -> pd.DataFrame:
    method = step.parameters["method"]
    out = frame
    for column in step.columns:
        learned = step.learned[column]
        if method == "one_hot":
            for level in learned["levels"]:
                name = f"{column}__{level}"
                out[name] = (out[column].astype(str) == str(level)).astype(int)
                if name not in prep.report.columns_added:
                    prep.report.columns_added.append(name)
            out = out.drop(columns=[column])
            if column not in prep.report.columns_removed:
                prep.report.columns_removed.append(column)
        elif method in {"ordinal", "frequency", "count", "target", "smoothed_mean_target"}:
            oof = learned.get("oof")
            if oof and prep._cross_fitted_pass:
                # Training rows get the encoding built without their own fold.
                fallback = learned.get("unknown", -1)
                out[column] = [oof.get(label, fallback) for label in out.index]
                continue
            mapping = learned["mapping"]
            # An unseen category is a real event, not a zero. -1 for ordinal and
            # the global fallback elsewhere keep it visible rather than blending
            # it into an existing level.
            fallback = learned.get("unknown", -1)
            out[column] = [mapping.get(str(v), fallback) for v in out[column]]
    return out


def _one_hot(frame: pd.DataFrame, column: str, params: dict, target: str | None) -> dict:
    levels = sorted({str(v) for v in frame[column].dropna()})
    return {"levels": levels}


def _ordinal(frame: pd.DataFrame, column: str, params: dict, target: str | None) -> dict:
    order = params.get("order")
    if not order:
        # A pandas ordered categorical already states its order. Falling
        # straight through to alphabetical would silently rank "high" below
        # "low" and produce a model nobody could explain.
        dtype = frame[column].dtype
        if isinstance(dtype, pd.CategoricalDtype) and dtype.ordered:
            order = list(dtype.categories)
    levels = [str(v) for v in order] if order else sorted({str(v) for v in frame[column].dropna()})
    return {"mapping": {level: i for i, level in enumerate(levels)}, "unknown": -1}


def _frequency(frame: pd.DataFrame, column: str, params: dict, target: str | None) -> dict:
    counts = frame[column].astype(str).value_counts(normalize=True)
    return {"mapping": {k: float(v) for k, v in counts.items()}, "unknown": 0.0}


def _count(frame: pd.DataFrame, column: str, params: dict, target: str | None) -> dict:
    counts = frame[column].astype(str).value_counts()
    return {"mapping": {k: int(v) for k, v in counts.items()}, "unknown": 0}


def _smoothed_means(
    levels: pd.Series, y: pd.Series, prior: float, smoothing: float
) -> dict[str, float]:
    """Per-level target mean, shrunk toward the prior by ``smoothing``.

    A level seen twice should not be trusted as much as a level seen a
    thousand times, so small levels are pulled toward the global mean.
    """
    mapping: dict[str, float] = {}
    for level, positions in levels.groupby(levels).groups.items():
        values = y.loc[positions].dropna()
        if values.empty:
            mapping[str(level)] = prior
            continue
        mapping[str(level)] = float((values.sum() + prior * smoothing) / (len(values) + smoothing))
    return mapping


def _target(frame: pd.DataFrame, column: str, params: dict, target: str | None) -> dict:
    """Cross-fitted target encoding with a smoothed prior.

    The naive version computes one mean per category from the whole training
    set and applies it to every row in that category. Each row's own outcome is
    then inside the number used to encode it -- textbook target leakage, worst
    exactly where the encoder is most tempting, on rare and high-cardinality
    levels.

    So two different things are learned:

    * ``folds`` -- out-of-fold encodings for the training rows. Each row is
      encoded from a mapping built *without* the fold it belongs to, so its own
      outcome never reaches it. These are what ``fit_transform`` returns.
    * ``mapping`` -- the full-data mapping, used by ``transform`` on data the
      encoder has not seen. There is no leakage there because those rows were
      not in the fit.

    This is why ``fit_transform(X)`` and ``fit(X).transform(X)`` deliberately
    differ for this encoder, and only for this encoder.
    """
    assert target is not None
    y = frame[target].map(to_number)
    prior = float(y.mean())
    smoothing = float(params.get("smoothing", 10.0))
    folds = int(params.get("folds", 5))
    levels = frame[column].astype(str)

    full_mapping = _smoothed_means(levels, y, prior, smoothing)

    # Out-of-fold values, keyed by index label so they can be reattached to the
    # exact training rows regardless of ordering.
    n = len(frame)
    effective_folds = max(2, min(folds, n)) if n >= 2 else 1
    oof: dict[Any, float] = {}

    if effective_folds < 2:
        oof = {label: prior for label in frame.index}
    else:
        # Deterministic contiguous folds: no RNG, so the same data always
        # produces the same encoding.
        assignment = np.arange(n) % effective_folds
        for fold in range(effective_folds):
            held_out = assignment == fold
            rest_levels = levels[~held_out]
            rest_y = y[~held_out]
            if rest_y.dropna().empty:
                fold_mapping, fold_prior = {}, prior
            else:
                fold_prior = float(rest_y.mean())
                fold_mapping = _smoothed_means(rest_levels, rest_y, fold_prior, smoothing)
            for label, level in zip(frame.index[held_out], levels[held_out], strict=True):
                oof[label] = fold_mapping.get(level, fold_prior)

    return {"mapping": full_mapping, "unknown": prior, "prior": prior, "oof": oof}


def _smoothed_mean_target(
    frame: pd.DataFrame, column: str, params: dict, target: str | None
) -> dict:
    """Plain smoothed mean-target encoding, with no cross-fitting.

    Named for what it is. Kept because it is occasionally the right choice --
    encoding a lookup table, or a column whose levels are all large -- but it
    leaks on the training rows and says so.
    """
    assert target is not None
    y = frame[target].map(to_number)
    prior = float(y.mean())
    smoothing = float(params.get("smoothing", 10.0))
    mapping = _smoothed_means(frame[column].astype(str), y, prior, smoothing)
    return {"mapping": mapping, "unknown": prior, "prior": prior}


_ENCODERS = {
    "one_hot": _one_hot,
    "ordinal": _ordinal,
    "frequency": _frequency,
    "count": _count,
    "target": _target,
    "smoothed_mean_target": _smoothed_mean_target,
}


# --------------------------------------------------------------------------
# Scaling
# --------------------------------------------------------------------------


def _fit_scale(prep: Preprocessor, step: Step, frame: pd.DataFrame) -> None:
    method = step.parameters["method"]
    for column in step.columns:
        step.learned[column] = _SCALERS[method](_numeric(frame, column), step.parameters)


def _apply_scale(prep: Preprocessor, step: Step, frame: pd.DataFrame) -> pd.DataFrame:
    method = step.parameters["method"]
    out = frame
    for column in step.columns:
        learned = step.learned[column]
        values = out[column].map(to_number)
        out[column] = _SCALE_APPLY[method](values, learned)
    return out


def _standard_fit(values: pd.Series, params: dict) -> dict:
    std = float(values.std(ddof=0))
    # A constant column has no spread to divide by. Dividing anyway produces
    # inf or nan; leaving it centred at zero is the honest result.
    return {"mean": float(values.mean()), "std": std if std > 0 else 1.0, "constant": std == 0}


def _minmax_fit(values: pd.Series, params: dict) -> dict:
    low, high = float(values.min()), float(values.max())
    return {"min": low, "max": high, "range": (high - low) or 1.0}


def _robust_fit(values: pd.Series, params: dict) -> dict:
    q1, q3 = float(values.quantile(0.25)), float(values.quantile(0.75))
    return {"median": float(values.median()), "iqr": (q3 - q1) or 1.0}


def _maxabs_fit(values: pd.Series, params: dict) -> dict:
    return {"maxabs": float(values.abs().max()) or 1.0}


def _yeo_fit(values: pd.Series, params: dict) -> dict:
    """Fit Yeo-Johnson by searching lambda for maximum normality.

    A coarse grid rather than an optimiser: the difference is negligible at
    this scale and a grid cannot fail to converge.
    """
    best_lambda, best_score = 1.0, -np.inf
    for candidate in np.linspace(-2.0, 3.0, 51):
        transformed = _yeo_apply(values, {"lambda": float(candidate)})
        spread = float(np.std(transformed))
        if spread == 0:
            continue
        skew = float(np.abs(pd.Series(transformed).skew()))
        score = -skew
        if score > best_score:
            best_lambda, best_score = float(candidate), score
    return {"lambda": best_lambda}


def _yeo_apply(values: pd.Series, learned: dict) -> pd.Series:
    lam = float(learned["lambda"])
    x = values.to_numpy(dtype=float)
    out = np.empty_like(x)
    positive = x >= 0

    if abs(lam) < 1e-8:
        out[positive] = np.log1p(x[positive])
    else:
        out[positive] = ((x[positive] + 1) ** lam - 1) / lam
    if abs(lam - 2.0) < 1e-8:
        out[~positive] = -np.log1p(-x[~positive])
    else:
        out[~positive] = -(((-x[~positive] + 1) ** (2 - lam) - 1) / (2 - lam))
    return pd.Series(out, index=values.index)


_SCALERS = {
    "standard": _standard_fit,
    "minmax": _minmax_fit,
    "robust": _robust_fit,
    "maxabs": _maxabs_fit,
    "log1p": lambda v, p: {"shift": float(min(0.0, v.min()))},
    "yeo_johnson": _yeo_fit,
    "quantile_rank": lambda v, p: {"sorted": np.sort(v.to_numpy())},
}


def _quantile_rank_apply(values: pd.Series, learned: dict) -> pd.Series:
    """Rank each value against the training distribution.

    ``np.searchsorted`` places NaN after every element, which would silently
    turn a missing value into the top quantile -- a fabricated observation at
    the extreme of the range. The missing mask is therefore restored
    afterwards, as every other scaler here already does.
    """
    reference = learned["sorted"]
    raw = values.to_numpy(dtype=float)
    ranks = np.searchsorted(reference, raw) / max(len(reference), 1)
    out = pd.Series(ranks, index=values.index, dtype=float)
    out[values.isna().to_numpy()] = np.nan
    return out


_SCALE_APPLY = {
    "standard": lambda v, learned: (v - learned["mean"]) / learned["std"],
    "minmax": lambda v, learned: (v - learned["min"]) / learned["range"],
    "robust": lambda v, learned: (v - learned["median"]) / learned["iqr"],
    "maxabs": lambda v, learned: v / learned["maxabs"],
    "log1p": lambda v, learned: np.log1p(v - learned["shift"]),
    "yeo_johnson": _yeo_apply,
    "quantile_rank": _quantile_rank_apply,
}


# --------------------------------------------------------------------------
# Missing indicators
# --------------------------------------------------------------------------


def _fit_indicator(prep: Preprocessor, step: Step, frame: pd.DataFrame) -> None:
    step.learned = {c: f"{c}__was_missing" for c in step.columns}


def _apply_indicator(prep: Preprocessor, step: Step, frame: pd.DataFrame) -> pd.DataFrame:
    for column, name in step.learned.items():
        frame[name] = frame[column].map(is_missing).astype(int)
        if name not in prep.report.columns_added:
            prep.report.columns_added.append(name)
    return frame


_FITTERS = {
    "impute": _fit_impute,
    "encode": _fit_encode,
    "scale": _fit_scale,
    "indicator": _fit_indicator,
}

_APPLIERS = {
    "impute": _apply_impute,
    "encode": _apply_encode,
    "scale": _apply_scale,
    "indicator": _apply_indicator,
}
