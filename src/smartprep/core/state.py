"""``StudioState`` -- one interaction state, shared by every visual surface.

The grid, the charts, the visual builder, the treatment sandbox and the
cleaning story all answer the same questions: what is filtered, what is
selected, which chart is showing, which treatment is being considered. Built
separately, each surface grows its own answer, and reconciling four
almost-identical state models afterwards is the work nobody schedules.

So the state is defined once, here, in the core -- not in the page. It is a
plain serialisable value:

* the browser sends it back as JSON, so a view can be restored or shared;
* Python can construct it directly, so the same view is reachable without a
  browser at all;
* it can be diffed, logged and replayed, like everything else in the library.

**This module changes nothing.** It records what a reader is looking at. A
filter here narrows a view; it never drops a row from anybody's data. The
distinction is the same one the grid makes on its own face: sorting and
filtering change what you see, never the data.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any

import pandas as pd

from .identity import StableRowIndex

__all__ = ["Comparison", "FilterClause", "Selection", "StudioState"]


class Comparison(Enum):
    """How a filter clause tests a value.

    Deliberately small and total: every operator here can be evaluated in
    Python and in the page from the same clause, so a filter cannot mean one
    thing on screen and another when it comes back.
    """

    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_OR_EQUAL = "ge"
    LESS_THAN = "lt"
    LESS_OR_EQUAL = "le"
    IN = "in"
    CONTAINS = "contains"
    IS_MISSING = "is_missing"
    NOT_MISSING = "not_missing"


@dataclass(frozen=True)
class FilterClause:
    """One condition over one column.

    A clause is data, not a closure, so it survives a round trip through JSON
    and can be shown to the reader in words -- a filter nobody can read is a
    filter nobody can check.
    """

    column: str
    comparison: Comparison
    value: Any = None

    def describe(self) -> str:
        words = {
            Comparison.EQUALS: "is",
            Comparison.NOT_EQUALS: "is not",
            Comparison.GREATER_THAN: "is greater than",
            Comparison.GREATER_OR_EQUAL: "is at least",
            Comparison.LESS_THAN: "is less than",
            Comparison.LESS_OR_EQUAL: "is at most",
            Comparison.IN: "is one of",
            Comparison.CONTAINS: "contains",
            Comparison.IS_MISSING: "is missing",
            Comparison.NOT_MISSING: "is present",
        }[self.comparison]
        if self.comparison in (Comparison.IS_MISSING, Comparison.NOT_MISSING):
            return f"{self.column} {words}"
        if self.comparison is Comparison.IN:
            listed = ", ".join(str(v) for v in (self.value or []))
            return f"{self.column} {words} [{listed}]"
        return f"{self.column} {words} {self.value!r}"

    def mask(self, frame: pd.DataFrame) -> pd.Series:
        """A boolean mask over ``frame``. Never mutates it."""
        from ..detectors.base import is_missing

        if self.column not in frame.columns:
            # A filter naming a column that no longer exists selects nothing
            # rather than raising: a view can outlive a schema change, and a
            # page that crashes on a stale filter is worse than one that shows
            # an empty result and says why.
            return pd.Series(False, index=frame.index)

        column = frame[self.column]
        missing = column.map(is_missing)

        if self.comparison is Comparison.IS_MISSING:
            return missing
        if self.comparison is Comparison.NOT_MISSING:
            return ~missing

        if self.comparison is Comparison.IN:
            wanted = {str(v) for v in (self.value or [])}
            return ~missing & column.map(lambda v: str(v) in wanted)
        if self.comparison is Comparison.CONTAINS:
            needle = str(self.value).casefold()
            return ~missing & column.map(lambda v: needle in str(v).casefold())
        if self.comparison is Comparison.EQUALS:
            return ~missing & column.map(lambda v: str(v) == str(self.value))
        if self.comparison is Comparison.NOT_EQUALS:
            return ~missing & column.map(lambda v: str(v) != str(self.value))

        # Ordered comparisons. A non-numeric cell is not smaller than a
        # number, it is uncomparable, so it drops out rather than counting as
        # a match either way.
        numeric = pd.to_numeric(column, errors="coerce")
        try:
            bound = float(self.value)
        except (TypeError, ValueError):
            return pd.Series(False, index=frame.index)

        operations = {
            Comparison.GREATER_THAN: numeric > bound,
            Comparison.GREATER_OR_EQUAL: numeric >= bound,
            Comparison.LESS_THAN: numeric < bound,
            Comparison.LESS_OR_EQUAL: numeric <= bound,
        }
        return operations[self.comparison].fillna(False).astype(bool)

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "comparison": self.comparison.value,
            "value": self.value,
            "describe": self.describe(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FilterClause:
        return cls(
            column=str(payload["column"]),
            comparison=Comparison(payload["comparison"]),
            value=payload.get("value"),
        )


@dataclass(frozen=True)
class Selection:
    """What a reader has picked out, in terms that survive a transformation.

    Rows are named by :mod:`~smartprep.core.identity` keys rather than
    positions. ``stable`` records whether those keys mean anything after the
    data changes -- a page showing an unstable selection should say so rather
    than quietly highlighting whatever now sits in those positions.
    """

    rows: tuple[str, ...] = ()
    columns: tuple[str, ...] = ()
    stable: bool = True
    origin: str = ""

    def __bool__(self) -> bool:
        return bool(self.rows or self.columns)

    def with_rows(self, rows: Iterable[Any], *, origin: str = "") -> Selection:
        return replace(self, rows=tuple(dict.fromkeys(str(r) for r in rows)), origin=origin)

    def with_columns(self, columns: Iterable[Any]) -> Selection:
        return replace(self, columns=tuple(dict.fromkeys(str(c) for c in columns)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": list(self.rows),
            "columns": list(self.columns),
            "stable": self.stable,
            "origin": self.origin,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Selection:
        return cls(
            rows=tuple(str(r) for r in payload.get("rows", [])),
            columns=tuple(str(c) for c in payload.get("columns", [])),
            stable=bool(payload.get("stable", True)),
            origin=str(payload.get("origin", "")),
        )


@dataclass
class StudioState:
    """Everything a visual surface needs to agree with the others.

    Constructed from a frame, mutated by intent-named methods rather than by
    reaching into the fields, and serialised whole. Every surface reads this
    and nothing else, which is what makes brushing in the grid and filtering
    in a chart the same operation seen twice.
    """

    identity: StableRowIndex
    fingerprint: str = ""
    filters: tuple[FilterClause, ...] = ()
    selection: Selection = field(default_factory=Selection)
    active_specs: tuple[str, ...] = ()
    current_stage: int = 0
    pending_treatment: dict[str, Any] | None = None
    review_context: dict[str, Any] = field(default_factory=dict)

    #: Bumped on every change, so a surface can tell a stale view from a
    #: current one without diffing the whole state.
    revision: int = 0

    # -- construction -------------------------------------------------------

    @classmethod
    def of(cls, frame: pd.DataFrame, **review_context: Any) -> StudioState:
        from .snapshot import DatasetFingerprint

        return cls(
            identity=StableRowIndex.of(frame),
            fingerprint=DatasetFingerprint.of(frame).content_hash,
            review_context=dict(review_context),
        )

    # -- intent -------------------------------------------------------------

    def _bump(self) -> StudioState:
        self.revision += 1
        return self

    def filter_by(self, *clauses: FilterClause) -> StudioState:
        """Add clauses. Narrows a view; removes nothing from the data."""
        self.filters = self.filters + tuple(clauses)
        return self._bump()

    def clear_filters(self) -> StudioState:
        self.filters = ()
        return self._bump()

    def select_rows(self, rows: Iterable[Any], *, origin: str = "") -> StudioState:
        """Record a row selection, marked with the identity's real strength."""
        self.selection = self.selection.with_rows(rows, origin=origin)
        self.selection = replace(self.selection, stable=self.identity.is_stable)
        return self._bump()

    def select_columns(self, columns: Iterable[Any]) -> StudioState:
        self.selection = self.selection.with_columns(columns)
        return self._bump()

    def clear_selection(self) -> StudioState:
        self.selection = Selection(stable=self.identity.is_stable)
        return self._bump()

    def show(self, *spec_ids: str) -> StudioState:
        self.active_specs = tuple(spec_ids)
        return self._bump()

    def go_to_stage(self, index: int) -> StudioState:
        self.current_stage = max(0, index)
        return self._bump()

    def consider(self, issue_id: str, treatment: str) -> StudioState:
        """Note which treatment is being weighed. Considering is not applying."""
        self.pending_treatment = {"issue_id": issue_id, "treatment": treatment}
        return self._bump()

    def stop_considering(self) -> StudioState:
        self.pending_treatment = None
        return self._bump()

    # -- resolution ---------------------------------------------------------

    def mask(self, frame: pd.DataFrame) -> pd.Series:
        """The rows the current filters admit. Every clause must hold."""
        keep = pd.Series(True, index=frame.index)
        for clause in self.filters:
            keep &= clause.mask(frame)
        return keep

    def _positions(self, frame: pd.DataFrame) -> list[int]:
        """Row positions the filters admit.

        Resolved positionally, never by index label. A frame with a duplicated
        index -- ordinary after a concat -- has several rows answering to the
        same label, so selecting by label silently pulls in rows the filters
        excluded. That is the exact failure this module exists to prevent, and
        it is invisible from outside because wrong rows still look like rows.
        """
        return [i for i, keep in enumerate(self.mask(frame).to_numpy()) if keep]

    def view(self, frame: pd.DataFrame) -> pd.DataFrame:
        """The filtered frame.

        A *view* in the ordinary English sense, and a copy in the pandas one:
        callers get something they can look at without any chance of writing
        through it to the dataset.
        """
        return frame.iloc[self._positions(frame)].copy()

    def _identity_for(self, frame: pd.DataFrame) -> StableRowIndex:
        """Keys aligned to *this* frame.

        The stored identity belongs to the frame the state was built from. Ask
        about a frame of a different length and it cannot be aligned, so the
        identity is derived afresh -- and if the rows themselves changed, keys
        that no longer match are keys that no longer name those rows, which is
        the correct answer rather than a near miss.
        """
        if len(self.identity) == len(frame):
            return self.identity
        return StableRowIndex.of(frame)

    def selected_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        """The selected rows, within the current filters.

        Selecting a row and then filtering it away must not resurrect it, so
        the two are intersected rather than either winning.
        """
        admitted = set(self._positions(frame))
        if not self.selection.rows:
            return frame.iloc[sorted(admitted)].copy()

        keys = self._identity_for(frame).keys
        wanted = set(self.selection.rows)
        positions = [i for i, key in enumerate(keys) if key in wanted and i in admitted]
        return frame.iloc[positions].copy()

    def describe(self) -> str:
        """The current view in words, for a reader and for a report."""
        parts = []
        if self.filters:
            parts.append("filtered where " + " and ".join(c.describe() for c in self.filters))
        if self.selection.rows:
            parts.append(f"{len(self.selection.rows)} rows selected")
            if not self.selection.stable:
                parts.append("(selection is positional and will not survive a transformation)")
        if self.selection.columns:
            parts.append("columns " + ", ".join(self.selection.columns))
        return "; ".join(parts) or "the whole dataset, nothing selected"

    # -- serialisation ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "fingerprint": self.fingerprint,
            "identity": self.identity.to_dict(),
            "filters": [c.to_dict() for c in self.filters],
            "selection": self.selection.to_dict(),
            "active_specs": list(self.active_specs),
            "current_stage": self.current_stage,
            "pending_treatment": self.pending_treatment,
            "review_context": dict(self.review_context),
            "revision": self.revision,
            "describe": self.describe(),
        }

    def to_json(self, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], identity: StableRowIndex) -> StudioState:
        """Rebuild a state the page sent back.

        The identity is supplied by the caller rather than trusted from the
        payload: it belongs to the frame in hand, and a page cannot be allowed
        to assert that a selection is stable when this frame says otherwise.
        """
        return cls(
            identity=identity,
            fingerprint=str(payload.get("fingerprint", "")),
            filters=tuple(FilterClause.from_dict(c) for c in payload.get("filters", [])),
            selection=Selection.from_dict(payload.get("selection", {})),
            active_specs=tuple(str(s) for s in payload.get("active_specs", [])),
            current_stage=int(payload.get("current_stage", 0)),
            pending_treatment=payload.get("pending_treatment"),
            review_context=dict(payload.get("review_context", {})),
            revision=int(payload.get("revision", 0)),
        )

    @classmethod
    def from_json(cls, payload: str, identity: StableRowIndex) -> StudioState:
        return cls.from_dict(json.loads(payload), identity)
