"""Learning validation rules, and refusing to learn the ones data cannot support.

A rule inferred from a sample is a statement about that sample. The moment it
runs against next month's data it becomes a claim about the world, and the
world was not consulted. Most of these tests are about the learner declining
to make that claim.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import smartprep as sp
from smartprep.learning import learn_rules


@pytest.fixture(scope="module")
def sample() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 400
    return pd.DataFrame(
        {
            "id": range(n),
            "amount": rng.normal(100, 15, n).round(2),
            "status": rng.choice(["paid", "pending", "failed"], n, p=[0.6, 0.3, 0.1]),
            "note": [f"free text number {i}" for i in range(n)],
            "almost_closed": ["a"] * (n - 1) + ["b"],
            "skewed": rng.lognormal(3, 1.4, n),
            "signed": rng.normal(0, 10, n),
        }
    )


def _rule(plan: object, kind: str, column: str) -> object | None:
    return next((r for r in plan.rules if r.kind == kind and r.column == column), None)


def test_learning_never_touches_the_data(sample: pd.DataFrame) -> None:
    before = sample.copy(deep=True)
    learn_rules(sample)
    pd.testing.assert_frame_equal(sample, before)


def test_a_closed_vocabulary_is_learned(sample: pd.DataFrame) -> None:
    rule = _rule(learn_rules(sample), "isin", "status")
    assert rule is not None
    assert set(rule.parameters["allowed"]) == {"paid", "pending", "failed"}


def test_a_level_seen_once_does_not_close_the_set(sample: pd.DataFrame) -> None:
    """It may be the first of many, or a typo. Closing the set on that
    evidence rejects whichever it turns out to be."""
    plan = learn_rules(sample)
    assert _rule(plan, "isin", "almost_closed") is None
    assert any(c == "almost_closed" for c, _ in plan.abstained)


def test_free_text_gets_no_rule(sample: pd.DataFrame) -> None:
    plan = learn_rules(sample)
    reasons = dict(plan.abstained)
    assert "note" in reasons
    assert "no shape worth asserting" in reasons["note"]


def test_bounds_are_widened_beyond_what_was_observed(sample: pd.DataFrame) -> None:
    """A bound at exactly the observed minimum rejects the first legitimately
    smaller value -- a false alarm on day one, and the reason validation gets
    switched off."""
    rule = _rule(learn_rules(sample), "between", "amount")
    assert rule is not None
    assert rule.parameters["minimum"] < sample["amount"].min()
    assert rule.parameters["maximum"] > sample["amount"].max()


def test_widening_does_not_invent_a_negative_bound(sample: pd.DataFrame) -> None:
    """A quantity that has never been negative gets a floor of zero, not of
    minus a hundred. A bound admitting impossible values is decoration."""
    for column in ("id", "skewed"):
        rule = _rule(learn_rules(sample), "between", column)
        assert rule is not None
        assert rule.parameters["minimum"] == 0.0
        assert "floored at zero" in rule.caveat


def test_a_genuinely_signed_column_keeps_its_negative_bound(
    sample: pd.DataFrame,
) -> None:
    """The negative case: flooring a column that really does go negative would
    reject valid data."""
    rule = _rule(learn_rules(sample), "between", "signed")
    assert rule is not None
    assert rule.parameters["minimum"] < 0


def test_a_skewed_column_is_learned_at_lower_confidence(sample: pd.DataFrame) -> None:
    """The upper tail of a skewed column is under-sampled, so a bound learned
    from it will reject the next large legitimate value."""
    skewed = _rule(learn_rules(sample), "between", "skewed")
    symmetric = _rule(learn_rules(sample), "between", "amount")
    assert skewed.confidence < symmetric.confidence
    assert "skewed" in skewed.caveat


def test_a_float_column_is_not_called_a_key(sample: pd.DataFrame) -> None:
    """All-distinct is what floats do. A `unique` rule there passes until the
    first legitimate coincidence and then fails for no reason."""
    plan = learn_rules(sample)
    assert _rule(plan, "unique", "skewed") is None
    assert _rule(plan, "unique", "id") is not None


def test_uniqueness_is_offered_as_evidence_not_proof(sample: pd.DataFrame) -> None:
    rule = _rule(learn_rules(sample), "unique", "id")
    assert rule.confidence < 0.8
    assert "not proof of one" in rule.caveat


def test_completeness_is_only_claimed_when_the_sample_is_unanimous() -> None:
    frame = pd.DataFrame({"whole": range(100), "holey": [None] + list(range(99))})
    plan = learn_rules(frame)
    assert _rule(plan, "not_null", "whole") is not None
    assert _rule(plan, "not_null", "holey") is None


def test_too_few_rows_learns_nothing_and_says_why() -> None:
    """A rule from twenty rows describes twenty rows."""
    plan = learn_rules(pd.DataFrame({"a": range(20)}))
    assert plan.rules == []
    assert any("below the" in reason for _, reason in plan.abstained)


def test_every_rule_carries_its_evidence_and_a_caveat(sample: pd.DataFrame) -> None:
    """A learned rule with no stated basis is indistinguishable from a guess."""
    for rule in learn_rules(sample).rules:
        assert rule.evidence_rows > 0
        assert 0 < rule.confidence <= 1
        assert len(rule.caveat.split()) >= 5


def test_the_sample_caveat_travels_with_the_plan(sample: pd.DataFrame) -> None:
    plan = learn_rules(sample)
    assert "were learned from" in plan.caveat
    assert plan.caveat in plan.summary()
    assert plan.to_dict()["caveat"] == plan.caveat


def test_the_learned_plan_actually_runs(sample: pd.DataFrame) -> None:
    """The rules must hold on the data they came from, or the learner is
    emitting constraints its own evidence violates."""
    result = learn_rules(sample).plan().run(sample)
    assert result.passed, result.summary()


def test_the_plan_exports_as_readable_code(sample: pd.DataFrame) -> None:
    """A learned plan nobody reads is one nobody can correct, and the
    corrections are where domain knowledge enters."""
    source = learn_rules(sample).to_python()
    assert "sp.ValidationPlan()" in source
    assert ".isin(" in source
    assert "#" in source, "every rule should carry its caveat as a comment"

    namespace: dict[str, object] = {}
    exec(compile(source.replace("result = plan.run(df)", ""), "<learned>", "exec"), namespace)  # noqa: S102
    assert len(namespace["plan"]) == len(learn_rules(sample).rules)


def test_learning_validates_nothing_by_itself(sample: pd.DataFrame) -> None:
    """The review step is the point. A learner that ran its own output would
    have removed it."""
    plan = learn_rules(sample)
    assert not hasattr(plan, "run")
    assert not hasattr(plan, "validate")


def test_an_unsupported_column_is_skipped_with_its_reason() -> None:
    frame = pd.DataFrame({"payload": [{"k": i} for i in range(80)], "n": range(80)})
    reasons = dict(learn_rules(frame).abstained)
    assert "payload" in reasons
    assert "no summary statistic" in reasons["payload"]


def test_the_public_api_exposes_it() -> None:
    assert hasattr(sp, "learn_rules")
    assert "learn_rules" in sp.__all__
