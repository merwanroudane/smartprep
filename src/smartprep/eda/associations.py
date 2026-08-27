"""Associations between columns of any type.

Pearson correlation answers one question about one pair of numeric columns.
Real tables are mixed, and a matrix that silently drops every categorical
column tells you the categorical columns do not matter -- which is usually
false and always misleading.

So each pair gets the measure that applies to it, and the measure used is
reported alongside the number. A 0.8 from Cramer's V and a 0.8 from Pearson do
not mean the same thing, and pretending they are interchangeable is worse than
showing both.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd

from ..detectors.base import is_missing, to_number
from .profile import ColumnKind, DatasetProfile

__all__ = [
    "Association",
    "AssociationMatrix",
    "associations",
    "cramers_v",
    "correlation_ratio",
    "MissingnessPattern",
    "missingness",
]


@dataclass(frozen=True)
class Association:
    """One pair, with the measure that was appropriate for it."""

    left: str
    right: str
    measure: str
    value: float
    kind: str  # "numeric-numeric" | "categorical-categorical" | "mixed"
    sample_size: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left,
            "right": self.right,
            "measure": self.measure,
            "value": round(self.value, 5),
            "kind": self.kind,
            "n": self.sample_size,
        }


@dataclass
class AssociationMatrix:
    """All pairwise associations, addressable and serialisable."""

    pairs: list[Association] = field(default_factory=list)
    columns: tuple[str, ...] = ()

    def get(self, left: str, right: str) -> Association | None:
        for pair in self.pairs:
            if {pair.left, pair.right} == {left, right}:
                return pair
        return None

    def strongest(self, n: int = 10, *, minimum: float = 0.0) -> list[Association]:
        return sorted(
            (p for p in self.pairs if abs(p.value) >= minimum),
            key=lambda p: -abs(p.value),
        )[:n]

    def for_column(self, column: str) -> list[Association]:
        return sorted(
            (p for p in self.pairs if column in (p.left, p.right)),
            key=lambda p: -abs(p.value),
        )

    def as_grid(self) -> dict[str, dict[str, float]]:
        """Square form, for a heatmap. Diagonal is 1.0."""
        grid = {a: {b: 0.0 for b in self.columns} for a in self.columns}
        for column in self.columns:
            grid[column][column] = 1.0
        for pair in self.pairs:
            grid[pair.left][pair.right] = pair.value
            grid[pair.right][pair.left] = pair.value
        return grid

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "columns": list(self.columns),
            "pairs": [p.to_dict() for p in self.pairs],
            "note": (
                "Different measures are not interchangeable. Pearson is signed and "
                "linear; Cramer's V and the correlation ratio are unsigned strength "
                "measures on [0, 1]."
            ),
        }

    def summary(self, n: int = 12) -> str:
        lines = [f"{len(self.pairs)} pairs across {len(self.columns)} columns", ""]
        for pair in self.strongest(n):
            lines.append(f"  {pair.left:20s} {pair.right:20s} {pair.measure:18s} {pair.value:+.3f}")
        return "\n".join(lines)


def cramers_v(left: pd.Series, right: pd.Series) -> float:
    """Association between two categorical columns, on [0, 1].

    Bias-corrected: the uncorrected statistic drifts upward with the number of
    categories, so two high-cardinality columns look related when they are not.
    """
    table = pd.crosstab(left, right)
    if table.size == 0 or table.shape[0] < 2 or table.shape[1] < 2:
        return 0.0

    observed = table.to_numpy(dtype=float)
    n = observed.sum()
    if n == 0:
        return 0.0

    row_totals = observed.sum(axis=1, keepdims=True)
    col_totals = observed.sum(axis=0, keepdims=True)
    expected = row_totals @ col_totals / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum(np.where(expected > 0, (observed - expected) ** 2 / expected, 0.0))

    phi2 = chi2 / n
    rows, cols = observed.shape
    phi2_corrected = max(0.0, phi2 - ((cols - 1) * (rows - 1)) / (n - 1))
    rows_corrected = rows - (rows - 1) ** 2 / (n - 1)
    cols_corrected = cols - (cols - 1) ** 2 / (n - 1)
    denominator = min(rows_corrected - 1, cols_corrected - 1)
    if denominator <= 0:
        return 0.0
    return float(math.sqrt(phi2_corrected / denominator))


def correlation_ratio(categories: pd.Series, values: pd.Series) -> float:
    """Association between a categorical and a numeric column, on [0, 1].

    The share of the numeric column's variance explained by group membership --
    the right question for this pairing, where Pearson has no meaning at all.
    """
    frame = pd.DataFrame({"g": categories.astype(str), "v": values}).dropna()
    if frame.empty or frame["g"].nunique() < 2:
        return 0.0

    overall = frame["v"].mean()
    total = float(((frame["v"] - overall) ** 2).sum())
    if total == 0:
        return 0.0

    between = 0.0
    for _, group in frame.groupby("g")["v"]:
        between += len(group) * (group.mean() - overall) ** 2
    return float(math.sqrt(max(0.0, between) / total))


def associations(
    frame: pd.DataFrame,
    dataset_profile: DatasetProfile | None = None,
    *,
    max_columns: int = 40,
    method: Literal["pearson", "kendall", "spearman"] = "spearman",
) -> AssociationMatrix:
    """Compute every pairwise association, choosing the measure per pair.

    ``method`` selects the numeric-numeric measure. Spearman is the default
    because it is rank-based and therefore not derailed by the outliers and
    skew that real data reliably contains.
    """
    from .profile import profile as build_profile

    dataset_profile = dataset_profile or build_profile(frame)

    usable = [
        name
        for name, column in dataset_profile.columns_profiled.items()
        # An identifier is distinct by construction; correlating it with
        # anything measures the row order, not a relationship.
        if column.kind
        in (
            ColumnKind.NUMERIC,
            ColumnKind.CATEGORICAL,
            ColumnKind.ORDINAL,
            ColumnKind.BOOLEAN,
        )
        and not column.is_constant
        and not column.is_identifier_like
    ][:max_columns]

    matrix = AssociationMatrix(columns=tuple(usable))

    numeric_cache = {
        name: frame[name].map(to_number)
        for name in usable
        if dataset_profile.get(name).kind in (ColumnKind.NUMERIC, ColumnKind.BOOLEAN)
    }

    for i, left in enumerate(usable):
        for right in usable[i + 1 :]:
            left_numeric = left in numeric_cache
            right_numeric = right in numeric_cache

            if left_numeric and right_numeric:
                a, b = numeric_cache[left], numeric_cache[right]
                usable_rows = a.notna() & b.notna()
                n = int(usable_rows.sum())
                if n < 3 or a[usable_rows].nunique() < 2 or b[usable_rows].nunique() < 2:
                    continue
                value = float(a[usable_rows].corr(b[usable_rows], method=method))
                matrix.pairs.append(Association(left, right, method, value, "numeric-numeric", n))

            elif not left_numeric and not right_numeric:
                pair = frame[[left, right]].dropna()
                if len(pair) < 3:
                    continue
                value = cramers_v(pair[left], pair[right])
                matrix.pairs.append(
                    Association(
                        left, right, "cramers_v", value, "categorical-categorical", len(pair)
                    )
                )

            else:
                category = right if left_numeric else left
                number = left if left_numeric else right
                pair = pd.DataFrame({"c": frame[category], "n": numeric_cache[number]}).dropna()
                if len(pair) < 3:
                    continue
                value = correlation_ratio(pair["c"], pair["n"])
                matrix.pairs.append(
                    Association(left, right, "correlation_ratio", value, "mixed", len(pair))
                )

    return matrix


@dataclass
class MissingnessPattern:
    """How absence is distributed, which is often more informative than its rate."""

    by_column: dict[str, int] = field(default_factory=dict)
    co_missing: list[tuple[str, str, float]] = field(default_factory=list)
    patterns: list[tuple[str, int]] = field(default_factory=list)
    rows_complete: int = 0
    rows_any_missing: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "by_column": dict(self.by_column),
            "co_missing": [
                {"left": a, "right": b, "jaccard": round(v, 4)} for a, b, v in self.co_missing
            ],
            "patterns": [{"pattern": p, "rows": n} for p, n in self.patterns],
            "rows_complete": self.rows_complete,
            "rows_any_missing": self.rows_any_missing,
        }

    def summary(self) -> str:
        lines = [
            f"{self.rows_any_missing} rows have at least one missing value, "
            f"{self.rows_complete} are complete",
            "",
        ]
        for column, count in sorted(self.by_column.items(), key=lambda kv: -kv[1]):
            if count:
                lines.append(f"  {column:22s} {count}")
        if self.co_missing:
            lines += ["", "Columns that go missing together:"]
            for left, right, score in self.co_missing[:8]:
                lines.append(f"  {left:20s} {right:20s} {score:.2f}")
        return "\n".join(lines)


def missingness(frame: pd.DataFrame, *, top_patterns: int = 12) -> MissingnessPattern:
    """Analyse the structure of absence, not just its volume.

    Two columns that are always missing together usually share one upstream
    cause, and finding that cause fixes both. A rate alone never shows it.
    """
    # Column-wise rather than DataFrame.map: that method arrived in pandas 2.1
    # and applymap is deprecated in newer versions, so neither works across the
    # supported range. This does, without a version probe.
    mask = frame.apply(lambda column: column.map(is_missing))
    result = MissingnessPattern(
        by_column={str(c): int(mask[c].sum()) for c in frame.columns},
        rows_complete=int((~mask.any(axis=1)).sum()),
        rows_any_missing=int(mask.any(axis=1).sum()),
    )

    affected = [c for c in frame.columns if mask[c].any()]
    for i, left in enumerate(affected):
        for right in affected[i + 1 :]:
            both = int((mask[left] & mask[right]).sum())
            either = int((mask[left] | mask[right]).sum())
            if either and both / either > 0.3:
                result.co_missing.append((str(left), str(right), both / either))
    result.co_missing.sort(key=lambda item: -item[2])

    if affected:
        signatures = mask[affected].apply(
            lambda row: "".join("1" if v else "0" for v in row), axis=1
        )
        result.patterns = [
            (str(pattern), int(count))
            for pattern, count in signatures.value_counts().head(top_patterns).items()
        ]

    return result
