"""Drift: comparing a new batch against a reference.

Three things get confused under one word, and the response to each differs:

    the data is wrong          -> cleaning
    the population moved       -> drift, and possibly fine
    the source changed shape   -> a contract violation

So drift is reported with an attribution, never as a bare boolean. And a single
metric is never enough: PSI, KS and Jensen-Shannon disagree about different
distributions, which is exactly why more than one is computed.

One addition beyond the usual: **cleaning drift**. If the *errors* needing
repair change over time, the problem is upstream, and no amount of local
cleaning will fix it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from ..detectors.base import is_missing, to_number

if TYPE_CHECKING:  # pragma: no cover
    from ..scan import ScanResult

__all__ = [
    "DriftSeverity",
    "ColumnDrift",
    "DriftReport",
    "compare",
    "cleaning_drift",
    "psi",
    "ks_statistic",
    "jensen_shannon",
]


class DriftSeverity(Enum):
    """How far a distribution has moved, in bands rather than a raw statistic.

    A PSI of 0.11 and one of 0.09 are not different findings, and reporting
    them as different numbers invites a threshold argument instead of a
    decision. The bands follow the conventional PSI reading.
    """

    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


def _bin_edges(reference: np.ndarray, bins: int) -> np.ndarray:
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(reference, quantiles))
    if len(edges) < 2:
        edges = np.array([reference.min() - 1e-9, reference.max() + 1e-9])
    edges[0], edges[-1] = -np.inf, np.inf
    return edges


def _histogram(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    counts, _ = np.histogram(values, bins=edges)
    total = counts.sum()
    return counts / total if total else counts.astype(float)


def psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """Population Stability Index.

    Note that PSI has no single canonical definition in the literature, and the
    familiar 0.1 / 0.25 thresholds are industry convention rather than a
    statistical result. It is reported alongside tests that do have one.
    """
    if len(reference) == 0 or len(current) == 0:
        return 0.0
    edges = _bin_edges(reference, bins)
    # A zero bin makes the log term infinite, so both sides get a small floor.
    ref = np.clip(_histogram(reference, edges), 1e-6, None)
    cur = np.clip(_histogram(current, edges), 1e-6, None)
    return float(np.sum((cur - ref) * np.log(cur / ref)))


def ks_statistic(reference: np.ndarray, current: np.ndarray) -> float:
    """Kolmogorov-Smirnov statistic: the largest gap between the two ECDFs."""
    if len(reference) == 0 or len(current) == 0:
        return 0.0
    grid = np.sort(np.concatenate([reference, current]))
    ref_cdf = np.searchsorted(np.sort(reference), grid, side="right") / len(reference)
    cur_cdf = np.searchsorted(np.sort(current), grid, side="right") / len(current)
    return float(np.max(np.abs(ref_cdf - cur_cdf)))


def jensen_shannon(reference: dict[str, float], current: dict[str, float]) -> float:
    """Jensen-Shannon divergence between two category distributions."""
    levels = sorted(set(reference) | set(current))
    if not levels:
        return 0.0
    p = np.array([reference.get(k, 0.0) for k in levels]) + 1e-12
    q = np.array([current.get(k, 0.0) for k in levels]) + 1e-12
    p, q = p / p.sum(), q / q.sum()
    m = 0.5 * (p + q)

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.sum(a * np.log(a / b)))

    return float(0.5 * kl(p, m) + 0.5 * kl(q, m))


@dataclass(frozen=True)
class ColumnDrift:
    """Drift for one column, across several metrics."""

    column: str
    kind: str
    severity: DriftSeverity
    metrics: dict[str, float]
    detail: str
    new_categories: tuple[str, ...] = ()
    lost_categories: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "kind": self.kind,
            "severity": self.severity.value,
            "metrics": {k: round(v, 5) for k, v in self.metrics.items()},
            "detail": self.detail,
            "new_categories": list(self.new_categories),
            "lost_categories": list(self.lost_categories),
        }


@dataclass
class DriftReport:
    """Drift across a dataset, with schema changes reported separately."""

    columns: list[ColumnDrift] = field(default_factory=list)
    added_columns: tuple[str, ...] = ()
    removed_columns: tuple[str, ...] = ()
    reference_rows: int = 0
    current_rows: int = 0

    @property
    def severity(self) -> DriftSeverity:
        order = list(DriftSeverity)
        if self.added_columns or self.removed_columns:
            return DriftSeverity.CRITICAL
        return max((c.severity for c in self.columns), key=order.index, default=DriftSeverity.NONE)

    @property
    def drifted(self) -> list[ColumnDrift]:
        return [c for c in self.columns if c.severity is not DriftSeverity.NONE]

    def contributors(self) -> list[tuple[str, float]]:
        """Which columns account for the drift, largest first.

        "Drift detected: True" is not actionable. A ranked attribution is.
        """
        weights = [
            (c.column, max(c.metrics.get("psi", 0.0), c.metrics.get("jensen_shannon", 0.0)))
            for c in self.drifted
        ]
        total = sum(w for _, w in weights)
        if total == 0:
            return []
        return sorted(
            ((name, weight / total) for name, weight in weights),
            key=lambda kv: -kv[1],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "severity": self.severity.value,
            "reference_rows": self.reference_rows,
            "current_rows": self.current_rows,
            "schema": {
                "added": list(self.added_columns),
                "removed": list(self.removed_columns),
            },
            "columns": [c.to_dict() for c in self.columns],
            "contributors": [
                {"column": name, "share": round(share, 4)} for name, share in self.contributors()
            ],
            "note": (
                "Distribution change is not automatically an error. A genuine "
                "population shift, a data-quality problem and a source change all "
                "look alike here and need different responses."
            ),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def summary(self) -> str:
        lines = [
            f"Drift: {self.severity.value.upper()}",
            f"reference {self.reference_rows} rows, current {self.current_rows} rows",
            "",
        ]
        if self.added_columns:
            lines.append(f"  schema: columns added {list(self.added_columns)}")
        if self.removed_columns:
            lines.append(f"  schema: columns removed {list(self.removed_columns)}")
        for column in sorted(self.columns, key=lambda c: -max(c.metrics.values(), default=0)):
            if column.severity is DriftSeverity.NONE:
                continue
            metrics = " ".join(f"{k}={v:.3f}" for k, v in column.metrics.items())
            lines.append(f"  {column.column:22s} {column.severity.value:9s} {metrics}")
            lines.append(f"      {column.detail}")
        if self.contributors():
            lines += ["", "Primary contributors:"]
            for name, share in self.contributors()[:5]:
                lines.append(f"  {name:22s} {share:.0%}")
        if not self.drifted and not self.added_columns and not self.removed_columns:
            lines.append("  No column moved beyond its threshold.")
        return "\n".join(lines)


def _severity(psi_value: float, ks_value: float) -> DriftSeverity:
    if psi_value >= 0.5 or ks_value >= 0.4:
        return DriftSeverity.CRITICAL
    if psi_value >= 0.25 or ks_value >= 0.25:
        return DriftSeverity.SEVERE
    if psi_value >= 0.1 or ks_value >= 0.15:
        return DriftSeverity.MODERATE
    if psi_value >= 0.05 or ks_value >= 0.1:
        return DriftSeverity.MINOR
    return DriftSeverity.NONE


def compare(reference: pd.DataFrame, current: pd.DataFrame) -> DriftReport:
    """Compare a new batch against a reference dataset."""
    report = DriftReport(
        added_columns=tuple(c for c in current.columns if c not in reference.columns),
        removed_columns=tuple(c for c in reference.columns if c not in current.columns),
        reference_rows=len(reference),
        current_rows=len(current),
    )

    for column in reference.columns:
        if column not in current.columns:
            continue

        ref_numeric = reference[column].map(to_number).dropna()
        cur_numeric = current[column].map(to_number).dropna()
        numeric_share = len(ref_numeric) / max(reference[column].notna().sum(), 1)

        if numeric_share > 0.9 and len(ref_numeric) > 5 and len(cur_numeric) > 5:
            report.columns.append(_numeric_drift(column, ref_numeric, cur_numeric))
        else:
            report.columns.append(_categorical_drift(column, reference[column], current[column]))

        missing_change = _missingness_drift(column, reference[column], current[column])
        if missing_change is not None:
            report.columns.append(missing_change)

    return report


def _numeric_drift(column: str, reference: pd.Series, current: pd.Series) -> ColumnDrift:
    ref, cur = reference.to_numpy(), current.to_numpy()
    metrics = {
        "psi": psi(ref, cur),
        "ks": ks_statistic(ref, cur),
        "mean_shift": float(abs(cur.mean() - ref.mean()) / (abs(ref.mean()) or 1.0)),
    }
    severity = _severity(metrics["psi"], metrics["ks"])
    return ColumnDrift(
        column=column,
        kind="numeric",
        severity=severity,
        metrics=metrics,
        detail=(
            f"mean {ref.mean():.4g} -> {cur.mean():.4g}, sd {ref.std():.4g} -> {cur.std():.4g}"
        ),
    )


def _categorical_drift(column: str, reference: pd.Series, current: pd.Series) -> ColumnDrift:
    ref_counts: dict[str, float] = {
        str(k): float(v)
        for k, v in reference.dropna().astype(str).value_counts(normalize=True).items()
    }
    cur_counts: dict[str, float] = {
        str(k): float(v)
        for k, v in current.dropna().astype(str).value_counts(normalize=True).items()
    }
    divergence = jensen_shannon(ref_counts, cur_counts)

    new = tuple(sorted(set(cur_counts) - set(ref_counts)))
    lost = tuple(sorted(set(ref_counts) - set(cur_counts)))

    # A category that never appeared before is a stronger signal than a shift in
    # the proportions of familiar ones.
    if new or divergence >= 0.1:
        severity = DriftSeverity.SEVERE
    elif divergence >= 0.05:
        severity = DriftSeverity.MODERATE
    elif divergence >= 0.01:
        severity = DriftSeverity.MINOR
    else:
        severity = DriftSeverity.NONE

    detail = f"{len(ref_counts)} -> {len(cur_counts)} categories"
    if new:
        detail += f"; unseen: {list(new)[:5]}"
    if lost:
        detail += f"; disappeared: {list(lost)[:5]}"

    return ColumnDrift(
        column=column,
        kind="categorical",
        severity=severity,
        metrics={"jensen_shannon": divergence},
        detail=detail,
        new_categories=new,
        lost_categories=lost,
    )


def _missingness_drift(column: str, reference: pd.Series, current: pd.Series) -> ColumnDrift | None:
    ref_rate = sum(1 for v in reference if is_missing(v)) / max(len(reference), 1)
    cur_rate = sum(1 for v in current if is_missing(v)) / max(len(current), 1)
    change = abs(cur_rate - ref_rate)
    if change < 0.05:
        return None

    severity = (
        DriftSeverity.SEVERE
        if change > 0.25
        else DriftSeverity.MODERATE
        if change > 0.1
        else DriftSeverity.MINOR
    )
    return ColumnDrift(
        column=f"{column} (missingness)",
        kind="missingness",
        severity=severity,
        metrics={"missing_rate_change": change},
        detail=f"missing {ref_rate:.1%} -> {cur_rate:.1%}",
    )


def cleaning_drift(reference: ScanResult, current: ScanResult) -> dict[str, Any]:
    """Compare the *problems* between two batches, not the values.

    If each batch needs different repairs, the cause is upstream. That is a
    different finding from the data having changed, and it is the one that
    tells you to go and talk to the source system.
    """
    ref_counts = {i.id: i.affected_row_count for i in reference.issues}
    cur_counts = {i.id: i.affected_row_count for i in current.issues}

    appeared = sorted(set(cur_counts) - set(ref_counts))
    resolved = sorted(set(ref_counts) - set(cur_counts))
    worsened = sorted(
        issue_id
        for issue_id in set(ref_counts) & set(cur_counts)
        if cur_counts[issue_id] > ref_counts[issue_id] * 1.5
    )

    shared = set(ref_counts) & set(cur_counts)
    stability = len(shared) / max(len(set(ref_counts) | set(cur_counts)), 1)

    verdict = "stable"
    if appeared and stability < 0.7:
        verdict = "upstream_change_likely"
    elif worsened:
        verdict = "degrading"
    elif resolved and not appeared:
        verdict = "improving"

    return {
        "schema_version": 1,
        "stability_score": round(stability * 100, 1),
        "verdict": verdict,
        "new_problems": appeared,
        "resolved_problems": resolved,
        "worsened_problems": worsened,
        "interpretation": {
            "stable": "the same problems recur; local cleaning rules should keep working",
            "improving": "fewer problems than the reference batch",
            "degrading": "existing problems affect more rows than before",
            "upstream_change_likely": (
                "problems appeared that the reference batch did not have. This "
                "usually means the source changed, and no local cleaning rule will "
                "fix the cause."
            ),
        }[verdict],
    }
