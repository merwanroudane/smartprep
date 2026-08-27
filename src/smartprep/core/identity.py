"""Stable row identity -- what a selection means after the data changes.

A selection made in a grid and applied to a chart has to survive whatever
happened to the frame in between. Positional indexes do not: drop three rows,
sort by a column, or reset an index, and row 47 is a different row. Every
linked-selection bug of that kind looks identical from the outside -- the
highlight lands on the wrong records and nobody notices, because wrong rows
still look like rows.

So a selection is carried as **keys**, and a key comes from the best identity
the frame actually offers:

``INDEX``
    The frame's own index, when it is unique. The natural answer, and the one
    that survives filtering and reordering.
``CONTENT``
    A hash of the row's values, when the index is not unique but the rows are.
    Survives reordering and index resets; does not survive editing the row,
    which is correct -- an edited row is a different row to anything that was
    selected before the edit.
``POSITIONAL``
    Last resort, when neither holds. Position *is* the identity, and it is
    therefore not stable across transformations.

The fallback is stated rather than hidden, exactly as :class:`~smartprep.viz.spec.Fidelity`
states that a chart was sampled. A caller who is told their selection is
positional can decide what to do about it; a caller who is told nothing will
assume it was stable.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd

__all__ = ["IdentitySource", "StableRowIndex"]


class IdentitySource(Enum):
    """Where a row's identity came from, and therefore what it survives."""

    INDEX = "index"
    CONTENT = "content"
    POSITIONAL = "positional"

    @property
    def survives_transformation(self) -> bool:
        """Whether a key of this kind still names the same row afterwards."""
        return self is not IdentitySource.POSITIONAL


def _content_key(values: tuple[Any, ...]) -> str:
    digest = hashlib.blake2b(
        "\x1f".join("" if v is None else repr(v) for v in values).encode("utf-8"),
        digest_size=8,
    )
    return f"c{digest.hexdigest()}"


@dataclass(frozen=True)
class StableRowIndex:
    """Keys for every row of a frame, plus an honest account of their strength.

    Built once per dataset and carried alongside it. Two frames built from the
    same rows produce the same keys, which is what lets a selection taken
    before a repair be resolved against the frame after it.
    """

    keys: tuple[str, ...]
    source: IdentitySource
    note: str = ""

    # -- construction -------------------------------------------------------

    @classmethod
    def of(cls, frame: pd.DataFrame) -> StableRowIndex:
        """Derive the strongest identity this frame supports."""
        index_values = list(frame.index)
        try:
            candidate = tuple(str(v) for v in index_values)
        except Exception:  # pragma: no cover - exotic index types
            candidate = ()

        if candidate and len(set(candidate)) == len(candidate):
            return cls(
                keys=candidate,
                source=IdentitySource.INDEX,
                note="the frame's index is unique, so it is the identity",
            )

        # No usable index. Try the rows themselves.
        try:
            rows = [tuple(record) for record in frame.itertuples(index=False, name=None)]
            content = tuple(_content_key(row) for row in rows)
        except Exception:  # pragma: no cover - unhashable cell contents
            content = ()

        if content and len(set(content)) == len(content):
            return cls(
                keys=content,
                source=IdentitySource.CONTENT,
                note=(
                    "the index is not unique, so rows are identified by their "
                    "contents; editing a row changes its identity"
                ),
            )

        return cls(
            keys=tuple(f"p{i}" for i in range(len(frame))),
            source=IdentitySource.POSITIONAL,
            note=(
                "neither the index nor the row contents are unique, so identity "
                "is positional and does NOT survive transformation"
            ),
        )

    # -- resolution ---------------------------------------------------------

    def __len__(self) -> int:
        return len(self.keys)

    @property
    def is_stable(self) -> bool:
        return self.source.survives_transformation

    def key_at(self, position: int) -> str:
        return self.keys[position]

    def keys_for(self, positions: Iterable[Any]) -> tuple[str, ...]:
        """Keys for row positions, skipping any that fall outside the frame."""
        return tuple(
            self.keys[p] for p in positions if isinstance(p, int) and 0 <= p < len(self.keys)
        )

    def positions_for(self, keys: Iterable[Any]) -> tuple[int, ...]:
        """Positions for keys.

        Keys that are not present are dropped rather than raising: a selection
        naturally outlives the rows it names, and a row removed by a repair
        should quietly leave the selection instead of breaking the page.
        """
        lookup = {key: position for position, key in enumerate(self.keys)}
        return tuple(lookup[k] for k in keys if k in lookup)

    def restrict(self, frame: pd.DataFrame, keys: Iterable[Any]) -> pd.DataFrame:
        """The subframe named by ``keys``, in frame order."""
        positions = self.positions_for(keys)
        return frame.iloc[list(positions)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.value,
            "stable": self.is_stable,
            "note": self.note,
            "rows": len(self.keys),
        }
