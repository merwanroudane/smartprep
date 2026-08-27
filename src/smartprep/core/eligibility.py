"""Auto-fix eligibility policy (AD-005, AD-006, AD-007).

The rule this module exists to enforce:

    Confidence that a problem is real does not authorise a repair.
    Only confidence in a *specific* repair does, and even then only after
    risk demotion.

The ladder is applied to ``repair_confidence``. ``detection_confidence`` never
reaches this module.
"""

from __future__ import annotations

from dataclasses import dataclass

from .enums import (
    DomainSensitivity,
    InformationLossRisk,
    RepairClass,
    Reversibility,
    Severity,
    StatisticalImpact,
)

__all__ = ["ConfidenceLadder", "RiskProfile", "DEFAULT_LADDER", "classify", "band_for"]


@dataclass(frozen=True)
class ConfidenceLadder:
    """Thresholds for AD-005. Values are configurable; ordering is not."""

    safe_auto_fix: float = 0.98
    auto_fix_with_log: float = 0.90
    review_recommended: float = 0.75
    user_confirmation_required: float = 0.60

    def __post_init__(self) -> None:
        rungs = (
            self.safe_auto_fix,
            self.auto_fix_with_log,
            self.review_recommended,
            self.user_confirmation_required,
        )
        if not all(a > b for a, b in zip(rungs, rungs[1:], strict=False)):
            raise ValueError(
                "Confidence ladder thresholds must be strictly descending; "
                f"got {rungs}. The band ordering in AD-005 is not configurable."
            )


DEFAULT_LADDER = ConfidenceLadder()


def band_for(repair_confidence: float, ladder: ConfidenceLadder = DEFAULT_LADDER) -> RepairClass:
    """Map a *repair* confidence to its unmodified band (AD-005).

    This is the starting point only. Never use it as the final decision -- call
    :func:`classify` so that risk demotion is applied.
    """
    if not 0.0 <= repair_confidence <= 1.0:
        raise ValueError(f"repair_confidence must be in [0, 1], got {repair_confidence}")
    if repair_confidence >= ladder.safe_auto_fix:
        return RepairClass.SAFE_AUTO_FIX
    if repair_confidence >= ladder.auto_fix_with_log:
        return RepairClass.AUTO_FIX_WITH_LOG
    if repair_confidence >= ladder.review_recommended:
        return RepairClass.REVIEW_RECOMMENDED
    if repair_confidence >= ladder.user_confirmation_required:
        return RepairClass.USER_CONFIRMATION_REQUIRED
    return RepairClass.AMBIGUOUS


@dataclass(frozen=True)
class RiskProfile:
    """The non-confidence half of the eligibility decision (AD-007)."""

    severity: Severity = Severity.NOTICE
    reversibility: Reversibility = Reversibility.REVERSIBLE
    information_loss_risk: InformationLossRisk = InformationLossRisk.NONE
    domain_sensitivity: DomainSensitivity = DomainSensitivity.NONE
    statistical_impact: StatisticalImpact = StatisticalImpact.NONE
    has_treatment_candidate: bool = True
    candidates_conflict: bool = False


def classify(
    repair_confidence: float,
    risk: RiskProfile,
    ladder: ConfidenceLadder = DEFAULT_LADDER,
) -> tuple[RepairClass, list[str]]:
    """Resolve a repair to its final :class:`RepairClass`.

    Two stages. First **routing**: a blocking severity, an absent treatment or a
    dependency on business knowledge each name *who* must decide, and
    short-circuit. These are not points on the autonomy ladder -- placing them
    there would let a low-confidence repair hide the fact that a domain expert
    could settle it immediately. Their precedence is fixed, so the outcome stays
    order-independent.

    Second, the **autonomy ladder** from ``repair_confidence`` (AD-005), lowered
    by risk ceilings. A ceiling may only lower the class, never raise it.

    Returns the class and the human-readable reasons, which feed the
    ``what auto mode did not do`` section of the report.
    """
    # Routing outcomes are decided first and are not points on the autonomy
    # ladder -- they say *who* must decide, not *how confident* we are. Forcing
    # them into the ladder would let a low-confidence repair mask the fact that
    # a domain expert could resolve it immediately. Their precedence is fixed,
    # so the result stays order-independent.
    if risk.severity is Severity.BLOCKING:
        return RepairClass.DO_NOT_TOUCH, [
            "severity is BLOCKING; repairing could destroy valid information"
        ]
    if not risk.has_treatment_candidate:
        return RepairClass.AMBIGUOUS, [
            "no treatment candidate could be constructed; the correct value is "
            "not inferable from the data"
        ]
    if risk.domain_sensitivity is DomainSensitivity.REQUIRES_DOMAIN_RULE:
        return RepairClass.DOMAIN_RULE_REQUIRED, [
            "resolution depends on a business rule the dataset does not contain"
        ]

    cls = band_for(repair_confidence, ladder)
    reasons: list[str] = []
    if not cls.is_autonomous:
        reasons.append(
            f"repair confidence {repair_confidence:.0%} is below the "
            f"{ladder.auto_fix_with_log:.0%} threshold for autonomous repair"
        )

    def demote(ceiling: RepairClass, why: str) -> None:
        nonlocal cls
        if cls > ceiling:
            cls = ceiling
            reasons.append(why)

    # Ceilings: each may only lower the class.
    if risk.reversibility is Reversibility.IRREVERSIBLE:
        demote(
            RepairClass.USER_CONFIRMATION_REQUIRED,
            "operation is irreversible; it can never be applied autonomously "
            "regardless of confidence",
        )
    if risk.information_loss_risk is InformationLossRisk.HIGH:
        demote(
            RepairClass.USER_CONFIRMATION_REQUIRED,
            "high risk of information loss",
        )
    if risk.candidates_conflict:
        demote(
            RepairClass.USER_CONFIRMATION_REQUIRED,
            "candidate treatments disagree; evidence is not decisive",
        )
    if risk.statistical_impact is StatisticalImpact.MATERIAL:
        demote(
            RepairClass.REVIEW_RECOMMENDED,
            "repair would materially change the distribution or relationships",
        )

    return cls, reasons
