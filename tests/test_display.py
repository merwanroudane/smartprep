"""Tables to journal convention, and the rule that keeps them honest.

The presentation layer's whole promise is that it computes nothing. A view
that derives its own count acquires the ability to disagree with the object it
describes, and a reader with two numbers has no way to choose. The first
section asserts that rather than trusting the docstring.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

import smartprep as sp
from conftest import SCAN_CONTEXT
from smartprep.core.enums import Severity
from smartprep.display import Align, Column, Table, format_number, humanise
from smartprep.views import audit_table, column_table, issue_table, severity_table


@pytest.fixture(scope="module")
def scanned(synthetic: pd.DataFrame) -> object:
    return sp.scan(synthetic, **SCAN_CONTEXT)


@pytest.fixture(scope="module")
def prepared_result(synthetic: pd.DataFrame) -> object:
    return sp.auto_prepare(synthetic, **SCAN_CONTEXT)


# ==========================================================================
# The view computes nothing
# ==========================================================================


def test_the_severity_table_agrees_with_the_object(scanned: object) -> None:
    """Every count in the table came from the findings; none was re-derived."""
    table = severity_table(scanned.issues)
    total = sum(row["n"] for row in table.rows)
    assert total == len(scanned.issues)

    for row in table.rows:
        expected = sum(1 for i in scanned.issues if i.severity is row["severity"])
        assert row["n"] == expected


def test_the_column_table_agrees_with_the_object(scanned: object) -> None:
    table = column_table(scanned)
    for row in table.rows:
        found = [i for i in scanned.issues if row["column"] in i.columns]
        assert row["n"] == len(found)
        assert row["worst"] == max(i.severity for i in found)


def test_the_audit_table_agrees_with_the_log(prepared_result: object) -> None:
    table = audit_table(prepared_result.audit)
    assert len(table) == len(list(prepared_result.audit))
    assert sum(r["cells"] for r in table.rows) == prepared_result.audit.cells_changed


def test_a_view_never_rounds_a_number_into_a_different_one(scanned: object) -> None:
    """Formatting may shorten a number. It may not change which number it is."""
    table = issue_table(scanned.issues)
    for row, issue in zip(table.rows, scanned.issues, strict=True):
        assert row["detection"] == issue.detection_confidence
        assert row["rows"] == issue.affected_row_count


def test_the_exported_frame_holds_values_not_strings(scanned: object) -> None:
    """A DataFrame of formatted strings cannot be sorted or filtered, which is
    the only reason to want a DataFrame."""
    frame = scanned.to_frame("columns")
    assert pd.api.types.is_integer_dtype(frame["Findings"])
    assert frame["Findings"].sum() > 0


# ==========================================================================
# Journal conventions
# ==========================================================================


def _sample() -> Table:
    return Table(
        columns=[
            Column("col", "Column"),
            Column("n", "Findings", Align.RIGHT),
            Column("conf", "Detection", Align.RIGHT, precision=0, unit="%"),
        ],
        rows=[
            {"col": "invoice_date", "n": 4, "conf": 0.99},
            {"col": "city", "n": 26, "conf": 0.9500000000000001},
            {"col": "revenue", "n": 1, "conf": None},
        ],
        title="Findings by column",
        notes=["Detection confidence is not repair confidence."],
    )


def test_text_tables_use_horizontal_rules_only() -> None:
    """Vertical rules add ink without adding information; the eye groups
    columns by alignment already."""
    text = _sample().to_text()
    assert "|" not in text
    assert text.count("---") >= 3


def test_figures_are_right_aligned_and_text_is_not() -> None:
    """Right alignment puts the units digit under the units digit, which is
    what makes two numbers comparable at a glance."""
    lines = _sample().to_text().splitlines()
    body = [line for line in lines if "invoice_date" in line or "city" in line]
    assert len(body) == 2
    # The single-digit count is padded to sit under the two-digit one.
    assert body[0].index("4") > body[1].index("2")


def test_precision_comes_from_the_quantity_not_the_float() -> None:
    """0.9500000000000001 is not more precise than 0.95, only longer."""
    assert "0.9500000000000001" not in _sample().to_text()
    assert "95%" in _sample().to_text()


def test_absence_is_a_dash_not_a_zero() -> None:
    """An empty cell and a zero are different claims."""
    text = _sample().to_text()
    assert "0%" not in text
    assert "-" in text.splitlines()[-2]


def test_notes_sit_below_the_foot_rule() -> None:
    text = _sample().to_text()
    assert text.strip().endswith("Detection confidence is not repair confidence.")


def test_plain_text_survives_a_cp1252_console() -> None:
    """A default Windows terminal raises UnicodeEncodeError on an em dash. A
    table that crashes the terminal it was written for is worse than one that
    prints a hyphen."""
    text = _sample().to_text()
    text.encode("cp1252")  # raises if a typographic character survived


def test_richer_formats_keep_the_real_characters() -> None:
    """The transliteration is for terminals only; HTML and LaTeX have no
    encoding problem and should not be degraded."""
    assert "—" in _sample().to_html() or "&mdash;" in _sample().to_html()


# ==========================================================================
# Enums read as words
# ==========================================================================


def test_severity_reads_as_a_word_not_an_ordinal(scanned: object) -> None:
    """Severity is an IntEnum, so a naive numeric check prints 5. That is the
    implementation's answer, not the reader's."""
    text = severity_table(scanned.issues).to_text()
    assert "Blocking" in text or "High warning" in text
    assert not re.search(r"^\s*[0-5]\s+\d", text, re.M)


def test_humanise_turns_a_member_into_a_phrase() -> None:
    assert humanise(Severity.HIGH_WARNING) == "High warning"
    assert humanise(None) == "—"
    assert humanise(True) == "yes"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "—"),
        (1234567, "1,234,567"),
        (0.5, "0.5000"),
        (12.3456, "12.35"),
        (98765.4321, "98,765"),
        (float("nan"), "—"),
    ],
)
def test_numbers_are_formatted_the_way_a_reader_would_write_them(
    value: object, expected: str
) -> None:
    assert format_number(value) == expected


# ==========================================================================
# Formats
# ==========================================================================


def test_latex_is_booktabs_with_no_vertical_rules() -> None:
    """booktabs exists to prevent exactly the rules a default table adds."""
    latex = _sample().to_latex(label="tab:x")
    for command in ("\\toprule", "\\midrule", "\\bottomrule", "\\label{tab:x}"):
        assert command in latex
    assert "\\hline" not in latex
    assert "|" not in latex.split("\\begin{tabular}")[1].split("}")[0]


def test_latex_escapes_what_would_break_a_build() -> None:
    """An unescaped underscore in a column name is a compile error in the
    reader's manuscript, not ours."""
    latex = _sample().to_latex()
    assert "invoice\\_date" in latex
    assert "99\\%" in latex


def test_markdown_carries_the_alignment() -> None:
    markdown = _sample().to_markdown()
    assert "---:" in markdown
    assert ":---" in markdown


def test_html_is_scoped_so_it_cannot_restyle_a_notebook() -> None:
    """A stylesheet that reaches beyond its own table is a library reformatting
    somebody else's document."""
    html = _sample().to_html()
    for rule in re.findall(r"^\.?([a-z-]+)\s*\{", html, re.M):
        assert rule.startswith("sp-"), f"unscoped CSS rule: {rule}"


def test_an_empty_table_says_what_it_means() -> None:
    """'Nothing to show' and 'nothing was found' are different, and only one
    is reassuring."""
    empty = Table(columns=[Column("a", "A")], rows=[], empty="No findings.")
    assert "No findings." in empty.to_text()
    assert "No findings." in empty.to_html()


def test_long_tables_say_what_they_cut() -> None:
    table = Table(
        columns=[Column("n", "N", Align.RIGHT)],
        rows=[{"n": i} for i in range(120)],
    )
    text = table.to_text(max_rows=10)
    assert "110 more rows" in text


# ==========================================================================
# The result objects
# ==========================================================================


def test_the_scan_repr_says_the_shape(scanned: object) -> None:
    """`<ScanResult issues=28 coverage=100%>` omits the two numbers a reader
    needs to know whether 28 is a lot."""
    text = repr(scanned)
    assert "rows=" in text and "cols=" in text
    assert "issues=" in text and "coverage=" in text


def test_the_notebook_view_leads_with_a_summary(scanned: object) -> None:
    html = scanned._repr_html_()
    assert "findings" in html
    assert "<table" in html


def test_every_named_view_builds(scanned: object, prepared_result: object) -> None:
    for what in ("findings", "severity", "columns", "categories"):
        assert isinstance(scanned.table(what), Table)
    for what in ("audit", "applied", "declined", "health", "findings"):
        assert isinstance(prepared_result.table(what), Table)


def test_an_unknown_view_names_the_ones_that_exist(scanned: object) -> None:
    with pytest.raises(ValueError, match="choose from"):
        scanned.table("nonsense")


def test_explain_states_what_was_left_open(prepared_result: object) -> None:
    """The disclosure that makes the rest trustworthy. A tool reporting only
    its successes leaves its silence to be interpreted."""
    text = prepared_result.explain()
    assert "left open" in text
    assert "guided_prepare()" in text


def test_show_still_opens_the_studio(prepared_result: object) -> None:
    """`show()` was published meaning 'open the Studio'. Repurposing a shipped
    method is what a major version is for, and a table is not worth one."""
    assert prepared_result.show.__doc__ is not None
    assert "studio" in prepared_result.show.__doc__.lower()
    # And the table view lives under its own name rather than replacing it.
    assert callable(prepared_result.display)


def test_the_audit_repr_counts_declines_too(prepared_result: object) -> None:
    """An audit that showed only its actions would make silence look like
    nothing had been considered."""
    text = repr(prepared_result.audit)
    assert "applied" in text and "declined" in text


def test_the_confidence_note_travels_with_the_numbers(scanned: object) -> None:
    """The distinction the library rests on was visible only to someone who
    knew to look for two similarly named dataclass fields."""
    text = issue_table(scanned.issues).to_text()
    assert "Detection" in text and "Repair" in text
    assert "Detection confidence is the certainty" in text


def test_exported_frames_are_readable_and_still_sort_correctly(scanned: object) -> None:
    """pandas coerces an IntEnum to int64, so a severity column exports as
    0, 3, 1 -- which sorts correctly and tells the reader nothing.

    An ordered categorical does both jobs: it prints "High warning" and
    compares in severity order rather than alphabetically, which is the whole
    reason not to export the name as a plain string.
    """
    frame = scanned.to_frame("findings")
    assert str(frame["Severity"].dtype) == "category"
    assert frame["Severity"].cat.ordered

    categories = list(frame["Severity"].cat.categories)
    assert categories[0] == "Info"
    assert categories[-1] == "Blocking"
    assert "High warning" in set(frame["Severity"])

    # Alphabetically "Critical review" precedes "Info"; by severity it does
    # not. The categorical must sort the second way.
    present = set(frame["Severity"].dropna())
    most_severe = max(present, key=categories.index)
    assert frame["Severity"].max() == most_severe
    assert most_severe != max(present)  # i.e. not the alphabetical answer


def test_numeric_columns_are_left_as_numbers(scanned: object) -> None:
    """The categorical treatment applies to enums only. Turning a confidence
    into a category would make it unusable for anything quantitative."""
    frame = scanned.to_frame("findings")
    assert pd.api.types.is_float_dtype(frame["Detection"])
    assert pd.api.types.is_integer_dtype(frame["Rows"])
