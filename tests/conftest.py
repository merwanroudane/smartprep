"""Shared fixtures.

Two datasets, two purposes:

* ``synthetic`` -- ships with the package, so the acceptance contract actually
  runs for anyone who installs it. Every test that can use it, does.
* ``raw`` -- the real 1,210-row stress workbook, which is not distributed.
  Tests using it are marked ``stress`` and skip cleanly when it is absent.

Both carry frozen counts. Changing one is a behaviour change, not a test fix.
"""

from __future__ import annotations

import pathlib

import pandas as pd
import pytest

import smartprep as sp
from synthetic import EXPECTED, build

ROOT = pathlib.Path(__file__).resolve().parents[1]
STRESS_WORKBOOK = ROOT / "data_project.xlsx"

#: Context describing the data's semantics to the detectors. In real use this
#: comes from a data contract; here it stands in for one.
SCAN_CONTEXT = {
    "identifier": "invoice_id",
    "key": "invoice_id",
    "compare_to": "invoice_date",
    "date_columns": ("invoice_date",),
    "categorical": (
        "country",
        "city",
        "sector",
        "payment_method",
        "currency",
        "status",
        "sales_channel",
    ),
}


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "stress: requires the real stress workbook, which is not distributed",
    )


# -- shipped fixture -------------------------------------------------------


@pytest.fixture(scope="session")
def synthetic() -> pd.DataFrame:
    return build()


@pytest.fixture(scope="session")
def expected() -> dict[str, int]:
    return EXPECTED


@pytest.fixture(scope="session")
def scanned(synthetic: pd.DataFrame) -> sp.ScanResult:
    return sp.scan(synthetic, **SCAN_CONTEXT)


@pytest.fixture(scope="session")
def prepared(synthetic: pd.DataFrame) -> sp.PreparationResult:
    return sp.auto_prepare(synthetic, **SCAN_CONTEXT)


# -- real stress workbook --------------------------------------------------


@pytest.fixture(scope="session")
def raw() -> pd.DataFrame:
    if not STRESS_WORKBOOK.exists():  # pragma: no cover
        pytest.skip(
            f"stress workbook not present at {STRESS_WORKBOOK}; "
            "these tests run in the project repository only"
        )
    return pd.read_excel(STRESS_WORKBOOK, sheet_name="raw_data", dtype=object)


@pytest.fixture(scope="session")
def result(raw: pd.DataFrame) -> sp.ScanResult:
    return sp.scan(raw, **SCAN_CONTEXT)


def issue(result: sp.ScanResult, issue_id: str) -> sp.Issue:
    """Fetch one issue by id, failing with a useful message if absent."""
    try:
        return result.get(issue_id)
    except KeyError as exc:
        raise AssertionError(str(exc)) from exc
