"""Detector suite.

Importing this package registers every built-in detector with ``REGISTRY``.
"""

from . import missing, numeric, relational, structural, temporal, textual  # noqa: F401
from .base import REGISTRY, Detector, DetectorRegistry, register

__all__ = ["REGISTRY", "Detector", "DetectorRegistry", "register"]
