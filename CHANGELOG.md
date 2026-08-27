# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Planned

- Multi-backend execution (Polars, DuckDB, Arrow)
- Semantic and domain rule packs
- Benchmark suite
- Documentation site and plugin architecture

## [1.0.3] -- 2026-08-27

The 1.0.2 artefacts were rejected by PyPI and never published; this is the
same release under a number the index accepts. Everything below describes the
work that went into it.

Output built for people. No analytical change.

### The problem

The core knew everything worth reporting and had no way to say it. A notebook
cell showed this:

```text
Issue(id='MISS-STRUCTURAL-payment_date',
      category=<IssueCategory.STRUCTURAL_MISSINGNESS: 'structural_missingness'>,
      severity=<Severity.INFO: 0>, rule_source=<RuleSource.INFERRED...
```

The sentence that mattered -- *"5 of the missing payment_date values occur
where status is Pending or Overdue; absence is the correct encoding here"* --
was three lines further in, past two raw enum members.

### Added -- tables to journal convention

`smartprep.display.Table` renders to plain text, Markdown, HTML and **LaTeX
with booktabs**. The conventions are the ones journals enforce, for reasons
that outlive any house style: horizontal rules only, figures right-aligned so
the units digit sits under the units digit, one precision per column chosen
from the quantity rather than the float's accidental tail, and notes below the
foot rule.

`0.9500000000000001` prints as `95%`. Absence prints as a dash, because an
empty cell and a zero are different claims.

### Added -- views on every result

`.display(what)`, `.table(what)`, `.to_frame(what)` and `_repr_html_` on
`ScanResult`, `PreparationResult` and `AuditLog`, plus `result.explain()` for
why a run ended where it did. Views by severity, category, column, audit,
health, and what automatic mode declined.

**The view computes nothing.** Every figure comes from the object it
describes, and a test asserts the two agree -- a view that derives its own
count can disagree with its source, and then a reader has two numbers and no
way to choose.

The detection/repair distinction now appears side by side in every findings
table, with the note explaining it. It is the rule the library rests on, and
it was previously visible only to someone who knew to look for two similarly
named dataclass fields.

### Fixed

- **Severity printed as `5`.** It is an `IntEnum`, so a numeric check caught
  it before the enum formatter did. It reads `Blocking` now.
- **The same defect survived in `to_frame()`.** pandas coerces an `IntEnum` to
  `int64`, so an exported severity column came out as 0, 3, 1 -- which sorts
  correctly and tells the reader nothing. Enum columns now export as *ordered*
  categoricals: they print `High warning` and still compare in severity order
  rather than alphabetically, where "Critical review" would precede "Info".
  Found by running the library against a real 1,210-row ledger, which is where
  a presentation bug is supposed to be found.
- **Plain text could crash a Windows terminal.** Box-drawing characters and em
  dashes raise `UnicodeEncodeError` on a cp1252 console. Text output is
  transliterated to ASCII; HTML, Markdown and LaTeX keep the real characters.
- `<ScanResult issues=28 coverage=100%>` omitted the two numbers a reader
  needs to judge whether 28 is a lot. It now reports rows and columns.

### Not changed

`PreparationResult.show()` still opens the Studio. It is published behaviour,
and repurposing a shipped method is what a major version is for -- a table is
not worth one. The table view is `.display()`.

## [1.0.1] -- 2026-08-27

Packaging fix. The 1.0.0 artefacts were rejected by PyPI and never published,
so this is the first release to reach the index.

### Fixed

- **PyPI rejected the upload with a bare `400 Bad Request`.** The metadata
  carried both a `License-Expression` and a `License :: OSI Approved ::`
  classifier, which PEP 639 forbids: when an expression is present the
  classifiers are not allowed. `twine check --strict` passes on it, so the
  only symptom is a status code with no message. The classifier is gone, and
  a comment in `pyproject.toml` says why it must not come back.

No library code changed between 1.0.0 and 1.0.1.

## [1.0.0] -- 2026-08-27

**First published release.** The 0.1 through 0.8 entries below are the
development history, kept because the decisions in them are the ones this
library is built on -- none of those versions was ever published.

### The commitment

The public API is stable from here. Every name in `smartprep.__all__` is
supported, and removing or changing one requires a 2.0. That is enforced
rather than intended: `tests/public_api.json` records the surface and a test
fails if a name joins or leaves it, so the promise survives a refactor
somebody makes in a hurry.

What 1.0 does **not** claim is completeness. Multi-backend execution, semantic
rule packs, root-cause analysis and a documentation site are absent. They are
additions, and none of them changes the meaning of anything shipped here.

### Added -- learning validation rules

`sp.learn_rules()` infers a `ValidationPlan` from data believed to be good.
Every learned rule carries its evidence, a confidence and **what would falsify
it**, because a rule inferred from a sample is a statement about that sample
and becomes a claim about the world the moment it runs against new data.

The learner abstains rather than guesses: a level seen once does not close a
vocabulary, free text gets no rule, and fewer than fifty rows learns nothing.
It validates nothing itself -- the plan is meant to be read and edited, and a
learner that ran its own output would have removed the review step.

### Added -- the API is frozen against accident

`tests/public_api.json` records the public surface, and a test fails if a name
joins or leaves it. Before 1.0 the API may change; it may not change *by
accident*, and a removed export is invisible in a six-hundred-line diff.

### Added -- performance budgets

Eleven, marked `slow`. Not "how fast is it" -- those numbers mean nothing in
CI -- but "did this become quadratic": scan against rows, profiling against
columns, the Studio against both, blocking against pair count.

### Fixed -- a four-minute Studio

Building a Studio over fifty thousand rows took **267 seconds**. Every
precomputed chart called `profile()` on the *entire frame* to draw one column,
so the catalogue multiplied the cost of the data rather than adding to it. The
sandbox did the same for its before/after comparisons. Both now profile the
one column they draw. Down to ~45 seconds on twenty thousand rows, with a
budget test that fails if it regresses.

The workflow also re-scanned the whole frame before and after every stage,
when a stage's "before" is the previous stage's "after". Health is carried
forward.

### Fixed -- a block key that does not discriminate now refuses

Every company name beginning "Company" shares a prefix, so a ten-thousand-row
file became one block and fifty million comparisons. Blocking exists to
prevent exactly that, and the failure looked like a hang -- the worst way for
a library to say the key is wrong. It now raises immediately, naming the block
and suggesting a key whose values differ early.

### Fixed

- Two public enums, `IssueCategory` and `DriftSeverity`, shipped without
  docstrings; `help()` on them said nothing. A test now requires one on every
  public callable.
- `Series.skew()` is typed as returning any scalar the frame could hold.



Missingness mechanism, anomalies no single column can see, and one duplicated
panel removed.

### Added -- why values are missing

`sp.mechanism()` tests, for each column with missing values, whether any other
column predicts its absence. Mann-Whitney for numeric predictors, chi-square
for categorical, with a **Holm-Bonferroni correction** -- twenty columns give
a hundred and ninety pairs, and at a nominal 5% about ten are significant by
arithmetic alone. Without the correction every wide dataset is diagnosed MAR.

**It rules out MCAR and never claims MNAR.** That is a fact about the problem,
not a gap in the implementation: MAR and MNAR differ only in whether absence
depends on the value that is *missing*, and no test on observed data can see
an unobserved value. A library reporting "MNAR" would be reporting a domain
judgement as a measurement. Every report carries that caveat, and a test
asserts it does.

### Added -- outliers no fence can reach

`sp.anomalies()` finds two kinds the per-column IQR check structurally cannot:

- **Multivariate.** 1.90 m is ordinary, 56 kg is ordinary, and someone who is
  both sits a long way from everyone else. Mahalanobis distance against a
  chi-square cutoff at the 99.9th percentile -- at 95% one row in twenty is
  "anomalous", which is a list nobody reads.
- **Contextual.** 30 °C is unexceptional; in Reykjavik it is not. Robust
  within-group deviation, using the median absolute deviation rather than the
  standard deviation, because an outlier inflates the very spread being used
  to detect it.

Neither repairs anything. An outlier is a question about a row, not a defect
in it, and deleting one because it is far away is how a dataset loses its most
informative records.

### Changed -- Explore folded into Build

The two panels had grown into the same thing: pick a chart, look at it. Build
is field-driven, brushable and keyboard-first, so Explore's three unique chart
types -- ECDF, box and target-by-category -- moved into it and the duplicate
panel is gone. The Studio dropped from 471 KB to 440 KB, and a test asserts
none of the three chart types was lost in the move.

### Fixed

- **`Index.get_indexer` raises on a duplicated index**, which is ordinary
  after a concat, and returns the wrong row wherever several rows answer to
  one label. Both anomaly paths now resolve rows positionally. That is the
  fourth place this project has hit the same failure, and it now has
  regression tests in all four.
- `scipy` has no type stubs and is a required dependency, so mypy is
  configured to say so once rather than emit four permanent errors that train
  everyone to ignore the output.

## [0.8.0.dev0] -- 2026-08-26

Domain-aware preparation: time-series, panel data and entity resolution.

### Added -- three diagnostics that refuse to act (AD-021)

`sp.timeseries()`, `sp.panel()` and `sp.link()`. Each answers questions about
the *shape* of data rather than its values, and each produces ordinary `Issue`
objects rather than its own report type -- three parallel review queues, three
audit trails and three vocabularies is the cost nobody schedules.

**Time series.** Cadence, with how much of the series actually keeps it: a
daily series with gaps and a weekly one with noise both infer "daily", and
only the agreement figure separates them. Plus missing periods, duplicate
timestamps, ordering, mixed timezones, and stale runs -- a value repeating far
longer than the series suggests, which is usually a feed that stopped updating
rather than a quantity that stopped moving.

**Panels.** The within/between variance decomposition every panel estimator
depends on and few datasets are checked for. A constant-within regressor is
collinear with the entity fixed effect and drops out, taking its coefficient
with it; a *weakly* varying one is worse, because it stays in and returns an
estimate identified by almost nothing. Plus duplicate entity-time pairs
(blocking -- the index is not what it claims), balance, and a completeness
matrix.

**Linkage.** Candidate pairs with per-field evidence, each naming the
comparator it used. Nothing is merged and there is no threshold: at 0.85 two
branches of one company become one, at 0.86 they stay apart. The score orders
the queue; every pair is still decided, and `map_to_canonical` offers a
reversible alternative to an irreversible merge. Blocking costs recall, so the
report states how many pairs were never compared.

### Fixed -- two bugs found while building

- **A sentinel that never fired.** The stale-run scan guarded with
  `run_value is not object()`, which constructs a *new* object each call and
  is therefore always true. Replaced with a real module sentinel, and the
  closing sentinel now ends the final run -- without it a series that ends
  inside a stale stretch never reported one, which is the case a reader most
  wants.
- **NumPy integers were compared as text.** `np.int64` is not a Python `int`,
  so an `isinstance` check against the builtins alone sent every numeric
  column down the string path, where 1200 and 1205 score 75% instead of
  99.6%. Every linkage score on a numeric field was wrong.

## [0.7.0.dev0] -- 2026-08-26

Visual workflow and composition. The pipeline you can see, and the three
encoding channels that were declared but never drawn.

### Added -- the visual workflow and pipeline canvas (AD-018)

A preparation run as stages you can disable, reorder within the rules,
inspect, and export as readable Python.

**A node implements nothing.** Each stage selects the operations
`auto_prepare` would have run for its own issue categories and hands them to
the same executor, writing to the same audit log. Running every stage produces
the frame and the audit records `auto_prepare` produces -- asserted on both
the shipped fixture and the real 1,210-row workbook.

That is the whole safety claim. A visual pipeline is where a data tool usually
acquires a second execution engine, and from then on two answers have to be
reconciled by hand forever.

The canvas shows per-stage status, elapsed time, rows and cells changed,
findings resolved and **created**, health delta, and the audit operations each
stage wrote -- named rather than restated, so the audit stays the single
record. Type repair showing `health -0.5` is the point: parsing `"1,200.50"`
into a number is obviously right and *exposes* range violations that were
hidden inside strings.

- The stage order is enforced, not suggested. Rearranging into an order that
  would produce a wrong answer is refused with the reason -- a range check on
  the string `"1,200.50"` is meaningless.
- Every issue category belongs to exactly one stage, and an operation mapping
  to none raises rather than being skipped. A repair owned by no stage would
  never run, and the pipeline would quietly do less than automatic mode while
  looking complete.

### Added -- faceting (AD-019)

`ChartSpec.panels()` splits a faceted spec into one ordinary spec per group,
so every backend draws small multiples with the code it already had and three
implementations never exist to drift apart. Consequences worth stating:
brushing links across panels because a panel keeps its row keys; the panels
share one scale, because a grid with private axes is a grid nobody may
compare; and faceting an aggregate is refused, because aggregated rows no
longer line up with the frame and attaching the wrong groups would put points
in panels they do not belong to.

Twelve panels is the cap. More cannot be compared at a glance, which is the
only thing small multiples are for.

### Added -- multi-series, and the `size` channel

`color` carries a series across bars, scatters and lines with one group
ordering computed on the spec. `size` maps value to **area**, not radius,
because area is what the eye reads as magnitude -- scaling the radius makes a
doubled value look four times larger, which is the most common way a size
channel lies.

### Fixed -- a rule that should have existed three reviews ago (AD-020)

| Channel | Claimed | Did |
|---|---|---|
| `Mark` enum | eleven marks | three had no renderer |
| `interactive` | every chart interactive | nothing read it |
| `color` | a colour channel | one mark, one backend |
| `facet` | small multiples | nothing drew it |
| `size` | a size channel | nothing drew it |

Five instances of one failure, found by different reviewers months apart. The
rule now: **a channel a spec declares must change what every renderer draws,
or be refused with a reason.** A test enumerates the channels and fails on any
that is neither -- it found `size` within a minute of being written.

## [0.6.1.dev0] -- 2026-08-26

Documentation that a test can hold down, and two encoding channels that were
declared but not honoured.

### Fixed -- three documentation defects, all introduced in one sitting

- The README announced drag-and-drop composition and linked brushing as
  **Implemented** in one row and **Not yet** three rows below it. Both had
  been true, of different weeks.
- The visual workflow canvas appeared twice under two names.
- `CHANGELOG.md -> Planned` repeated four entries.

None of these were caught, because nothing tested documentation.

### Added -- a capability registry

`smartprep.capabilities` is now the single source of truth for what the
package can do, and the README's table is **generated** from it. A test checks
that every capability marked implemented names a real importable symbol, that
nothing marked planned already exists, and that the README has not drifted.

Four hand-written lists claiming the same facts is a job nobody schedules and
everybody loses. This is the same lesson as the `Mark` enum that declared
marks nothing could draw and the `interactive` flag no renderer read, applied
to prose instead of to code.

### Fixed -- `color` was declared everywhere and honoured almost nowhere

`ChartSpec.color` was read by exactly one mark in one renderer, and
`Composition.color` was accepted, validated, then silently dropped. A channel
one backend draws and another ignores is a chart that means two things.

Colour is now honoured by SVG, Matplotlib and Plotly, for bars, horizontal
bars and scatters, with the group ordering computed once on the spec -- so a
category is the same colour on screen, in a PDF and in a slide. A legend
meaning one thing in a report and another in a deck is worse than no legend.

### Fixed -- `facet` was declared and drawn by nothing

`compose()` now refuses a faceted composition, naming v0.7, and a `ChartSpec`
built with a facet by hand carries an annotation saying it is not drawn. A
facet that silently produced one panel would read as "faceting made no
difference to this data", which is a different and far more misleading claim
than "faceting did not happen".

### Added -- AD-017, Portable Studio and Live Studio

The builder's limitation is now a named architectural position rather than a
footnote. The page cannot run pandas, so it composes from precomputed specs;
putting an aggregation engine in the browser was **rejected, not deferred**,
because a number computed there has to be reconciled with the Python one
forever afterwards. The way out is a Live mode sharing the same `StudioState`,
`Composition`, `ChartSpec` and core operations -- the general case answered by
a round trip to the real engine rather than by a second one.

## [0.6.0.dev0] -- 2026-08-26

The visual analytics foundation: one interaction state, and the four surfaces
that share it.

### Added -- one shared interaction state (AD-015)

`StudioState` is defined in the core, before any of the visual features, and
every panel reads it and nothing else. Filter in the grid and the charts
narrow; click a bar and the rows behind it highlight everywhere at once.

Built surface by surface instead, each would grow its own answer to "what is
selected", and reconciling four almost-identical state models afterwards is
the work nobody schedules. It is a plain serialisable value: the browser sends
a view back, Python constructs the same view without a browser, and a view can
be diffed, logged and replayed.

A filter narrows a **view** and drops nothing — `state.view(df)` is a view in
English and a copy in pandas, so a caller who edits what they were shown
cannot reach the dataset.

### Added -- stable row identity

Drop three rows, sort by a column, or reset an index, and row 47 is a
different row. Selections carried as positions break in a way that is
invisible from outside: the highlight lands on the wrong records, and nobody
notices, because wrong rows still look like rows.

`StableRowIndex` derives the strongest identity a frame offers -- its unique
index, else a content hash, else position -- and **says which one it got**. A
positional identity is reported as not surviving transformation, exactly as a
sampled chart says it was sampled. The page cannot override this: identity
comes from the frame in hand, never from the payload.

Chart marks now carry the keys they were computed from, which is what makes
brushing a selection rather than a highlight.

### Added -- the visual builder

Drag a field onto a shelf, or focus one and press `1` or `2`. Both routes
build the same `Composition` -- an accessible alternative that builds
something different is not an alternative.

It refuses two things. A field with nine thousand levels does not become a bar
chart, and the refusal says what to do instead: a wall of unreadable labels is
worse than an empty panel. And it never recommends without explaining -- every
suggestion carries the sentence that justifies it.

The builder does not aggregate in the browser. Every combination the page can
show was composed in Python before the file was written; a combination nobody
precomputed is answered with the Python line that produces it. The Studio is
one file and cannot run pandas, and pretending otherwise would mean shipping a
second and worse implementation of it.

### Added -- the treatment sandbox (AD-016)

Every candidate repair, and what it would actually do: how many cells move,
which values, and what it costs the statistics you were about to reason from.
Parsing `1,200.50` is obviously right and still doubles the standard
deviation, which anyone choosing needs to know before they choose.

Imputation always improves completeness -- that is what it is for -- so the
spread and the distinct count are reported beside it: what a repair spends,
not only what it buys.

**A preview never applies anything and there is no way to make it.** No
`apply()`, no audit record, and the caller's frame is untouched. Committing
goes back through guided mode, the only path that records who decided and why.
Deliberate friction: a sandbox with a commit button is a second way to change
data, and the second way is always the one that skips the audit.

Preview and apply are the *same* operation over a copy, and a test asserts
they produce an identical frame and an identical cell count. A preview also
records the fingerprint of the frame it saw, because the same treatment after
three other repairs touches a different number of cells.

### Added -- smart grid 2.0 and cross-filtering

Multi-column sort, column show/hide, arrow-key row navigation, and
**alt-click a cell to filter the whole page on that value**. Filters appear as
removable chips naming themselves in words -- a filter nobody can read is a
filter nobody can check.

### Added -- accessibility

- **Every chart offers its numbers.** A picture is not an accessible format:
  alt text says what a chart is *about*, only the numbers say what it shows.
  Built from the same `spec.data` the renderer drew, so the table and the
  picture cannot disagree.
- **Contrast measured rather than eyeballed.** `--muted` and `--warn` were
  3.66:1 and 3.64:1, below AA. `--muted` carries every rationale, caption and
  fidelity note in the library -- which is to say it carries the caveats, and
  a caveat a reader cannot read is a caveat that was not given. Both now clear
  4.5:1, and a test measures it.
- Tooltips are reachable by keyboard, and dismissable with Escape.
- Brushable marks are focusable and operable with Enter or Space.

### Added -- three more invariants

The rules the v0.5.1 review named are now asserted rather than documented:
**Preview is not Apply**, **Profiling is not Repair**, and **no silent
destructive transformation** -- every applied change carries a reason, a
confidence and a rule source, and every refusal carries a reason too.

### Corrected

- **A date column was being blocked from every chart.** `identifier_like`
  fired on any nearly-all-distinct column, and a date column is nearly
  all-distinct because that is what dates are. It now applies to categoricals
  only, which is the only place the inference means anything.
- **Three places resolved a row by its index label.** A frame with a repeated
  index -- ordinary after a concat -- has several rows answering to the same
  label, so a label-keyed lookup silently resolved all of them to whichever
  came last. `selected_frame` returned rows the filters had excluded, a bar
  carried keys pointing into the wrong category, and a filtered scatter named
  unfiltered rows. All three now work positionally.

  This is the exact failure the identity layer exists to prevent, and it was
  inside the identity layer. It is invisible from outside: the wrong rows are
  still rows, the counts are still plausible, and nothing raises. Six
  regression tests now hold it down.
- **The Studio grew to 3.2 MB on a 1,210-row workbook.** Every precomputed
  chart is markup that ships inside the file, and two catalogues were built
  from a full cross product. Both are capped, dense scatters drop per-point
  hover text and selection -- twelve hundred focusable dots is a keyboard trap
  rather than keyboard access -- and a test now fails if the page grows past
  its budget. Down to ~1 MB, and the documented size was corrected: AD-013
  still claimed ~300 KB.
- Charts are drawn from every row while the grid loads the first 500, so a
  selection can name rows the grid cannot show. The link bar now says how
  many, instead of a count that reads as "those rows are not selected".

## [0.5.1.dev0] -- 2026-08-26

Architectural invariants asserted rather than documented, accessibility
basics, and a PDF a reader can navigate and cite.

### Fixed -- a field that claimed something nothing honoured

- **`ChartSpec.interactive: bool = True` was read by no code at all.** Every
  spec claimed to be interactive, including ones bound for a PDF, and nothing
  contradicted the claim because nothing consulted it. It is replaced by
  `interaction: Interaction` (`NONE`, `HOVER`, `EXPLORE`) -- a ceiling each
  renderer now genuinely honours, and a separate axis from `animation_field`
  (AD-014). A chart may be animated and static, interactive and unanimated,
  both, or neither, and all four are expressible.
- `spec.as_static()` lowers the ceiling once for print, so the PDF and
  PowerPoint publishers stop being places where a renderer could decide for
  itself what print means.

### Added -- the invariants have tests now

`tests/test_architecture_invariants.py` asserts the four rules that ordinary
feature tests cannot catch, because each is about two components agreeing
rather than one component working:

- **Core is not UI.** The same exported decisions replayed through the Studio
  and through `guided_prepare()` must produce an identical frame, identical
  waivers, an identical audit log and the same status. If cleaning logic ever
  drifted into the browser, this is the test that would fail.
- **The ChartSpec is the source of truth.** Every backend draws the same
  number of points from the same spec, reads the same title, and repeats the
  sampling caveat. A reader must never be able to tell which renderer drew a
  figure by comparing what it says.
- **Interaction is not animation.** All four combinations are constructible,
  and the ceiling is honoured: a static spec emits no hover markup, and
  Matplotlib renders a spec byte-identically whether its ceiling is `EXPLORE`
  or `NONE`, because paper cannot hover either way.
- **Charts come from EDA results, not from frames.** A histogram and the
  profile it was built from must agree on the row count.

### Added -- accessibility

- Charts announce themselves: `<title>` and `<desc>` as the first children of
  every SVG, carrying the rationale **and the sampling caveat**. A reader
  using a screen reader is exactly the reader who cannot see the footnote, and
  a sampled chart that reads as a full one is the most dangerous thing the
  library could say.
- Keyboard operation throughout: a skip link, visible focus rings, sortable
  grid headers reachable and operable by keyboard, selectable rows, and
  `aria-sort` so a screen reader learns the table was reordered rather than
  only the arrow changing.
- Quality overlays no longer signal with colour alone -- flagged and changed
  cells carry a marker and a weight as well as a wash.
- `prefers-reduced-motion` is honoured. Stage playback still works; it simply
  will not start on its own.

### Added -- stage walkthrough controls

Play **and pause**, a speed choice, a labelled button per step, and a live
region announcing "Step 3 of 5" with what changed. Motion a reader cannot stop
is motion imposed on them, and the walkthrough is the one place the library
moves at all.

### Added -- a PDF worth citing

Contents with real page numbers, a running header and footer on every page, a
caption under every figure naming what it shows and why it was drawn, table
continuation notes rather than silent truncation, and a methodology appendix
stating the four distinctions the library is built on -- so a reader holding
only the PDF does not have to have read the documentation to know that scan
coverage is not data health.

Numbering is computed in one pass from the deck, and regression tests follow a
contents entry to the page it names.

### Changed

- `pypdf` added to the `dev` extra: the export regression tests read the PDFs
  back, and a test-only dependency that is installed here but nowhere else is
  how the scipy gap happened.

## [0.5.0.dev0] -- 2026-08-26

Renderer backends, publishing, and an interactive Studio separated from the
archival report.

### Fixed -- overclaims

- **The `Mark` enum declared three marks nothing could draw.** `AREA`, `BOX`
  and `TEXT` fell through to a "no renderer" message. All three are now
  implemented, along with a proper `STEP` renderer, and a test asserts that no
  declared mark lacks one -- a public enum promising a mark nobody can render
  is the same class of dishonesty as a docstring promising a guarantee the code
  lacks.
- **AD-010 claimed the Studio was complete.** Against the Studio specification
  it is the MVP review workspace; drag-and-drop composition, linked brushing
  and the visual workflow canvas do not exist. Corrected, so nobody reads the
  status line as saying those are no longer required.
- The README no longer implies the report is interactive. Hover titles in SVG
  are a convenience; zoom and select are the tool, and those live in the
  Studio and the Plotly backend.

### Added -- renderer backends

- `to_matplotlib()` -- publication-quality static figures, and the route to
  PNG and PDF.
- `to_plotly()` -- genuine interactivity: zoom, pan, box and lasso select.
- `save_chart()` -- writes `.svg`, `.png`, `.pdf`, `.html` or `.json`, choosing
  the backend from the suffix. SVG still needs nothing installed.
- Both optional backends are imported lazily and, when absent, raise
  `BackendUnavailable` naming the install command rather than an `ImportError`
  from somewhere deep inside a report.

### Added -- chart builders

`box_chart` (whiskers clipped to the fences so one extreme cannot flatten every
box), `ecdf_chart` (no bin width to argue about), `scatter_chart`
(deterministically sampled above 3,000 points, and it says so), `target_chart`
(how the outcome moves across a feature's levels), `kpi_chart` and
`stage_chart`.

### Added -- publishing

- `result.publish(path)` -- PDF, PowerPoint, notebook, HTML or Markdown, chosen
  by suffix. Every format renders the same `ChartSpec` objects, so a figure in
  a slide cannot disagree with the one on screen.
- The notebook is runnable code that reproduces the analysis, not a transcript
  describing it. A report the reader can run is a report they can disagree
  with.
- Every deck carries "What auto mode did NOT do" as a slide, never an appendix.

### Added -- interactive Studio

- **Smart data grid** -- sortable, searchable, filterable, with per-cell
  quality overlays. The overlay is why it is not merely a table: a reader sees
  *where* a finding is rather than reading that one exists.
- **Chart explorer** -- choose a question; the column pairing decides the
  chart, so nobody has to justify a chart type the data has already implied.
- **Stage walkthrough** -- step or play through raw, repaired and
  by-dimension. The only animation admitted, because the frames are ordered
  steps of a real process.
- Tooltips across every rendered mark.

### Changed -- the report and the Studio are separate products (AD-013)

They were one artifact and the compromise hurt both. The archival HTML report
stays ~30 KB, script-free beyond navigation, and renders correctly years from
now. The Studio is ~300 KB with the interactive layer. Both draw the same
specs, so they cannot disagree. `HtmlDocument(interactive=...)` is the switch
and defaults to off, because the archival guarantee is the one that breaks
silently.

- New extras: `smartprep[viz]` for matplotlib and plotly, `smartprep[pptx]`
  for PowerPoint. The core still draws its own charts with neither.

## [0.4.0.dev0] -- 2026-08-26

Four correctness fixes, then the EDA, visualization, HTML and Studio layers.

### Fixed -- correctness

These were all cases where the library did something different from what it
said, which is the failure mode the whole design exists to avoid.

- **Target encoding was not cross-fitted**, despite a docstring claiming
  leave-one-out. It built one mean per category from the whole training set and
  applied it to every row in that category, so each row's own outcome sat
  inside the number encoding it. Now genuinely cross-fitted:
  ``fit_transform`` returns out-of-fold values, ``transform`` uses the
  full-data mapping, and the asymmetry is documented. The plain variant remains
  available as ``smoothed_mean_target``, named for what it is.
- **``quantile_rank`` turned NaN into 1.0.** ``searchsorted`` places NaN past
  every element, so a missing value silently became the top quantile -- a
  fabricated extreme observation. Every scaler now preserves the missing mask,
  asserted for all seven.
- **``allow_extra_columns`` was declared and never enforced.** A contract
  inferred from one column validated a frame with two as passing, so the
  contract did not mean what it said.
- **The privacy scanner missed low-rate PII.** One email in ten free-text rows
  reported nothing, because column classification and cell detection ran off a
  single threshold. They are now separate: a column needs a majority to be
  *typed* as PII, but one confirmed match is enough to report that PII is
  present.
- The license contradiction is resolved: AD-011 now records Apache-2.0 as
  frozen, matching what every build has shipped.
- **scipy was an undeclared dependency.** pandas delegates `Series.skew()` and
  `Series.kurtosis()` to scipy, and the EDA profile computes both for every
  numeric column. The development environment happened to have scipy, so the
  tests passed while a clean install of the package crashed on `profile()`.
  Now declared. CI additionally installs the built wheel into a clean
  environment and runs the shipped suite there, because testing only against
  the repo checkout is exactly what hid this.

### Added -- EDA engine

Backend objects, serialisable, usable from Python with no interface.

- ``profile()`` -- dataset and per-column profiles with numeric, categorical,
  datetime and text summaries, histograms, ECDFs, and identifier/constant
  detection. NaN and Infinity serialise as null rather than producing JSON
  nothing else can read.
- ``associations()`` -- Spearman, Cramer's V (bias-corrected) and the
  correlation ratio, each applied where it belongs. A Pearson-only matrix drops
  categorical columns and implies they carry no signal.
- ``missingness()`` -- co-missingness and pattern analysis, because two columns
  absent on the same rows usually share one upstream cause.
- ``compare_profiles()`` -- before/after with statistical guardrails: variance
  shrinkage, mean shift, merged categories and row loss are flagged as red
  flags rather than left for the reader to notice.

### Added -- visualization

- ``ChartSpec`` -- a chart described as data. Writing charts against a plotting
  library binds them to one output format; writing them three times guarantees
  the three drift apart.
- Chart builders that are **diagnostic-driven**: a histogram is chosen because
  the column is skewed, not because it is a float. Every chart carries a
  ``rationale``, and every chart states its ``Fidelity`` so a reader never
  assumes they are seeing every point.
- ``render_svg()`` -- a built-in renderer with no plotting dependency, so a
  report can always draw its own charts. Escapes cell values, carries hover
  titles and an accessible label.

### Added -- reporting and Studio

- ``result.report(kind, fmt="html")`` -- self-contained HTML with no CDN and no
  build step. A report that needs a network stops working the moment it is
  archived.
- ``sp.studio(df)`` -- the interactive workspace: overview, profile, EDA,
  issue inbox, guided decision cards and the audit timeline. Renders inline in
  a notebook, saves to a file, or opens in a browser.
- **The Studio applies nothing in the browser.** Decisions recorded there are
  exported as the same JSON that ``guided_prepare(decisions=...)`` replays, so
  the interface can never become a second implementation of cleaning and no
  click is unreproducible.

### Changed

- A mostly-datetime column is now profiled as datetime rather than text.
  Requiring purity lost range, frequency and gap analysis exactly when a column
  has unparsed values -- when they matter most.
- Category-merge detection triggers at halved-or-more distinct values; exactly
  halved is the commonest real case, since merging case variants collapses each
  pair into one.
- ``ScanResult.report()`` and ``PreparationResult.report()`` take a format, and
  ``export_report()`` infers it from the file suffix.

## [0.3.0.dev0] -- 2026-08-26

Guided mode, preprocessing, validation, privacy and drift. Cleaning is no
longer the only thing the library does.

### Added

**Guided mode**

- `guided_prepare()` returns a `GuidedSession` -- the questions are exactly
  what auto mode refused to decide, so the two are one engine rather than two.
- Decision cards carrying evidence, the reasons auto mode abstained, and only
  those treatments that can actually be carried out.
- Questions ordered by dependency then urgency: asking about an outlier in a
  column still stored as text asks about a number nobody has computed.
- `QuestionLevel` from `minimal` to `expert`, so a three-decision review and a
  forty-decision review differ by level rather than by tool.
- Decisions are data: `export_decisions()` / `load_decisions()` replay a
  reviewed session on new data and reproduce the same output.
- `result.open_guided()` continues an automatic run without restarting the
  analysis.

**Preprocessing** -- deliberately separate from cleaning, and never run inside
`auto_prepare()`

- `Preprocessor` with fit/transform discipline: 8 imputation methods, 5
  encoders, 7 scalers, missing indicators.
- Leakage guard: target encoding, sequential fills that read the future, and
  features that correlate with the target above 0.98 are all flagged with a
  remedy.
- `recommend_preprocessing()` proposes a pipeline from cardinality, skew,
  missing rate and analysis goal, with a reason and rejected alternatives for
  every step. Econometrics and EDA goals decline to scale or encode at all.

**Validation and contracts**

- `ValidationPlan` -- chainable rules, graded PASS/WARNING/ERROR/CRITICAL
  against configurable thresholds, with every rule run so one failure cannot
  hide another.
- `result.split()` sunders passing from failing rows.
- `DataContract.infer()` proposes a contract from reviewed data;
  `.diff()` classifies changes as backward-compatible, forward-compatible,
  breaking or **semantically** breaking.
- YAML and JSON export without adding a dependency.

**Privacy**

- `PrivacyScanner` with checksum and range validation, not regex alone -- a
  16-digit order reference is neither a card number nor a phone number.
- Re-identification risk through quasi-identifier combinations, reported
  separately from whether a direct identifier was found.
- `mask`, `redact`, `hash_value`, `pseudonymise`, `generalise`.
- Every report states that detection cannot prove absence.

**Drift**

- PSI, KS, Jensen-Shannon, missingness drift and schema drift, with a ranked
  attribution rather than a boolean.
- `cleaning_drift()` -- if the *problems* change between batches, the cause is
  upstream and no local rule will fix it.

### Changed

- A date column held entirely as text is now detected and parsed. The
  mixed-representation detector could not see it: a column that is *entirely*
  strings has only one representation, so nothing looked mixed.
- Waived findings no longer hold the completion status at `BLOCKED`. A waiver
  is a recorded human decision, and refusing to accept it meant the library
  never accepted an answer it had asked for.
- `parse_datetime_unambiguous` no longer scales its confidence by how much of
  the column was already clean.

### Fixed

- The auto-to-guided handoff reused the completed audit log, replaying its
  applied records into the second run and doubling every count.
- A closure in group-wise imputation captured the loop variable, so every
  column would have used the last column's statistics.

## [0.2.0.dev0] -- 2026-08-26

Diagnosis-only becomes a preparation engine. Repairs are applied, recorded and
reversible; nothing ambiguous is touched.

### Added

- `auto_prepare()` -- scan, apply only what is provably safe, re-scan what those
  repairs invalidated, and report what was refused.
- `clean()` -- convenience alias. Not a more aggressive mode; warns on stderr
  when findings remain.
- `PreparationResult` -- raw/clean/verified frames, review queue, health before
  and after, audit, plan, snapshots, reports.
- `Operation` and `RepairPlan` -- the only path through which data changes.
  Operations declare a scope, and the scope determines which detectors their
  change invalidates.
- Transactional execution: every operation snapshots first, and a failure
  restores rather than leaving the frame half-changed.
- `AuditLog` -- records refusals alongside changes, with fingerprints on both
  sides and the reason automatic mode abstained.
- `DataHealthScore` -- five independent dimensions, unweighted overall, with the
  contributing issue ids named per dimension.
- `verified_df`, `finalize()` and audited waivers (AD-004).
- Markdown reports: pre-cleaning, post-cleaning and before/after comparison.
  Every preparation report carries a mandatory "What auto mode did NOT do".
- JSON serialisation for `Issue`, `ScanResult` and `PreparationResult`, each
  carrying a `schema_version`.
- Detector applicability protocol -- "could not run" is now distinct from "ran
  and found nothing", which is what makes a coverage figure mean anything.
- `strict=True` on `scan()` -- raise on detector failure rather than silently
  reducing coverage.
- Progress callbacks and per-detector timings.
- `RowSet` -- findings carry both index positions and index labels, so a
  non-default index cannot mislead.
- A deterministic 42-row fixture that ships with the package, exercising all 14
  detectors. 120 of 182 tests now run without external data.

### Changed

- `ScanResult.get()` raises `KeyError` naming the available ids, instead of a
  bare `StopIteration` surfacing far from the mistake.
- `ScanResult.find()` filters by category, column, severity and repair class.
- Missingness recommends `record_only` rather than adding an indicator column;
  adding a column silently alters the schema, and imputation is a modelling
  decision.
- `parse_datetime_unambiguous` confidence now reflects confidence in the
  conversion rather than the share of the column that was already clean. The
  old formula gated a deterministic parse on an unrelated fact.
- Version bumped to 0.2.0.dev0.

### Fixed

- `.github/` is now included in the sdist.
- Fixed seven type errors surfaced by strict mypy, including an unchecked
  `Optional` dereference in the geography detector.

## [0.1.0.dev0] -- 2026-08-26

First development release. Diagnosis layer only; no repair is applied.

### Added

- `sp.scan()` -- full applicable scan with a no-mutation guarantee enforced at
  runtime.
- Issue model: `Issue`, `Evidence`, `TreatmentCandidate`, with detection
  confidence and repair confidence held as separate fields.
- Confidence policy (`ConfidenceLadder`) and multi-factor eligibility
  (`classify`), combining repair confidence with severity, reversibility,
  information-loss risk, domain sensitivity and statistical impact.
- Canonical entity graph for geographic reference data, with aliases,
  transliterations, language variants and historical names.
- Date interpretation separating invalid, ambiguous, format-conflicting and
  unambiguous values.
- Fourteen detectors across structural, temporal, textual, numeric and
  cross-field categories.
- Acceptance suite of 81 tests, including negative controls asserting what must
  not be flagged.

### Design decisions

- Irreversible operations can never be classified `SAFE_AUTO_FIX`, at any
  confidence.
- Scan coverage and data health are reported as separate measures; 100%
  coverage never implies correct data.
- Invalid dates are reported with no treatment candidate rather than a guess.
