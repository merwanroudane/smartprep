"""PII detection and privacy-preserving transformations.

Two rules govern this module.

**Detection is never a guarantee.** Automated PII detection finds patterns; it
cannot promise it found everything. Every result carries a confidence and an
explicit false-negative warning, because a scanner that reports "no PII" with
no caveat invites someone to publish a dataset on its say-so.

**Quasi-identifiers matter as much as direct ones.** A table with no names in
it can still identify people through the combination of postcode, birth date
and job title. Re-identification risk is therefore reported separately from
whether a direct identifier was found.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

from ..core.rows import RowSet
from ..detectors.base import is_missing

__all__ = [
    "Sensitivity",
    "PrivacyFinding",
    "PrivacyReport",
    "PrivacyScanner",
    "mask",
    "redact",
    "hash_value",
    "pseudonymise",
    "generalise",
]


class Sensitivity(Enum):
    """Classification, ordered by how much exposure costs."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    QUASI_IDENTIFIER = "quasi_identifier"
    DIRECT_IDENTIFIER = "direct_identifier"
    SENSITIVE = "sensitive"


@dataclass(frozen=True)
class Detector:
    """One PII pattern."""

    name: str
    sensitivity: Sensitivity
    pattern: re.Pattern[str]
    validator: Any = None
    confidence: float = 0.9


def _luhn(value: str) -> bool:
    """Checksum for card numbers.

    A regex alone flags any 16-digit string -- order numbers, serials, hashes.
    The checksum is what separates a card number from a number.
    """
    digits = [int(c) for c in re.sub(r"[ -]", "", value) if c.isdigit()]
    if not 12 <= len(digits) <= 19:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _plausible_phone(value: str) -> bool:
    """Digit count within the E.164 range.

    The pattern alone matches any long digit string, so a 16-digit order
    reference reads as a phone number. E.164 caps a subscriber number at 15
    digits and nothing shorter than 7 is dialable, which separates the two.

    This still cannot distinguish a 10-digit phone number from a 10-digit
    account number, which is why the confidence stays moderate.
    """
    digits = sum(c.isdigit() for c in value)
    return 7 <= digits <= 15


DETECTORS: tuple[Detector, ...] = (
    Detector(
        "email",
        Sensitivity.DIRECT_IDENTIFIER,
        re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$"),
        confidence=0.97,
    ),
    Detector(
        "credit_card",
        Sensitivity.SENSITIVE,
        re.compile(r"^[\d\s-]{12,25}$"),
        validator=_luhn,
        confidence=0.95,
    ),
    Detector(
        "iban",
        Sensitivity.SENSITIVE,
        re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$"),
        confidence=0.9,
    ),
    Detector(
        "phone",
        Sensitivity.DIRECT_IDENTIFIER,
        re.compile(r"^\+?[\d][\d\s().-]{5,17}\d$"),
        validator=_plausible_phone,
        confidence=0.75,
    ),
    Detector(
        "ipv4",
        Sensitivity.QUASI_IDENTIFIER,
        re.compile(r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$"),
        confidence=0.95,
    ),
    Detector(
        "national_id",
        Sensitivity.DIRECT_IDENTIFIER,
        re.compile(r"^\d{3}-?\d{2}-?\d{4}$"),
        confidence=0.6,
    ),
    Detector(
        "postcode",
        Sensitivity.QUASI_IDENTIFIER,
        re.compile(r"^\d{4,6}$|^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$"),
        confidence=0.5,
    ),
)

#: Unanchored forms, for finding personal data inside free text. Anchored
#: matching alone never sees an email sitting in the middle of a sentence.
EMBEDDED_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[A-Za-z]{2,}"),
    "ipv4": re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]?){12,19}\b"),
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"),
}

#: Column names that signal sensitivity even when the values look ordinary.
NAME_HINTS: dict[str, Sensitivity] = {
    "name": Sensitivity.DIRECT_IDENTIFIER,
    "surname": Sensitivity.DIRECT_IDENTIFIER,
    "firstname": Sensitivity.DIRECT_IDENTIFIER,
    "lastname": Sensitivity.DIRECT_IDENTIFIER,
    "email": Sensitivity.DIRECT_IDENTIFIER,
    "phone": Sensitivity.DIRECT_IDENTIFIER,
    "address": Sensitivity.DIRECT_IDENTIFIER,
    "passport": Sensitivity.DIRECT_IDENTIFIER,
    "ssn": Sensitivity.DIRECT_IDENTIFIER,
    "iban": Sensitivity.SENSITIVE,
    "salary": Sensitivity.CONFIDENTIAL,
    "birth": Sensitivity.QUASI_IDENTIFIER,
    "dob": Sensitivity.QUASI_IDENTIFIER,
    "gender": Sensitivity.QUASI_IDENTIFIER,
    "postcode": Sensitivity.QUASI_IDENTIFIER,
    "zip": Sensitivity.QUASI_IDENTIFIER,
    "city": Sensitivity.QUASI_IDENTIFIER,
    "ethnicity": Sensitivity.SENSITIVE,
    "religion": Sensitivity.SENSITIVE,
    "health": Sensitivity.SENSITIVE,
    "diagnosis": Sensitivity.SENSITIVE,
}


@dataclass(frozen=True)
class PrivacyFinding:
    """One column classified, with the evidence behind it."""

    column: str
    kind: str
    sensitivity: Sensitivity
    confidence: float
    match_rate: float
    rows: RowSet
    evidence: str
    from_column_name: bool = False
    #: True when the pattern was found inside longer text rather than as the
    #: whole value -- the column is not that kind, but it contains one.
    embedded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "kind": self.kind,
            "sensitivity": self.sensitivity.value,
            "confidence": self.confidence,
            "match_rate": round(self.match_rate, 4),
            "rows_matched": len(self.rows),
            "evidence": self.evidence,
            "inferred_from_column_name": self.from_column_name,
            "embedded_in_text": self.embedded,
        }


@dataclass
class PrivacyReport:
    """What was found, and what could still be there."""

    findings: list[PrivacyFinding] = field(default_factory=list)
    row_count: int = 0

    @property
    def direct_identifiers(self) -> list[PrivacyFinding]:
        return [f for f in self.findings if f.sensitivity is Sensitivity.DIRECT_IDENTIFIER]

    @property
    def quasi_identifiers(self) -> list[PrivacyFinding]:
        return [f for f in self.findings if f.sensitivity is Sensitivity.QUASI_IDENTIFIER]

    @property
    def sensitive(self) -> list[PrivacyFinding]:
        return [f for f in self.findings if f.sensitivity is Sensitivity.SENSITIVE]

    def reidentification_risk(self, frame: pd.DataFrame) -> dict[str, Any]:
        """Estimate how identifiable rows are through quasi-identifiers.

        A direct identifier is obvious. The subtler exposure is a combination
        that is unique to one person, so this measures how many rows are alone
        in their quasi-identifier group.
        """
        columns = [f.column for f in self.quasi_identifiers if f.column in frame.columns]
        if not columns or frame.empty:
            return {"columns": columns, "unique_rows": 0, "unique_rate": 0.0, "level": "unknown"}

        sizes = frame.groupby(columns, dropna=False).size()
        unique = int((sizes == 1).sum())
        rate = unique / len(frame)
        level = "high" if rate > 0.5 else "medium" if rate > 0.1 else "low"
        return {
            "columns": columns,
            "unique_rows": unique,
            "unique_rate": round(rate, 4),
            "smallest_group": int(sizes.min()),
            "level": level,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "rows": self.row_count,
            "findings": [f.to_dict() for f in self.findings],
            "caveat": (
                "Automated detection finds patterns it was taught. It cannot prove "
                "the absence of personal data, and a clean result is not clearance "
                "to publish."
            ),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @property
    def embedded_findings(self) -> list[PrivacyFinding]:
        """Personal data found inside free text, in columns not typed as PII."""
        return [f for f in self.findings if f.embedded]

    def summary(self) -> str:
        if not self.findings:
            return (
                "No personal data matched the known patterns.\n\n"
                "This is not a guarantee. Detection covers the patterns it was "
                "taught; free text, unusual formats and local identifier schemes "
                "can pass unnoticed. Review before publishing."
            )
        lines = [f"{len(self.findings)} column(s) classified", ""]
        for finding in sorted(self.findings, key=lambda f: f.sensitivity.value):
            source = " (from column name)" if finding.from_column_name else ""
            if finding.embedded:
                source = " (inside free text)"
            lines.append(
                f"  {finding.column:22s} {finding.sensitivity.value:18s} "
                f"{finding.kind:14s} {finding.confidence:.0%}{source}"
            )
            lines.append(f"      {finding.evidence}")
        lines += [
            "",
            "Detection is not proof of absence. A column reported as clean may "
            "still contain personal data in a form these patterns do not cover.",
        ]
        return "\n".join(lines)


class PrivacyScanner:
    """Classify columns, and separately find personal data inside them.

    These are two different questions, and running both off one threshold was a
    real gap. A free-text column holding one email in ten rows is not an *email
    column* -- but it still contains an email, and reporting nothing at all
    because it failed the column test is the wrong answer for a privacy tool.

    Hence two thresholds:

    * ``column_classification_threshold`` -- the share of values that must
      match before the column itself is typed as, say, an email column.
    * ``cell_detection_threshold`` -- how many individual matches are enough to
      report that personal data is present somewhere inside it. One is enough.
    """

    def __init__(
        self,
        *,
        column_classification_threshold: float = 0.5,
        cell_detection_threshold: int = 1,
        min_match_rate: float | None = None,
    ) -> None:
        # ``min_match_rate`` was the single knob before the split. Honoured so
        # existing callers keep working; it sets the column threshold only.
        self.column_classification_threshold = (
            min_match_rate if min_match_rate is not None else column_classification_threshold
        )
        self.cell_detection_threshold = max(1, cell_detection_threshold)

    @property
    def min_match_rate(self) -> float:
        """Superseded by ``column_classification_threshold``; kept for callers."""
        return self.column_classification_threshold

    def scan(self, frame: pd.DataFrame) -> PrivacyReport:
        report = PrivacyReport(row_count=len(frame))

        for column in frame.columns:
            values = [v for v in frame[column] if not is_missing(v)]
            if not values:
                continue

            best: PrivacyFinding | None = None
            embedded: list[PrivacyFinding] = []

            for detector in DETECTORS:
                whole = [
                    i
                    for i, v in enumerate(frame[column])
                    if isinstance(v, str)
                    and detector.pattern.match(v.strip())
                    and (detector.validator is None or detector.validator(v.strip()))
                ]
                rate = len(whole) / len(values)

                if whole and rate >= self.column_classification_threshold:
                    candidate = self._finding(column, detector, whole, rate, frame.index)
                    if best is None or candidate.confidence > best.confidence:
                        best = candidate
                    continue

                # Either too few whole-value matches to type the column, or the
                # pattern only appears inside longer strings. Both still mean
                # personal data is present.
                inside = whole or self._embedded_positions(frame[column], detector)
                if len(inside) >= self.cell_detection_threshold:
                    embedded.append(
                        self._finding(
                            column,
                            detector,
                            inside,
                            len(inside) / len(values),
                            frame.index,
                            embedded=True,
                        )
                    )

            report.findings.extend(embedded)

            if best is None and embedded:
                continue

            if best is None:
                hint = self._from_name(column)
                if hint is not None:
                    best = PrivacyFinding(
                        column=column,
                        kind=hint[0],
                        sensitivity=hint[1],
                        confidence=0.55,
                        match_rate=0.0,
                        rows=RowSet(),
                        evidence=(
                            f"column name contains {hint[0]!r}; the values do not match "
                            "a known pattern, so this is a name-based guess"
                        ),
                        from_column_name=True,
                    )

            if best is not None:
                report.findings.append(best)

        return report

    @staticmethod
    def _embedded_positions(series: pd.Series, detector: Detector) -> list[int]:
        """Find the pattern inside longer text rather than as the whole value."""
        pattern = EMBEDDED_PATTERNS.get(detector.name)
        if pattern is None:
            return []

        found: list[int] = []
        for position, value in enumerate(series):
            if not isinstance(value, str):
                continue
            for match in pattern.findall(value):
                text = match if isinstance(match, str) else match[0]
                if detector.validator is None or detector.validator(text):
                    found.append(position)
                    break
        return found

    def _finding(
        self,
        column: str,
        detector: Detector,
        positions: list[int],
        rate: float,
        index: Any,
        *,
        embedded: bool = False,
    ) -> PrivacyFinding:
        where = "found inside longer text" if embedded else "as the whole value"
        return PrivacyFinding(
            column=column,
            kind=detector.name,
            sensitivity=detector.sensitivity,
            # An embedded match is a real match. The column is simply not
            # *typed* as that kind, so confidence is not scaled down by rate --
            # one confirmed email is one confirmed email.
            confidence=detector.confidence if embedded else detector.confidence * rate,
            match_rate=rate,
            rows=RowSet.of(positions).with_index(index),
            evidence=(
                f"{len(positions)} value(s) contain a {detector.name} {where} "
                f"({rate:.1%} of the column)"
            ),
            embedded=embedded,
        )

    @staticmethod
    def _from_name(column: str) -> tuple[str, Sensitivity] | None:
        lowered = column.lower()
        for hint, sensitivity in NAME_HINTS.items():
            if hint in lowered:
                return hint, sensitivity
        return None


# --------------------------------------------------------------------------
# Transformations
# --------------------------------------------------------------------------


def mask(value: Any, *, keep_first: int = 1, keep_last: int = 2, char: str = "*") -> Any:
    """Hide the middle, keep enough to recognise a record you already know."""
    if is_missing(value):
        return value
    text = str(value)
    if "@" in text:  # keep the domain: it is usually the useful part
        local, _, domain = text.partition("@")
        head = local[:keep_first]
        return f"{head}{char * max(len(local) - keep_first, 1)}@{domain}"
    if len(text) <= keep_first + keep_last:
        return char * len(text)
    return f"{text[:keep_first]}{char * (len(text) - keep_first - keep_last)}{text[-keep_last:]}"


def redact(value: Any, *, placeholder: str = "[REDACTED]") -> Any:
    if is_missing(value):
        return value
    return placeholder


def hash_value(value: Any, *, salt: str = "", length: int = 16) -> Any:
    """One-way hash.

    Without a salt this is reversible for any small domain -- an unsalted hash
    of a phone number can be brute-forced in seconds -- so a salt is strongly
    advised whenever the value space is enumerable.
    """
    if is_missing(value):
        return value
    digest = hashlib.sha256((salt + str(value)).encode("utf-8")).hexdigest()
    return digest[:length]


def pseudonymise(series: pd.Series, *, prefix: str = "ID") -> pd.Series:
    """Replace values with stable surrogate keys.

    The mapping is consistent within the call, so joins still work, but is not
    retained -- there is no lookup table to leak.
    """
    mapping: dict[str, str] = {}
    out = []
    for value in series:
        if is_missing(value):
            out.append(value)
            continue
        key = str(value)
        if key not in mapping:
            mapping[key] = f"{prefix}-{len(mapping) + 1:06d}"
        out.append(mapping[key])
    return pd.Series(out, index=series.index)


def generalise(value: Any, *, bucket: float = 10.0) -> Any:
    """Round into buckets, so a value identifies a group rather than a person."""
    if is_missing(value):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    low = (number // bucket) * bucket
    return f"[{low:g}, {low + bucket:g})"
