"""The Issue model -- the unit of currency between every layer of SmartPrep.

Detectors emit :class:`Issue`. Triage classifies it. Repair consumes it. Reports
render it. Guided mode turns it into a question. Nothing else crosses layers.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any

from .eligibility import DEFAULT_LADDER, ConfidenceLadder, RiskProfile, classify
from .enums import (
    DomainSensitivity,
    InformationLossRisk,
    IssueCategory,
    RepairClass,
    Reversibility,
    RuleSource,
    Severity,
    StatisticalImpact,
)
from .rows import RowSet

__all__ = ["Evidence", "TreatmentCandidate", "Issue"]


def _jsonable(value: Any) -> Any:
    """Coerce a value into something ``json.dumps`` accepts."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


@dataclass(frozen=True)
class Evidence:
    """Why the detector believes what it believes.

    Evidence is preserved verbatim so a reviewer can disagree with the library.

    ``affected_rows`` holds *positions*. ``index_labels`` holds the matching
    index labels and is attached by ``scan()`` -- see :mod:`smartprep.core.rows`
    for why both are required.
    """

    summary: str
    affected_rows: tuple[int, ...] = ()
    sample_values: tuple[Any, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)
    index_labels: tuple[Any, ...] = ()

    @property
    def affected_row_count(self) -> int:
        return len(self.affected_rows)

    @property
    def rows(self) -> RowSet:
        """Positions and labels together, so callers cannot confuse the two."""
        return RowSet(self.affected_rows, self.index_labels)

    def with_index(self, index: Any) -> Evidence:
        """Return a copy carrying the index label for every affected position."""
        resolved = self.rows.with_index(index)
        return dataclasses.replace(
            self,
            affected_rows=resolved.positions,
            index_labels=resolved.labels,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "rows": self.rows.as_dict(),
            "sample_values": [_jsonable(v) for v in self.sample_values],
            "details": _jsonable(self.details),
        }


@dataclass(frozen=True)
class TreatmentCandidate:
    """One possible repair, with its own confidence and risk (AD-006).

    ``repair_confidence`` answers "is *this fix* correct?" -- a different and
    usually much lower number than the detector's confidence that a problem
    exists.
    """

    name: str
    description: str
    repair_confidence: float
    reversibility: Reversibility = Reversibility.REVERSIBLE
    information_loss_risk: InformationLossRisk = InformationLossRisk.NONE
    statistical_impact: StatisticalImpact = StatisticalImpact.NONE
    domain_sensitivity: DomainSensitivity = DomainSensitivity.NONE
    parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.repair_confidence <= 1.0:
            raise ValueError(
                f"repair_confidence for {self.name!r} must be in [0, 1], "
                f"got {self.repair_confidence}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "repair_confidence": self.repair_confidence,
            "reversibility": self.reversibility.value,
            "information_loss_risk": self.information_loss_risk.value,
            "statistical_impact": self.statistical_impact.value,
            "domain_sensitivity": self.domain_sensitivity.value,
            "parameters": _jsonable(self.parameters),
        }


@dataclass
class Issue:
    """A single detected data-quality finding."""

    id: str
    category: IssueCategory
    severity: Severity
    detection_confidence: float
    rule_source: RuleSource
    evidence: Evidence
    columns: tuple[str, ...] = ()
    treatments: tuple[TreatmentCandidate, ...] = ()
    recommended: str | None = None
    notes: str = ""
    detector: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.detection_confidence <= 1.0:
            raise ValueError(
                f"detection_confidence for {self.id!r} must be in [0, 1], "
                f"got {self.detection_confidence}"
            )
        if self.recommended is not None and self.recommended not in {
            t.name for t in self.treatments
        }:
            raise ValueError(
                f"issue {self.id!r} recommends {self.recommended!r}, which is not "
                "among its treatment candidates"
            )

    @property
    def affected_row_count(self) -> int:
        return self.evidence.affected_row_count

    @property
    def rows(self) -> RowSet:
        return self.evidence.rows

    @property
    def recommended_treatment(self) -> TreatmentCandidate | None:
        if self.recommended is None:
            return self.treatments[0] if self.treatments else None
        return next(t for t in self.treatments if t.name == self.recommended)

    def risk_profile(self) -> RiskProfile:
        """Assemble the risk half of the eligibility decision (AD-007)."""
        best = self.recommended_treatment
        if best is None:
            return RiskProfile(severity=self.severity, has_treatment_candidate=False)

        # Candidates conflict when two of them are similarly confident but
        # propose materially different outcomes -- the evidence is not decisive.
        conflict = False
        if len(self.treatments) > 1:
            ranked = sorted(self.treatments, key=lambda t: t.repair_confidence, reverse=True)
            conflict = (ranked[0].repair_confidence - ranked[1].repair_confidence) < 0.10

        return RiskProfile(
            severity=self.severity,
            reversibility=best.reversibility,
            information_loss_risk=best.information_loss_risk,
            domain_sensitivity=best.domain_sensitivity,
            statistical_impact=best.statistical_impact,
            has_treatment_candidate=True,
            candidates_conflict=conflict,
        )

    def triage(self, ladder: ConfidenceLadder = DEFAULT_LADDER) -> tuple[RepairClass, list[str]]:
        """Final repair class plus the reasons auto mode may not act (AD-007)."""
        best = self.recommended_treatment
        confidence = best.repair_confidence if best else 0.0
        return classify(confidence, self.risk_profile(), ladder)

    @property
    def repair_class(self) -> RepairClass:
        return self.triage()[0]

    @property
    def abstention_reasons(self) -> list[str]:
        """Why automatic mode will not act on this finding."""
        cls, reasons = self.triage()
        return [] if cls.is_autonomous else reasons

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible structure.

        ``schema_version`` is included so stored results remain readable after
        the model evolves.
        """
        repair_class, reasons = self.triage()
        return {
            "schema_version": 1,
            "id": self.id,
            "detector": self.detector,
            "category": self.category.value,
            "severity": self.severity.name,
            "detection_confidence": self.detection_confidence,
            "rule_source": self.rule_source.value,
            "columns": list(self.columns),
            "evidence": self.evidence.to_dict(),
            "treatments": [t.to_dict() for t in self.treatments],
            "recommended": self.recommended,
            "repair_class": repair_class.name,
            "abstention_reasons": reasons if not repair_class.is_autonomous else [],
            "notes": self.notes,
        }
