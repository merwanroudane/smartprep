"""The interactive layer for the Studio.

The HTML report and the Studio are different products and this module is what
separates them:

* the **report** is self-contained, offline and archival, with static SVG --
  it must still render correctly in ten years from a file on a disk;
* the **Studio** is an analysis tool, where zoom, brushing and linked
  selection are the point.

Both draw the *same* ``ChartSpec`` objects. The interactivity here is written
in plain JavaScript over the spec JSON embedded in the page -- no CDN, no
bundler, no 4 MB of vendored library. That keeps the Studio a single file you
can email, while still giving it real interaction rather than hover text.

Nothing here computes or repairs anything. It reads specs and records
decisions.
"""

from __future__ import annotations

__all__ = ["GRID_CSS", "GRID_SCRIPT", "CHART_SCRIPT", "data_grid_html"]

GRID_CSS = """
.grid-wrap { border: 1px solid var(--line); border-radius: 7px; overflow: auto;
  max-height: 460px; position: relative; }
table.grid { border-collapse: separate; border-spacing: 0; width: 100%;
  font-size: 12px; font-family: ui-monospace, Menlo, Consolas, monospace; }
table.grid th { position: sticky; top: 0; background: var(--panel); z-index: 2;
  cursor: pointer; user-select: none; white-space: nowrap; }
table.grid th:focus-visible, table.grid tr:focus-visible {
  outline: 3px solid var(--accent); outline-offset: -3px; }
table.grid th:hover { color: var(--accent); }
table.grid th .dir { color: var(--accent); font-size: 9px; }
table.grid td { white-space: nowrap; max-width: 260px; overflow: hidden;
  text-overflow: ellipsis; }
table.grid tr.sel td { background: #eaf2f8; }
td.q-missing { background: #fdf2f2; color: var(--danger); font-style: italic; }
td.q-flagged { background: #fdf8ee; font-weight: 600; }
td.q-flagged::before { content: "\\26a0\\fe0e "; color: var(--warn); }
td.q-changed { border-left: 2px solid var(--ok); }
td.q-changed::before { content: "\\2713 "; color: var(--ok); }
.grid-tools { display: flex; gap: 8px; margin-bottom: 9px; flex-wrap: wrap;
  align-items: center; }
.grid-tools input, .grid-tools select { font: inherit; font-size: 12px;
  padding: 5px 9px; border: 1px solid var(--line); border-radius: 5px; }
.grid-tools input[type=search] { min-width: 220px; }
.grid-count { color: var(--muted); font-size: 12px; }
.builder { display: flex; gap: 8px; flex-wrap: wrap; align-items: flex-end;
  margin-bottom: 14px; }
.builder label { display: flex; flex-direction: column; font-size: 11px;
  color: var(--muted); gap: 3px; }
.builder select { font: inherit; font-size: 12px; padding: 5px 9px;
  border: 1px solid var(--line); border-radius: 5px; min-width: 130px; }
#builder-out { border: 1px solid var(--line); border-radius: 7px; padding: 8px;
  min-height: 300px; }
.stage-controls { display: flex; gap: 10px; align-items: center; margin: 10px 0;
  flex-wrap: wrap; }
.stage-controls input[type=range] { flex: 1; max-width: 340px; }
.stage-controls button { font: inherit; font-size: 12px; padding: 4px 12px;
  cursor: pointer; border: 1px solid var(--line); border-radius: 5px;
  background: var(--bg); }
.stage-controls button:hover { border-color: var(--accent); color: var(--accent); }
.stage-steps { display: flex; gap: 6px; flex-wrap: wrap; margin: 8px 0; }
.stage-steps button.on { background: var(--accent); color: #fff;
  border-color: var(--accent); }
#stage-label { font-size: 12px; color: var(--muted); }
@media (prefers-reduced-motion: reduce) {
  /* Playback still works; it simply will not start on its own. */
  .stage-controls #stage-play[data-auto] { display: none; }
}
.chart-tip { position: fixed; pointer-events: none; background: #1f2933;
  color: #fff; font-size: 11px; padding: 5px 8px; border-radius: 4px;
  opacity: 0; transition: opacity .1s; z-index: 50; white-space: pre; }
.interactive-chart svg { cursor: crosshair; }
.brushed { outline: 2px solid var(--accent); }
"""

#: Sorting, filtering, quality overlays and row selection over an embedded
#: dataset. Rendered from a JSON payload so the same grid works for any frame.
GRID_SCRIPT = """
(function () {
  var SP = window.SP;
  if (!SP) { return; }
  var payload = SP.payload;
  var body = document.getElementById('grid-body');
  var head = document.getElementById('grid-head');
  var search = document.getElementById('grid-search');
  var colSel = document.getElementById('grid-col');
  var qualSel = document.getElementById('grid-quality');
  var count = document.getElementById('grid-count');
  var toggles = document.getElementById('col-toggles');
  if (!body) { return; }

  var sorts = [];   // [{i, dir}] -- innermost last, so shift-click nests

  // ---- column visibility -----------------------------------------------
  // A forty-column frame is not a grid, it is a horizontal scroll. Hiding a
  // column removes it from the view and from nothing else.
  if (toggles) {
    toggles.innerHTML = payload.columns.map(function (c, i) {
      return "<label><input type='checkbox' checked data-col='" + i + "'>" + c + "</label>";
    }).join('');
    toggles.addEventListener('change', function (e) {
      var box = e.target.closest('input[data-col]');
      if (!box) { return; }
      var i = parseInt(box.dataset.col, 10);
      SP.update(function (st) {
        var at = st.hidden.indexOf(i);
        if (box.checked && at >= 0) { st.hidden.splice(at, 1); }
        if (!box.checked && at < 0) { st.hidden.push(i); }
      });
    });
  }

  function visible(i) { return SP.state.hidden.indexOf(i) < 0; }

  function paintHead() {
    head.querySelectorAll('th').forEach(function (th, i) {
      th.style.display = visible(i) ? '' : 'none';
    });
  }

  // ---- rendering --------------------------------------------------------
  function render(st, view) {
    var rows = view.slice();
    // Multi-column sort: the last key clicked breaks ties in the ones before
    // it, which is the only reading of "sort by A then B" that is useful.
    if (sorts.length) {
      rows.sort(function (a, b) {
        for (var k = 0; k < sorts.length; k++) {
          var s = sorts[k];
          var x = a.cells[s.i], y = b.cells[s.i];
          var nx = parseFloat(x), ny = parseFloat(y);
          var cmp = (!isNaN(nx) && !isNaN(ny))
            ? (nx - ny)
            : String(x).localeCompare(String(y));
          if (cmp) { return cmp * s.dir; }
        }
        return 0;
      });
    }

    body.innerHTML = rows.slice(0, 400).map(function (row) {
      var cells = row.cells.map(function (v, i) {
        if (!visible(i)) { return ''; }
        var cls = row.flags[i] ? 'q-' + row.flags[i] : '';
        var text = v === null || v === undefined || v === '' ? '\u2014' : String(v);
        return '<td class="' + cls + '" data-col="' + i + '" tabindex="-1">' +
          text.replace(/&/g, '&amp;').replace(/</g, '&lt;') + '</td>';
      }).join('');
      var picked = st.rows.indexOf(row.key) >= 0;
      return '<tr tabindex="0" data-key="' + row.key + '"' +
        ' aria-selected="' + (picked ? 'true' : 'false') + '"' +
        (picked ? ' class="sel"' : '') + '>' + cells + '</tr>';
    }).join('');

    if (count) {
      count.textContent = rows.length + ' of ' + payload.rows.length + ' rows' +
        (rows.length > 400 ? ' (showing first 400)' : '') +
        (st.rows.length ? ' \u00b7 ' + st.rows.length + ' selected' : '');
    }
    paintHead();
  }

  // ---- sorting ----------------------------------------------------------
  head.querySelectorAll('th').forEach(function (th, i) {
    function sort(additive) {
      var at = -1;
      sorts.forEach(function (s, k) { if (s.i === i) { at = k; } });
      if (at >= 0) {
        sorts[at].dir = -sorts[at].dir;
      } else {
        if (!additive) { sorts = []; }
        sorts.push({ i: i, dir: 1 });
      }
      head.querySelectorAll('th').forEach(function (h, j) {
        var marker = h.querySelector('.dir');
        var mine = null;
        sorts.forEach(function (s, k) { if (s.i === j) { mine = { s: s, k: k }; } });
        if (marker) {
          marker.textContent = mine
            ? (mine.s.dir > 0 ? '\u25b2' : '\u25bc') +
              (sorts.length > 1 ? String(mine.k + 1) : '')
            : '';
        }
        h.setAttribute('aria-sort', mine
          ? (mine.s.dir > 0 ? 'ascending' : 'descending') : 'none');
      });
      SP.update(function () {});
    }
    th.addEventListener('click', function (e) { sort(e.shiftKey); });
    th.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); sort(e.shiftKey); }
    });
  });

  // ---- selecting and cross-filtering ------------------------------------
  function rowOf(node) { return node ? node.closest('tr[data-key]') : null; }

  body.addEventListener('click', function (e) {
    // Alt-click a cell filters on its value. That is the cross-filter: one
    // gesture in the grid narrows every chart on the page, because they all
    // read the same state.
    var cell = e.target.closest('td[data-col]');
    if (cell && e.altKey) {
      var column = payload.columns[parseInt(cell.dataset.col, 10)];
      var text = cell.textContent === '\u2014' ? '' : cell.textContent;
      SP.addFilter({
        column: column,
        comparison: text === '' ? 'is_missing' : 'eq',
        value: text,
        describe: column + (text === '' ? ' is missing' : " is '" + text + "'")
      });
      return;
    }
    var tr = rowOf(e.target);
    if (tr) { SP.toggleKey(tr.dataset.key); }
  });

  body.addEventListener('keydown', function (e) {
    var tr = rowOf(e.target);
    if (!tr) { return; }
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      SP.toggleKey(tr.dataset.key);
      return;
    }
    // Arrow keys walk the rows, so a keyboard user is not tabbing through
    // four hundred of them to reach the fifth.
    var next = e.key === 'ArrowDown' ? tr.nextElementSibling
             : e.key === 'ArrowUp' ? tr.previousElementSibling : null;
    if (next) { e.preventDefault(); next.focus(); }
  });

  [[search, 'search'], [colSel, 'searchColumn'], [qualSel, 'quality']].forEach(function (pair) {
    var el = pair[0], key = pair[1];
    if (!el) { return; }
    el.addEventListener('input', function () {
      SP.update(function (st) { st[key] = el.value; });
    });
  });

  SP.subscribe(render);
  SP.update(function () {});
})();
"""


#: Tooltips, brush-to-zoom and a live chart builder over the embedded specs.
CHART_SCRIPT = """
(function () {
  // --- tooltips on every rendered mark ---------------------------------
  var tip = document.createElement('div');
  tip.className = 'chart-tip';
  document.body.appendChild(tip);

  function show(node, x, y) {
    var title = node && node.querySelector ? node.querySelector('title') : null;
    if (!title) { return; }
    tip.textContent = title.textContent;
    tip.style.opacity = '1';
    if (x !== undefined) {
      tip.style.left = (x + 14) + 'px';
      tip.style.top = (y + 14) + 'px';
    }
  }

  document.addEventListener('mouseover', function (e) {
    show(e.target.closest(
      'rect[data-v], circle[data-v], .chart svg rect, .chart svg circle'));
  });

  // A tooltip only a mouse can reach is a tooltip half the readers never see.
  // The marks are focusable because they are brushable, so focusing one shows
  // its value in the same place hovering does.
  document.addEventListener('focusin', function (e) {
    var node = e.target.closest('[data-keys]');
    if (!node) { return; }
    var box = node.getBoundingClientRect();
    show(node, box.left + box.width / 2, box.top + box.height);
  });
  document.addEventListener('focusout', function () { tip.style.opacity = '0'; });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { tip.style.opacity = '0'; }
  });
  document.addEventListener('mousemove', function (e) {
    tip.style.left = (e.clientX + 14) + 'px';
    tip.style.top = (e.clientY + 14) + 'px';
  });
  document.addEventListener('mouseout', function (e) {
    if (e.target.closest('svg')) { tip.style.opacity = '0'; }
  });

  // --- chart builder ----------------------------------------------------
  var specs = window.__SMARTPREP_SPECS__ || {};
  var out = document.getElementById('builder-out');
  var pick = document.getElementById('builder-chart');
  if (out && pick) {
    function draw() {
      var chosen = specs[pick.value];
      out.innerHTML = chosen ? chosen.svg :
        '<p class="lede">No chart for that combination.</p>';
      var why = document.getElementById('builder-why');
      if (why) { why.textContent = chosen ? chosen.rationale : ''; }
    }
    pick.addEventListener('change', draw);
    draw();
  }

  // --- stage walkthrough -------------------------------------------------
  // Frames are ordered steps of a real process, so moving through them
  // carries meaning. Nothing animates for decoration. Playback is under the
  // reader's control -- play, pause, speed, and a direct jump to any step --
  // because motion a reader cannot stop is motion imposed on them.
  var slider = document.getElementById('stage-slider');
  var stageOut = document.getElementById('stage-out');
  var stageLabel = document.getElementById('stage-label');
  var stages = window.__SMARTPREP_STAGES__ || [];
  if (slider && stageOut && stages.length) {
    slider.max = String(stages.length - 1);
    var timer = null;
    var play = document.getElementById('stage-play');
    var speed = document.getElementById('stage-speed');
    var steps = document.getElementById('stage-steps');

    if (steps) {
      steps.innerHTML = stages.map(function (frame, i) {
        return '<button type="button" data-step="' + i + '">' +
          (i + 1) + '. ' + frame.label + '</button>';
      }).join('');
    }

    function showStage() {
      var at = parseInt(slider.value, 10);
      var frame = stages[at];
      stageOut.innerHTML = frame.svg;
      // The transition description, not only the label: a reader needs to
      // know what changed between this frame and the last, not merely where
      // they are.
      stageLabel.textContent = 'Step ' + (at + 1) + ' of ' + stages.length +
        ' — ' + frame.label + ' — ' + frame.note;
      if (steps) {
        steps.querySelectorAll('button').forEach(function (b, i) {
          b.classList.toggle('on', i === at);
          b.setAttribute('aria-current', i === at ? 'step' : 'false');
        });
      }
    }

    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
      if (play) { play.textContent = 'Play'; play.setAttribute('aria-pressed', 'false'); }
    }

    function start() {
      stop();
      var wait = speed ? parseInt(speed.value, 10) : 700;
      if (play) { play.textContent = 'Pause'; play.setAttribute('aria-pressed', 'true'); }
      timer = setInterval(function () {
        var next = parseInt(slider.value, 10) + 1;
        if (next >= stages.length) { stop(); return; }
        slider.value = String(next);
        showStage();
      }, wait);
    }

    slider.addEventListener('input', function () { stop(); showStage(); });
    if (play) {
      play.addEventListener('click', function () {
        if (timer) { stop(); return; }
        if (parseInt(slider.value, 10) >= stages.length - 1) { slider.value = '0'; }
        start();
      });
    }
    if (speed) { speed.addEventListener('change', function () { if (timer) { start(); } }); }
    if (steps) {
      steps.addEventListener('click', function (e) {
        var button = e.target.closest('button[data-step]');
        if (!button) { return; }
        stop();
        slider.value = button.dataset.step;
        showStage();
      });
    }
    showStage();
  }
})();
"""


def data_grid_html(columns: list[str]) -> str:
    """The grid shell. Rows arrive as JSON and are rendered by the script."""
    import html as _html

    # scope, role and tabindex are what make the grid usable without a mouse:
    # a screen reader announces which column a cell belongs to, and a keyboard
    # user can reach and operate every sort control.
    header = "".join(
        f"<th scope='col' tabindex='0' role='columnheader' aria-sort='none'>"
        f"{_html.escape(str(c))} <span class='dir' aria-hidden='true'></span></th>"
        for c in columns
    )
    options = "".join(
        f"<option value='{_html.escape(str(c))}'>{_html.escape(str(c))}</option>" for c in columns
    )
    return (
        "<div class='grid-tools'>"
        "<label class='sr-only' for='grid-search'>Search values</label>"
        "<input type='search' id='grid-search' placeholder='Search values…'>"
        "<label class='sr-only' for='grid-col'>Column to search</label>"
        f"<select id='grid-col'><option value='*'>all columns</option>{options}</select>"
        "<label class='sr-only' for='grid-quality'>Filter by data quality</label>"
        "<select id='grid-quality'>"
        "<option value='all'>all rows</option>"
        "<option value='missing'>rows with missing values</option>"
        "<option value='flagged'>rows in a finding</option>"
        "</select>"
        "<span class='grid-count' id='grid-count' role='status' "
        "aria-live='polite'></span>"
        "</div>"
        "<div class='col-toggles' id='col-toggles' role='group' "
        "aria-label='Show or hide columns'></div>"
        "<div class='grid-wrap' tabindex='0' role='region' "
        "aria-label='Data grid'><table class='grid'>"
        f"<thead id='grid-head'><tr>{header}</tr></thead>"
        "<tbody id='grid-body'></tbody></table></div>"
        "<p class='lede' style='margin-top:10px'>Click a row to select it; "
        "arrow keys move between rows. Enter on a column header sorts, "
        "shift-Enter adds a second sort key. <b>Alt-click a cell</b> to filter "
        "the whole page on that value. Flagged cells carry a marker as well as "
        "a colour. "
        "Sorting and filtering here change what you see, never the data.</p>"
    )
