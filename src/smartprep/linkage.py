"""Entity resolution -- which records are the same thing.

``Candidate pair -> evidence -> guided decision -> merge / keep / map -> audit``

The temptation in record linkage is to pick a similarity threshold and merge
above it. That produces a number nobody can defend: at 0.85 two branches of
one company become one, at 0.86 they stay apart, and the dataset's conclusions
turn on a constant somebody chose on a Tuesday.

So nothing here merges anything. Linkage produces **candidate pairs with
evidence**, and every pair becomes an ordinary
:class:`~smartprep.core.issue.Issue` that goes through the same triage and the
same guided review as every other finding. There is no separate decision
system, no separate audit, and no threshold that silently decides.

What the similarity score *is* for: ordering the queue, so a reviewer sees the
obvious matches first and the hard ones while they still have patience.

The cost of comparing every record with every other is quadratic, so records
are **blocked** first: grouped by a cheap key, and compared only within a
group. Blocking trades recall for tractability, and the report says how much
was skipped rather than presenting the survivors as if they were everything.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

from .core.enums import (
    DomainSensitivity,
    InformationLossRisk,
    IssueCategory,
    Reversibility,
    RuleSource,
    Severity,
    StatisticalImpact,
)
from .core.issue import Evidence, Issue, TreatmentCandidate

__all__ = ["FieldMatch", "CandidatePair", "LinkageReport", "link"]

#: Most pairs one block may contribute before the block is refused.
#:
#: Blocking exists to make the comparison tractable, and a block key that does
#: not discriminate silently gives that up: every name beginning "Company"
#: shares a four-character prefix, so a ten-thousand-row file becomes one
#: block and fifty million comparisons. The failure looks like a hang, which
#: is the worst way for a library to say "your block key is wrong".
_MAX_BLOCK_PAIRS = 2_000_000


def _fold(value: Any) -> str:
    """Normalise for comparison without destroying non-Latin text.

    NFKD and drop combining marks, then casefold. Never ASCII-encode: that
    erases every Arabic, Chinese or Cyrillic name to the empty string, and
    empty strings match each other perfectly.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    stripped = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


@dataclass(frozen=True)
class FieldMatch:
    """How one field compared, and how it was compared.

    The comparator is recorded because "0.9 similar" means different things
    for a name and a postcode, and a reviewer deciding on the pair needs to
    know which they are looking at.
    """

    field: str
    left: Any
    right: Any
    score: float
    comparator: str

    @property
    def agrees(self) -> bool:
        return self.score >= 0.999

    def describe(self) -> str:
        if self.agrees:
            return f"{self.field}: identical"
        return (
            f"{self.field}: {self.left!r} vs {self.right!r} ({self.score:.0%} by {self.comparator})"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "left": str(self.left),
            "right": str(self.right),
            "score": round(self.score, 4),
            "comparator": self.comparator,
            "agrees": self.agrees,
        }


@dataclass(frozen=True)
class CandidatePair:
    """Two records that might be one, and the evidence either way."""

    left: int
    right: int
    matches: tuple[FieldMatch, ...]
    block: str = ""

    @property
    def score(self) -> float:
        """Mean field similarity. An ordering, never a decision."""
        return sum(m.score for m in self.matches) / len(self.matches) if self.matches else 0.0

    @property
    def agreeing(self) -> tuple[str, ...]:
        return tuple(m.field for m in self.matches if m.agrees)

    @property
    def disagreeing(self) -> tuple[str, ...]:
        return tuple(m.field for m in self.matches if not m.agrees)

    def describe(self) -> str:
        return (
            f"rows {self.left} and {self.right} agree on "
            f"{', '.join(self.agreeing) or 'nothing'}"
            + (f"; differ on {', '.join(self.disagreeing)}" if self.disagreeing else "")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "left": self.left,
            "right": self.right,
            "score": round(self.score, 4),
            "block": self.block,
            "matches": [m.to_dict() for m in self.matches],
            "describe": self.describe(),
        }


@dataclass
class LinkageReport:
    """Candidate pairs, and an honest account of what was not compared."""

    fields: tuple[str, ...]
    rows: int
    pairs: list[CandidatePair] = field(default_factory=list)
    blocks: int = 0
    compared: int = 0
    #: Pairs that blocking never brought together. Reported because a linkage
    #: run that only shows what it found reads as exhaustive.
    skipped: int = 0
    largest_block: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def recall_note(self) -> str:
        total = self.rows * (self.rows - 1) // 2
        if not total:
            return "nothing to compare"
        share = self.compared / total
        return (
            f"{self.compared:,} of {total:,} possible pairs compared "
            f"({share:.1%}); blocking skipped the rest"
        )

    def summary(self) -> str:
        lines = [
            f"linkage on {', '.join(self.fields)}: {len(self.pairs):,} candidate pairs "
            f"from {self.rows:,} rows",
            f"  {self.blocks:,} blocks, largest {self.largest_block:,} rows",
            f"  {self.recall_note}",
        ]
        for pair in self.pairs[:5]:
            lines.append(f"  {pair.score:.0%}  {pair.describe()}")
        if len(self.pairs) > 5:
            lines.append(f"  ... and {len(self.pairs) - 5:,} more")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fields": list(self.fields),
            "rows": self.rows,
            "pairs": [p.to_dict() for p in self.pairs[:500]],
            "pair_count": len(self.pairs),
            "blocks": self.blocks,
            "compared": self.compared,
            "skipped": self.skipped,
            "largest_block": self.largest_block,
            "recall_note": self.recall_note,
            "issues": [i.id for i in self.issues],
        }


def _is_number(value: Any) -> bool:
    """Whether a value is numeric, including NumPy and pandas scalar types."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        or (hasattr(value, "dtype") and pd.api.types.is_numeric_dtype(value.dtype))
    )


def _compare(left: Any, right: Any) -> tuple[float, str]:
    """Similarity of two values, and the comparator that produced it."""
    if pd.isna(left) or pd.isna(right):
        # Missing is not evidence of agreement or disagreement. Scoring it as
        # either would let absent data argue for a merge.
        return 0.5, "unknown (a value is missing)"

    # numbers, including numpy's -- np.int64 is not a Python int, so an
    # isinstance check against the builtins alone silently sends every
    # numeric column down the string path, where 1200 and 1205 score 75%
    # instead of 99.6%.
    if _is_number(left) and _is_number(right):
        scale = max(abs(float(left)), abs(float(right)), 1.0)
        return max(0.0, 1.0 - abs(float(left) - float(right)) / scale), "numeric distance"

    a, b = _fold(left), _fold(right)
    if not a or not b:
        return 0.5, "unknown (a value is empty)"
    if a == b:
        return 1.0, "exact after folding"
    return SequenceMatcher(None, a, b).ratio(), "sequence similarity"


def link(
    frame: pd.DataFrame,
    fields: tuple[str, ...],
    *,
    block_on: str | None = None,
    block_prefix: int = 4,
    minimum: float = 0.7,
    limit: int = 500,
) -> LinkageReport:
    """Find records that might be the same entity. Merges nothing.

    Parameters
    ----------
    fields:
        Columns to compare. More fields make a pair easier to judge, not
        harder: a reviewer deciding on a name alone is guessing.
    block_on:
        Column whose value groups records for comparison. Defaults to the
        first field, blocked on its first ``block_prefix`` folded characters.
    minimum:
        Pairs below this mean similarity are not surfaced. This is a
        **queue cutoff**, not a merge threshold -- nothing above it is
        merged either.
    limit:
        Most pairs to return, highest score first.
    """
    missing = [f for f in fields if f not in frame.columns]
    if missing:
        raise KeyError(f"no such columns: {', '.join(missing)}")
    if not fields:
        raise ValueError("linkage needs at least one field to compare")

    report = LinkageReport(fields=tuple(fields), rows=len(frame))

    key_column = block_on or fields[0]
    blocks: dict[str, list[int]] = {}
    for position in range(len(frame)):
        raw = frame.iloc[position][key_column]
        key = _fold(raw)[:block_prefix] or "\x00"
        blocks.setdefault(key, []).append(position)

    report.blocks = len(blocks)
    report.largest_block = max((len(v) for v in blocks.values()), default=0)

    oversized = {
        key: len(members)
        for key, members in blocks.items()
        if len(members) * (len(members) - 1) // 2 > _MAX_BLOCK_PAIRS
    }
    if oversized:
        worst, size = max(oversized.items(), key=lambda kv: kv[1])
        raise ValueError(
            f"the block key put {size:,} records into the block {worst!r}, which "
            f"is {size * (size - 1) // 2:,} comparisons -- blocking is supposed "
            "to avoid exactly that. The key does not discriminate: try a longer "
            "block_prefix, or block_on a column whose values differ early "
            "(a postcode rather than a company name that starts 'Company')."
        )

    found: list[CandidatePair] = []
    for key, positions in blocks.items():
        for i, left in enumerate(positions):
            for right in positions[i + 1 :]:
                report.compared += 1
                matches = []
                for name in fields:
                    a = frame.iloc[left][name]
                    b = frame.iloc[right][name]
                    score, comparator = _compare(a, b)
                    matches.append(FieldMatch(name, a, b, score, comparator))
                pair = CandidatePair(left, right, tuple(matches), block=key)
                if pair.score >= minimum:
                    found.append(pair)

    total = report.rows * (report.rows - 1) // 2
    report.skipped = max(0, total - report.compared)
    found.sort(key=lambda p: p.score, reverse=True)
    report.pairs = found[:limit]
    report.issues = _issues_for(report)
    return report


def _issues_for(report: LinkageReport) -> list[Issue]:
    """One finding per candidate pair, in the ordinary shape.

    Deliberately not a separate review system: a possible duplicate entity
    goes through the same triage, the same ladder and the same guided queue as
    a mistyped date, and its resolution lands in the same audit.
    """
    issues: list[Issue] = []
    for pair in report.pairs:
        evidence_lines = "; ".join(m.describe() for m in pair.matches)
        issues.append(
            Issue(
                id=f"LINK-{pair.left}-{pair.right}",
                category=IssueCategory.CONFLICTING_DUPLICATE,
                severity=Severity.WARNING,
                # Confidence that these records *resemble* each other. Whether
                # they are the same entity is a different question, and it is
                # the one the treatments refuse to answer.
                detection_confidence=round(pair.score, 4),
                rule_source=RuleSource.INFERRED_RELATIONSHIP,
                columns=report.fields,
                evidence=Evidence(
                    summary=f"{pair.describe()} -- {evidence_lines}",
                    affected_rows=(pair.left, pair.right),
                    details=pair.to_dict(),
                ),
                detector="linkage",
                treatments=(
                    TreatmentCandidate(
                        name="merge_records",
                        description="Treat these as one entity and combine them",
                        repair_confidence=0.0,
                        reversibility=Reversibility.IRREVERSIBLE,
                        information_loss_risk=InformationLossRisk.HIGH,
                        statistical_impact=StatisticalImpact.MATERIAL,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                    ),
                    TreatmentCandidate(
                        name="keep_separate",
                        description="Two similar records that are genuinely different",
                        repair_confidence=0.0,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                    ),
                    TreatmentCandidate(
                        name="map_to_canonical",
                        description=(
                            "Keep both rows, and record that they refer to one "
                            "entity -- reversible, unlike a merge"
                        ),
                        repair_confidence=0.0,
                        reversibility=Reversibility.REVERSIBLE,
                        domain_sensitivity=DomainSensitivity.REQUIRES_DOMAIN_RULE,
                    ),
                ),
                notes=(
                    "similarity orders the queue; it does not decide. Two branches "
                    "of one company and one company twice look identical from the "
                    "fields alone"
                ),
            )
        )
    return issues
