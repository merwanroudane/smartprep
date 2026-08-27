"""Detector protocol, registry and shared parsing helpers.

A detector observes and reports. It never mutates the frame (AD-003) and never
decides whether a repair may be applied -- that is triage's job (AD-007).
"""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from collections.abc import Callable, Iterator
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from ..core.issue import Issue

__all__ = [
    "Detector",
    "DetectorRegistry",
    "REGISTRY",
    "register",
    "physical_type",
    "to_number",
    "numeric_series",
    "is_missing",
]


@runtime_checkable
class Detector(Protocol):
    """Anything that turns a frame into findings."""

    name: str

    def detect(self, frame: pd.DataFrame, **context: Any) -> list[Issue]: ...


class DetectorRegistry:
    """Plugin registry. Detectors self-register so ``full_scan`` finds them."""

    def __init__(self) -> None:
        self._detectors: dict[str, Detector] = {}

    def register(self, detector: Detector) -> Detector:
        if detector.name in self._detectors:
            raise ValueError(f"detector {detector.name!r} is already registered")
        self._detectors[detector.name] = detector
        return detector

    def __iter__(self) -> Iterator[Detector]:
        return iter(self._detectors.values())

    def __len__(self) -> int:
        return len(self._detectors)

    def get(self, name: str) -> Detector:
        return self._detectors[name]

    def names(self) -> list[str]:
        return sorted(self._detectors)


REGISTRY = DetectorRegistry()


def register(cls: Callable[[], Detector]) -> Callable[[], Detector]:
    """Class decorator: instantiate and register a detector."""
    REGISTRY.register(cls())
    return cls


# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------

_FORMATTED_NUMBER = re.compile(r"^[+-]?[\d,]+(?:\.\d+)?$")


def is_missing(value: Any) -> bool:
    """Whether one cell holds no value.

    Every null pandas can produce, not only the three that predate the
    nullable dtypes. ``pd.NA`` is what ``Int64``, ``boolean``, ``Float64`` and
    ``string`` columns use, and those are the modern defaults -- a library
    that did not recognise it would report a column as complete when it is
    not, and under-report missingness across every detector that asks.

    Checked by identity first because ``pd.NA`` raises on ``bool()`` and
    ``np.isnan`` refuses non-floats: an ordinary truthiness test here throws
    rather than answering.
    """
    if value is None or value is pd.NaT or value is pd.NA:
        return True
    if isinstance(value, float) and np.isnan(value):
        return True
    # numpy's own NaT, which is a distinct object from pandas'.
    if isinstance(value, np.datetime64 | np.timedelta64):
        return bool(np.isnat(value))
    # Masked scalars from nullable arrays, and anything else that knows it is
    # null. Guarded because pd.isna answers arrays as arrays.
    if isinstance(value, (str, bytes, list, tuple, dict, set)):
        return False
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):  # pragma: no cover - exotic objects
        return False
    return bool(result) if isinstance(result, (bool, np.bool_)) else False


def physical_type(value: Any) -> str:
    """Classify the *storage* form of a single cell.

    ``dtype`` alone hides mixed representations inside an object column, which
    is the failure the fixture was chosen to expose.
    """
    if is_missing(value):
        return "missing"
    if isinstance(value, (_dt.datetime, pd.Timestamp)):
        return "datetime"
    if isinstance(value, _dt.date):
        return "date"
    if isinstance(value, (bool, np.bool_)):
        return "bool"
    if isinstance(value, (int, np.integer)):
        return "int"
    if isinstance(value, (float, np.floating)):
        return "float"
    if isinstance(value, str):
        stripped = value.strip()
        try:
            float(stripped)
            return "numeric-string"
        except ValueError:
            pass
        if _FORMATTED_NUMBER.match(stripped):
            return "formatted-numeric-string"
        return "string"
    return type(value).__name__


def to_number(value: Any) -> float:
    """Best-effort numeric coercion that understands thousands separators."""
    if is_missing(value):
        return float("nan")
    if isinstance(value, (bool, np.bool_)):
        return float("nan")
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    if isinstance(value, str):
        candidate = value.strip().replace(",", "")
        try:
            return float(candidate)
        except ValueError:
            return float("nan")
    # A duration is a quantity. Leaving it uncoerced sent every timedelta
    # column to the categorical branch, where "3 days" is a label rather than
    # three days and no summary statistic means anything.
    if isinstance(value, (pd.Timedelta, _dt.timedelta)):
        return float(pd.Timedelta(value).total_seconds())
    if isinstance(value, np.timedelta64):
        return float(pd.Timedelta(value).total_seconds())
    return float("nan")


def numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    """Coerce a column to float without touching the original frame."""
    return frame[column].map(to_number).astype(float)


def has_non_ascii(value: str) -> list[tuple[str, str]]:
    """Return ``(character, unicode-name)`` for every non-ASCII character."""
    return [(ch, unicodedata.name(ch, "UNNAMED")) for ch in value if ord(ch) > 127]
