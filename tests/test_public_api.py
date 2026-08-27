"""The public surface, frozen against accidental change.

Before 1.0 the API may change; it may not change *by accident*. Removing a
name, or adding one nobody meant to support, are both easy to do in a refactor
and impossible to notice in a diff of six hundred lines. The snapshot makes
either one a failing test with a message saying which.

Updating the snapshot is the deliberate act:

    python -c "import json,pathlib,smartprep as sp; \\
      pathlib.Path('tests/public_api.json').write_text(json.dumps(sorted(sp.__all__), indent=1))"

Doing that in the same commit as the change is the point -- the reviewer then
sees the surface move, which is exactly the thing worth reviewing.
"""

from __future__ import annotations

import json
import pathlib

import pytest

import smartprep as sp

SNAPSHOT = pathlib.Path(__file__).with_name("public_api.json")


def _recorded() -> set[str]:
    return set(json.loads(SNAPSHOT.read_text(encoding="utf-8")))


def test_nothing_was_removed_from_the_public_api() -> None:
    """A removed name breaks somebody's import. Deliberate removals update the
    snapshot; accidental ones fail here."""
    missing = sorted(_recorded() - set(sp.__all__))
    assert not missing, (
        f"these names left the public API: {missing}. If that was intended, "
        "regenerate tests/public_api.json in the same commit."
    )


def test_nothing_was_added_without_being_noticed() -> None:
    """An accidental export is a support commitment nobody agreed to."""
    added = sorted(set(sp.__all__) - _recorded())
    assert not added, (
        f"these names joined the public API: {added}. If that was intended, "
        "regenerate tests/public_api.json in the same commit."
    )


def test_every_exported_name_actually_exists() -> None:
    """``__all__`` is a promise. A name in it that cannot be imported turns
    `from smartprep import *` into an AttributeError."""
    broken = [name for name in sp.__all__ if not hasattr(sp, name)]
    assert not broken, f"exported but absent: {broken}"


def test_the_public_api_has_no_duplicates() -> None:
    assert len(sp.__all__) == len(set(sp.__all__))


def test_star_import_works() -> None:
    """The literal thing ``__all__`` controls, exercised rather than assumed."""
    namespace: dict[str, object] = {}
    exec("from smartprep import *", namespace)  # noqa: S102
    for name in sp.__all__:
        assert name in namespace, f"{name} is in __all__ but star-import missed it"


def test_nothing_public_is_private_by_name() -> None:
    # Dunders are conventional public API; a single leading underscore is not.
    leading = [name for name in sp.__all__ if name.startswith("_") and not name.startswith("__")]
    assert not leading, f"underscore names should not be exported: {leading}"


@pytest.mark.parametrize(
    "name",
    ["scan", "auto_prepare", "guided_prepare", "clean", "studio", "profile", "publish"],
)
def test_the_documented_entry_points_are_present(name: str) -> None:
    """The five entry points AD-002 froze, plus the two the README opens with.
    These are the names most likely to be depended on, so they get their own
    assertion rather than living only inside the snapshot."""
    assert name in sp.__all__
    assert callable(getattr(sp, name))


def test_every_public_callable_has_a_docstring() -> None:
    """An exported function with no docstring is an API nobody can use from
    the REPL, which is where most people meet it."""
    undocumented = [
        name
        for name in sp.__all__
        if callable(getattr(sp, name)) and not (getattr(sp, name).__doc__ or "").strip()
    ]
    assert not undocumented, f"public but undocumented: {undocumented}"


def test_the_version_is_readable_and_parseable() -> None:
    from packaging.version import Version

    assert isinstance(sp.__version__, str)
    Version(sp.__version__)
