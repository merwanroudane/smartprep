"""Data contracts: what the data promises, in a form a machine can enforce.

The useful move here is not writing a schema by hand. It is **inferring** one
from data you have already reviewed, editing it, and then holding future
batches to it. Exploratory work becomes a production gate without anyone
retyping it.

Schema changes are classified rather than merely reported, because "a column
was added" and "a column changed meaning" need different responses.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

from ..detectors.base import is_missing, physical_type, to_number
from .plan import ValidationPlan

__all__ = ["ChangeKind", "SchemaChange", "ColumnContract", "DataContract"]


class ChangeKind(Enum):
    """How a schema change affects consumers.

    The distinction that matters most is the last one: a column whose type and
    name are unchanged but whose *meaning* moved will pass every structural
    check and break every downstream number.
    """

    BACKWARD_COMPATIBLE = "backward_compatible"
    FORWARD_COMPATIBLE = "forward_compatible"
    BREAKING = "breaking"
    SEMANTIC_BREAKING = "semantic_breaking"


@dataclass(frozen=True)
class SchemaChange:
    kind: ChangeKind
    column: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"[{self.kind.value}] {self.column}: {self.detail}"


@dataclass
class ColumnContract:
    """What one column promises."""

    name: str
    dtype: str
    nullable: bool = True
    unique: bool = False
    minimum: float | None = None
    maximum: float | None = None
    allowed: list[str] | None = None
    unit: str | None = None
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None and v != ""}


@dataclass
class DataContract:
    """A versioned agreement about a dataset's shape and content."""

    name: str
    version: str = "1.0"
    columns: dict[str, ColumnContract] = field(default_factory=dict)
    primary_key: tuple[str, ...] = ()
    allow_extra_columns: bool = False

    # -- inference ----------------------------------------------------------

    @classmethod
    def infer(
        cls,
        frame: pd.DataFrame,
        *,
        name: str = "dataset",
        version: str = "1.0",
        max_categories: int = 20,
    ) -> DataContract:
        """Propose a contract from observed data.

        This is a **proposal**, not a discovery of truth. Bounds come from the
        range that happened to be present, so a contract inferred from one
        quarter will reject a legitimately larger value next quarter. Widen it
        before enforcing.
        """
        contract = cls(name=name, version=version)
        for column in frame.columns:
            series = frame[column]
            present = [v for v in series if not is_missing(v)]
            forms = {physical_type(v) for v in present}
            numeric = series.map(to_number)
            is_numeric = bool(present) and numeric.notna().sum() == len(present)

            column_contract = ColumnContract(
                name=column,
                dtype="numeric" if is_numeric else ("mixed" if len(forms) > 1 else "text"),
                nullable=len(present) < len(series),
                unique=bool(present) and series.dropna().is_unique,
            )
            if is_numeric:
                column_contract.minimum = float(numeric.min())
                column_contract.maximum = float(numeric.max())
            elif 0 < series.nunique(dropna=True) <= max_categories:
                column_contract.allowed = sorted({str(v) for v in present})

            contract.columns[column] = column_contract

        keys = [c.name for c in contract.columns.values() if c.unique and not c.nullable]
        contract.primary_key = (keys[0],) if keys else ()
        return contract

    # -- enforcement --------------------------------------------------------

    def to_validation_plan(self, frame: pd.DataFrame | None = None) -> ValidationPlan:
        """Compile the contract into runnable checks."""
        plan = ValidationPlan(frame)
        if not self.allow_extra_columns:
            # Declared on the contract and, until now, never enforced -- so the
            # contract did not mean what it said.
            plan.no_unexpected_columns(list(self.columns))
        for column in self.columns.values():
            plan.column_exists(column.name)
            if not column.nullable:
                plan.not_null(column.name)
            if column.unique:
                plan.unique(column.name)
            if column.minimum is not None and column.maximum is not None:
                plan.between(column.name, column.minimum, column.maximum)
            if column.allowed:
                plan.isin(column.name, list(column.allowed))
        if len(self.primary_key) > 1:
            plan.unique_together(*self.primary_key)
        return plan

    def validate(self, frame: pd.DataFrame) -> Any:
        return self.to_validation_plan().run(frame)

    # -- evolution ----------------------------------------------------------

    def diff(self, other: DataContract) -> list[SchemaChange]:
        """Classify how ``other`` differs from this contract."""
        changes: list[SchemaChange] = []

        for name, column in other.columns.items():
            if name not in self.columns:
                changes.append(
                    SchemaChange(
                        ChangeKind.BACKWARD_COMPATIBLE if column.nullable else ChangeKind.BREAKING,
                        name,
                        "column added" + ("" if column.nullable else " and is not nullable"),
                    )
                )

        for name, column in self.columns.items():
            if name not in other.columns:
                changes.append(SchemaChange(ChangeKind.BREAKING, name, "column removed"))
                continue

            new = other.columns[name]
            if column.dtype != new.dtype:
                widened = column.dtype != "mixed" and new.dtype == "mixed"
                changes.append(
                    SchemaChange(
                        ChangeKind.FORWARD_COMPATIBLE if widened else ChangeKind.BREAKING,
                        name,
                        f"type {column.dtype} -> {new.dtype}",
                    )
                )
            if not column.nullable and new.nullable:
                changes.append(SchemaChange(ChangeKind.BREAKING, name, "became nullable"))
            if column.unique and not new.unique:
                changes.append(SchemaChange(ChangeKind.BREAKING, name, "uniqueness lost"))
            if column.allowed and new.allowed:
                removed = set(column.allowed) - set(new.allowed)
                added = set(new.allowed) - set(column.allowed)
                if removed:
                    changes.append(
                        SchemaChange(
                            ChangeKind.BREAKING, name, f"categories disappeared: {sorted(removed)}"
                        )
                    )
                if added:
                    changes.append(
                        SchemaChange(
                            ChangeKind.BACKWARD_COMPATIBLE,
                            name,
                            f"new categories: {sorted(added)}",
                        )
                    )
            if column.unit and new.unit and column.unit != new.unit:
                changes.append(
                    SchemaChange(
                        ChangeKind.SEMANTIC_BREAKING,
                        name,
                        f"unit changed {column.unit} -> {new.unit}; the numbers still "
                        "parse but no longer mean the same thing",
                    )
                )
        return changes

    @staticmethod
    def is_breaking(changes: list[SchemaChange]) -> bool:
        return any(c.kind in (ChangeKind.BREAKING, ChangeKind.SEMANTIC_BREAKING) for c in changes)

    # -- serialisation ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "name": self.name,
            "version": self.version,
            "primary_key": list(self.primary_key),
            "allow_extra_columns": self.allow_extra_columns,
            "columns": {k: v.to_dict() for k, v in self.columns.items()},
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_yaml(self) -> str:
        """Emit YAML without taking a dependency for it.

        The contract is a flat mapping of scalars and short lists, so a tiny
        writer is safer than adding PyYAML to the core install.
        """
        lines = [
            f"name: {self.name}",
            f"version: {self.version}",
            f"allow_extra_columns: {str(self.allow_extra_columns).lower()}",
        ]
        if self.primary_key:
            lines.append(f"primary_key: [{', '.join(self.primary_key)}]")
        lines.append("columns:")
        for name, column in self.columns.items():
            lines.append(f"  {name}:")
            for key, value in column.to_dict().items():
                if key == "name":
                    continue
                if isinstance(value, list):
                    items = ", ".join(json.dumps(v, ensure_ascii=False) for v in value)
                    rendered = f"[{items}]"
                elif isinstance(value, bool):
                    rendered = str(value).lower()
                else:
                    rendered = (
                        json.dumps(value, ensure_ascii=False)
                        if isinstance(value, str)
                        else str(value)
                    )
                lines.append(f"    {key}: {rendered}")
        return "\n".join(lines)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> DataContract:
        contract = cls(
            name=payload["name"],
            version=payload.get("version", "1.0"),
            primary_key=tuple(payload.get("primary_key", ())),
            allow_extra_columns=payload.get("allow_extra_columns", False),
        )
        for name, spec in payload.get("columns", {}).items():
            contract.columns[name] = ColumnContract(
                name=name, **{k: v for k, v in spec.items() if k != "name"}
            )
        return contract

    def summary(self) -> str:
        lines = [f"Contract {self.name} v{self.version}", ""]
        for column in self.columns.values():
            flags = []
            if not column.nullable:
                flags.append("not null")
            if column.unique:
                flags.append("unique")
            if column.minimum is not None:
                flags.append(f"[{column.minimum:g}, {column.maximum:g}]")
            if column.allowed:
                flags.append(f"{len(column.allowed)} categories")
            lines.append(f"  {column.name:22s} {column.dtype:8s} {', '.join(flags)}")
        return "\n".join(lines)
