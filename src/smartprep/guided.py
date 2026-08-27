"""``guided_prepare()`` -- the human in the loop (AD-002).

Guided mode is not a second implementation of cleaning. It is the same engine
with the abstentions turned into questions: everything auto mode refused to
decide is exactly what guided mode asks about.

The API is programmatic first. A decision is data -- recordable, replayable,
diffable -- and the terminal interface is a thin layer over it. That ordering
matters: a decision you cannot replay is a click, and a click is not
reproducible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

from .core.audit import AuditLog, AuditRecord, DecisionSource
from .core.enums import RuleSource, Severity
from .core.issue import Issue, TreatmentCandidate
from .core.operations import RepairPlan
from .core.snapshot import EnvironmentManifest
from .exceptions import SmartPrepAmbiguityError
from .prepare import PreparationResult, _build_plan
from .repair.actions import build_operation, has_action
from .repair.executor import RepairExecutor
from .scan import ScanResult, scan

__all__ = [
    "Action",
    "Decision",
    "Question",
    "GuidedSession",
    "guided_prepare",
    "QuestionLevel",
]


class Action(Enum):
    """What the user chose to do about a finding."""

    USE_RECOMMENDATION = "use_recommendation"
    CHOOSE_ALTERNATIVE = "choose_alternative"
    SKIP = "skip"
    WAIVE = "waive"
    LEAVE_UNRESOLVED = "leave_unresolved"


class QuestionLevel(Enum):
    """How much the session should ask about.

    A researcher who wants three decisions and a colleague who wants forty are
    both right; the difference is the level, not a different engine.
    """

    MINIMAL = "minimal"
    IMPORTANT_ONLY = "important_only"
    STANDARD = "standard"
    STRICT = "strict"
    EXPERT = "expert"

    @property
    def minimum_severity(self) -> Severity:
        return {
            QuestionLevel.MINIMAL: Severity.CRITICAL_REVIEW,
            QuestionLevel.IMPORTANT_ONLY: Severity.HIGH_WARNING,
            QuestionLevel.STANDARD: Severity.WARNING,
            QuestionLevel.STRICT: Severity.NOTICE,
            QuestionLevel.EXPERT: Severity.INFO,
        }[self]


@dataclass(frozen=True)
class Decision:
    """One recorded answer. Serialisable, so a session can be replayed."""

    issue_id: str
    action: Action
    treatment: str | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "action": self.action.value,
            "treatment": self.treatment,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Decision:
        return cls(
            issue_id=payload["issue_id"],
            action=Action(payload["action"]),
            treatment=payload.get("treatment"),
            reason=payload.get("reason", ""),
        )


@dataclass(frozen=True)
class Question:
    """A finding presented for decision, with everything needed to decide."""

    issue: Issue
    position: int
    total: int

    @property
    def issue_id(self) -> str:
        return self.issue.id

    @property
    def options(self) -> tuple[TreatmentCandidate, ...]:
        """Only treatments that can actually be carried out.

        Offering an option with no implementation would be a menu item that
        does nothing -- worse than not offering it.
        """
        return tuple(t for t in self.issue.treatments if has_action(t.name))

    @property
    def recommended(self) -> TreatmentCandidate | None:
        best = self.issue.recommended_treatment
        return best if best and has_action(best.name) else None

    def render(self) -> str:
        """Format the decision card (plan, 'Decision Cards')."""
        repair_class, reasons = self.issue.triage()
        lines = [
            f"Issue {self.position} of {self.total}",
            f"  id         {self.issue.id}",
            f"  columns    {', '.join(self.issue.columns) or '-'}",
            f"  severity   {self.issue.severity.name}",
            f"  class      {repair_class.name}",
            f"  rows       {self.issue.affected_row_count}",
            "",
            f"Problem    {self.issue.evidence.summary}",
            f"Evidence   detection confidence {self.issue.detection_confidence:.0%}, "
            f"source {self.issue.rule_source.value}",
        ]
        if reasons:
            lines += ["", "Why automatic mode did not act:"]
            lines += [f"  - {r}" for r in reasons]
        if self.issue.notes:
            lines += ["", f"Note       {self.issue.notes}"]

        if self.options:
            lines += ["", "Options:"]
            for option in sorted(self.options, key=lambda t: -t.repair_confidence):
                mark = "*" if self.recommended and option.name == self.recommended.name else " "
                lines.append(
                    f"  {mark} {option.name:32s} confidence {option.repair_confidence:.0%}  "
                    f"{option.reversibility.value}"
                )
                lines.append(f"      {option.description}")
        else:
            lines += [
                "",
                "No treatment can be carried out for this finding. The correct "
                "value is not inferable from the data.",
            ]

        lines += ["", "  skip / waive(reason) / leave_unresolved"]
        return "\n".join(lines)


@dataclass
class GuidedSession:
    """An interactive preparation run, driven one decision at a time."""

    frame: pd.DataFrame
    scan_result: ScanResult
    context: dict[str, Any]
    level: QuestionLevel = QuestionLevel.STANDARD
    decisions: dict[str, Decision] = field(default_factory=dict)
    _auto_plan: RepairPlan | None = None
    _auto_audit: AuditLog | None = None

    # -- the queue ----------------------------------------------------------

    @property
    def queue(self) -> list[Issue]:
        """Findings needing a decision, ordered by dependency then urgency.

        Representation problems come first. Asking about an outlier in a column
        still stored as text means asking about a number nobody has computed
        yet.
        """
        from .core.operations import SCOPE_ORDER, OperationScope

        def dependency_rank(issue: Issue) -> int:
            best = issue.recommended_treatment
            if best is None:
                return SCOPE_ORDER[OperationScope.VALUE]
            operation = build_operation(issue, best)
            if operation is None:
                return SCOPE_ORDER[OperationScope.VALUE]
            return SCOPE_ORDER[operation.scope]

        candidates = [
            i
            for i in self.scan_result.issues
            if not i.repair_class.is_autonomous and i.severity >= self.level.minimum_severity
        ]
        return sorted(
            candidates,
            key=lambda i: (dependency_rank(i), -i.severity, -i.affected_row_count),
        )

    @property
    def questions(self) -> list[Question]:
        pending = [i for i in self.queue if i.id not in self.decisions]
        total = len(pending)
        return [Question(issue, n, total) for n, issue in enumerate(pending, 1)]

    def next_question(self) -> Question | None:
        questions = self.questions
        return questions[0] if questions else None

    @property
    def answered(self) -> int:
        return len(self.decisions)

    @property
    def remaining(self) -> int:
        return len(self.questions)

    @property
    def progress(self) -> float:
        total = self.answered + self.remaining
        return 1.0 if total == 0 else self.answered / total

    # -- answering ----------------------------------------------------------

    def answer(
        self,
        issue_id: str,
        action: Action | str = Action.USE_RECOMMENDATION,
        *,
        treatment: str | None = None,
        reason: str = "",
    ) -> GuidedSession:
        """Record a decision. Nothing is applied until :meth:`finish`."""
        issue = self.scan_result.get(issue_id)
        action = Action(action) if isinstance(action, str) else action

        if action is Action.USE_RECOMMENDATION:
            best = issue.recommended_treatment
            if best is None:
                raise SmartPrepAmbiguityError(
                    f"{issue_id} has no recommended treatment -- the correct value is "
                    "not inferable from the data. Choose 'waive' or 'leave_unresolved'."
                )
            treatment = best.name
        elif action is Action.CHOOSE_ALTERNATIVE:
            if treatment is None:
                raise ValueError("choose_alternative requires treatment=...")
            names = {t.name for t in issue.treatments}
            if treatment not in names:
                raise ValueError(
                    f"{treatment!r} is not a treatment for {issue_id}; available: {sorted(names)}"
                )
        elif action is Action.WAIVE and not reason.strip():
            raise ValueError("waiving a finding requires a reason; that is the point of it")

        if treatment is not None and not has_action(treatment):
            raise SmartPrepAmbiguityError(
                f"treatment {treatment!r} is described but not implemented yet, so it "
                "cannot be applied. Choose another option, or leave the finding "
                "unresolved."
            )

        self.decisions[issue_id] = Decision(issue_id, action, treatment, reason)
        return self

    def accept_all_recommendations(self, *, max_severity: Severity | None = None) -> GuidedSession:
        """Answer every open question with its recommendation.

        A convenience for review sessions, not a way to bypass review: findings
        with no workable treatment are still left unresolved rather than forced.
        """
        for question in list(self.questions):
            if max_severity is not None and question.issue.severity > max_severity:
                continue
            if question.recommended is None:
                self.decisions[question.issue_id] = Decision(
                    question.issue_id,
                    Action.LEAVE_UNRESOLVED,
                    reason="no workable treatment exists",
                )
            else:
                self.answer(question.issue_id, Action.USE_RECOMMENDATION)
        return self

    def skip(self, issue_id: str, reason: str = "") -> GuidedSession:
        return self.answer(issue_id, Action.SKIP, reason=reason)

    def waive(self, issue_id: str, reason: str) -> GuidedSession:
        return self.answer(issue_id, Action.WAIVE, reason=reason)

    # -- applying -----------------------------------------------------------

    def finish(self) -> PreparationResult:
        """Apply the safe repairs plus every decision, and re-verify.

        Auto-safe repairs are applied here too, so a guided session is never
        worse-informed than an automatic one -- both run the same engine.
        """
        from . import __version__

        audit = self._auto_audit if self._auto_audit is not None else AuditLog()
        plan = RepairPlan()
        if self._auto_plan is not None:
            for operation in self._auto_plan.operations:
                plan.add(operation)

        waivers: dict[str, str] = {}

        for issue_id, decision in self.decisions.items():
            issue = self.scan_result.get(issue_id)

            if decision.action in (Action.SKIP, Action.LEAVE_UNRESOLVED):
                audit.append(self._record(issue, decision, "left unresolved by the user"))
                continue

            if decision.action is Action.WAIVE:
                waivers[issue_id] = decision.reason
                audit.append(self._record(issue, decision, f"waived: {decision.reason}"))
                continue

            treatment = next(t for t in issue.treatments if t.name == decision.treatment)
            chosen = build_operation(issue, treatment)
            if chosen is None:  # pragma: no cover - guarded in answer()
                audit.append(self._record(issue, decision, "treatment not implemented"))
                continue
            plan.add(chosen)

        executor = RepairExecutor(decision_source=DecisionSource.USER)
        outcome = executor.run(self.frame, plan, audit=audit)
        after = scan(outcome.frame, **self.context)

        result = PreparationResult(
            raw_df=self.frame.copy(deep=True),
            clean_df=outcome.frame,
            before_scan=self.scan_result,
            after_scan=after,
            audit=outcome.audit,
            plan=plan,
            snapshots=outcome.snapshots,
            environment=EnvironmentManifest.capture(__version__),
        )
        for issue_id, reason in waivers.items():
            # A waiver survives only if the finding survived the repairs.
            if issue_id in {i.id for i in after.issues}:
                result.waivers[issue_id] = reason
        return result

    @staticmethod
    def _record(issue: Issue, decision: Decision, reason: str) -> AuditRecord:
        return AuditRecord(
            operation_id=AuditRecord.next_id("USER"),
            operation=decision.action.value,
            issue_ids=(issue.id,),
            columns=issue.columns,
            rows=issue.rows,
            parameters={"treatment": decision.treatment or ""},
            reason=reason,
            rule_source=RuleSource.USER_DEFINED,
            repair_class=issue.repair_class,
            decision_source=DecisionSource.USER,
            repair_confidence=0.0,
            reversible=True,
            applied=False,
        )

    # -- persistence --------------------------------------------------------

    def export_decisions(self) -> str:
        """Serialise the session so it can be replayed on new data."""
        return json.dumps(
            {
                "schema_version": 1,
                "level": self.level.value,
                "decisions": [d.to_dict() for d in self.decisions.values()],
            },
            indent=2,
            ensure_ascii=False,
        )

    def load_decisions(self, payload: str | dict[str, Any]) -> GuidedSession:
        """Replay recorded decisions.

        Decisions for findings that are not present are ignored rather than
        raising: data changes, and a stale answer should not block a run.
        """
        data = json.loads(payload) if isinstance(payload, str) else payload
        known = {i.id for i in self.scan_result.issues}
        for entry in data.get("decisions", []):
            decision = Decision.from_dict(entry)
            if decision.issue_id in known:
                self.decisions[decision.issue_id] = decision
        return self

    # -- display ------------------------------------------------------------

    def summary(self) -> str:
        by_class: dict[str, int] = {}
        for issue in self.queue:
            by_class[issue.repair_class.name] = by_class.get(issue.repair_class.name, 0) + 1
        lines = [
            "Guided Review Queue",
            "",
            f"  level      {self.level.value}",
            f"  answered   {self.answered}",
            f"  remaining  {self.remaining}",
            "",
        ]
        for name, count in sorted(by_class.items()):
            lines.append(f"  {name:30s} {count}")
        return "\n".join(lines)

    def __repr__(self) -> str:  # pragma: no cover - display only
        return f"<GuidedSession answered={self.answered} remaining={self.remaining}>"


def guided_prepare(
    frame: pd.DataFrame,
    *,
    level: QuestionLevel | str = QuestionLevel.STANDARD,
    decisions: str | dict[str, Any] | None = None,
    only_unresolved: ScanResult | PreparationResult | None = None,
    **context: Any,
) -> GuidedSession:
    """Scan, then hand back a session of the decisions only a human can make.

    ``decisions`` replays a previously exported session, so a reviewed dataset
    can be re-prepared without answering the same questions again.

    ``only_unresolved`` continues from an automatic run rather than starting
    over -- the scan, the safe repairs and the issue ids are all carried
    forward.
    """
    if not isinstance(frame, pd.DataFrame):
        raise TypeError(f"guided_prepare() expects a DataFrame, got {type(frame).__name__}")

    level = QuestionLevel(level) if isinstance(level, str) else level

    if isinstance(only_unresolved, PreparationResult):
        source_frame = only_unresolved.raw_df
        result = only_unresolved.before_scan
        if not context:
            context = dict(only_unresolved.context)
    else:
        source_frame = frame
        result = (
            only_unresolved if isinstance(only_unresolved, ScanResult) else scan(frame, **context)
        )

    # The plan and audit are always rebuilt from the scan rather than carried
    # over. Reusing a completed audit log would replay its applied records into
    # a second run and double every count.
    plan, audit, _ = _build_plan(result)
    session = GuidedSession(
        frame=source_frame.copy(deep=True),
        scan_result=result,
        context=context,
        level=level,
    )
    session._auto_plan = plan
    session._auto_audit = audit

    if decisions is not None:
        session.load_decisions(decisions)
    return session


def _open_guided(self: PreparationResult, **overrides: Any) -> GuidedSession:
    """Continue an automatic run interactively (plan, 'Guided Mode handoff').

    The user must not have to restart the analysis: the scan, the applied
    repairs, the issue ids and the audit all carry across.
    """
    context = dict(self.context)
    context.update(overrides)
    return guided_prepare(self.raw_df, only_unresolved=self, **context)


PreparationResult.open_guided = _open_guided  # type: ignore[attr-defined]
