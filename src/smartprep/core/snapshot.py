"""Dataset snapshots and fingerprints.

Reproducibility needs more than generated code. It needs to be able to prove
that the data going in was the data you think it was, and to restore exactly
what was there before an operation ran.
"""

from __future__ import annotations

import hashlib
import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

__all__ = ["DatasetFingerprint", "DatasetSnapshot", "EnvironmentManifest"]


def _hash(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


@dataclass(frozen=True)
class DatasetFingerprint:
    """Identity of a dataset at a point in time."""

    rows: int
    columns: int
    schema_hash: str
    content_hash: str
    column_order_hash: str

    @classmethod
    def of(cls, frame: pd.DataFrame) -> DatasetFingerprint:
        schema = _hash(*(f"{c}:{frame[c].dtype}" for c in frame.columns))
        order = _hash(*(str(c) for c in frame.columns))
        # pandas hashing is stable across runs for identical content, which is
        # what a fingerprint needs -- not cryptographic strength.
        try:
            content = _hash(str(pd.util.hash_pandas_object(frame, index=True).sum()))
        except TypeError:
            # Object columns holding unhashable values fall back to a repr hash.
            content = _hash(frame.to_csv(index=True))
        return cls(len(frame), frame.shape[1], schema, content, order)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "columns": self.columns,
            "schema_hash": self.schema_hash[:16],
            "content_hash": self.content_hash[:16],
            "column_order_hash": self.column_order_hash[:16],
        }


@dataclass(frozen=True)
class EnvironmentManifest:
    """What produced a result, so it can be reproduced or explained."""

    python: str
    platform: str
    smartprep: str
    pandas: str
    numpy: str
    captured_at: str

    @classmethod
    def capture(cls, smartprep_version: str) -> EnvironmentManifest:
        import numpy

        return cls(
            python=sys.version.split()[0],
            platform=platform.platform(),
            smartprep=smartprep_version,
            pandas=pd.__version__,
            numpy=numpy.__version__,
            captured_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "python": self.python,
            "platform": self.platform,
            "smartprep": self.smartprep,
            "pandas": self.pandas,
            "numpy": self.numpy,
            "captured_at": self.captured_at,
        }


@dataclass
class DatasetSnapshot:
    """A restorable copy of the data at one version.

    Snapshots hold a deep copy. That is memory the library spends deliberately:
    without it, "reversible" is a claim rather than a guarantee.
    """

    version: int
    label: str
    frame: pd.DataFrame
    fingerprint: DatasetFingerprint
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @classmethod
    def of(cls, frame: pd.DataFrame, version: int, label: str) -> DatasetSnapshot:
        copy = frame.copy(deep=True)
        return cls(version, label, copy, DatasetFingerprint.of(copy))

    def restore(self) -> pd.DataFrame:
        return self.frame.copy(deep=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "label": self.label,
            "created_at": self.created_at,
            "fingerprint": self.fingerprint.to_dict(),
        }
