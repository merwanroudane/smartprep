"""Visualization: a chart is a specification, and renderers realise it.

Writing a chart directly against a plotting library binds it to one output
format. Writing it three times, once per format, guarantees the three drift
apart. So charts are described as :class:`ChartSpec` data and rendered by
whichever backend the destination needs.

``render_svg`` is built in and depends on nothing, so a report can always draw
its own charts. Matplotlib and Plotly are optional accelerants, not
requirements.
"""

from .builders import (
    association_heatmap,
    before_after_chart,
    box_chart,
    category_chart,
    column_charts,
    distribution_chart,
    ecdf_chart,
    health_chart,
    issue_chart,
    kpi_chart,
    missingness_chart,
    overview_charts,
    scatter_chart,
    stage_chart,
    target_chart,
    timeline_chart,
)
from .compose import (
    AGGREGATES,
    Composition,
    CompositionRefused,
    Field,
    Recommendation,
    compose,
    fields_of,
    recommend,
)
from .renderers import (
    BackendUnavailable,
    available_backends,
    render,
    save_chart,
    to_matplotlib,
    to_plotly,
)
from .spec import ChartSet, ChartSpec, Encoding, Fidelity, Interaction, Mark
from .svg import LIGHT, Theme, render_svg

__all__ = [
    "ChartSpec",
    "ChartSet",
    "Encoding",
    "Mark",
    "Fidelity",
    "Interaction",
    "Composition",
    "CompositionRefused",
    "Field",
    "Recommendation",
    "compose",
    "fields_of",
    "recommend",
    "AGGREGATES",
    "render_svg",
    "render",
    "save_chart",
    "to_matplotlib",
    "to_plotly",
    "available_backends",
    "BackendUnavailable",
    "Theme",
    "LIGHT",
    "distribution_chart",
    "category_chart",
    "missingness_chart",
    "association_heatmap",
    "timeline_chart",
    "health_chart",
    "before_after_chart",
    "issue_chart",
    "column_charts",
    "overview_charts",
    "box_chart",
    "ecdf_chart",
    "scatter_chart",
    "target_chart",
    "kpi_chart",
    "stage_chart",
]
