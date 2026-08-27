"""What SmartPrep can actually do, in one machine-readable place.

Four documents used to claim what exists — the README's capability table, the
architecture record's status lines, the changelog, and the docstrings — and
keeping four hand-written lists in step is a job nobody schedules and everybody
loses. They drifted within a single day of work: the README announced
drag-and-drop composition as implemented in one row and "not yet" three rows
below it, both true of different weeks.

So the claims live here, once, next to the code that has to honour them, and a
test checks three things:

* every capability marked implemented names a real, importable symbol;
* no capability marked planned names one that already exists;
* the README's table matches this registry row for row.

A claim nothing tests is a claim that goes stale. This is the same lesson as
the ``Mark`` enum that declared marks nothing could draw and the ``interactive``
flag that no renderer read — applied to prose instead of to code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

__all__ = ["Status", "Capability", "CAPABILITIES", "capability_table", "check_capabilities"]


class Status(Enum):
    """How far along a capability is. Deliberately coarse.

    Finer grades invite the wishful middle -- "mostly done", "in progress" --
    which is where an overclaim hides. A thing either works, or it is a plan
    with a version number on it.
    """

    IMPLEMENTED = "implemented"
    PARTIAL = "partial"
    PLANNED = "planned"

    @property
    def label(self) -> str:
        return {"implemented": "**Implemented**", "partial": "Partial", "planned": "Planned"}[
            self.value
        ]


@dataclass(frozen=True)
class Capability:
    """One claim, and what would prove it.

    ``proof`` names a symbol importable from ``smartprep``. An implemented
    capability whose proof cannot be imported is a lie the test suite catches;
    a planned capability whose proof *can* be imported is documentation that
    has fallen behind the code, which is the less harmful direction but still
    wrong.
    """

    name: str
    summary: str
    status: Status
    since: str = ""
    #: Attribute path on the ``smartprep`` package, e.g. ``"studio"`` or
    #: ``"viz.compose"``. Empty when nothing in the public API would show it.
    proof: str = ""
    #: Milestone this is scheduled for, when one has been decided. Empty is
    #: a legitimate answer: a planned capability with no chosen release is
    #: honest, and naming a version to look decisive is not. Whatever is here
    #: must be *ahead* of the published version -- see ``check_capabilities``.
    planned_for: str = ""
    #: Stated limits of what *is* implemented. A capability with a caveat
    #: nobody wrote down reads as a capability without one.
    caveat: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "summary": self.summary,
            "status": self.status.value,
            "since": self.since,
            "proof": self.proof,
            "planned_for": self.planned_for,
            "caveat": self.caveat,
        }


_I, _P, _PARTIAL = Status.IMPLEMENTED, Status.PLANNED, Status.PARTIAL

#: The single source of truth. Ordered as the README presents them.
CAPABILITIES: tuple[Capability, ...] = (
    Capability(
        "scan",
        "`sp.scan()` — full diagnosis, no mutation",
        _I,
        since="0.1.0.dev0",
        proof="scan",
    ),
    Capability(
        "auto_prepare",
        "`sp.auto_prepare()` — apply only what is provably safe",
        _I,
        since="0.1.0.dev0",
        proof="auto_prepare",
    ),
    Capability(
        "guided_prepare",
        "`sp.guided_prepare()` — human-in-the-loop decisions",
        _I,
        since="0.2.0.dev0",
        proof="guided_prepare",
    ),
    Capability(
        "clean",
        "`sp.clean()` — convenience alias",
        _I,
        since="0.1.0.dev0",
        proof="clean",
    ),
    Capability(
        "detectors",
        "14 detectors, issue model, triage policy",
        _I,
        since="0.1.0.dev0",
        proof="Issue",
    ),
    Capability(
        "audit",
        "Audit trail, snapshots, rollback, idempotence",
        _I,
        since="0.1.0.dev0",
        proof="AuditLog",
    ),
    Capability(
        "health",
        "Data health score",
        _I,
        since="0.1.0.dev0",
        proof="DataHealthScore",
    ),
    Capability(
        "completion",
        "`verified_df`, `finalize()`, waivers",
        _I,
        since="0.2.0.dev0",
        proof="CompletionState",
    ),
    Capability(
        "text_reports",
        "Markdown + JSON reports",
        _I,
        since="0.2.0.dev0",
        proof="publish",
    ),
    Capability(
        "preprocessing_advice",
        "`recommend_preprocessing()` — goal-aware advice",
        _I,
        since="0.2.0.dev0",
        proof="recommend_preprocessing",
    ),
    Capability(
        "preprocessing",
        "`Preprocessor` — impute, encode, scale, leakage guard",
        _I,
        since="0.2.0.dev0",
        proof="Preprocessor",
    ),
    Capability(
        "validation",
        "`ValidationPlan` and `DataContract`",
        _I,
        since="0.2.0.dev0",
        proof="ValidationPlan",
    ),
    Capability(
        "privacy",
        "`PrivacyScanner` and PII transformations",
        _I,
        since="0.2.0.dev0",
        proof="PrivacyScanner",
    ),
    Capability(
        "drift",
        "Drift and cleaning drift",
        _I,
        since="0.2.0.dev0",
        proof="cleaning_drift",
    ),
    Capability(
        "eda",
        "`profile()`, `associations()`, `missingness()`",
        _I,
        since="0.3.0.dev0",
        proof="profile",
    ),
    Capability(
        "chart_spec",
        "`ChartSpec` + SVG renderer",
        _I,
        since="0.3.0.dev0",
        proof="ChartSpec",
    ),
    Capability(
        "html_report",
        "Self-contained HTML reports",
        _I,
        since="0.3.0.dev0",
        proof="publish",
    ),
    Capability(
        "renderer_backends",
        "Matplotlib and Plotly renderers",
        _I,
        since="0.5.0.dev0",
        proof="viz.to_matplotlib",
    ),
    Capability(
        "chart_export",
        "PNG / PDF / SVG / HTML chart export",
        _I,
        since="0.5.0.dev0",
        proof="viz.save_chart",
    ),
    Capability(
        "publishing",
        "PDF, PowerPoint and notebook publishing",
        _I,
        since="0.5.0.dev0",
        proof="publish",
    ),
    Capability(
        "interaction_state",
        "Shared interaction state, stable row identity",
        _I,
        since="0.6.0.dev0",
        proof="StudioState",
    ),
    Capability(
        "visual_builder",
        "Drag-and-drop composition, keyboard equivalent",
        _I,
        since="0.6.0.dev0",
        proof="compose",
        caveat=(
            "The portable Studio composes from charts precomputed in Python. "
            "A pairing nobody precomputed is answered with the line of Python "
            "that builds it, because the page does not aggregate in the browser."
        ),
    ),
    Capability(
        "linked_brushing",
        "Linked brushing and cross-filtering",
        _I,
        since="0.6.0.dev0",
        proof="Selection",
        caveat=(
            "Marks are individually selectable up to 250 points; past that a "
            "chart is filtered rather than picked at, and it says so."
        ),
    ),
    Capability(
        "treatment_sandbox",
        "Smart data grid, treatment sandbox",
        _I,
        since="0.6.0.dev0",
        proof="preview_candidates",
    ),
    Capability(
        "studio",
        "`sp.studio()` — grid, builder, sandbox, brushing, stages",
        _I,
        since="0.4.0.dev0",
        proof="studio",
    ),
    Capability(
        "faceting",
        "Faceting and multi-series composition",
        _I,
        since="0.7.0.dev0",
        proof="ChartSpec",
        caveat=(
            "Small multiples share one scale and cap at 12 panels, because "
            "more cannot be compared at a glance. Faceting an aggregate is "
            "refused: aggregated rows no longer line up with the frame, so "
            "the groups cannot be attached honestly."
        ),
    ),
    Capability(
        "visual_workflow",
        "Visual Workflow Builder / Pipeline Canvas",
        _I,
        since="0.7.0.dev0",
        proof="Workflow",
        caveat=(
            "Stages are a fixed, ordered set; a node filters the plan the core "
            "already built rather than implementing anything. Running every "
            "stage produces the frame and audit auto_prepare produces."
        ),
    ),
    Capability(
        "entity_resolution",
        "Entity resolution, record linkage",
        _I,
        since="0.8.0.dev0",
        proof="link",
        caveat=(
            "Produces candidate pairs with evidence and routes each through "
            "guided review. It merges nothing: similarity orders the queue, it "
            "does not decide. Blocking trades recall for tractability and the "
            "report says how many pairs were never compared."
        ),
    ),
    Capability(
        "time_series",
        "Time-series and panel diagnostics",
        _I,
        since="0.8.0.dev0",
        proof="panel",
        caveat=(
            "Diagnosis, not modelling: cadence, gaps, duplicate timestamps, "
            "ordering, timezones and stale runs; panel balance, duplicate "
            "entity-time pairs and within/between variance. No forecasting, "
            "no estimation."
        ),
    ),
    Capability(
        "missingness_mechanism",
        "Missingness mechanism evidence (MCAR testing)",
        _I,
        since="1.0.1",
        proof="mechanism",
        caveat=(
            "Rules out MCAR; never claims MNAR. MAR and MNAR differ only in "
            "whether absence depends on the unobserved value, which no test on "
            "observed data can see. p-values carry a Holm-Bonferroni correction."
        ),
    ),
    Capability(
        "anomaly_detection",
        "Multivariate and contextual outliers",
        _I,
        since="1.0.1",
        proof="anomalies",
        caveat=(
            "Mahalanobis distance for joint outliers, robust within-group "
            "deviation for contextual ones. Neither repairs anything: an "
            "outlier is a question about a row, not a defect in it."
        ),
    ),
    Capability(
        "rule_learning",
        "Learn validation rules from a trusted sample",
        _I,
        since="1.0.1",
        proof="learn_rules",
        caveat=(
            "Every learned rule carries its evidence, a confidence and what "
            "would falsify it, and the learner abstains where the evidence is "
            "thin. It validates nothing: the plan is meant to be read and "
            "edited before it is run."
        ),
    ),
    Capability(
        "presentation",
        "Journal-convention tables in text, Markdown, HTML and LaTeX",
        _I,
        since="1.0.2",
        proof="Table",
        caveat=(
            "The view computes nothing: every figure comes from the object it "
            "describes, and a test asserts the two agree. Plain text is "
            "transliterated to ASCII so a cp1252 console cannot raise on it."
        ),
    ),
    Capability(
        "multi_backend",
        "Multi-backend execution",
        _P,
        # No milestone: the review was right that inventing "v1.1" to
        # silence an inconsistency promises a release nobody has decided on.
        # A bare "Planned" is the honest status until one is chosen.
    ),
)


def capability_table() -> str:
    """The registry as the Markdown table the README carries.

    Generated rather than transcribed, so the README cannot say something the
    package does not.
    """
    lines = ["| Capability | Status |", "|---|---|"]
    for capability in CAPABILITIES:
        status = capability.status.label
        if capability.status is not Status.IMPLEMENTED and capability.planned_for:
            status = f"{status} (v{capability.planned_for})"
        lines.append(f"| {capability.summary} | {status} |")
    return "\n".join(lines)


def check_capabilities() -> list[str]:
    """Problems with the registry itself. Empty means it is honest.

    Returns complaints rather than raising, so a caller can print all of them
    at once instead of fixing them one import error at a time.
    """
    import importlib

    problems: list[str] = []
    root = importlib.import_module("smartprep")

    for capability in CAPABILITIES:
        if not capability.proof:
            if capability.status is Status.IMPLEMENTED:
                problems.append(f"{capability.name}: claimed implemented with nothing to prove it")
            continue

        target: Any = root
        found = True
        for part in capability.proof.split("."):
            target = getattr(target, part, None)
            if target is None:
                found = False
                break

        if capability.status is Status.IMPLEMENTED and not found:
            problems.append(
                f"{capability.name}: claimed implemented, but smartprep."
                f"{capability.proof} does not exist"
            )
        if capability.status is Status.PLANNED and found:
            problems.append(
                f"{capability.name}: claimed planned, but smartprep."
                f"{capability.proof} already exists"
            )

    for capability in CAPABILITIES:
        if capability.status is Status.IMPLEMENTED and capability.planned_for:
            problems.append(f"{capability.name}: implemented, yet scheduled for a milestone")

        # A milestone in the past is the defect this check exists for: at
        # 1.0.0, "Planned (v0.9)" tells a reader the project has missed a
        # deadline it never had. An unset milestone is fine; a stale one is
        # not.
        if capability.planned_for:
            from packaging.version import InvalidVersion, Version

            try:
                scheduled = Version(capability.planned_for)
                published = Version(root.__version__)
            except InvalidVersion:  # pragma: no cover - malformed by hand
                problems.append(f"{capability.name}: {capability.planned_for!r} is not a version")
            else:
                if scheduled <= published:
                    problems.append(
                        f"{capability.name}: planned for {capability.planned_for}, "
                        f"which {root.__version__} has already passed"
                    )

    return problems
