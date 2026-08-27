"""Row references that are unambiguous about position versus label.

Detectors work positionally -- `np.flatnonzero` returns offsets. Users think in
index labels. On a frame whose index is not ``0..n-1`` those disagree, and
reporting a bare integer silently invites the reader to look at the wrong row.

Every finding therefore carries both. Detectors emit positions; ``scan()``
attaches the labels once, centrally, so the two can never drift apart.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

__all__ = ["RowSet", "Indexable"]


@runtime_checkable
class Indexable(Protocol):
    """Anything positionally addressable -- a list, a tuple, a pandas Index.

    Structural rather than nominal so ``core`` does not have to import pandas
    just to describe the argument.
    """

    def __len__(self) -> int: ...

    def __getitem__(self, position: int) -> Any: ...


@dataclass(frozen=True)
class RowSet:
    """Rows a finding applies to, addressable either way.

    ``labels`` is empty until the scan attaches the frame's index. When it is
    populated it is the same length as ``positions`` and aligned element-wise.
    """

    positions: tuple[int, ...] = ()
    labels: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        if self.labels and len(self.labels) != len(self.positions):
            raise ValueError(
                f"RowSet has {len(self.positions)} positions but {len(self.labels)} "
                "labels; they must align element-wise"
            )

    def __len__(self) -> int:
        return len(self.positions)

    def __bool__(self) -> bool:
        return bool(self.positions)

    def __iter__(self) -> Iterable[int]:
        return iter(self.positions)

    @classmethod
    def of(cls, positions: Iterable[int]) -> RowSet:
        return cls(tuple(int(p) for p in positions))

    def with_index(self, index: Indexable) -> RowSet:
        """Return a copy carrying the label for each position.

        Out-of-range positions are dropped rather than raising: a detector that
        miscounts should produce a smaller finding, not abort the whole scan.
        """
        size = len(index)
        kept = tuple(p for p in self.positions if 0 <= p < size)
        return RowSet(kept, tuple(index[p] for p in kept))

    @property
    def labelled(self) -> bool:
        return bool(self.labels)

    def head(self, n: int = 5) -> tuple[int, ...]:
        return self.positions[:n]

    def as_dict(self) -> dict[str, Any]:
        return {
            "count": len(self.positions),
            "positions": list(self.positions),
            "labels": [str(v) for v in self.labels] if self.labels else None,
        }
