"""Text integrity: category variants and genuine Unicode damage.

The hard requirement here is asymmetric. Missing ``Manufacturing`` spelled with a
dotless i is a miss; flagging ``Algerie`` spelled correctly in French is worse,
because it teaches users the tool cannot be trusted with their language.
"""

from __future__ import annotations

import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

from ..core.enums import (
    DomainSensitivity,
    InformationLossRisk,
    IssueCategory,
    Reversibility,
    RuleSource,
    Severity,
)
from ..core.issue import Evidence, Issue, TreatmentCandidate
from .base import register

__all__ = [
    "CategoryVariantDetector",
    "UnicodeConfusableDetector",
    "CONFUSABLES",
    "INVISIBLE",
]


#: Characters that look like ASCII letters but are not. Restricted to genuine
#: homoglyph risks -- accented Latin letters are *not* included, because they
#: carry meaning in French, Spanish, Portuguese and many other languages.
CONFUSABLES: dict[str, str] = {
    "ı": "i",  # LATIN SMALL LETTER DOTLESS I
    "İ": "I",  # LATIN CAPITAL LETTER I WITH DOT ABOVE
    "а": "a",  # CYRILLIC SMALL LETTER A
    "е": "e",  # CYRILLIC SMALL LETTER IE
    "о": "o",  # CYRILLIC SMALL LETTER O
    "р": "p",  # CYRILLIC SMALL LETTER ER
    "с": "c",  # CYRILLIC SMALL LETTER ES
    "х": "x",  # CYRILLIC SMALL LETTER HA
    "һ": "h",  # CYRILLIC SMALL LETTER SHHA
    "А": "A",
    "Е": "E",
    "О": "O",
    "Р": "P",
    "С": "C",
    "Х": "X",
    "‐": "-",  # HYPHEN
    "–": "-",  # EN DASH
    "—": "-",  # EM DASH
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
}

#: Characters that are always damage: invisible, zero-width or control.
INVISIBLE = {"​", "‌", "‍", "﻿", " ", " ", " "}


def _is_legitimate_letter(ch: str) -> bool:
    """True for accented Latin letters and non-Latin scripts used as themselves.

    A character is legitimate when stripping its combining marks yields a plain
    ASCII letter (``e-acute`` -> ``e``), or when it belongs to a script that is
    simply not Latin (Arabic, Greek, CJK).
    """
    if ch in CONFUSABLES or ch in INVISIBLE:
        return False
    if unicodedata.category(ch).startswith("C"):
        return False
    decomposed = unicodedata.normalize("NFKD", ch)
    base = "".join(c for c in decomposed if not unicodedata.combining(c))
    return bool(base.strip())


@register
class UnicodeConfusableDetector:
    """Flag homoglyphs and invisible characters -- and nothing else."""

    name = "unicode_confusable"

    def detect(self, frame: pd.DataFrame, **context: Any) -> list[Issue]:
        issues: list[Issue] = []
        for column in frame.columns:
            hits: dict[str, list[tuple[str, str]]] = {}
            rows: list[int] = []
            for idx, value in enumerate(frame[column]):
                if not isinstance(value, str):
                    continue
                bad = [
                    (ch, unicodedata.name(ch, "UNNAMED"))
                    for ch in value
                    if ch in CONFUSABLES or ch in INVISIBLE
                ]
                if bad:
                    hits[value] = bad
                    rows.append(idx)
            if not hits:
                continue

            repaired = {
                v: "".join(CONFUSABLES.get(c, "" if c in INVISIBLE else c) for c in v) for v in hits
            }
            issues.append(
                Issue(
                    id=f"UNICODE-{column}",
                    category=IssueCategory.UNICODE_CONFUSABLE,
                    severity=Severity.HIGH_WARNING,
                    detection_confidence=0.99,
                    rule_source=RuleSource.EXTERNAL_REFERENCE,
                    columns=(column,),
                    evidence=Evidence(
                        summary=(
                            f"{len(hits)} distinct values in {column!r} contain characters "
                            "that imitate ASCII or are invisible"
                        ),
                        affected_rows=tuple(rows),
                        sample_values=tuple(hits),
                        details={
                            "findings": {
                                v: [f"{c} U+{ord(c):04X} {n}" for c, n in chars]
                                for v, chars in hits.items()
                            },
                            "proposed": repaired,
                        },
                    ),
                    treatments=(
                        TreatmentCandidate(
                            name="fold_confusables",
                            description=(
                                "Replace homoglyphs with their ASCII counterparts and "
                                "strip invisible characters."
                            ),
                            repair_confidence=0.97,
                            reversibility=Reversibility.REVERSIBLE_WITH_SNAPSHOT,
                            information_loss_risk=InformationLossRisk.LOW,
                        ),
                    ),
                    recommended="fold_confusables",
                )
            )
        return issues


@register
class CategoryVariantDetector:
    """Cluster surface variants of one category and grade each merge separately.

    Whitespace and case differences are mechanical and safe. A spelling
    correction is a judgement about intent and is not.
    """

    name = "category_variant"

    def __init__(self, max_cardinality: int = 50) -> None:
        self.max_cardinality = max_cardinality

    def detect(
        self, frame: pd.DataFrame, *, categorical: tuple[str, ...] = (), **context: Any
    ) -> list[Issue]:
        columns = categorical or tuple(
            c
            for c in frame.columns
            if frame[c].map(lambda v: isinstance(v, str)).any()
            and frame[c].nunique(dropna=True) <= self.max_cardinality
        )

        issues: list[Issue] = []
        for column in columns:
            values = [v for v in frame[column] if isinstance(v, str)]
            if not values:
                continue
            counts = Counter(values)

            clusters: dict[str, set[str]] = defaultdict(set)
            for value in counts:
                clusters[self._key(value)].add(value)

            variant_groups = {k: v for k, v in clusters.items() if len(v) > 1}
            mechanical, semantic = self._grade(variant_groups, counts)
            # Folding can only group values whose letters already match. A
            # misspelling or a language variant differs by a real character, so
            # a similarity pass is needed to see that `Tourismm` and `Tourism`
            # are one category -- as a proposal, never as a merge.
            semantic.update(self._near_matches(clusters, counts))

            if not variant_groups and not semantic:
                continue

            rows = tuple(
                idx
                for idx, v in enumerate(frame[column])
                if isinstance(v, str) and (self._key(v) in variant_groups or v in semantic)
            )

            treatments = [
                TreatmentCandidate(
                    name="canonicalise_mechanical",
                    description=(
                        "Merge variants that differ only by whitespace, case or "
                        "punctuation. Reversible from the stored original."
                    ),
                    repair_confidence=0.99,
                    reversibility=Reversibility.REVERSIBLE_WITH_SNAPSHOT,
                    information_loss_risk=InformationLossRisk.NONE,
                    parameters={"mapping": mechanical},
                )
            ]
            if semantic:
                treatments.append(
                    TreatmentCandidate(
                        name="merge_semantic_variants",
                        description=(
                            "Merge variants that differ by spelling or language. "
                            "Requires confirmation -- a merge cannot be undone once "
                            "the distinct values are gone."
                        ),
                        repair_confidence=0.80,
                        reversibility=Reversibility.IRREVERSIBLE,
                        information_loss_risk=InformationLossRisk.MEDIUM,
                        domain_sensitivity=DomainSensitivity.CONTEXTUAL,
                        parameters={"candidates": semantic},
                    )
                )

            issues.append(
                Issue(
                    id=f"CAT-{column}",
                    category=IssueCategory.CATEGORY_VARIANT,
                    severity=Severity.WARNING,
                    detection_confidence=0.99,
                    rule_source=RuleSource.STATISTICAL_RULE,
                    columns=(column,),
                    evidence=Evidence(
                        summary=(
                            f"{column!r} holds {len(counts)} surface forms that reduce to "
                            f"{len(clusters)} canonical categories"
                        ),
                        affected_rows=rows,
                        sample_values=tuple(sorted(next(iter(variant_groups.values())))),
                        details={
                            "clusters": {k: sorted(v) for k, v in variant_groups.items()},
                            "mechanical_merges": mechanical,
                            "semantic_candidates": semantic,
                        },
                    ),
                    treatments=tuple(treatments),
                    recommended="canonicalise_mechanical",
                )
            )
        return issues

    @staticmethod
    def _key(value: str) -> str:
        """Fold to a comparison key: case, whitespace and punctuation-insensitive."""
        folded = unicodedata.normalize("NFKD", value)
        folded = "".join(c for c in folded if not unicodedata.combining(c))
        folded = "".join(CONFUSABLES.get(c, c) for c in folded)
        return "".join(c for c in folded.lower() if c.isalnum())

    #: Similarity above which two distinct categories are *proposed* as one.
    #: Deliberately high: 0.85 separates `Tourismm`/`Tourism` (0.93) and
    #: `Algerie`/`Algeria` (0.86) from `Cash`/`Card` (0.75), which must stay
    #: apart. Short strings are skipped entirely -- at three characters almost
    #: everything looks similar.
    SIMILARITY_THRESHOLD = 0.85
    MIN_LENGTH = 5

    @classmethod
    def _near_matches(cls, clusters: dict[str, set[str]], counts: Counter[str]) -> dict[str, str]:
        """Propose merges between clusters that are similar but not identical."""
        weight = {key: sum(counts[v] for v in members) for key, members in clusters.items()}
        keys = [k for k in clusters if len(k) >= cls.MIN_LENGTH]
        proposals: dict[str, str] = {}

        for i, left in enumerate(keys):
            for right in keys[i + 1 :]:
                ratio = SequenceMatcher(None, left, right).ratio()
                if ratio < cls.SIMILARITY_THRESHOLD:
                    continue
                # The more frequent spelling wins; frequency is the only
                # evidence available without a domain dictionary.
                minor, major = (left, right) if weight[left] < weight[right] else (right, left)
                target = max(clusters[major], key=lambda v: counts[v])
                for member in clusters[minor]:
                    proposals[member] = target
        return proposals

    @staticmethod
    def _grade(
        groups: dict[str, set[str]], counts: Counter[str]
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Split each cluster's merges into mechanical and semantic."""
        mechanical: dict[str, str] = {}
        semantic: dict[str, str] = {}
        for members in groups.values():
            winner = max(members, key=lambda v: (counts[v], -len(v)))
            for member in members:
                if member == winner:
                    continue

                # Mechanical when the two differ only in case, spacing,
                # punctuation or a homoglyph -- their letter content is the
                # same. Anything else is a spelling or language judgement.
                def content(text: str) -> str:
                    folded = "".join(CONFUSABLES.get(c, c) for c in text)
                    return "".join(c for c in folded.lower() if c.isalnum())

                (mechanical if content(member) == content(winner) else semantic)[member] = winner
        return mechanical, semantic
