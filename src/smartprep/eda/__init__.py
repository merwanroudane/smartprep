"""EDA as backend objects.

Every statistic a chart, a report or the Studio needs is computed here and
returned as plain serialisable data. Nothing in this package knows what a plot
looks like -- which is what lets the same numbers drive a terminal summary, a
PNG, an HTML page and a slide without three implementations disagreeing.
"""

from .associations import (
    Association,
    AssociationMatrix,
    MissingnessPattern,
    associations,
    correlation_ratio,
    cramers_v,
    missingness,
)
from .comparison import ColumnComparison, ProfileComparison, compare_profiles
from .profile import (
    CategoricalSummary,
    ColumnKind,
    ColumnProfile,
    DatasetProfile,
    DatetimeSummary,
    Histogram,
    NumericSummary,
    TextSummary,
    profile,
)
from .typemap import SUPPORT, TypeSupport, support_for, support_table

__all__ = [
    "TypeSupport",
    "SUPPORT",
    "support_for",
    "support_table",
    "profile",
    "DatasetProfile",
    "ColumnProfile",
    "ColumnKind",
    "Histogram",
    "NumericSummary",
    "CategoricalSummary",
    "DatetimeSummary",
    "TextSummary",
    "associations",
    "AssociationMatrix",
    "Association",
    "cramers_v",
    "correlation_ratio",
    "missingness",
    "MissingnessPattern",
    "compare_profiles",
    "ProfileComparison",
    "ColumnComparison",
]
