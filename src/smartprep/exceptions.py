"""Exceptions.

Messages state what was found, what it means and what to do next. A user should
never have to read the source to understand a SmartPrep error.
"""

from __future__ import annotations

__all__ = [
    "SmartPrepError",
    "SmartPrepTypeError",
    "SmartPrepSchemaError",
    "SmartPrepValidationError",
    "SmartPrepBackendError",
    "SmartPrepAmbiguityError",
    "SmartPrepUnsafeRepairError",
    "SmartPrepPrivacyError",
    "SmartPrepContractError",
]


class SmartPrepError(Exception):
    """Base class for every SmartPrep error."""


class SmartPrepTypeError(SmartPrepError):
    """A column's representation cannot be resolved to one semantic type."""


class SmartPrepSchemaError(SmartPrepError):
    """The observed schema contradicts the expected one."""


class SmartPrepValidationError(SmartPrepError):
    """A validation rule failed above its configured threshold."""


class SmartPrepBackendError(SmartPrepError):
    """The selected backend cannot execute an operation with the same semantics."""


class SmartPrepAmbiguityError(SmartPrepError):
    """A decision was demanded where the data supports more than one answer."""


class SmartPrepUnsafeRepairError(SmartPrepError):
    """A repair was requested that the safety policy forbids.

    Raised, for example, when ``verified_df`` is accessed while blocking issues
    remain unresolved (AD-004).
    """


class SmartPrepPrivacyError(SmartPrepError):
    """An operation would expose data classified as sensitive."""


class SmartPrepContractError(SmartPrepError):
    """A data contract was violated or is internally inconsistent."""
