"""The workflow -- a preparation pipeline as nodes, executed by the core.

A visual pipeline is the point at which a data tool usually acquires a second
execution engine. The canvas grows its own idea of what "apply missing-value
repairs" means, the Python API keeps the original, and from then on the two
answers have to be reconciled by hand forever.

So a node is **not** an implementation. It is a filter over the plan the core
already built:

``Visual node -> serializable specification -> the same RepairPlan -> RepairExecutor``

Every stage below selects a subset of the operations `auto_prepare` would have
run, and hands that subset to the same executor, producing the same audit
records. Running every stage is therefore not merely *similar* to
``auto_prepare`` -- it is the same operations in the same order, and a test
asserts the frames and the audits match.

What the workflow adds is not power but **control and visibility**: disable a
stage, reorder within the rules, see what each one cost, and export the whole
thing as Python you can read.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

from .core.audit import AuditLog
from .core.enums import IssueCategory
from .core.issue import Issue
from .core.operations import Operation, RepairPlan
from .exceptions import SmartPrepError

__all__ = [
    "Stage",
    "Node",
    "NodeOutcome",
    "Workflow",
    "WorkflowRun",
    "WorkflowError",
    "default_workflow",
]


class WorkflowError(SmartPrepError):
    """The workflow cannot be run as arranged."""


class Stage(Enum):
    """The stages of a preparation pipeline, in the only order they work.

    The order is not a convention. Types are repaired before ranges because a
    range check on the string ``"1,200.50"`` is meaningless; duplicates are
    resolved after categories because ``Marrakech`` and ``Marrakesh`` are not
    duplicates until they are the same word. A canvas that let a reader
    arrange these freely would let them arrange a wrong answer.
    """

    LOAD = "load"
    SCAN = "scan"
    TYPES = "types"
    MISSING = "missing"
    CATEGORIES = "categories"
    DUPLICATES = "duplicates"
    OUTLIERS = "outliers"
    VALIDATE = "validate"
    REPORT = "report"

    @property
    def order(self) -> int:
        return list(Stage).index(self)

    @property
    def repairs(self) -> bool:
        """Whether this stage changes data at all."""
        return self in _REPAIR_CATEGORIES

    @property
    def label(self) -> str:
        return {
            Stage.LOAD: "Load",
            Stage.SCAN: "Scan",
            Stage.TYPES: "Type repair",
            Stage.MISSING: "Missing values",
            Stage.CATEGORIES: "Categories",
            Stage.DUPLICATES: "Duplicates",
            Stage.OUTLIERS: "Ranges and outliers",
            Stage.VALIDATE: "Validate",
            Stage.REPORT: "Report",
        }[self]


#: Which findings each repairing stage owns. Every category the detectors can
#: raise appears exactly once, so no operation is silently homeless: a repair
#: belonging to no stage would never run, and the workflow would quietly do
#: less than ``auto_prepare`` while looking complete.
_REPAIR_CATEGORIES: dict[Stage, frozenset[IssueCategory]] = {
    Stage.TYPES: frozenset(
        {
            IssueCategory.MIXED_PHYSICAL_TYPE,
            IssueCategory.INVALID_DATE,
            IssueCategory.AMBIGUOUS_DATE,
            IssueCategory.CURRENCY_CONTEXT,
        }
    ),
    Stage.MISSING: frozenset(
        {
            IssueCategory.MISSINGNESS,
            IssueCategory.SUSPICIOUS_MISSINGNESS,
            IssueCategory.STRUCTURAL_MISSINGNESS,
            IssueCategory.SENTINEL_CANDIDATE,
        }
    ),
    Stage.CATEGORIES: frozenset(
        {
            IssueCategory.CATEGORY_VARIANT,
            IssueCategory.UNICODE_CONFUSABLE,
            IssueCategory.GEOGRAPHIC_CONFLICT,
            IssueCategory.UNKNOWN_ENTITY,
        }
    ),
    Stage.DUPLICATES: frozenset(
        {
            IssueCategory.EXACT_DUPLICATE,
            IssueCategory.CONFLICTING_DUPLICATE,
            IssueCategory.IDENTIFIER_METADATA_MISMATCH,
        }
    ),
    Stage.OUTLIERS: frozenset(
        {
            IssueCategory.RANGE_VIOLATION,
            IssueCategory.FORMULA_VIOLATION,
            IssueCategory.STATE_CONTRADICTION,
            IssueCategory.ACCOUNTING_IMPLAUSIBILITY,
            IssueCategory.UNUSUAL_PATTERN,
        }
    ),
}


def stage_for(category: IssueCategory) -> Stage | None:
    """Which stage owns a finding, or ``None`` if nothing does."""
    for stage, categories in _REPAIR_CATEGORIES.items():
        if category in categories:
            return stage
    return None


@dataclass
class Node:
    """One step, as data.

    Serialisable, so a pipeline built by dragging is the same object as one
    written in Python, can be saved beside the dataset, and replays exactly.
    """

    stage: Stage
    id: str = ""
    label: str = ""
    enabled: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        self.id = self.id or f"node-{self.stage.value}"
        self.label = self.label or self.stage.label

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "stage": self.stage.value,
            "label": self.label,
            "enabled": self.enabled,
            "parameters": dict(self.parameters),
            "depends_on": list(self.depends_on),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Node:
        return cls(
            stage=Stage(payload["stage"]),
            id=str(payload.get("id", "")),
            label=str(payload.get("label", "")),
            enabled=bool(payload.get("enabled", True)),
            parameters=dict(payload.get("parameters", {})),
            depends_on=tuple(str(d) for d in payload.get("depends_on", [])),
            note=str(payload.get("note", "")),
        )


@dataclass
class NodeOutcome:
    """What one node actually did. The canvas shows this; it does not compute it."""

    node_id: str
    stage: Stage
    status: str = "pending"  # pending | skipped | ran | refused
    elapsed_seconds: float = 0.0
    rows_affected: int = 0
    cells_changed: int = 0
    issues_resolved: int = 0
    issues_created: int = 0
    warnings: list[str] = field(default_factory=list)
    health_before: float | None = None
    health_after: float | None = None
    validation_passed: bool | None = None
    #: Operation ids written to the audit log by this node. The canvas links
    #: to the audit rather than restating it, so there is one record.
    audit_operations: list[str] = field(default_factory=list)

    @property
    def health_delta(self) -> float | None:
        if self.health_before is None or self.health_after is None:
            return None
        return round(self.health_after - self.health_before, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "stage": self.stage.value,
            "status": self.status,
            "elapsed_seconds": round(self.elapsed_seconds, 4),
            "rows_affected": self.rows_affected,
            "cells_changed": self.cells_changed,
            "issues_resolved": self.issues_resolved,
            "issues_created": self.issues_created,
            "warnings": list(self.warnings),
            "health_before": self.health_before,
            "health_after": self.health_after,
            "health_delta": self.health_delta,
            "validation_passed": self.validation_passed,
            "audit_operations": list(self.audit_operations),
        }


@dataclass
class WorkflowRun:
    """The result of executing a workflow.

    Carries the same audit log the rest of the library produces, because it
    *is* the same audit log -- the nodes ran core operations.
    """

    frame: pd.DataFrame
    audit: AuditLog
    outcomes: list[NodeOutcome] = field(default_factory=list)
    before_scan: Any = None
    after_scan: Any = None

    @property
    def cells_changed(self) -> int:
        return sum(o.cells_changed for o in self.outcomes)

    @property
    def ran(self) -> list[NodeOutcome]:
        return [o for o in self.outcomes if o.status == "ran"]

    @property
    def skipped(self) -> list[NodeOutcome]:
        return [o for o in self.outcomes if o.status == "skipped"]

    def outcome(self, node_id: str) -> NodeOutcome:
        for candidate in self.outcomes:
            if candidate.node_id == node_id:
                return candidate
        raise KeyError(f"no outcome for node {node_id!r}")

    def summary(self) -> str:
        lines = [f"{len(self.ran)} of {len(self.outcomes)} stages ran"]
        for outcome in self.outcomes:
            mark = {"ran": "  ", "skipped": "- ", "refused": "! "}.get(outcome.status, "? ")
            delta = outcome.health_delta
            lines.append(
                f"{mark}{outcome.stage.label:22s} {outcome.cells_changed:>6,} cells"
                + (f"  health {delta:+.1f}" if delta else "")
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcomes": [o.to_dict() for o in self.outcomes],
            "cells_changed": self.cells_changed,
            "stages_ran": len(self.ran),
        }


@dataclass
class Workflow:
    """A pipeline of nodes, arranged and executed under the core's rules."""

    nodes: list[Node] = field(default_factory=list)
    name: str = "preparation"

    # -- editing ------------------------------------------------------------

    def add(self, stage: Stage, **kwargs: Any) -> Node:
        if any(n.stage is stage for n in self.nodes):
            raise WorkflowError(
                f"{stage.label} is already in this workflow. A stage runs once; "
                "running it twice would repair findings that no longer exist."
            )
        node = Node(stage=stage, **kwargs)
        self.nodes.append(node)
        self.nodes.sort(key=lambda n: n.stage.order)
        return node

    def remove(self, node_id: str) -> Workflow:
        self.nodes = [n for n in self.nodes if n.id != node_id]
        return self

    def get(self, node_id: str) -> Node:
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise KeyError(f"no node {node_id!r}")

    def disable(self, node_id: str) -> Workflow:
        self.get(node_id).enabled = False
        return self

    def enable(self, node_id: str) -> Workflow:
        self.get(node_id).enabled = True
        return self

    def configure(self, node_id: str, **parameters: Any) -> Workflow:
        self.get(node_id).parameters.update(parameters)
        return self

    def connect(self, node_id: str, depends_on: str) -> Workflow:
        """Declare a dependency. Refused when it would invert the stage order."""
        node, upstream = self.get(node_id), self.get(depends_on)
        if upstream.stage.order > node.stage.order:
            raise WorkflowError(
                f"{node.label} cannot depend on {upstream.label}: "
                f"{upstream.label} runs later. "
                "Repairing ranges before types would test a string against a number."
            )
        node.depends_on = tuple(dict.fromkeys((*node.depends_on, depends_on)))
        return self

    def move(self, node_id: str, position: int) -> Workflow:
        """Reorder, within the rules.

        Accepted only when the result still runs stages in a valid order --
        the canvas may rearrange presentation, never correctness.
        """
        node = self.get(node_id)
        rest = [n for n in self.nodes if n.id != node_id]
        rest.insert(max(0, min(position, len(rest))), node)
        problems = _order_problems(rest)
        if problems:
            raise WorkflowError("; ".join(problems))
        self.nodes = rest
        return self

    # -- validity -----------------------------------------------------------

    def validate(self) -> list[str]:
        """Everything wrong with this arrangement. Empty means runnable."""
        problems = _order_problems(self.nodes)
        known = {n.id for n in self.nodes}
        for node in self.nodes:
            for dependency in node.depends_on:
                if dependency not in known:
                    problems.append(f"{node.label} depends on {dependency!r}, which is not here")
                elif not self.get(dependency).enabled and node.enabled:
                    problems.append(
                        f"{node.label} depends on {self.get(dependency).label}, which is disabled"
                    )
        if not any(n.stage is Stage.SCAN for n in self.nodes):
            problems.append("a workflow without a Scan stage has nothing to act on")
        return problems

    def ordered(self) -> list[Node]:
        return sorted(self.nodes, key=lambda n: n.stage.order)

    # -- execution ----------------------------------------------------------

    def run(self, frame: pd.DataFrame, **context: Any) -> WorkflowRun:
        """Execute the enabled stages against ``frame``.

        Each repairing stage takes the subset of the plan the core already
        built for its own categories and hands it to the same executor. There
        is no second engine here, which is why running every stage gives the
        frame and the audit that ``auto_prepare`` gives.
        """
        problems = self.validate()
        if problems:
            raise WorkflowError("this workflow cannot run: " + "; ".join(problems))

        from .prepare import _build_plan
        from .repair.executor import RepairExecutor
        from .scan import scan

        before = scan(frame, **context)
        plan, audit, _ = _build_plan(before)

        by_stage: dict[Stage, list[Operation]] = {}
        homeless: list[Operation] = []
        issues = {issue.id: issue for issue in before.issues}
        for operation in plan.ordered():
            stage = _stage_of(operation, issues)
            if stage is None:
                homeless.append(operation)
            else:
                by_stage.setdefault(stage, []).append(operation)

        current = frame
        run = WorkflowRun(frame=frame, audit=audit, before_scan=before)
        open_before = {i.id for i in before.issues}
        # Health carried forward: a stage's "before" is the previous stage's
        # "after", and re-deriving it means scanning the whole frame twice per
        # stage. On fifty thousand rows that was most of the canvas.
        health_before = before.health().overall
        latest = before

        for node in self.ordered():
            outcome = NodeOutcome(node_id=node.id, stage=node.stage)
            run.outcomes.append(outcome)

            if not node.enabled:
                outcome.status = "skipped"
                outcome.warnings.append("disabled; its findings are left open")
                continue

            if not node.stage.repairs:
                # Load, Scan, Validate and Report do not change data. They are
                # nodes because a pipeline a reader cannot see the shape of is
                # a pipeline they cannot check.
                outcome.status = "ran"
                if node.stage is Stage.VALIDATE:
                    outcome.validation_passed = _validate(current, node, outcome, **context)
                continue

            operations = by_stage.get(node.stage, [])
            if not operations:
                outcome.status = "ran"
                outcome.warnings.append("nothing in this dataset needed this stage")
                continue

            started = time.perf_counter()
            already = len(audit.records)

            stage_plan = RepairPlan()
            for operation in operations:
                stage_plan.add(operation)
            executed = RepairExecutor().run(current, stage_plan, audit=audit)
            # The records this stage appended. An Operation carries no id --
            # the audit assigns one when it records the change, which is
            # exactly the right place for identity to come from.
            written = audit.records[already:]

            current = executed.frame
            after = scan(current, **context)
            latest = after
            open_after = {i.id for i in after.issues}

            outcome.status = "refused" if executed.refused else "ran"
            outcome.elapsed_seconds = time.perf_counter() - started
            # From this stage's own records, never from the shared log:
            # ExecutionOutcome.cells_changed sums the whole audit, and the
            # audit is shared across stages, so reading it here would count
            # every earlier stage again in every later one.
            outcome.cells_changed = sum(r.cells_changed for r in written if r.applied)
            # Rows come from the audit rather than the operations: the audit
            # records what was actually touched, an operation only what was
            # proposed.
            outcome.rows_affected = sum(len(r.rows) for r in written if r.applied)
            outcome.issues_resolved = len(open_before - open_after)
            outcome.issues_created = len(open_after - open_before)
            outcome.health_before = round(health_before, 2)
            outcome.health_after = round(after.health().overall, 2)
            health_before = outcome.health_after
            outcome.audit_operations = [r.operation_id for r in written if r.applied]
            outcome.warnings.extend(reason for _, reason in executed.refused)
            open_before = open_after

        if homeless:
            # Loud, because the alternative is a pipeline that looks complete
            # and quietly does less than automatic mode.
            names = ", ".join(sorted({o.name for o in homeless}))
            raise WorkflowError(
                f"these repairs belong to no stage and would never run: {names}. "
                "Add their issue categories to a stage before shipping."
            )

        run.frame = current
        # The last stage already scanned this exact frame; scanning it again
        # would be the same answer at the same cost.
        run.after_scan = latest if current is not frame else before
        return run

    # -- serialisation and export -------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "name": self.name,
            "nodes": [n.to_dict() for n in self.ordered()],
        }

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Workflow:
        return cls(
            name=str(payload.get("name", "preparation")),
            nodes=[Node.from_dict(n) for n in payload.get("nodes", [])],
        )

    @classmethod
    def from_json(cls, payload: str) -> Workflow:
        return cls.from_dict(json.loads(payload))

    def to_python(self) -> str:
        """The equivalent script, as readable code.

        A pipeline you cannot export is a pipeline you cannot review, put in
        version control, or run on a machine without a browser.
        """
        lines = [
            "import pandas as pd",
            "import smartprep as sp",
            "",
            f"# {self.name}",
            "workflow = sp.Workflow()",
        ]
        for node in self.ordered():
            arguments = f"sp.Stage.{node.stage.name}"
            if node.parameters:
                arguments += ", " + ", ".join(f"{k}={v!r}" for k, v in node.parameters.items())
            lines.append(f"workflow.add({arguments})")
            if not node.enabled:
                lines.append(f"workflow.disable({node.id!r})  # {node.note or 'disabled'}")
        lines += ["", "run = workflow.run(df)", "print(run.summary())"]
        return "\n".join(lines)


def _order_problems(nodes: list[Node]) -> list[str]:
    """Stages arranged in an order that would produce a wrong answer."""
    problems: list[str] = []
    seen: list[Node] = []
    for node in nodes:
        for earlier in seen:
            if earlier.stage.order > node.stage.order:
                problems.append(
                    f"{node.label} is placed after {earlier.label}, but must run before it"
                )
        seen.append(node)
    return problems


def _stage_of(operation: Operation, issues: dict[str, Issue]) -> Stage | None:
    for issue_id in operation.issue_ids:
        issue = issues.get(issue_id)
        if issue is not None:
            found = stage_for(issue.category)
            if found is not None:
                return found
    return None


def _validate(frame: pd.DataFrame, node: Node, outcome: NodeOutcome, **context: Any) -> bool | None:
    """Run a validation plan if the node was given one."""
    plan = node.parameters.get("plan")
    if plan is None:
        outcome.warnings.append("no validation plan configured; nothing was checked")
        return None
    result = plan.run(frame)
    outcome.warnings.extend(str(f) for f in getattr(result, "failures", [])[:5])
    return bool(getattr(result, "passed", False))


def default_workflow() -> Workflow:
    """The standard pipeline: every stage, in the order that works."""
    workflow = Workflow()
    for stage in Stage:
        workflow.add(stage)
    return workflow
