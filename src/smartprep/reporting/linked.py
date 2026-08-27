"""Linked analytics -- one interaction state, shared by every panel on the page.

This is the browser half of :mod:`smartprep.core.state`. The Python object and
this script hold the same shape, so a view assembled by clicking can be sent
back, rebuilt in Python, and replayed -- and a view assembled in Python can be
handed to the page.

**What the page is allowed to do.** It filters, selects, counts and
highlights. Those are properties of a *view*, and computing them here is what
makes brushing feel immediate instead of arriving a round trip later.

**What the page is never allowed to do.** Compute an analysis. There is no
mean, no correlation, no imputation and no repair in this file. Every
statistic shown anywhere in the Studio was computed by the SmartPrep core and
arrived as a rendered :class:`~smartprep.viz.spec.ChartSpec`. The distinction
matters because the moment a browser computes a number a reader might quote,
that number has to be reconciled with the Python one forever afterwards.

The visual builder therefore chooses among **precomputed** compositions rather
than aggregating in JavaScript. A combination nobody precomputed is answered
with the one line of Python that produces it, which is honest about the
single-file design (AD-013): the page cannot run pandas, and pretending
otherwise would mean shipping a second, worse implementation of it.
"""

from __future__ import annotations

__all__ = ["LINKED_CSS", "STATE_SCRIPT", "BUILDER_SCRIPT", "SANDBOX_SCRIPT"]


LINKED_CSS = """
.chips { display: flex; gap: 7px; flex-wrap: wrap; margin: 10px 0; min-height: 26px;
  align-items: center; }
.chip { display: inline-flex; align-items: center; gap: 6px; font-size: 11px;
  border: 1px solid var(--line); background: var(--panel); border-radius: 13px;
  padding: 3px 6px 3px 11px; }
.chip b { font-weight: 600; }
.chip button { border: 0; background: transparent; cursor: pointer; font: inherit;
  color: var(--muted); padding: 0 4px; border-radius: 50%; line-height: 1; }
.chip button:hover { color: var(--danger); }
.chips .empty { color: var(--muted); font-size: 12px; }
.linkbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
  border: 1px solid var(--line); border-radius: 7px; padding: 9px 13px;
  margin-bottom: 14px; background: var(--panel); }
.linkbar .count { font-size: 12px; }
.linkbar .count b { font-variant-numeric: tabular-nums; }
.linkbar button { font: inherit; font-size: 12px; padding: 4px 11px; cursor: pointer;
  border: 1px solid var(--line); border-radius: 5px; background: var(--bg); }
.linkbar button:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.linkbar button:disabled { opacity: .45; cursor: default; }
.warn-unstable { color: var(--warn); font-size: 11px; }
.chart svg .mark-dim { opacity: .18; }
.chart svg .mark-on { stroke: var(--fg); stroke-width: 1.5; }
.chart figure { margin: 0; }
.chart figcaption { font-size: 11px; color: var(--muted); margin-top: 6px; }
details.data-table { margin-top: 8px; }
details.data-table summary { font-size: 11px; color: var(--accent); cursor: pointer; }
details.data-table table { font-size: 11px; margin: 8px 0 0; }
.col-toggles { display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 9px; }
.col-toggles label { font-size: 11px; border: 1px solid var(--line); border-radius: 4px;
  padding: 2px 8px; cursor: pointer; display: inline-flex; gap: 5px; align-items: center; }
.col-toggles input { margin: 0; }
.col-toggles label:has(input:checked) { border-color: var(--accent); color: var(--accent); }
.builder-grid { display: grid; grid-template-columns: 210px 1fr; gap: 18px; }
.field-well { border: 1px solid var(--line); border-radius: 7px; padding: 9px;
  max-height: 420px; overflow-y: auto; }
.field-well h4 { margin: 0 0 8px; font-size: 11px; text-transform: uppercase;
  letter-spacing: .05em; color: var(--muted); }
.field { display: flex; justify-content: space-between; gap: 8px; align-items: center;
  border: 1px solid var(--line); border-radius: 5px; padding: 4px 8px; margin-bottom: 5px;
  font-size: 12px; cursor: grab; background: var(--bg); }
.field[aria-disabled="true"] { opacity: .5; cursor: not-allowed; }
.field .k { font-size: 10px; color: var(--muted); }
.field.dragging { opacity: .4; }
.shelf { border: 1px dashed var(--line); border-radius: 6px; padding: 7px 10px;
  min-height: 38px; margin-bottom: 8px; font-size: 12px; }
.shelf.over { border-color: var(--accent); background: #eef4f8; }
.shelf .lbl { font-size: 10px; text-transform: uppercase; letter-spacing: .05em;
  color: var(--muted); display: block; }
.shelf .val { font-weight: 600; }
.shelf button.drop { border: 0; background: none; cursor: pointer; color: var(--muted); }
.recs button { display: block; width: 100%; text-align: left; font: inherit;
  font-size: 12px; padding: 6px 9px; margin-bottom: 5px; border: 1px solid var(--line);
  border-radius: 5px; background: var(--bg); cursor: pointer; }
.recs button:hover { border-color: var(--accent); }
.recs .why { display: block; color: var(--muted); font-size: 11px; margin-top: 2px; }
.sandbox-card { border: 1px solid var(--line); border-radius: 7px; padding: 12px 14px;
  margin-bottom: 11px; }
.sandbox-card.chosen { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.sandbox-card h4 { margin: 0 0 4px; font-size: 13px; }
.sandbox-card .delta { font-size: 12px; font-family: ui-monospace, Menlo, monospace; }
.sandbox-card .delta.moved { color: var(--warn); }
.sandbox-card .refused { color: var(--muted); font-style: italic; font-size: 12px; }
.preview-banner { border-left: 3px solid var(--accent); background: #eef4f8;
  padding: 9px 13px; border-radius: 0 5px 5px 0; font-size: 12px; margin-bottom: 12px; }
.canvas { display: flex; flex-direction: column; gap: 0; margin: 14px 0; }
.node { border: 1px solid var(--line); border-radius: 7px; padding: 10px 14px;
  background: var(--bg); position: relative; }
.node.ran { border-left: 3px solid var(--ok); }
.node.skipped { border-left: 3px solid var(--line); opacity: .62; }
.node.refused { border-left: 3px solid var(--danger); }
.node.idle { border-left: 3px solid var(--muted); }
.node h4 { margin: 0 0 3px; font-size: 13px; display: flex; gap: 9px;
  align-items: baseline; }
.node h4 .stage-no { color: var(--muted); font-size: 11px;
  font-variant-numeric: tabular-nums; }
.node .metrics { display: flex; gap: 16px; flex-wrap: wrap; font-size: 11px;
  color: var(--muted); font-variant-numeric: tabular-nums; margin-top: 4px; }
.node .metrics b { color: var(--fg); font-weight: 600; }
.node .metrics .up { color: var(--ok); }
.node .metrics .down { color: var(--warn); }
.node .warn { font-size: 11px; color: var(--warn); margin-top: 5px; }
.node .ops { font-size: 10px; color: var(--muted); margin-top: 4px;
  font-family: ui-monospace, Menlo, monospace; }
.flow-arrow { align-self: center; color: var(--muted); font-size: 15px;
  line-height: 1; padding: 3px 0; }
.canvas-export { margin-top: 14px; }
.canvas-export pre { background: var(--panel); border: 1px solid var(--line);
  border-radius: 6px; padding: 11px 13px; overflow-x: auto; font-size: 11px; }
"""


#: The store. Everything else on the page reads it and nothing else.
STATE_SCRIPT = """
(function () {
  var payload = window.__SMARTPREP_GRID__ || { columns: [], rows: [] };
  var meta = window.__SMARTPREP_STATE__ || {};

  var state = {
    filters: [],
    rows: [],          // stable keys
    columns: [],
    hidden: [],        // columns hidden from the grid
    search: '',
    searchColumn: '*',
    quality: 'all',
    revision: 0
  };

  var listeners = [];

  // ---- filter evaluation, mirroring core/state.py exactly ----------------
  // The same ten comparisons, so a clause built here means what it means in
  // Python. Anything richer belongs in Python, not in a second dialect.
  function test(clause, cells, columnIndex) {
    var i = columnIndex[clause.column];
    if (i === undefined) { return false; }
    var raw = cells[i];
    var missing = raw === null || raw === undefined || raw === '';
    switch (clause.comparison) {
      case 'is_missing': return missing;
      case 'not_missing': return !missing;
    }
    if (missing) { return false; }
    var text = String(raw);
    switch (clause.comparison) {
      case 'eq': return text === String(clause.value);
      case 'ne': return text !== String(clause.value);
      case 'contains':
        return text.toLowerCase().indexOf(String(clause.value).toLowerCase()) >= 0;
      case 'in':
        return (clause.value || []).map(String).indexOf(text) >= 0;
    }
    var n = parseFloat(text), bound = parseFloat(clause.value);
    if (isNaN(n) || isNaN(bound)) { return false; }
    switch (clause.comparison) {
      case 'gt': return n > bound;
      case 'ge': return n >= bound;
      case 'lt': return n < bound;
      case 'le': return n <= bound;
    }
    return false;
  }

  var columnIndex = {};
  payload.columns.forEach(function (c, i) { columnIndex[c] = i; });

  function matchesFilters(row) {
    for (var i = 0; i < state.filters.length; i++) {
      if (!test(state.filters[i], row.cells, columnIndex)) { return false; }
    }
    return true;
  }

  function matchesSearch(row) {
    var term = (state.search || '').toLowerCase();
    if (state.quality === 'missing' &&
        row.flags.indexOf('missing') < 0) { return false; }
    if (state.quality === 'flagged' &&
        row.flags.indexOf('flagged') < 0) { return false; }
    if (!term) { return true; }
    if (state.searchColumn === '*') {
      return row.cells.some(function (v) {
        return String(v).toLowerCase().indexOf(term) >= 0;
      });
    }
    var i = columnIndex[state.searchColumn];
    return i !== undefined && String(row.cells[i]).toLowerCase().indexOf(term) >= 0;
  }

  function inView() {
    return payload.rows.filter(function (r) {
      return matchesFilters(r) && matchesSearch(r);
    });
  }

  var SP = {
    payload: payload,
    meta: meta,
    columnIndex: columnIndex,

    get state() { return state; },

    subscribe: function (fn) { listeners.push(fn); return fn; },

    update: function (mutate) {
      mutate(state);
      state.revision += 1;
      var view = inView();
      listeners.forEach(function (fn) { fn(state, view); });
    },

    inView: inView,

    // Row keys currently in view -- what "the selection" means when nothing
    // has been explicitly picked.
    viewKeys: function () {
      return inView().map(function (r) { return r.key; });
    },

    isSelected: function (key) {
      return state.rows.length === 0 || state.rows.indexOf(key) >= 0;
    },

    hasSelection: function () { return state.rows.length > 0; },

    addFilter: function (clause) {
      SP.update(function (s) {
        var already = s.filters.some(function (f) {
          return f.column === clause.column && f.comparison === clause.comparison &&
                 String(f.value) === String(clause.value);
        });
        if (!already) { s.filters = s.filters.concat([clause]); }
      });
    },

    removeFilter: function (i) {
      SP.update(function (s) {
        s.filters = s.filters.filter(function (_, j) { return j !== i; });
      });
    },

    clearAll: function () {
      SP.update(function (s) { s.filters = []; s.rows = []; s.columns = []; });
    },

    selectKeys: function (keys, additive) {
      SP.update(function (s) {
        if (!additive) { s.rows = keys.slice(); return; }
        var merged = s.rows.slice();
        keys.forEach(function (k) { if (merged.indexOf(k) < 0) { merged.push(k); } });
        s.rows = merged;
      });
    },

    toggleKey: function (key) {
      SP.update(function (s) {
        var at = s.rows.indexOf(key);
        if (at >= 0) { s.rows.splice(at, 1); } else { s.rows.push(key); }
      });
    },

    // The serialised state, in the shape core/state.py rebuilds from.
    export: function () {
      return {
        schema_version: 1,
        fingerprint: meta.fingerprint || '',
        filters: state.filters,
        selection: {
          rows: state.rows,
          columns: state.columns,
          stable: !!(meta.identity && meta.identity.stable),
          origin: 'studio'
        },
        active_specs: [],
        current_stage: 0,
        pending_treatment: null,
        review_context: meta.review_context || {},
        revision: state.revision
      };
    }
  };

  window.SP = SP;

  // ---- the link bar: what is filtered, what is selected -----------------
  var bar = document.getElementById('link-count');
  var chips = document.getElementById('filter-chips');
  var clear = document.getElementById('link-clear');
  var copy = document.getElementById('link-copy');

  var loaded = {};
  payload.rows.forEach(function (r) { loaded[r.key] = true; });

  function renderBar(s, view) {
    if (bar) {
      var selected = s.rows.length;
      // Charts are drawn from every row; the grid holds only the first page of
      // them. Selecting a bar can therefore name rows the grid cannot show, and
      // a count that quietly ignored them would read as "those rows are not
      // selected" rather than "those rows are not loaded here".
      var offscreen = s.rows.filter(function (k) { return !loaded[k]; }).length;
      bar.innerHTML = '<b>' + view.length.toLocaleString() + '</b> of <b>' +
        payload.rows.length.toLocaleString() + '</b> rows in view' +
        (selected ? ' · <b>' + selected.toLocaleString() + '</b> selected' : '') +
        (offscreen
          ? " <span class='warn-unstable'>(" + offscreen.toLocaleString() +
            ' beyond the rows loaded into this grid)</span>'
          : '');
    }
    if (chips) {
      if (!s.filters.length && !s.rows.length) {
        chips.innerHTML = "<span class='empty'>No filters. Click a bar, a point " +
          "or a cell to filter; click a row to select it.</span>";
      } else {
        chips.innerHTML = s.filters.map(function (f, i) {
          return "<span class='chip'><b>" + f.describe + "</b>" +
            "<button type='button' data-drop='" + i + "' aria-label='Remove filter: " +
            f.describe + "'>\\u00d7</button></span>";
        }).join('') + (s.rows.length
          ? "<span class='chip'><b>" + s.rows.length + " rows selected</b>" +
            "<button type='button' data-drop='rows' aria-label='Clear selection'>" +
            "\\u00d7</button></span>"
          : '');
      }
    }
    if (clear) { clear.disabled = !s.filters.length && !s.rows.length; }
  }

  if (chips) {
    chips.addEventListener('click', function (e) {
      var button = e.target.closest('button[data-drop]');
      if (!button) { return; }
      if (button.dataset.drop === 'rows') {
        SP.update(function (s) { s.rows = []; });
      } else {
        SP.removeFilter(parseInt(button.dataset.drop, 10));
      }
    });
  }
  if (clear) { clear.addEventListener('click', function () { SP.clearAll(); }); }
  if (copy) {
    copy.addEventListener('click', function () {
      var text = JSON.stringify(SP.export(), null, 2);
      if (navigator.clipboard) { navigator.clipboard.writeText(text); }
      copy.textContent = 'Copied';
      setTimeout(function () { copy.textContent = 'Copy view state'; }, 1400);
    });
  }

  SP.subscribe(renderBar);

  // ---- brushing: a mark knows the rows behind it ------------------------
  // Every datum carries the stable keys it was computed from, so clicking a
  // bar selects those rows rather than that position. Without the keys this
  // would be a highlight pretending to be a selection.
  document.addEventListener('click', function (e) {
    var mark = e.target.closest('[data-keys]');
    if (!mark) { return; }
    var keys = (mark.dataset.keys || '').split(',').filter(Boolean);
    if (!keys.length) { return; }
    SP.selectKeys(keys, e.shiftKey || e.metaKey || e.ctrlKey);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') { return; }
    var mark = e.target.closest('[data-keys]');
    if (!mark) { return; }
    e.preventDefault();
    var keys = (mark.dataset.keys || '').split(',').filter(Boolean);
    if (keys.length) { SP.selectKeys(keys, e.shiftKey); }
  });

  // Dim the marks outside the selection, everywhere at once. This is the
  // whole visible payoff of one shared state.
  SP.subscribe(function (s) {
    document.querySelectorAll('[data-keys]').forEach(function (mark) {
      var keys = (mark.dataset.keys || '').split(',').filter(Boolean);
      var on = !s.rows.length || keys.some(function (k) { return s.rows.indexOf(k) >= 0; });
      mark.classList.toggle('mark-dim', !on);
      mark.classList.toggle('mark-on', !!s.rows.length && on);
    });
  });

  SP.update(function () {});
})();
"""


#: The builder. Assembles a composition; shows the matching precomputed spec.
BUILDER_SCRIPT = """
(function () {
  var catalogue = window.__SMARTPREP_COMPOSITIONS__ ||
    { specs: {}, fields: [], recommendations: [] };
  var wells = document.getElementById('field-well');
  var out = document.getElementById('compose-out');
  if (!wells || !out || !window.SP) { return; }

  var choice = { x: null, y: null, aggregate: 'count' };

  function signature(c) {
    return [c.x || '', c.y || '', c.aggregate || 'count'].join('|');
  }

  function renderFields() {
    wells.innerHTML = "<h4>Fields</h4>" + catalogue.fields.map(function (f) {
      var blocked = f.blocked ? " aria-disabled='true' title='" + f.blocked + "'" : '';
      return "<div class='field' draggable='" + (f.blocked ? 'false' : 'true') +
        "' data-field='" + f.name + "' tabindex='0' role='button'" + blocked +
        " aria-label='" + f.name + ", " + f.kind +
        (f.blocked ? ', not plottable: ' + f.blocked : '') + "'>" +
        "<span>" + f.name + "</span><span class='k'>" + f.kind.slice(0, 4) + "</span></div>";
    }).join('');
  }

  function renderShelves() {
    ['x', 'y'].forEach(function (slot) {
      var shelf = document.getElementById('shelf-' + slot);
      if (!shelf) { return; }
      var value = choice[slot];
      shelf.innerHTML = "<span class='lbl'>" + (slot === 'x' ? 'First field' : 'Second field') +
        "</span>" + (value
          ? "<span class='val'>" + value + "</span> <button type='button' class='drop' " +
            "data-clear='" + slot + "' aria-label='Remove " + value + "'>\\u00d7</button>"
          : "<span class='k'>drop a field here, or select one and press " +
            (slot === 'x' ? '1' : '2') + "</span>");
    });
  }

  function draw() {
    var spec = catalogue.specs[signature(choice)];
    var why = document.getElementById('compose-why');
    if (!choice.x && !choice.y) {
      out.innerHTML = "<p class='lede'>Choose a field to begin.</p>";
      if (why) { why.textContent = ''; }
      return;
    }
    if (spec) {
      out.innerHTML = spec.svg + (spec.table || '');
      if (why) { why.textContent = spec.rationale || ''; }
    } else {
      // Honest about the single-file design: the page cannot run pandas, so
      // a combination nobody precomputed is answered with the line that
      // produces it rather than with a chart assembled in JavaScript.
      var call = "sp.compose(df, sp.fields_of(sp.profile(df)), sp.Composition(" +
        (choice.x ? "x='" + choice.x + "'" : '') +
        (choice.y ? ", y='" + choice.y + "'" : '') +
        (choice.aggregate !== 'count' ? ", aggregate='" + choice.aggregate + "'" : '') + '))';
      out.innerHTML = "<p class='lede'>That combination was not precomputed for this " +
        "page. The Studio does not aggregate in the browser, so nothing here can " +
        "invent it. In Python:</p><pre class='mono'>" + call + "</pre>";
      if (why) { why.textContent = ''; }
    }
    if (window.SP) { window.SP.update(function () {}); }
  }

  function set(slot, name) {
    var field = catalogue.fields.filter(function (f) { return f.name === name; })[0];
    if (!field || field.blocked) { return; }
    choice[slot] = name;
    renderShelves();
    draw();
  }

  // Drag and drop, and an exact keyboard equivalent. Both routes build the
  // same composition object -- an alternative that produces something
  // different is not an alternative.
  var dragging = null;
  wells.addEventListener('dragstart', function (e) {
    var field = e.target.closest('.field');
    if (!field || field.getAttribute('aria-disabled') === 'true') { return; }
    dragging = field.dataset.field;
    field.classList.add('dragging');
    e.dataTransfer.setData('text/plain', dragging);
  });
  wells.addEventListener('dragend', function (e) {
    var field = e.target.closest('.field');
    if (field) { field.classList.remove('dragging'); }
    dragging = null;
  });
  wells.addEventListener('keydown', function (e) {
    var field = e.target.closest('.field');
    if (!field) { return; }
    if (e.key === '1' || e.key === 'Enter') { e.preventDefault(); set('x', field.dataset.field); }
    if (e.key === '2') { e.preventDefault(); set('y', field.dataset.field); }
  });

  ['x', 'y'].forEach(function (slot) {
    var shelf = document.getElementById('shelf-' + slot);
    if (!shelf) { return; }
    shelf.addEventListener('dragover', function (e) {
      e.preventDefault();
      shelf.classList.add('over');
    });
    shelf.addEventListener('dragleave', function () { shelf.classList.remove('over'); });
    shelf.addEventListener('drop', function (e) {
      e.preventDefault();
      shelf.classList.remove('over');
      set(slot, e.dataTransfer.getData('text/plain') || dragging);
    });
    shelf.addEventListener('click', function (e) {
      var button = e.target.closest('button[data-clear]');
      if (!button) { return; }
      choice[button.dataset.clear] = null;
      renderShelves();
      draw();
    });
  });

  var aggregate = document.getElementById('compose-aggregate');
  if (aggregate) {
    aggregate.addEventListener('change', function () {
      choice.aggregate = aggregate.value;
      draw();
    });
  }

  var recs = document.getElementById('compose-recs');
  if (recs) {
    recs.innerHTML = catalogue.recommendations.map(function (r) {
      return "<button type='button' data-x='" + (r.composition.x || '') + "' data-y='" +
        (r.composition.y || '') + "' data-agg='" + (r.composition.aggregate || 'count') +
        "'>" + r.label + "<span class='why'>" + r.why + "</span></button>";
    }).join('');
    recs.addEventListener('click', function (e) {
      var button = e.target.closest('button[data-x]');
      if (!button) { return; }
      choice.x = button.dataset.x || null;
      choice.y = button.dataset.y || null;
      choice.aggregate = button.dataset.agg || 'count';
      if (aggregate) { aggregate.value = choice.aggregate; }
      renderShelves();
      draw();
    });
  }

  renderFields();
  renderShelves();
  draw();
})();
"""


#: The sandbox. Shows what each candidate would do; commits nothing.
SANDBOX_SCRIPT = """
(function () {
  var previews = window.__SMARTPREP_PREVIEWS__ || {};
  var pick = document.getElementById('sandbox-issue');
  var out = document.getElementById('sandbox-out');
  if (!pick || !out) { return; }

  function card(p) {
    if (p.refusal) {
      return "<div class='sandbox-card'><h4>" + p.treatment + "</h4>" +
        "<p class='refused'>Cannot be previewed \\u2014 " + p.refusal + "</p></div>";
    }
    var deltas = (p.deltas || []).filter(function (d) { return d.changed; });
    var examples = (p.examples || []).map(function (e) {
      return "<tr><td class='mono'>" + e.column + "</td><td class='mono'>" +
        (e.before || '\\u2014') + "</td><td class='mono'>" + (e.after || '\\u2014') +
        "</td></tr>";
    }).join('');
    return "<div class='sandbox-card'><h4>" + p.treatment + "</h4>" +
      "<p class='lede'>" + (p.description || '') + "</p>" +
      "<p class='delta'>" + p.cells_changed.toLocaleString() + " cells across " +
      p.rows_affected.toLocaleString() + " rows \\u00b7 repair confidence " +
      Math.round(p.repair_confidence * 100) + "% \\u00b7 " +
      (p.reversible ? 'reversible' : '<b>irreversible</b>') + "</p>" +
      (deltas.length
        ? "<p class='delta moved'>" + deltas.map(function (d) { return d.describe; })
            .slice(0, 6).join('<br>') + "</p>"
        : "<p class='delta'>No summary statistic moved.</p>") +
      (examples
        ? "<table><caption class='sr-only'>Example cells this treatment would " +
          "change</caption><thead><tr><th scope='col'>column</th>" +
          "<th scope='col'>before</th><th scope='col'>after</th></tr></thead>" +
          "<tbody>" + examples + "</tbody></table>"
        : '') +
      "</div>";
  }

  function draw() {
    var chosen = previews[pick.value];
    if (!chosen) { out.innerHTML = "<p class='lede'>Nothing to preview.</p>"; return; }
    out.innerHTML =
      "<div class='preview-banner'><b>Preview only.</b> Nothing here has been " +
      "applied and nothing here can be. Choose a treatment in <b>Guided</b> to " +
      "record a decision \\u2014 that is the only path that writes an audit " +
      "record.</div>" + chosen.map(card).join('');
  }

  pick.addEventListener('change', draw);
  draw();
})();
"""
