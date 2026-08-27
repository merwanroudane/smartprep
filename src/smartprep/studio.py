"""``sp.studio()`` -- the interactive workspace.

Per AD-010 and the Studio specification, this is **not a second
implementation**. It renders results the core already computed, and the only
thing it produces is a decision file that ``guided_prepare(decisions=...)``
replays. No cleaning logic lives here.

It is a single self-contained HTML page rather than a client/server
application. That is a deliberate trade: no build step, no port, no process to
leave running, and it works identically in a notebook, a browser, an emailed
archive and a locked-down machine. What it gives up is writing changes back
into the live session -- which is exactly the capability that would let clicks
become unreproducible, so losing it costs less than it looks.
"""

from __future__ import annotations

import pathlib
import tempfile
import webbrowser
from typing import Any

import pandas as pd

from .prepare import PreparationResult, auto_prepare
from .reporting.html import studio_html
from .scan import ScanResult, scan

__all__ = ["Studio", "studio"]


class Studio:
    """A rendered workspace over one dataset.

    Display it in a notebook, save it, or open it in a browser. The decisions
    exported from the page feed straight back into guided mode.
    """

    def __init__(self, html: str, source: ScanResult | PreparationResult) -> None:
        self.html = html
        self.source = source

    def save(self, path: str = "smartprep_studio.html") -> str:
        target = pathlib.Path(path)
        target.write_text(self.html, encoding="utf-8")
        return str(target.resolve())

    def open(self) -> str:
        """Write to a temporary file and open the default browser."""
        target = pathlib.Path(tempfile.gettempdir()) / "smartprep_studio.html"
        target.write_text(self.html, encoding="utf-8")
        webbrowser.open(target.as_uri())
        return str(target)

    def apply_decisions(
        self, decisions: str, frame: pd.DataFrame, **context: Any
    ) -> PreparationResult:
        """Replay decisions exported from the page.

        This is the whole contract between the interface and the engine: the
        page emits JSON, guided mode applies it. Nothing else crosses.
        """
        from .guided import guided_prepare

        return guided_prepare(frame, decisions=decisions, **context).finish()

    def _repr_html_(self) -> str:  # pragma: no cover - notebook display hook
        """Render inline in Jupyter, sandboxed so its CSS cannot escape."""
        import base64

        encoded = base64.b64encode(self.html.encode("utf-8")).decode("ascii")
        return (
            f'<iframe src="data:text/html;base64,{encoded}" '
            'style="width:100%;height:760px;border:1px solid #e4e7eb;border-radius:7px"'
            ' sandbox="allow-scripts allow-popups"></iframe>'
        )

    def __repr__(self) -> str:  # pragma: no cover - display only
        return f"<Studio {len(self.html) // 1024} KB — .save(), .open(), or display it>"


def studio(
    data: pd.DataFrame | ScanResult | PreparationResult,
    *,
    prepare: bool = True,
    open_browser: bool = False,
    **context: Any,
) -> Studio:
    """Open the Studio over a frame, a scan, or a completed preparation.

    Parameters
    ----------
    data:
        A DataFrame, or a result you already computed. Passing an existing
        result avoids re-running the scan.
    prepare:
        With a DataFrame, run ``auto_prepare`` first so the Studio can show
        before/after and the audit. Set ``False`` for diagnosis only.
    open_browser:
        Also open the page in the default browser.
    """
    if isinstance(data, pd.DataFrame):
        source: ScanResult | PreparationResult = (
            auto_prepare(data, **context) if prepare else scan(data, **context)
        )
        frame = data
    elif isinstance(data, PreparationResult):
        source, frame = data, data.clean_df
    elif isinstance(data, ScanResult):
        source, frame = data, None
    else:
        raise TypeError(
            "studio() expects a DataFrame, ScanResult or PreparationResult, "
            f"got {type(data).__name__}"
        )

    workspace = Studio(studio_html(source, frame), source)
    if open_browser:
        workspace.open()
    return workspace
