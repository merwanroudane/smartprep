"""Unit tests for the safety policy itself (AD-005, AD-006, AD-007)."""

from __future__ import annotations

import pytest

from smartprep.core.eligibility import ConfidenceLadder, RiskProfile, band_for, classify
from smartprep.core.enums import (
    DomainSensitivity,
    InformationLossRisk,
    RepairClass,
    Reversibility,
    Severity,
    StatisticalImpact,
)


@pytest.mark.parametrize(
    "confidence, expected",
    [
        (1.00, RepairClass.SAFE_AUTO_FIX),
        (0.98, RepairClass.SAFE_AUTO_FIX),
        (0.979, RepairClass.AUTO_FIX_WITH_LOG),
        (0.90, RepairClass.AUTO_FIX_WITH_LOG),
        (0.899, RepairClass.REVIEW_RECOMMENDED),
        (0.75, RepairClass.REVIEW_RECOMMENDED),
        (0.749, RepairClass.USER_CONFIRMATION_REQUIRED),
        (0.60, RepairClass.USER_CONFIRMATION_REQUIRED),
        (0.599, RepairClass.AMBIGUOUS),
        (0.00, RepairClass.AMBIGUOUS),
    ],
)
def test_single_confidence_ladder(confidence: float, expected: RepairClass) -> None:
    assert band_for(confidence) is expected


def test_ladder_ordering_cannot_be_inverted() -> None:
    with pytest.raises(ValueError, match="strictly descending"):
        ConfidenceLadder(safe_auto_fix=0.5, auto_fix_with_log=0.9)


def test_high_detection_confidence_does_not_authorise_deletion() -> None:
    """AD-006: certainty that a row is anomalous is not certainty it should go."""
    outcome, reasons = classify(
        0.30,  # repair confidence -- would deleting be right?
        RiskProfile(
            reversibility=Reversibility.IRREVERSIBLE,
            information_loss_risk=InformationLossRisk.HIGH,
        ),
    )
    assert outcome is RepairClass.AMBIGUOUS
    assert not outcome.is_autonomous
    # The report must be able to say why, even when confidence alone decided it.
    assert any("below the" in r for r in reasons)


def test_irreversible_operations_can_never_be_safe_auto_fix() -> None:
    outcome, reasons = classify(1.0, RiskProfile(reversibility=Reversibility.IRREVERSIBLE))
    assert outcome is RepairClass.USER_CONFIRMATION_REQUIRED
    assert any("irreversible" in r for r in reasons)


def test_blocking_severity_forces_do_not_touch() -> None:
    outcome, _ = classify(1.0, RiskProfile(severity=Severity.BLOCKING))
    assert outcome is RepairClass.DO_NOT_TOUCH


def test_domain_rule_requirement_overrides_confidence() -> None:
    outcome, _ = classify(
        0.99, RiskProfile(domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE)
    )
    assert outcome is RepairClass.DOMAIN_RULE_REQUIRED


def test_material_statistical_impact_caps_at_review() -> None:
    outcome, _ = classify(0.99, RiskProfile(statistical_impact=StatisticalImpact.MATERIAL))
    assert outcome is RepairClass.REVIEW_RECOMMENDED


def test_absent_treatment_forces_ambiguous() -> None:
    outcome, _ = classify(1.0, RiskProfile(has_treatment_candidate=False))
    assert outcome is RepairClass.AMBIGUOUS


def test_demotion_is_monotone_and_order_independent() -> None:
    """Stacking risks may only lower the class, never raise it."""
    clean = classify(0.99, RiskProfile())[0]
    risky = classify(
        0.99,
        RiskProfile(
            reversibility=Reversibility.IRREVERSIBLE,
            information_loss_risk=InformationLossRisk.HIGH,
            statistical_impact=StatisticalImpact.MATERIAL,
        ),
    )[0]
    assert clean is RepairClass.SAFE_AUTO_FIX
    assert risky < clean


def test_demotion_never_promotes_a_low_confidence_repair() -> None:
    """No combination of benign risk factors can lift a weak repair."""
    outcome, _ = classify(0.20, RiskProfile(reversibility=Reversibility.REVERSIBLE))
    assert outcome is RepairClass.AMBIGUOUS


def test_conflicting_candidates_require_confirmation() -> None:
    outcome, reasons = classify(0.95, RiskProfile(candidates_conflict=True))
    assert outcome is RepairClass.USER_CONFIRMATION_REQUIRED
    assert any("disagree" in r for r in reasons)


def test_reasons_explain_why_auto_mode_abstained() -> None:
    """The report must be able to say what it did not do, and why."""
    _, reasons = classify(
        0.99,
        RiskProfile(
            reversibility=Reversibility.IRREVERSIBLE,
            information_loss_risk=InformationLossRisk.HIGH,
        ),
    )
    assert reasons and all(isinstance(r, str) and r for r in reasons)
