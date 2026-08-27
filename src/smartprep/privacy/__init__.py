"""Privacy: PII detection and privacy-preserving transformations.

Detection finds the patterns it was taught. It cannot prove the absence of
personal data, and every report says so.
"""

from .scanner import (
    PrivacyFinding,
    PrivacyReport,
    PrivacyScanner,
    Sensitivity,
    generalise,
    hash_value,
    mask,
    pseudonymise,
    redact,
)

__all__ = [
    "PrivacyScanner",
    "PrivacyReport",
    "PrivacyFinding",
    "Sensitivity",
    "mask",
    "redact",
    "hash_value",
    "pseudonymise",
    "generalise",
]
