"""Renderer backends, chart export, publishing and the interactive Studio."""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re

import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT
from smartprep.viz import (
    BackendUnavailable,
    ChartSpec,
    Mark,
    available_backends,
    box_chart,
    ecdf_chart,
    kpi_chart,
    render,
    render_svg,
    save_chart,
    scatter_chart,
    stage_chart,
    target_chart,
    to_matplotlib,
    to_plotly,
)

HAS_MPL = available_backends()["matplotlib"]
HAS_PLOTLY = available_backends()["plotly"]
needs_mpl = pytest.mark.skipif(not HAS_MPL, reason="matplotlib not installed")
needs_plotly = pytest.mark.skipif(not HAS_PLOTLY, reason="plotly not installed")
needs_pypdf = pytest.mark.skipif(
    importlib.util.find_spec("pypdf") is None, reason="pypdf not installed"
)


@pytest.fixture(scope="module")
def prepared(request) -> sp.PreparationResult:
    from synthetic import build

    return sp.auto_prepare(build(), **SCAN_CONTEXT)


@pytest.fixture(scope="module")
def specs(request) -> dict[str, ChartSpec]:
    from synthetic import build

    frame = build()
    dataset = sp.profile(frame)
    return {
        "histogram": sp.viz.distribution_chart(dataset.get("unit_price")),
        "box": box_chart(dataset.get("unit_price"), dataset.get("employee_count")),
        "ecdf": ecdf_chart(dataset.get("unit_price")),
        "scatter": scatter_chart(frame, "quantity", "invoice_amount"),
        "category": sp.viz.category_chart(dataset.get("sector")),
        "matrix": sp.viz.association_heatmap(sp.associations(frame, dataset)),
        "kpi": kpi_chart([("93", "health")]),
    }


# -- every declared mark can be drawn -------------------------------------


def test_no_mark_is_declared_without_a_renderer() -> None:
    """A public enum listing a mark nobody can draw is the same class of
    dishonesty as a docstring promising a guarantee the code lacks."""
    import inspect

    import smartprep.viz.svg as svg_module

    source = inspect.getsource(svg_module.render_svg)
    missing = [m.name for m in Mark if f"Mark.{m.name}:" not in source]
    assert not missing, f"declared but never rendered: {missing}"


@pytest.mark.parametrize("mark", list(Mark))
def test_every_mark_renders_something(mark: Mark) -> None:
    data = {
        Mark.BOX: [{"label": "a", "min": 1, "q1": 3, "median": 5, "q3": 7, "max": 9}],
        Mark.MATRIX: [{"left": "a", "right": "b", "value": 0.5, "measure": "spearman"}],
        Mark.HEATMAP: [{"left": "a", "right": "b", "value": 0.5, "measure": "spearman"}],
        Mark.HISTOGRAM: [{"centre": 1.0, "count": 3, "bin_start": 0, "bin_end": 2}],
        Mark.TEXT: [{"value": "42", "label": "answer"}],
    }.get(mark, [{"x": 1, "y": 2, "label": "a", "count": 3, "value": 1.0}])

    svg = render_svg(ChartSpec(mark=mark, data=data, title="t"))
    assert svg.startswith("<svg")
    assert "No renderer for mark" not in svg


def test_box_plot_shows_outliers_beyond_the_fences() -> None:
    spec = ChartSpec(
        mark=Mark.BOX,
        data=[
            {"label": "a", "min": 1, "q1": 3, "median": 5, "q3": 7, "max": 9, "outliers": [40.0]}
        ],
        title="box",
    )
    assert "outlier" in render_svg(spec)


# -- new builders ---------------------------------------------------------


def test_box_chart_clips_whiskers_to_the_fences(specs) -> None:
    """One distant value must not flatten every box into a sliver."""
    chart = specs["box"]
    assert chart is not None
    for row in chart.data:
        assert row["min"] <= row["q1"] <= row["median"] <= row["q3"] <= row["max"]


def test_ecdf_has_no_bin_width_to_argue_about(specs) -> None:
    chart = specs["ecdf"]
    assert chart is not None
    assert "no bin width" in chart.rationale
    assert chart.data[0]["proportion"] <= chart.data[-1]["proportion"]


def test_scatter_samples_large_data_and_says_so() -> None:
    frame = pd.DataFrame({"a": range(9000), "b": range(9000)})
    chart = scatter_chart(frame, "a", "b", limit=500)
    assert chart is not None
    assert len(chart.data) == 500
    assert chart.is_sampled
    assert "9,000" in chart.fidelity_note


def test_scatter_sampling_is_deterministic() -> None:
    """The same data must always produce the same picture."""
    frame = pd.DataFrame({"a": range(5000), "b": range(5000)})
    first = scatter_chart(frame, "a", "b", limit=200)
    second = scatter_chart(frame, "a", "b", limit=200)
    assert first.data == second.data


def test_target_chart_reports_the_separation() -> None:
    frame = pd.DataFrame({"g": ["a"] * 20 + ["b"] * 20, "y": [1.0] * 20 + [9.0] * 20})
    chart = target_chart(frame, "g", "y")
    assert chart is not None
    assert "separate the target" in chart.rationale


def test_target_chart_declines_high_cardinality() -> None:
    frame = pd.DataFrame({"g": [f"lvl{i}" for i in range(60)], "y": range(60)})
    assert target_chart(frame, "g", "y") is None


def test_stage_chart_sets_the_animation_axis() -> None:
    """Animation is allowed only where the frames are steps of a real process."""
    chart = stage_chart([("raw", 60.0), ("clean", 90.0)], title="t", reason="stages")
    assert chart.animation_field == "stage"


# -- backends -------------------------------------------------------------


def test_svg_backend_always_available() -> None:
    assert available_backends()["svg"] is True


@needs_mpl
@pytest.mark.parametrize(
    "name", ["histogram", "box", "ecdf", "scatter", "category", "matrix", "kpi"]
)
def test_matplotlib_renders_every_chart(specs, name: str) -> None:
    import matplotlib.pyplot as plt

    figure = to_matplotlib(specs[name])
    assert figure.get_axes()
    plt.close(figure)


@needs_mpl
def test_matplotlib_figure_carries_the_rationale(specs) -> None:
    import matplotlib.pyplot as plt

    figure = to_matplotlib(specs["histogram"])
    captions = [t.get_text() for t in figure.texts]
    assert any(captions), "the reason for the chart must survive into the figure"
    plt.close(figure)


@needs_plotly
@pytest.mark.parametrize("name", ["histogram", "box", "ecdf", "scatter", "matrix"])
def test_plotly_renders_every_chart(specs, name: str) -> None:
    figure = to_plotly(specs[name])
    assert figure.data or figure.layout.annotations


@needs_plotly
def test_plotly_is_where_real_interaction_lives(specs) -> None:
    """Hover titles in SVG are a convenience; zoom and select are the tool."""
    figure = to_plotly(specs["scatter"])
    assert figure.layout.dragmode == "zoom"


def test_render_dispatches_by_backend_name(specs) -> None:
    assert render(specs["histogram"], "svg").startswith("<svg")


def test_unknown_backend_is_rejected(specs) -> None:
    with pytest.raises(ValueError, match="unknown backend"):
        render(specs["histogram"], "crayon")


def test_a_missing_backend_names_the_install_command(monkeypatch) -> None:
    """An ImportError from deep inside a report tells the user nothing."""
    import builtins

    from smartprep.viz import renderers

    real = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "matplotlib":
            raise ImportError("blocked for the test")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(BackendUnavailable, match=r"pip install"):
        renderers._require("matplotlib", "viz")


# -- export ---------------------------------------------------------------


def test_svg_export_needs_no_backend(specs, tmp_path) -> None:
    out = save_chart(specs["histogram"], str(tmp_path / "c.svg"))
    assert pathlib.Path(out).read_text(encoding="utf-8").startswith("<svg")


def test_json_export_round_trips(specs, tmp_path) -> None:
    out = save_chart(specs["histogram"], str(tmp_path / "c.json"))
    payload = json.loads(pathlib.Path(out).read_text(encoding="utf-8"))
    assert payload["mark"] == "histogram"


@needs_mpl
@pytest.mark.parametrize("suffix", [".png", ".pdf"])
def test_raster_and_print_export(specs, tmp_path, suffix: str) -> None:
    out = save_chart(specs["histogram"], str(tmp_path / f"c{suffix}"))
    assert pathlib.Path(out).stat().st_size > 2000


def test_html_export_falls_back_rather_than_failing(specs, tmp_path) -> None:
    """Without plotly the call still produces a valid self-contained file."""
    out = save_chart(specs["histogram"], str(tmp_path / "c.html"))
    text = pathlib.Path(out).read_text(encoding="utf-8")
    assert "<svg" in text or "plotly" in text.lower()


def test_unknown_export_suffix_is_rejected(specs, tmp_path) -> None:
    with pytest.raises(ValueError, match="cannot infer a format"):
        save_chart(specs["histogram"], str(tmp_path / "c.tiff"))


# -- publishing -----------------------------------------------------------


@needs_mpl
def test_pdf_publishes_multiple_pages(prepared, tmp_path) -> None:
    out = prepared.publish(str(tmp_path / "r.pdf"))
    assert pathlib.Path(out).stat().st_size > 20_000


@needs_mpl
@needs_pypdf
def test_the_pdf_is_navigable(prepared, tmp_path) -> None:
    """Contents, page numbers and a running header.

    A report nobody can cite a page of is a report nobody argues with. These
    are regression assertions rather than aesthetics: the numbering is
    computed in one pass from the deck, so a change to how slides map to
    pages silently desynchronises the contents unless something checks.
    """
    from pypdf import PdfReader

    target = prepared.publish(str(tmp_path / "navigable.pdf"))
    reader = PdfReader(target)
    total = len(reader.pages)

    contents = reader.pages[1].extract_text()
    assert "Contents" in contents

    # Every page states where it sits, and the last page agrees with the
    # count the contents page was numbered against.
    assert f"{total} of {total}" in reader.pages[-1].extract_text()
    assert "Methodology and caveats" in reader.pages[-1].extract_text()


@needs_mpl
@needs_pypdf
def test_the_pdf_contents_point_at_the_right_pages(prepared, tmp_path) -> None:
    """The numbers in the contents are not decoration."""
    from pypdf import PdfReader

    from smartprep.reporting.publish import build_deck

    deck = build_deck(prepared)
    target = prepared.publish(str(tmp_path / "toc.pdf"))
    reader = PdfReader(target)

    contents = reader.pages[1].extract_text()
    for slide in deck.slides[:4]:
        assert slide.title[:28] in contents

    # Follow the first entry: the page it names must be the one that carries
    # that heading.
    first = deck.slides[0]
    assert first.title[:28] in reader.pages[2].extract_text()


@needs_mpl
@needs_pypdf
def test_every_printed_figure_carries_a_caption(prepared, tmp_path) -> None:
    """A figure without a caption is a figure a reader cannot cite, and a
    sampled figure without one is a figure that misleads."""
    from pypdf import PdfReader

    target = prepared.publish(str(tmp_path / "captioned.pdf"))
    text = " ".join(page.extract_text() for page in PdfReader(target).pages)
    assert "Figure " in text


@needs_mpl
@needs_pypdf
def test_the_pdf_states_the_distinctions_it_is_built_on(prepared, tmp_path) -> None:
    """Scan coverage is not health; detection confidence is not repair
    confidence; clean_df is not verified_df. A reader holding only the PDF
    should not have to have read the documentation to know that."""
    from pypdf import PdfReader

    target = prepared.publish(str(tmp_path / "methodology.pdf"))
    text = " ".join(page.extract_text() for page in PdfReader(target).pages)
    for claim in (
        "Scan coverage is not data health",
        "Detection confidence is not repair confidence",
        "clean_df is not verified_df",
        "Cleaning is not preprocessing",
    ):
        assert claim in text, f"the PDF does not state: {claim}"


def test_pptx_publishes(prepared, tmp_path) -> None:
    pytest.importorskip("pptx")
    out = prepared.publish(str(tmp_path / "r.pptx"))
    assert pathlib.Path(out).stat().st_size > 20_000


def test_notebook_is_runnable_code_not_a_transcript(prepared, tmp_path) -> None:
    """A report the reader can run is a report they can disagree with."""
    out = prepared.publish(str(tmp_path / "r.ipynb"))
    notebook = json.loads(pathlib.Path(out).read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    code = [c for c in notebook["cells"] if c["cell_type"] == "code"]
    assert len(code) >= 6
    assert any("auto_prepare" in "".join(c["source"]) for c in code)


def test_notebook_carries_the_open_findings(prepared, tmp_path) -> None:
    out = prepared.publish(str(tmp_path / "r.ipynb"))
    text = pathlib.Path(out).read_text(encoding="utf-8")
    assert "not a verified dataset" in text
    assert "DUP-CONFLICT-invoice_id" in text


def test_publish_rejects_an_unknown_format(prepared, tmp_path) -> None:
    with pytest.raises(ValueError, match="cannot publish"):
        prepared.publish(str(tmp_path / "r.docx"))


@needs_mpl
def test_the_deck_always_discloses_inaction(prepared) -> None:
    from smartprep.reporting import build_deck

    deck = build_deck(prepared)
    titles = [s.title for s in deck.slides]
    assert "What auto mode did NOT do" in titles
    slide = next(s for s in deck.slides if s.title == "What auto mode did NOT do")
    assert "not a verified dataset" in slide.body


# -- Studio versus report -------------------------------------------------


def test_studio_has_an_interactive_grid(prepared) -> None:
    page = sp.studio(prepared).html
    assert "grid-body" in page
    assert "q-flagged" in page, "quality overlay is why it is not merely a table"


def test_studio_has_a_chart_explorer(prepared) -> None:
    assert "builder-chart" in sp.studio(prepared).html


def test_studio_has_the_stage_walkthrough(prepared) -> None:
    assert "stage-slider" in sp.studio(prepared).html


def test_the_stage_walkthrough_is_under_the_readers_control(prepared) -> None:
    """Play, pause, speed and a jump to any step.

    The stage frames are the one place the library moves, and motion a reader
    cannot stop is motion imposed on them. Each control is asserted because
    each is the difference between a walkthrough and an animation playing at
    somebody.
    """
    page = sp.studio(prepared).html
    assert "id='stage-play'" in page
    assert "id='stage-speed'" in page
    assert "id='stage-steps'" in page
    assert "aria-pressed" in page
    # The label is a live region, so a screen reader is told which step is
    # showing rather than silently left on the first one.
    assert "aria-live='polite'" in page


def test_each_stage_names_what_changed_not_only_where_you_are(prepared) -> None:
    from smartprep.reporting.interactive import CHART_SCRIPT

    assert "'Step ' + (at + 1) + ' of ' + stages.length" in CHART_SCRIPT
    assert "frame.note" in CHART_SCRIPT


def test_studio_sections_cover_the_workflow(prepared) -> None:
    page = sp.studio(prepared).html
    sections = set(re.findall(r'data-target="([a-z]+)"', page))
    # "explore" is gone deliberately: it duplicated the builder. Its three
    # unique chart types were folded into "build" rather than dropped.
    assert {"overview", "grid", "eda", "build", "issues", "guided", "audit"} <= sections
    assert "explore" not in sections


def test_the_archival_report_carries_no_interactive_assets(prepared) -> None:
    """A file meant to open correctly in ten years must not need scripts."""
    report = prepared.report("preparation", "html")
    assert "grid-body" not in report
    assert "stage-slider" not in report
    assert len(report) < len(sp.studio(prepared).html)


def test_both_remain_self_contained(prepared) -> None:
    for page in (prepared.report("preparation", "html"), sp.studio(prepared).html):
        assert not re.search(r'(src|href)\s*=\s*"https?://', page)


def test_grid_caps_rows_and_says_so() -> None:
    frame = pd.DataFrame({"a": range(1200), "b": range(1200)})
    page = sp.studio(frame, prepare=False).html
    assert "first 500" in page
    assert "stays in Python" in page


def test_grid_payload_is_valid_json(prepared) -> None:
    page = sp.studio(prepared).html
    match = re.search(r"window\.__SMARTPREP_GRID__ = (\{.*?\});", page, re.S)
    assert match
    payload = json.loads(match.group(1))
    assert payload["columns"] and payload["rows"]
    assert len(payload["rows"][0]["cells"]) == len(payload["columns"])
