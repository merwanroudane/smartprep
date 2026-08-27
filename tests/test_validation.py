"""Validation plans and data contracts."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from smartprep.exceptions import SmartPrepValidationError
from smartprep.validation import ChangeKind, DataContract, Outcome, ValidationPlan


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": ["A", "B", "C", "C", "E"],
            "rating": [1.0, 5.0, 9.0, 3.0, None],
            "status": ["Paid", "Pending", "Paid", "Invalid", "Paid"],
            "amount": [10.0, 20.0, 30.0, 40.0, 50.0],
        }
    )


# -- grading --------------------------------------------------------------


def test_a_passing_rule_is_a_pass(frame: pd.DataFrame) -> None:
    result = ValidationPlan().not_null("id").run(frame)
    assert result.outcome is Outcome.PASS
    assert result.passed


def test_failures_are_graded_not_binary(frame: pd.DataFrame) -> None:
    """2% failing and 40% failing are not the same event."""
    result = ValidationPlan().between("rating", 1, 5, error_at=0.5, critical_at=0.9).run(frame)
    assert result.get("between:rating").outcome is Outcome.WARNING

    strict = ValidationPlan().between("rating", 1, 5, error_at=0.1).run(frame)
    assert strict.get("between:rating").outcome is Outcome.ERROR


def test_the_worst_rule_sets_the_overall_outcome(frame: pd.DataFrame) -> None:
    """2 of 5 rows duplicated is 40%, past the 25% critical threshold."""
    result = ValidationPlan().not_null("id").unique("id").run(frame)
    assert result.get("not_null:id").outcome is Outcome.PASS
    assert result.get("unique:id").outcome is Outcome.CRITICAL
    assert result.outcome is Outcome.CRITICAL


def test_every_rule_runs_so_one_failure_cannot_hide_another(frame: pd.DataFrame) -> None:
    result = (
        ValidationPlan()
        .unique("id")
        .between("rating", 1, 5)
        .isin("status", ["Paid", "Pending"])
        .run(frame)
    )
    assert len(result.results) == 3
    assert len(result.failing_rules) == 3


def test_evaluated_count_is_reported(frame: pd.DataFrame) -> None:
    """A rule that silently evaluated nothing is not a pass."""
    result = ValidationPlan().not_null("id").run(frame)
    assert result.get("not_null:id").evaluated == len(frame)


# -- rules ----------------------------------------------------------------


def test_range_ignores_missing_values(frame: pd.DataFrame) -> None:
    """Absence is the not_null rule's business; conflating them hides both."""
    result = ValidationPlan().between("rating", 1, 5).run(frame)
    assert result.get("between:rating").failed == 1


def test_isin_catches_unexpected_categories(frame: pd.DataFrame) -> None:
    result = ValidationPlan().isin("status", ["Paid", "Pending"]).run(frame)
    assert result.get("isin:status").failed == 1


def test_matches_applies_a_pattern(frame: pd.DataFrame) -> None:
    result = ValidationPlan().matches("id", r"^[A-Z]$").run(frame)
    assert result.get("matches:id").outcome is Outcome.PASS


def test_unique_together_checks_the_combination(frame: pd.DataFrame) -> None:
    result = ValidationPlan().unique_together("id", "amount").run(frame)
    assert result.get("unique_together:id+amount").outcome is Outcome.PASS


def test_custom_expression_rule(frame: pd.DataFrame) -> None:
    result = ValidationPlan().custom("amount > 0", name="positive_amount").run(frame)
    assert result.get("positive_amount").outcome is Outcome.PASS


def test_implies_passes_where_the_condition_is_false(frame: pd.DataFrame) -> None:
    result = (
        ValidationPlan()
        .implies("status == 'Pending'", "amount < 25", name="pending_small")
        .run(frame)
    )
    assert result.get("pending_small").outcome is Outcome.PASS


def test_a_missing_column_is_critical_not_a_crash(frame: pd.DataFrame) -> None:
    result = ValidationPlan().not_null("absent").run(frame)
    assert result.get("not_null:absent").outcome is Outcome.CRITICAL


def test_duplicate_rule_names_are_rejected() -> None:
    plan = ValidationPlan().not_null("id")
    with pytest.raises(ValueError, match="already in this plan"):
        plan.not_null("id")


def test_an_unevaluable_rule_says_so(frame: pd.DataFrame) -> None:
    plan = ValidationPlan().custom("this is not an expression", columns=())
    with pytest.raises(SmartPrepValidationError, match="could not be evaluated"):
        plan.run(frame)


# -- sundering ------------------------------------------------------------


def test_split_separates_passing_from_failing_rows(frame: pd.DataFrame) -> None:
    """A verdict is less useful than being able to look at the failures."""
    result = ValidationPlan().between("rating", 1, 5).isin("status", ["Paid", "Pending"]).run(frame)
    valid, invalid = result.split()
    assert len(valid) + len(invalid) == len(frame)
    assert len(invalid) == 2


def test_failing_rows_carry_index_labels() -> None:
    frame = pd.DataFrame({"rating": [1.0, 99.0]}, index=["first", "second"])
    result = ValidationPlan().between("rating", 1, 5).run(frame)
    assert result.get("between:rating").rows.labels == ("second",)


# -- gates ----------------------------------------------------------------


def test_raise_if_failed_is_a_ci_gate(frame: pd.DataFrame) -> None:
    result = ValidationPlan().unique("id").run(frame)
    with pytest.raises(SmartPrepValidationError, match="validation reached"):
        result.raise_if_failed(at=Outcome.ERROR)


def test_gate_can_be_set_above_the_outcome(frame: pd.DataFrame) -> None:
    result = ValidationPlan().between("rating", 1, 5, error_at=0.9).run(frame)
    result.raise_if_failed(at=Outcome.CRITICAL)


def test_result_serialises(frame: pd.DataFrame) -> None:
    payload = json.loads(ValidationPlan().unique("id").run(frame).to_json())
    assert payload["schema_version"] == 1
    assert payload["rules"][0]["thresholds"]["error_at"] == 0.05


# -- contracts ------------------------------------------------------------


def test_contract_is_inferred_from_data(frame: pd.DataFrame) -> None:
    contract = DataContract.infer(frame, name="orders")
    assert contract.columns["amount"].dtype == "numeric"
    assert contract.columns["amount"].minimum == 10.0
    assert contract.columns["rating"].nullable is True
    assert contract.columns["status"].allowed


def test_inferred_contract_validates_its_own_data(frame: pd.DataFrame) -> None:
    contract = DataContract.infer(frame, name="orders")
    result = contract.validate(frame)
    assert not [r for r in result.failing_rules if r.rule.name.startswith("between")]


def test_contract_catches_a_new_out_of_range_value(frame: pd.DataFrame) -> None:
    contract = DataContract.infer(frame, name="orders")
    future = frame.copy()
    future.loc[0, "amount"] = 999999.0
    assert contract.validate(future).outcome.failed


def test_contract_round_trips_through_json(frame: pd.DataFrame) -> None:
    contract = DataContract.infer(frame, name="orders")
    restored = DataContract.from_dict(json.loads(contract.to_json()))
    assert restored.name == contract.name
    assert set(restored.columns) == set(contract.columns)


def test_contract_emits_yaml_without_a_dependency(frame: pd.DataFrame) -> None:
    yaml = DataContract.infer(frame, name="orders").to_yaml()
    assert yaml.startswith("name: orders")
    assert "columns:" in yaml


# -- schema evolution -----------------------------------------------------


def test_added_nullable_column_is_backward_compatible(frame: pd.DataFrame) -> None:
    before = DataContract.infer(frame, name="orders")
    after = DataContract.infer(frame.assign(note=[None] * len(frame)), name="orders")
    changes = before.diff(after)
    added = [c for c in changes if c.column == "note"]
    assert added and added[0].kind is ChangeKind.BACKWARD_COMPATIBLE


def test_removed_column_is_breaking(frame: pd.DataFrame) -> None:
    before = DataContract.infer(frame, name="orders")
    after = DataContract.infer(frame.drop(columns=["amount"]), name="orders")
    changes = before.diff(after)
    assert any(c.column == "amount" and c.kind is ChangeKind.BREAKING for c in changes)
    assert DataContract.is_breaking(changes)


def test_a_unit_change_is_semantically_breaking(frame: pd.DataFrame) -> None:
    """The numbers still parse. They no longer mean the same thing."""
    before = DataContract.infer(frame, name="orders")
    after = DataContract.infer(frame, name="orders")
    before.columns["amount"].unit = "EUR"
    after.columns["amount"].unit = "DZD"

    changes = before.diff(after)
    assert any(c.kind is ChangeKind.SEMANTIC_BREAKING for c in changes)
    assert DataContract.is_breaking(changes)


def test_identical_contracts_have_no_changes(frame: pd.DataFrame) -> None:
    contract = DataContract.infer(frame, name="orders")
    assert contract.diff(DataContract.infer(frame, name="orders")) == []


def test_new_category_is_backward_compatible(frame: pd.DataFrame) -> None:
    before = DataContract.infer(frame, name="orders")
    extended = pd.concat([frame, frame.head(1).assign(status="Refunded")], ignore_index=True)
    changes = before.diff(DataContract.infer(extended, name="orders"))
    assert any(c.column == "status" and c.kind is ChangeKind.BACKWARD_COMPATIBLE for c in changes)


# -- P0 regressions -------------------------------------------------------


def test_allow_extra_columns_is_enforced(frame: pd.DataFrame) -> None:
    """The flag was declared, serialised, and never read -- so the contract
    did not mean what it said."""
    contract = DataContract.infer(frame, name="orders")
    assert contract.allow_extra_columns is False

    result = contract.validate(frame.assign(surprise=[1] * len(frame)))
    assert result.outcome.failed
    assert result.get("no_unexpected_columns").outcome is Outcome.CRITICAL


def test_a_permissive_contract_accepts_extra_columns(frame: pd.DataFrame) -> None:
    contract = DataContract.infer(frame, name="orders")
    contract.allow_extra_columns = True
    assert not contract.validate(frame.assign(surprise=[1] * len(frame))).outcome.failed


def test_exact_columns_still_pass(frame: pd.DataFrame) -> None:
    contract = DataContract.infer(frame, name="orders")
    result = contract.validate(frame)
    assert result.get("no_unexpected_columns").outcome is Outcome.PASS
