"""Performance budgets, asserted rather than assumed.

Not a benchmark in the "how fast is it" sense -- those numbers depend on the
machine and mean nothing in CI. These are **budgets**: a scan of a hundred
thousand rows must finish in seconds, not minutes, and the Studio must stay a
file you can email. Each one caught a real regression once, or guards a place
where the cost is quadratic if somebody is careless.

The limits are deliberately loose, several times what the operation actually
takes here, so the suite fails on an algorithmic change rather than on a slow
afternoon. A budget tight enough to flake is a budget that gets deleted.

Marked ``slow``: they build large frames, and a developer running the suite
between edits should not wait for them.

    pytest -m "not slow"     # the fast loop
    pytest -m slow           # the budgets
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

import smartprep as sp

pytestmark = pytest.mark.slow


def _frame(rows: int, columns: int = 12) -> pd.DataFrame:
    """A frame with the mess a real one has: mixed types, nulls, categories."""
    rng = np.random.default_rng(0)
    data: dict[str, object] = {}
    for i in range(columns // 4):
        data[f"num{i}"] = rng.normal(100, 20, rows)
        data[f"cat{i}"] = rng.choice(["alpha", "beta", "gamma", "delta"], rows)
        data[f"date{i}"] = pd.date_range("2020-01-01", periods=rows, freq="h")
        holed = pd.Series(rng.normal(size=rows))
        holed[rng.random(rows) < 0.1] = np.nan
        data[f"holed{i}"] = holed
    return pd.DataFrame(data)


class _Timer:
    def __enter__(self) -> _Timer:
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        self.elapsed = time.perf_counter() - self.start


@pytest.mark.parametrize("rows", [10_000, 100_000])
def test_scan_stays_linear_in_rows(rows: int) -> None:
    """The guard that matters most: a detector doing something quadratic is
    invisible at fixture size and fatal at real size."""
    frame = _frame(rows)
    with _Timer() as timer:
        result = sp.scan(frame)
    assert result.row_count == rows
    budget = 4.0 + rows / 10_000
    assert timer.elapsed < budget, (
        f"scan of {rows:,} rows took {timer.elapsed:.1f}s, budget {budget:.1f}s"
    )


def test_profiling_a_wide_frame_is_not_quadratic_in_columns() -> None:
    """Sixty columns, not twelve. Anything comparing every column with every
    other shows up here and nowhere else in the suite."""
    frame = _frame(5_000, columns=60)
    with _Timer() as timer:
        described = sp.profile(frame)
    assert len(described.columns_profiled) == frame.shape[1]
    assert timer.elapsed < 20.0, f"profiling 60 columns took {timer.elapsed:.1f}s"


def test_auto_prepare_completes_within_budget() -> None:
    frame = _frame(50_000)
    with _Timer() as timer:
        result = sp.auto_prepare(frame)
    assert result.clean_df is not None
    assert timer.elapsed < 60.0, f"auto_prepare took {timer.elapsed:.1f}s"


def test_the_studio_stays_a_file_you_can_email() -> None:
    """AD-013's promise is about bytes. It was broken once -- a full cross
    product of chart compositions produced 3.2 MB -- and the caps that fixed
    it are only real if something measures them."""
    frame = _frame(20_000)
    with _Timer() as timer:
        page = sp.studio(frame).html
    size = len(page.encode("utf-8"))

    # Measured at ~45s and ~1.1 MB here. The budget is generous because a
    # tight one flakes on a slow machine and a flaky budget gets deleted; it
    # is still far under the four minutes the whole-frame profile calls cost
    # before they were fixed, which is the class of regression this catches.
    assert size < 2_500_000, f"the Studio is {size // 1024:,} KB on 20k rows"
    assert timer.elapsed < 150.0, f"building the Studio took {timer.elapsed:.1f}s"


def test_studio_cost_does_not_explode_with_rows() -> None:
    """Four times the rows must not cost sixteen times the work.

    The bug this guards against was exactly that shape: every precomputed
    chart profiled the entire frame, so the catalogue multiplied the cost of
    the data rather than adding to it.
    """
    with _Timer() as small:
        sp.studio(_frame(5_000))
    with _Timer() as large:
        sp.studio(_frame(20_000))

    ratio = large.elapsed / max(small.elapsed, 0.01)
    assert ratio < 12.0, (
        f"4x the rows cost {ratio:.1f}x the time; that is superlinear enough "
        "to suggest work is being repeated per chart rather than per dataset"
    )


def test_the_archival_report_does_not_grow_with_the_data(tmp_path: object) -> None:
    """A report of a million rows and a report of a thousand describe the same
    things. If the file grows with the data, something is embedding rows."""
    small = sp.auto_prepare(_frame(1_000))
    large = sp.auto_prepare(_frame(30_000))

    import pathlib

    sizes = []
    for name, result in (("small", small), ("large", large)):
        written = result.export_report(str(pathlib.Path(str(tmp_path)) / f"{name}.html"))
        sizes.append(pathlib.Path(written).stat().st_size)

    assert sizes[1] < sizes[0] * 3, (
        f"the report grew from {sizes[0] // 1024} KB to {sizes[1] // 1024} KB "
        "for 30x the rows; something is embedding data rather than summarising it"
    )


def test_linkage_blocking_keeps_the_comparison_tractable() -> None:
    """Without blocking this is quadratic: ten thousand records is fifty
    million pairs. The whole point of the block key is that this test finishes.
    """
    rng = np.random.default_rng(1)
    # The distinguishing part comes first. A key that does not discriminate is
    # covered by the refusal test below.
    names = [f"{rng.integers(0, 3000)} Company Ltd" for _ in range(10_000)]
    frame = pd.DataFrame({"name": names, "city": rng.choice(["A", "B"], 10_000)})

    with _Timer() as timer:
        report = sp.link(frame, ("name", "city"), block_prefix=4)

    total_pairs = len(frame) * (len(frame) - 1) // 2
    assert report.compared < total_pairs / 50, "blocking is not reducing the work"
    assert timer.elapsed < 30.0, f"linkage took {timer.elapsed:.1f}s"


def test_a_block_key_that_does_not_discriminate_is_refused() -> None:
    """Every name beginning "Company" shares a prefix, so a ten-thousand-row
    file becomes one block and fifty million comparisons.

    Left alone this looks like a hang, which is the worst way for a library to
    say the block key is wrong.
    """
    rng = np.random.default_rng(1)
    names = [f"Company {rng.integers(0, 3000)} Ltd" for _ in range(10_000)]
    frame = pd.DataFrame({"name": names, "city": rng.choice(["A", "B"], 10_000)})

    with _Timer() as timer, pytest.raises(ValueError, match="does not discriminate"):
        sp.link(frame, ("name", "city"), block_prefix=6)
    assert timer.elapsed < 15.0, "the refusal should be immediate, not eventual"


def test_mechanism_testing_is_bounded_by_its_column_cap() -> None:
    """Every column against every other is quadratic in columns, so the
    predictor count is capped. This asserts the cap is doing something."""
    rng = np.random.default_rng(2)
    rows = 3_000
    data = {f"x{i}": rng.normal(size=rows) for i in range(40)}
    target = pd.Series(rng.normal(size=rows))
    target[rng.random(rows) < 0.2] = np.nan
    data["target"] = target

    with _Timer() as timer:
        report = sp.mechanism(pd.DataFrame(data))
    assert report.get("target").tested_against <= 25
    assert timer.elapsed < 30.0, f"mechanism testing took {timer.elapsed:.1f}s"


def test_repeated_preparation_is_idempotent_and_cheap() -> None:
    """The second run has nothing to repair, so it must not cost what the
    first did. A pass that re-does its own work is a pass that will be run
    twice by somebody."""
    frame = _frame(20_000)
    first = sp.auto_prepare(frame)
    with _Timer() as timer:
        second = sp.auto_prepare(first.clean_df)
    assert second.audit.cells_changed == 0, "a second pass changed data"
    assert timer.elapsed < 30.0
