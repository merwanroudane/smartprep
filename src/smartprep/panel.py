"""Panel-data diagnostics -- what is wrong with an entity-by-time table.

A panel is not a longer cross-section. Estimators that difference within an
entity, or absorb an entity fixed effect, depend on facts about the *shape* of
the table that no ordinary column check would notice:

* a variable that never changes inside an entity is collinear with the fixed
  effect and drops out of the model, silently taking its coefficient with it;
* a variable that barely changes inside an entity is worse, because it stays
  in and returns an estimate nobody can trust;
* duplicated entity-time pairs mean the panel index is not what it claims;
* an unbalanced panel is often perfectly fine and sometimes a survivorship
  filter, and the two are indistinguishable from the counts alone.

So the checks here are about the index and the variation, not the values. As
everywhere else, findings are ordinary
:class:`~smartprep.core.issue.Issue` objects, they route through the same
triage, and **nothing is repaired**: dropping an entity to balance a panel is
a modelling decision, and a library that made it quietly would be choosing a
result on the analyst's behalf.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from .core.enums import (
    DomainSensitivity,
    InformationLossRisk,
    IssueCategory,
    RuleSource,
    Severity,
    StatisticalImpact,
)
from .core.issue import Evidence, Issue, TreatmentCandidate

__all__ = ["PanelReport", "Variation", "panel"]

#: Below this share of total variance, a regressor's within-entity movement is
#: too small to identify a coefficient from, even though the estimator will
#: happily return one.
_WEAK_WITHIN = 0.05


@dataclass(frozen=True)
class Variation:
    """How a column moves within an entity versus between entities.

    The decomposition every panel estimator depends on and few datasets are
    checked for. ``within_share`` near zero means the variable is essentially
    a property of the entity, not an observation about it.
    """

    column: str
    within: float
    between: float
    constant_entities: int
    total_entities: int

    @property
    def within_share(self) -> float:
        total = self.within + self.between
        return self.within / total if total else 0.0

    @property
    def is_constant_within(self) -> bool:
        """True when the column never moves inside any entity."""
        return self.within == 0.0

    @property
    def is_weak_within(self) -> bool:
        return not self.is_constant_within and self.within_share < _WEAK_WITHIN

    def describe(self) -> str:
        if self.is_constant_within:
            return (
                f"{self.column} never changes within an entity -- collinear with "
                "an entity fixed effect"
            )
        return f"{self.column}: {self.within_share:.0%} of variance is within-entity" + (
            f", constant in {self.constant_entities} of {self.total_entities} entities"
            if self.constant_entities
            else ""
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "within": round(self.within, 6),
            "between": round(self.between, 6),
            "within_share": round(self.within_share, 4),
            "constant_within": self.is_constant_within,
            "weak_within": self.is_weak_within,
            "constant_entities": self.constant_entities,
            "total_entities": self.total_entities,
        }


@dataclass
class PanelReport:
    """The shape of a panel, and what that shape permits."""

    entity: str
    time: str
    rows: int
    entities: int = 0
    periods: int = 0
    duplicate_pairs: int = 0
    observations_per_entity: dict[str, int] = field(default_factory=dict)
    variation: list[Variation] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def is_balanced(self) -> bool:
        counts = set(self.observations_per_entity.values())
        return len(counts) <= 1

    @property
    def completeness(self) -> float:
        """Observed cells as a share of a fully balanced panel."""
        cells = self.entities * self.periods
        return (self.rows - self.duplicate_pairs) / cells if cells else 0.0

    @property
    def constant_within(self) -> list[Variation]:
        return [v for v in self.variation if v.is_constant_within]

    @property
    def weak_within(self) -> list[Variation]:
        return [v for v in self.variation if v.is_weak_within]

    def summary(self) -> str:
        shape = "balanced" if self.is_balanced else "unbalanced"
        lines = [
            f"panel {self.entity} x {self.time}: {self.entities:,} entities, "
            f"{self.periods:,} periods, {self.rows:,} rows ({shape})",
            f"  completeness {self.completeness:.0%} of a full grid",
        ]
        if self.duplicate_pairs:
            lines.append(f"  {self.duplicate_pairs:,} duplicate entity-time pairs")
        if not self.is_balanced:
            counts = self.observations_per_entity.values()
            lines.append(f"  observations per entity: {min(counts)} to {max(counts)}")
        for variation in self.constant_within:
            lines.append(f"  {variation.describe()}")
        for variation in self.weak_within:
            lines.append(f"  {variation.describe()}")
        return "\n".join(lines)

    def completeness_matrix(self, limit: int = 40) -> pd.DataFrame:
        """Which entity-period cells exist. The panel's shape, as a table."""
        return self._matrix.iloc[:limit] if self._matrix is not None else pd.DataFrame()

    _matrix: pd.DataFrame | None = None

    def charts(self) -> list[Any]:
        from .viz.spec import ChartSpec, Encoding, Mark

        out: list[ChartSpec] = []
        if self.observations_per_entity:
            ordered = sorted(
                self.observations_per_entity.items(), key=lambda kv: kv[1], reverse=True
            )[:40]
            out.append(
                ChartSpec(
                    mark=Mark.HORIZONTAL_BAR,
                    data=[{"label": str(k), "value": float(v)} for k, v in ordered],
                    x=Encoding("value"),
                    y=Encoding("label", "nominal"),
                    title=f"Observations per {self.entity}",
                    x_label="periods observed",
                    rationale=(
                        "An unbalanced panel is often fine and sometimes a "
                        "survivorship filter; the counts are where the difference "
                        "shows."
                    ),
                )
            )
        if self.variation:
            out.append(
                ChartSpec(
                    mark=Mark.HORIZONTAL_BAR,
                    data=[
                        {"label": v.column, "value": round(v.within_share, 4)}
                        for v in self.variation
                    ],
                    x=Encoding("value"),
                    y=Encoding("label", "nominal"),
                    title="Within-entity share of variance",
                    x_label="share",
                    rules=[("x", _WEAK_WITHIN, "weak")],
                    rationale=(
                        "A regressor with almost no within-entity movement cannot "
                        "identify a coefficient, though the estimator will return "
                        "one anyway."
                    ),
                )
            )
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "time": self.time,
            "rows": self.rows,
            "entities": self.entities,
            "periods": self.periods,
            "balanced": self.is_balanced,
            "completeness": round(self.completeness, 4),
            "duplicate_pairs": self.duplicate_pairs,
            "variation": [v.to_dict() for v in self.variation],
            "issues": [i.id for i in self.issues],
        }


def _variation_of(frame: pd.DataFrame, entity: str, column: str) -> Variation | None:
    """Decompose a column's variance into within-entity and between-entity.

    The standard decomposition: between is the variance of the entity means,
    within is the mean variance around them. Reported as a share because the
    absolute numbers depend on units and the share does not.
    """
    values = pd.to_numeric(frame[column], errors="coerce")
    if values.notna().sum() < 3:
        return None

    grouped = values.groupby(frame[entity], dropna=True)
    entity_means = grouped.mean()
    if len(entity_means.dropna()) < 2:
        return None

    between = float(entity_means.var(ddof=0))
    deviations = values - frame[entity].map(entity_means)
    within = float(deviations.var(ddof=0))

    spans = grouped.nunique(dropna=True)
    return Variation(
        column=column,
        within=0.0 if pd.isna(within) else within,
        between=0.0 if pd.isna(between) else between,
        constant_entities=int((spans <= 1).sum()),
        total_entities=int(len(spans)),
    )


def panel(
    frame: pd.DataFrame,
    entity: str,
    time: str,
    *,
    columns: tuple[str, ...] | None = None,
) -> PanelReport:
    """Diagnose the shape of a panel. Never modifies ``frame``.

    Parameters
    ----------
    entity, time:
        The two keys that together should identify a row.
    columns:
        Which columns to decompose. Defaults to every numeric column that is
        not one of the keys.
    """
    for name in (entity, time):
        if name not in frame.columns:
            raise KeyError(f"no column {name!r} in this frame")

    report = PanelReport(entity=entity, time=time, rows=len(frame))
    keys = frame[[entity, time]].astype(str)

    report.entities = int(frame[entity].nunique(dropna=True))
    report.periods = int(frame[time].nunique(dropna=True))
    report.duplicate_pairs = int(keys.duplicated().sum())
    report.observations_per_entity = {
        str(k): int(v) for k, v in frame.groupby(entity, dropna=True).size().items()
    }

    watched = columns or tuple(
        c
        for c in frame.columns
        if c not in (entity, time) and pd.api.types.is_numeric_dtype(frame[c])
    )
    report.variation = [v for c in watched if (v := _variation_of(frame, entity, c)) is not None]

    try:
        report._matrix = (
            frame.assign(_present=1)
            .pivot_table(index=entity, columns=time, values="_present", aggfunc="size")
            .notna()
        )
    except (ValueError, KeyError):  # pragma: no cover - exotic key types
        report._matrix = None

    report.issues = _issues_for(report, keys)
    return report


def _issues_for(report: PanelReport, keys: pd.DataFrame) -> list[Issue]:
    issues: list[Issue] = []

    if report.duplicate_pairs:
        positions = tuple(int(p) for p in keys.duplicated().to_numpy().nonzero()[0])
        issues.append(
            Issue(
                id=f"PANEL-DUPLICATE-{report.entity}-{report.time}",
                category=IssueCategory.EXACT_DUPLICATE,
                severity=Severity.BLOCKING,
                detection_confidence=1.0,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=(report.entity, report.time),
                evidence=Evidence(
                    summary=(
                        f"{report.duplicate_pairs:,} rows repeat an "
                        f"{report.entity}-{report.time} pair, so these two columns "
                        "do not identify a row and the panel index is not what it "
                        "claims to be"
                    ),
                    affected_rows=positions,
                    details={"duplicate_pairs": report.duplicate_pairs},
                ),
                detector="panel",
                treatments=(
                    TreatmentCandidate(
                        name="review_panel_index",
                        description=(
                            "Decide whether a third key is missing, or whether "
                            "these are genuine repeated observations"
                        ),
                        repair_confidence=0.0,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                    ),
                ),
                notes="an estimator given this index will silently average the pair",
            )
        )

    if not report.is_balanced and report.observations_per_entity:
        counts = report.observations_per_entity.values()
        issues.append(
            Issue(
                id=f"PANEL-UNBALANCED-{report.entity}",
                category=IssueCategory.MISSINGNESS,
                severity=Severity.NOTICE,
                detection_confidence=1.0,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=(report.entity, report.time),
                evidence=Evidence(
                    summary=(
                        f"the panel is unbalanced: {min(counts)} to {max(counts)} "
                        f"observations per {report.entity}, "
                        f"{report.completeness:.0%} of a full grid"
                    ),
                    details={
                        "min": min(counts),
                        "max": max(counts),
                        "completeness": round(report.completeness, 4),
                    },
                ),
                detector="panel",
                treatments=(
                    TreatmentCandidate(
                        name="review_panel_balance",
                        description=(
                            "Decide whether entities are missing periods or simply "
                            "did not exist in them"
                        ),
                        repair_confidence=0.0,
                        information_loss_risk=InformationLossRisk.HIGH,
                        statistical_impact=StatisticalImpact.MATERIAL,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                    ),
                ),
                notes=(
                    "an unbalanced panel is usually fine and occasionally a "
                    "survivorship filter; the counts alone cannot tell you which"
                ),
            )
        )

    for variation in report.constant_within:
        issues.append(
            Issue(
                id=f"PANEL-CONSTANT-WITHIN-{variation.column}",
                category=IssueCategory.UNUSUAL_PATTERN,
                severity=Severity.HIGH_WARNING,
                detection_confidence=1.0,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=(variation.column,),
                evidence=Evidence(
                    summary=(
                        f"{variation.column} never changes within an entity, so it "
                        "is collinear with an entity fixed effect and will be "
                        "dropped by any within estimator"
                    ),
                    details=variation.to_dict(),
                ),
                detector="panel",
                notes=("not an error in the data -- a fact about what this variable can identify"),
            )
        )

    for variation in report.weak_within:
        issues.append(
            Issue(
                id=f"PANEL-WEAK-WITHIN-{variation.column}",
                category=IssueCategory.UNUSUAL_PATTERN,
                severity=Severity.WARNING,
                detection_confidence=0.9,
                rule_source=RuleSource.STATISTICAL_RULE,
                columns=(variation.column,),
                evidence=Evidence(
                    summary=(
                        f"only {variation.within_share:.1%} of {variation.column}'s "
                        "variance is within-entity; a within estimator will return "
                        "a coefficient, and it will be identified by very little"
                    ),
                    details=variation.to_dict(),
                ),
                detector="panel",
                notes=(
                    "worse than no variation at all: no variation drops the term "
                    "visibly, weak variation keeps it and looks like an answer"
                ),
            )
        )

    return issues
