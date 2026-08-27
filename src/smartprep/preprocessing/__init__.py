"""Preprocessing -- a different job from cleaning, kept deliberately separate.

Cleaning fixes what is wrong. Preprocessing transforms what is right so an
analysis can use it. Preprocessing therefore never runs inside
``auto_prepare()``; you ask for it explicitly.
"""

from .advisor import Goal, PreprocessingAdvice, Recommendation
from .advisor import recommend as recommend_preprocessing
from .core import LeakageWarning, PreprocessingReport, Preprocessor, Step

__all__ = [
    "Preprocessor",
    "PreprocessingReport",
    "Step",
    "LeakageWarning",
    "Goal",
    "Recommendation",
    "PreprocessingAdvice",
    "recommend_preprocessing",
]
